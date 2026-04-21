"""
Fundraising Campaign Agent
Handles: CSV upload → email generation → campaign execution → follow-ups → response classification
"""

import csv
import io
import uuid
import json
import random
from datetime import datetime, timedelta
from typing import Optional

from shared.prompt_engine import PromptEngine
from shared.memory import MemoryStore
from shared.email_service import EmailService


class FundraisingAgent:
    """
    Autonomous Fundraising Campaign Agent.
    Manages the full lifecycle of investor outreach campaigns.
    """

    def __init__(self, prompt_engine: PromptEngine, memory: MemoryStore,
                 email_service: EmailService):
        self.ai = prompt_engine
        self.memory = memory
        self.email = email_service
        print("🚀 FundraisingAgent initialized")

    # -------------------------------------------------------------------
    # 1. CSV Upload & Parsing
    # -------------------------------------------------------------------

    def parse_investor_csv(self, csv_content: str) -> list:
        """
        Parse investor CSV data.
        Expected columns: Investor Name, Email, Firm, Investment Focus
        """
        reader = csv.DictReader(io.StringIO(csv_content))
        investors = []
        for row in reader:
            investor = {
                "name": row.get("Investor Name", row.get("name", "")).strip(),
                "email": row.get("Email", row.get("email", "")).strip(),
                "firm": row.get("Firm", row.get("firm", "")).strip(),
                "investment_focus": row.get("Investment Focus",
                                           row.get("investment_focus", "")).strip(),
            }
            if investor["name"] and investor["email"]:
                investors.append(investor)

        return investors

    def load_investors(self, investors: list, campaign_id: str = None):
        """Store parsed investors into the memory layer."""
        for inv in investors:
            self.memory.upsert_contact(
                agent_type="fundraising",
                email=inv["email"],
                name=inv["name"],
                state="new",
                metadata={"firm": inv["firm"], "investment_focus": inv["investment_focus"]},
            )
        return len(investors)

    # -------------------------------------------------------------------
    # 2. Personalized Email Generation
    # -------------------------------------------------------------------

    def generate_emails(self, investors: list) -> list:
        """
        Generate personalized outreach emails for each investor using the AI layer.
        """
        generated = []
        for inv in investors:
            raw = self.ai.generate("investor_outreach", {
                "investor_name": inv["name"],
                "firm": inv["firm"],
                "investment_focus": inv["investment_focus"],
            })

            # Parse the generated email
            subject, body = self._parse_email_output(raw)

            generated.append({
                "to_email": inv["email"],
                "to_name": inv["name"],
                "firm": inv["firm"],
                "subject": subject,
                "body": body,
                "raw_output": raw,
            })

        return generated

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
            subject = "TruBot AI – Investor Outreach"

        return subject, body

    # -------------------------------------------------------------------
    # 3. Campaign Execution
    # -------------------------------------------------------------------

    def run_campaign(self, investors: list, campaign_name: str = None) -> dict:
        """
        Full campaign execution: generate emails → send → track.
        Returns campaign results.
        """
        campaign_id = f"fund_{uuid.uuid4().hex[:8]}"
        campaign_name = campaign_name or f"Fundraising Campaign {datetime.now().strftime('%Y-%m-%d')}"

        # Create campaign record
        self.memory.create_campaign(
            campaign_id=campaign_id,
            agent_type="fundraising",
            name=campaign_name,
            total_recipients=len(investors),
        )

        # Load investors into memory
        self.load_investors(investors, campaign_id)

        # Generate personalized emails
        emails = self.generate_emails(investors)

        # Send emails
        sent_count = 0
        results = []
        for email_data in emails:
            send_result = self.email.send_email(
                to_email=email_data["to_email"],
                subject=email_data["subject"],
                body=email_data["body"],
                to_name=email_data["to_name"],
                metadata={"campaign_id": campaign_id, "firm": email_data["firm"]},
            )

            # Store in memory
            self.memory.store_message(
                agent_type="fundraising",
                recipient_email=email_data["to_email"],
                recipient_name=email_data["to_name"],
                subject=email_data["subject"],
                body=email_data["body"],
                campaign_id=campaign_id,
                message_type="outreach",
            )

            # Update contact state
            self.memory.update_contact_state("fundraising", email_data["to_email"], "contacted")
            self.memory.increment_messages_sent("fundraising", email_data["to_email"])

            if send_result["status"] == "sent":
                sent_count += 1

            results.append({
                "investor": email_data["to_name"],
                "email": email_data["to_email"],
                "subject": email_data["subject"],
                "body": email_data["body"],
                "status": send_result["status"],
            })

        # Update campaign stats
        self.memory.update_campaign_stats(
            campaign_id,
            status="completed",
            sent_count=sent_count,
        )

        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "total_investors": len(investors),
            "sent": sent_count,
            "failed": len(investors) - sent_count,
            "emails": results,
        }

    # -------------------------------------------------------------------
    # 4. Follow-up Logic
    # -------------------------------------------------------------------

    def generate_followups(self, campaign_id: str = None) -> list:
        """
        Generate follow-up emails for investors who haven't responded.
        Rule-based: sends follow-up if no response detected.
        """
        contacts = self.memory.get_contacts(agent_type="fundraising", state="contacted")
        followups = []

        for contact in contacts:
            metadata = {}
            try:
                raw_meta = contact.get("metadata", "{}")
                if raw_meta:
                    metadata = json.loads(raw_meta) if isinstance(raw_meta, str) else raw_meta
            except (json.JSONDecodeError, TypeError):
                metadata = {}

            messages_sent = contact.get("messages_sent", 1)
            if messages_sent >= 3:
                continue  # Max 3 touchpoints

            raw = self.ai.generate("investor_followup", {
                "investor_name": contact["name"],
                "firm": metadata.get("firm", "your firm"),
                "investment_focus": metadata.get("investment_focus", "technology"),
                "days_since": random.randint(3, 7),
                "followup_number": messages_sent,
            })

            subject, body = self._parse_email_output(raw)

            # Send the follow-up
            send_result = self.email.send_email(
                to_email=contact["email"],
                subject=subject,
                body=body,
                to_name=contact["name"],
            )

            # Store in memory
            self.memory.store_message(
                agent_type="fundraising",
                recipient_email=contact["email"],
                recipient_name=contact["name"],
                subject=subject,
                body=body,
                campaign_id=campaign_id,
                message_type="followup",
            )

            self.memory.update_contact_state("fundraising", contact["email"], "followed_up")
            self.memory.increment_messages_sent("fundraising", contact["email"])

            followups.append({
                "investor": contact["name"],
                "email": contact["email"],
                "subject": subject,
                "body": body,
                "followup_number": messages_sent + 1,
                "status": send_result["status"],
            })

        return followups

    # -------------------------------------------------------------------
    # 5. Response Classification
    # -------------------------------------------------------------------

    def classify_response(self, email: str, reply_text: str) -> dict:
        """
        Classify an investor's reply using the AI layer.
        Updates the contact state accordingly.
        """
        classification = self.ai.classify_response(reply_text)

        # Update contact state based on classification
        state_map = {
            "INTERESTED": "interested",
            "NOT_INTERESTED": "not_interested",
            "NEUTRAL": "responded",
        }
        new_state = state_map.get(classification["category"], "responded")
        self.memory.update_contact_state(
            "fundraising", email, new_state,
            response_category=classification["category"]
        )

        return {
            "email": email,
            "category": classification["category"],
            "reason": classification["reason"],
            "new_state": new_state,
        }

    def simulate_responses(self) -> list:
        """
        Simulate investor responses for demo purposes.
        Returns a mix of interested, not interested, and neutral replies.
        """
        mock_replies = {
            "INTERESTED": [
                "Thanks for reaching out! TruBot AI sounds very aligned with our thesis. Would love to schedule a call next week to learn more about your metrics.",
                "This is interesting. We've been looking at AI-native CRM plays. Let's chat — how's Thursday?",
                "I'd love to hear more. Can you send over your deck and we'll find time to connect?",
            ],
            "NOT_INTERESTED": [
                "Thanks for thinking of us, but this isn't a fit for our current fund. Best of luck!",
                "We're not actively looking at this space right now. Pass for now.",
                "Appreciate the note. We've already made our CRM/AI bet this cycle. Good luck with the raise.",
            ],
            "NEUTRAL": [
                "Thanks for the email. Can you send more details about your unit economics?",
                "Interesting. Let me review internally and get back to you.",
                "Noted — we'll keep TruBot AI on our radar.",
            ],
        }

        contacts = self.memory.get_contacts(agent_type="fundraising", state="contacted")
        if not contacts:
            contacts = self.memory.get_contacts(agent_type="fundraising", state="followed_up")

        results = []
        for contact in contacts:
            # Simulate ~40% response rate
            if random.random() > 0.40:
                continue

            # Weighted distribution: 30% interested, 30% not interested, 40% neutral
            r = random.random()
            if r < 0.30:
                category = "INTERESTED"
            elif r < 0.60:
                category = "NOT_INTERESTED"
            else:
                category = "NEUTRAL"

            reply_text = random.choice(mock_replies[category])
            classification = self.classify_response(contact["email"], reply_text)

            results.append({
                "investor": contact["name"],
                "email": contact["email"],
                "reply": reply_text,
                "classification": classification,
            })

        return results

    # -------------------------------------------------------------------
    # Stats
    # -------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Get fundraising campaign statistics."""
        contacts = self.memory.get_contacts(agent_type="fundraising")
        campaigns = self.memory.get_campaigns(agent_type="fundraising")
        messages = self.memory.get_messages(agent_type="fundraising")

        state_counts = {}
        for c in contacts:
            state = c.get("state", "unknown")
            state_counts[state] = state_counts.get(state, 0) + 1

        return {
            "total_investors": len(contacts),
            "total_campaigns": len(campaigns),
            "total_messages": len(messages),
            "state_breakdown": state_counts,
            "campaigns": campaigns,
        }
