"""
Email Service - Shared AI Layer
Handles email sending (mock mode for demo, SMTP for production).
"""

import os
import json
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional


class EmailService:
    """
    Email sending service with mock and SMTP modes.
    Mock mode logs emails to memory for demo purposes.
    """

    def __init__(self, mode: str = None):
        self.mode = mode or os.environ.get("EMAIL_MODE", "mock")  # "mock" or "smtp"
        self.smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("SMTP_USER", "")
        self.smtp_pass = os.environ.get("SMTP_PASS", "")
        self.from_email = os.environ.get("FROM_EMAIL", "outreach@trubot.ai")

        # Track sent emails in-memory for mock mode
        self.sent_log = []
        print(f"📧 EmailService initialized in '{self.mode}' mode")

    def send_email(self, to_email: str, subject: str, body: str,
                   to_name: str = "", metadata: dict = None) -> dict:
        """
        Send an email (mock or real).
        Returns a result dict with status and details.
        """
        if self.mode == "smtp":
            return self._send_smtp(to_email, subject, body, to_name)
        else:
            return self._send_mock(to_email, subject, body, to_name, metadata)

    def _send_mock(self, to_email: str, subject: str, body: str,
                   to_name: str = "", metadata: dict = None) -> dict:
        """Simulate sending an email."""
        # Simulate occasional failures (5% chance) for realism
        success = random.random() > 0.05

        result = {
            "status": "sent" if success else "bounced",
            "to_email": to_email,
            "to_name": to_name,
            "subject": subject,
            "body": body,
            "sent_at": datetime.now().isoformat(),
            "message_id": f"mock_{len(self.sent_log) + 1}_{random.randint(1000, 9999)}",
            "mode": "mock",
            "metadata": metadata or {},
        }

        self.sent_log.append(result)
        return result

    def _send_smtp(self, to_email: str, subject: str, body: str,
                   to_name: str = "") -> dict:
        """Send a real email via SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email

            # Plain text body
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.from_email, to_email, msg.as_string())

            return {
                "status": "sent",
                "to_email": to_email,
                "to_name": to_name,
                "subject": subject,
                "sent_at": datetime.now().isoformat(),
                "mode": "smtp",
            }
        except Exception as e:
            return {
                "status": "failed",
                "to_email": to_email,
                "error": str(e),
                "mode": "smtp",
            }

    def send_batch(self, recipients: list, subject_template: str = None,
                   body_template: str = None, emails: list = None) -> dict:
        """
        Send a batch of emails.
        Either provide pre-generated emails list, or templates + recipients.
        Returns batch results summary.
        """
        results = {"sent": 0, "failed": 0, "details": []}

        if emails:
            # Pre-generated emails (from AI)
            for email_data in emails:
                result = self.send_email(
                    to_email=email_data.get("to_email", ""),
                    subject=email_data.get("subject", ""),
                    body=email_data.get("body", ""),
                    to_name=email_data.get("to_name", ""),
                    metadata=email_data.get("metadata", {}),
                )
                if result["status"] == "sent":
                    results["sent"] += 1
                else:
                    results["failed"] += 1
                results["details"].append(result)
        else:
            # Template-based batch
            for recipient in recipients:
                subject = subject_template or "Hello"
                body = body_template or "Default body"
                result = self.send_email(
                    to_email=recipient.get("email", ""),
                    subject=subject,
                    body=body,
                    to_name=recipient.get("name", ""),
                )
                if result["status"] == "sent":
                    results["sent"] += 1
                else:
                    results["failed"] += 1
                results["details"].append(result)

        results["total"] = results["sent"] + results["failed"]
        return results

    def simulate_tracking(self, message_count: int, segment: str = "general") -> dict:
        """
        Simulate email tracking metrics (opens, clicks, conversions).
        Returns realistic rates based on segment type.
        """
        # Realistic email metric ranges by segment
        rates = {
            "active":      {"open": (0.40, 0.65), "click": (0.10, 0.25), "conversion": (0.03, 0.10)},
            "dormant":     {"open": (0.08, 0.20), "click": (0.02, 0.08), "conversion": (0.005, 0.02)},
            "high_intent": {"open": (0.50, 0.75), "click": (0.15, 0.35), "conversion": (0.05, 0.15)},
            "investor":    {"open": (0.30, 0.55), "click": (0.05, 0.15), "conversion": (0.02, 0.08)},
            "general":     {"open": (0.20, 0.40), "click": (0.05, 0.15), "conversion": (0.01, 0.05)},
        }

        r = rates.get(segment, rates["general"])
        open_rate = random.uniform(*r["open"])
        click_rate = random.uniform(*r["click"])
        conv_rate = random.uniform(*r["conversion"])

        opens = int(message_count * open_rate)
        clicks = int(message_count * click_rate)
        conversions = int(message_count * conv_rate)

        return {
            "total_sent": message_count,
            "opens": opens,
            "clicks": clicks,
            "conversions": conversions,
            "open_rate": round(open_rate * 100, 1),
            "click_rate": round(click_rate * 100, 1),
            "conversion_rate": round(conv_rate * 100, 1),
            "segment": segment,
        }

    def send_real_email(self, to_email: str, subject: str, body: str,
                       to_name: str = "", smtp_user: str = None,
                       smtp_pass: str = None) -> dict:
        """
        Send a REAL email via SMTP — works regardless of current mode.
        Used for live demo: sends one actual email to a real inbox.
        Uses credentials from params or environment variables.
        """
        sender = smtp_user or self.smtp_user or os.environ.get("SMTP_USER", "")
        password = smtp_pass or self.smtp_pass or os.environ.get("SMTP_PASS", "")

        if not sender or not password:
            return {
                "status": "failed",
                "to_email": to_email,
                "error": "SMTP_USER and SMTP_PASS must be set in .env file",
                "mode": "smtp",
            }

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"TruBot AI <{sender}>"
            msg["To"] = f"{to_name} <{to_email}>" if to_name else to_email
            msg["Reply-To"] = sender

            # Plain text version
            msg.attach(MIMEText(body, "plain"))

            # HTML version (professional look)
            html_body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;
                        padding: 24px; color: #333;">
                <div style="border-bottom: 2px solid #6c5ce7; padding-bottom: 12px; margin-bottom: 20px;">
                    <span style="font-size: 18px; font-weight: bold; color: #6c5ce7;">TruBot AI</span>
                    <span style="font-size: 12px; color: #888; margin-left: 8px;">Autonomous Campaign Agent</span>
                </div>
                <div style="line-height: 1.7; font-size: 15px; white-space: pre-wrap;">{body}</div>
                <div style="margin-top: 30px; padding-top: 16px; border-top: 1px solid #eee;
                            font-size: 12px; color: #999;">
                    Sent via TruBot AI Campaign Agent MVP
                </div>
            </div>
            """
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(sender, password)
                server.sendmail(sender, to_email, msg.as_string())

            result = {
                "status": "sent",
                "to_email": to_email,
                "to_name": to_name,
                "subject": subject,
                "sent_at": datetime.now().isoformat(),
                "mode": "smtp_real",
            }
            self.sent_log.append(result)
            return result

        except smtplib.SMTPAuthenticationError:
            return {
                "status": "failed",
                "to_email": to_email,
                "error": "Gmail authentication failed. Check SMTP_USER and SMTP_PASS (use App Password, not regular password)",
                "mode": "smtp",
            }
        except Exception as e:
            return {
                "status": "failed",
                "to_email": to_email,
                "error": str(e),
                "mode": "smtp",
            }

    def get_sent_log(self) -> list:
        """Return all mock-sent emails."""
        return self.sent_log

    def clear_log(self):
        """Clear the sent log."""
        self.sent_log = []
