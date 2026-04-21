"""
CRM Sales Campaign Agent
Handles: Dataset loading → Segmentation → Campaign generation → Execution → Tracking
"""

import csv
import io
import uuid
import random
import json
from datetime import datetime, timedelta
from typing import Optional
from collections import Counter

from shared.prompt_engine import PromptEngine
from shared.memory import MemoryStore
from shared.email_service import EmailService


# ---------------------------------------------------------------------------
# Segmentation strategies
# ---------------------------------------------------------------------------

def rule_based_segmentation(users: list) -> dict:
    """
    Rule-based segmentation into 3 groups:
    - Active: last activity within 30 days
    - Dormant: no activity in 90+ days
    - High-intent: recent activity + high engagement signals
    """
    segments = {"active": [], "dormant": [], "high_intent": []}
    now = datetime.now()

    for user in users:
        last_activity = user.get("last_activity", "")
        if isinstance(last_activity, str) and last_activity:
            try:
                last_dt = datetime.strptime(last_activity, "%Y-%m-%d")
            except ValueError:
                last_dt = now - timedelta(days=60)
        else:
            last_dt = now - timedelta(days=60)

        days_inactive = (now - last_dt).days

        # Engagement signals
        page_views = int(user.get("page_views", 0))
        sessions = int(user.get("sessions", 0))
        purchases = int(user.get("purchases", 0))
        engagement_score = page_views * 0.3 + sessions * 0.5 + purchases * 5

        # Segmentation rules
        if days_inactive <= 30 and engagement_score >= 15:
            segments["high_intent"].append(user)
        elif days_inactive <= 30:
            segments["active"].append(user)
        elif days_inactive >= 90:
            segments["dormant"].append(user)
        else:
            # 31-89 days — classify by engagement
            if engagement_score >= 10:
                segments["active"].append(user)
            else:
                segments["dormant"].append(user)

    return segments


def ml_segmentation(users: list) -> dict:
    """
    ML-based segmentation using K-Means clustering on engagement features.
    Falls back to rule-based if sklearn is unavailable.
    """
    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        import numpy as np
    except ImportError:
        print("⚠️  sklearn not available. Falling back to rule-based segmentation.")
        return rule_based_segmentation(users)

    now = datetime.now()

    # Build feature matrix
    features = []
    for user in users:
        last_activity = user.get("last_activity", "")
        try:
            last_dt = datetime.strptime(last_activity, "%Y-%m-%d")
            days_inactive = (now - last_dt).days
        except (ValueError, TypeError):
            days_inactive = 60

        features.append([
            days_inactive,
            int(user.get("page_views", 0)),
            int(user.get("sessions", 0)),
            int(user.get("purchases", 0)),
        ])

    X = np.array(features)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # K-Means with 3 clusters
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)

    # Map clusters to meaningful segment names by analyzing centroids
    cluster_stats = {}
    for i in range(3):
        mask = labels == i
        cluster_stats[i] = {
            "avg_days_inactive": float(np.mean(X[mask, 0])),
            "avg_page_views": float(np.mean(X[mask, 1])),
            "avg_sessions": float(np.mean(X[mask, 2])),
            "avg_purchases": float(np.mean(X[mask, 3])),
            "count": int(np.sum(mask)),
        }

    # Assign labels: most inactive = dormant, most engaged = high_intent, rest = active
    sorted_clusters = sorted(cluster_stats.keys(),
                             key=lambda c: cluster_stats[c]["avg_days_inactive"])

    label_map = {
        sorted_clusters[0]: "high_intent",  # least inactive (most recent)
        sorted_clusters[1]: "active",
        sorted_clusters[2]: "dormant",       # most inactive
    }

    # Refine: among the least inactive, the one with highest engagement = high_intent
    if cluster_stats[sorted_clusters[0]]["avg_purchases"] < cluster_stats[sorted_clusters[1]]["avg_purchases"]:
        label_map[sorted_clusters[0]] = "active"
        label_map[sorted_clusters[1]] = "high_intent"

    segments = {"active": [], "dormant": [], "high_intent": []}
    for user, label in zip(users, labels):
        segment_name = label_map[label]
        segments[segment_name].append(user)

    return segments, cluster_stats


class CRMAgent:
    """
    Autonomous CRM Sales Campaign Agent.
    Manages segmentation, campaign generation, execution, and tracking.
    """

    def __init__(self, prompt_engine: PromptEngine, memory: MemoryStore,
                 email_service: EmailService):
        self.ai = prompt_engine
        self.memory = memory
        self.email = email_service
        self.segments = {}
        self.segmentation_method = "rule_based"  # or "ml"
        print("📊 CRMAgent initialized")

    # -------------------------------------------------------------------
    # 1. Dataset Loading
    # -------------------------------------------------------------------

    def parse_user_csv(self, csv_content: str) -> list:
        """Parse CRM user dataset from CSV."""
        reader = csv.DictReader(io.StringIO(csv_content))
        users = []
        for row in reader:
            user = {
                "name": row.get("Name", row.get("name", "")).strip(),
                "email": row.get("Email", row.get("email", "")).strip(),
                "last_activity": row.get("Last Activity", row.get("last_activity", "")).strip(),
                "page_views": int(row.get("Page Views", row.get("page_views", 0)) or 0),
                "sessions": int(row.get("Sessions", row.get("sessions", 0)) or 0),
                "purchases": int(row.get("Purchases", row.get("purchases", 0)) or 0),
                "plan": row.get("Plan", row.get("plan", "free")).strip(),
            }
            if user["name"] and user["email"]:
                users.append(user)
        return users

    def load_users(self, users: list):
        """Store parsed users into memory."""
        for user in users:
            self.memory.upsert_contact(
                agent_type="crm",
                email=user["email"],
                name=user["name"],
                state="new",
                metadata={
                    "last_activity": user["last_activity"],
                    "page_views": user["page_views"],
                    "sessions": user["sessions"],
                    "purchases": user["purchases"],
                    "plan": user["plan"],
                },
            )
        return len(users)

    # -------------------------------------------------------------------
    # 2. Segmentation
    # -------------------------------------------------------------------

    def segment_users(self, users: list, method: str = "rule_based") -> dict:
        """
        Segment users into Active, Dormant, and High-Intent groups.
        Supports rule-based and ML (K-Means) methods.
        """
        self.segmentation_method = method
        cluster_stats = None

        if method == "ml":
            result = ml_segmentation(users)
            if isinstance(result, tuple):
                self.segments, cluster_stats = result
            else:
                self.segments = result
        else:
            self.segments = rule_based_segmentation(users)

        # Update contact segments in memory
        for segment_name, segment_users in self.segments.items():
            for user in segment_users:
                self.memory.upsert_contact(
                    agent_type="crm",
                    email=user["email"],
                    name=user["name"],
                    segment=segment_name,
                    state="segmented",
                    metadata={
                        "last_activity": user.get("last_activity", ""),
                        "page_views": user.get("page_views", 0),
                        "sessions": user.get("sessions", 0),
                        "purchases": user.get("purchases", 0),
                        "plan": user.get("plan", "free"),
                    },
                )

        summary = {
            "method": method,
            "segments": {k: len(v) for k, v in self.segments.items()},
            "total_users": sum(len(v) for v in self.segments.values()),
        }
        if cluster_stats:
            summary["cluster_analysis"] = cluster_stats

        return summary

    # -------------------------------------------------------------------
    # 3. Campaign Generation
    # -------------------------------------------------------------------

    def generate_campaign_messages(self, segments: dict = None) -> dict:
        """Generate AI-powered campaign messages for each segment."""
        segments = segments or self.segments
        campaigns = {}

        # Feature list for active users (randomly pick)
        features = ["AI Campaign Builder", "Smart Segmentation", "Auto Follow-ups",
                     "CRM Dashboard", "Email Templates", "Analytics Suite"]

        for segment_name, users in segments.items():
            template_name = f"crm_campaign_{segment_name}"
            sample_users = users[:5] if len(users) > 5 else users  # Generate for a sample

            messages = []
            for user in sample_users:
                context = {
                    "user_name": user["name"],
                    "last_activity": user.get("last_activity", "a while ago"),
                }

                if segment_name == "active":
                    context["feature_used"] = random.choice(features)
                elif segment_name == "dormant":
                    context["previous_engagement"] = f"{user.get('sessions', 0)} sessions, {user.get('purchases', 0)} purchases previously"
                elif segment_name == "high_intent":
                    context["intent_signals"] = f"{user.get('page_views', 0)} page views, {user.get('sessions', 0)} sessions, {user.get('purchases', 0)} purchases recently"

                raw = self.ai.generate(template_name, context)
                subject, body = self._parse_email_output(raw)

                messages.append({
                    "to_email": user["email"],
                    "to_name": user["name"],
                    "subject": subject,
                    "body": body,
                    "segment": segment_name,
                })

            campaigns[segment_name] = {
                "segment_size": len(users),
                "messages_generated": len(messages),
                "sample_messages": messages,
            }

        return campaigns

    def _parse_email_output(self, raw: str) -> tuple:
        """Parse SUBJECT: / BODY: format from LLM output."""
        subject = ""
        body = raw
        lines = raw.strip().split("\n")
        body_start = 0

        for i, line in enumerate(lines):
            if line.strip().upper().startswith("SUBJECT:"):
                subject = line.split(":", 1)[1].strip()
            elif line.strip().upper().startswith("BODY:"):
                body_start = i + 1
                break

        if body_start > 0:
            body = "\n".join(lines[body_start:]).strip()
        if not subject:
            subject = "A message from TruBot AI"

        return subject, body

    # -------------------------------------------------------------------
    # 4. Campaign Execution
    # -------------------------------------------------------------------

    def run_campaign(self, campaign_name: str = None, method: str = "rule_based",
                     users: list = None) -> dict:
        """
        Full campaign execution pipeline:
        Segment → Generate → Send → Track
        """
        campaign_id = f"crm_{uuid.uuid4().hex[:8]}"
        campaign_name = campaign_name or f"CRM Campaign {datetime.now().strftime('%Y-%m-%d')}"

        if not self.segments and users:
            self.segment_users(users, method=method)

        total_users = sum(len(v) for v in self.segments.values())

        # Create campaign
        self.memory.create_campaign(
            campaign_id=campaign_id,
            agent_type="crm",
            name=campaign_name,
            total_recipients=total_users,
        )

        # Generate messages
        campaign_messages = self.generate_campaign_messages()

        # Send messages (or simulate)
        total_sent = 0
        all_results = []

        for segment_name, data in campaign_messages.items():
            segment_users = self.segments.get(segment_name, [])

            for msg in data["sample_messages"]:
                send_result = self.email.send_email(
                    to_email=msg["to_email"],
                    subject=msg["subject"],
                    body=msg["body"],
                    to_name=msg["to_name"],
                    metadata={"campaign_id": campaign_id, "segment": segment_name},
                )

                self.memory.store_message(
                    agent_type="crm",
                    recipient_email=msg["to_email"],
                    recipient_name=msg["to_name"],
                    subject=msg["subject"],
                    body=msg["body"],
                    campaign_id=campaign_id,
                    message_type="campaign",
                    metadata={"segment": segment_name},
                )

                self.memory.update_contact_state("crm", msg["to_email"], "contacted")
                self.memory.increment_messages_sent("crm", msg["to_email"])

                if send_result["status"] == "sent":
                    total_sent += 1

                all_results.append({
                    "name": msg["to_name"],
                    "email": msg["to_email"],
                    "segment": segment_name,
                    "subject": msg["subject"],
                    "status": send_result["status"],
                })

        # Update campaign stats
        self.memory.update_campaign_stats(
            campaign_id, status="completed", sent_count=total_sent
        )

        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "segmentation_method": self.segmentation_method,
            "segments": {k: len(v) for k, v in self.segments.items()},
            "total_sent": total_sent,
            "messages": campaign_messages,
            "send_results": all_results,
        }

    # -------------------------------------------------------------------
    # 5. Tracking Simulation
    # -------------------------------------------------------------------

    def simulate_tracking(self, campaign_id: str = None) -> dict:
        """
        Simulate email tracking metrics per segment.
        Returns open rates, click rates, and conversions.
        """
        tracking = {}
        total_stats = {"opens": 0, "clicks": 0, "conversions": 0, "total_sent": 0}

        for segment_name, users in self.segments.items():
            count = len(users)
            stats = self.email.simulate_tracking(count, segment_name)
            tracking[segment_name] = stats

            total_stats["opens"] += stats["opens"]
            total_stats["clicks"] += stats["clicks"]
            total_stats["conversions"] += stats["conversions"]
            total_stats["total_sent"] += count

        # Update campaign stats if we have a campaign_id
        if campaign_id:
            campaigns = self.memory.get_campaigns(agent_type="crm")
            if campaigns:
                cid = campaign_id or campaigns[0]["campaign_id"]
                self.memory.update_campaign_stats(
                    cid,
                    open_count=total_stats["opens"],
                    click_count=total_stats["clicks"],
                    conversion_count=total_stats["conversions"],
                )

        # Overall rates
        total = total_stats["total_sent"] or 1
        tracking["overall"] = {
            "total_sent": total_stats["total_sent"],
            "total_opens": total_stats["opens"],
            "total_clicks": total_stats["clicks"],
            "total_conversions": total_stats["conversions"],
            "open_rate": round(total_stats["opens"] / total * 100, 1),
            "click_rate": round(total_stats["clicks"] / total * 100, 1),
            "conversion_rate": round(total_stats["conversions"] / total * 100, 1),
        }

        return tracking

    # -------------------------------------------------------------------
    # Stats
    # -------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Get CRM agent statistics."""
        contacts = self.memory.get_contacts(agent_type="crm")
        campaigns = self.memory.get_campaigns(agent_type="crm")
        messages = self.memory.get_messages(agent_type="crm")

        segment_counts = Counter(c.get("segment", "unknown") for c in contacts)
        state_counts = Counter(c.get("state", "unknown") for c in contacts)

        return {
            "total_users": len(contacts),
            "total_campaigns": len(campaigns),
            "total_messages": len(messages),
            "segment_breakdown": dict(segment_counts),
            "state_breakdown": dict(state_counts),
        }
