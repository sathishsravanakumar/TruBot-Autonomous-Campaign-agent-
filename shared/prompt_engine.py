"""
Prompt Engine - Shared AI Layer
Reusable LLM interface for generating personalized messages.
Supports: Groq API (production), OpenAI API, and Mock mode (demo/testing).
"""

import os
import json
import random
import time
from typing import Optional

# Try to import Groq first, then OpenAI; fall back gracefully
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# ---------------------------------------------------------------------------
# Prompt Templates – used by both Fundraising & CRM agents
# ---------------------------------------------------------------------------

TEMPLATES = {
    # ---- Fundraising Templates ----
    "investor_outreach": """You are a professional fundraising outreach specialist for TruBot AI,
an AI-powered SaaS platform that helps SMEs automate customer engagement through
intelligent chatbots and CRM automation.

Write a personalized cold outreach email to an investor with the following profile:
- Name: {investor_name}
- Firm: {firm}
- Investment Focus: {investment_focus}

Context about TruBot AI:
- Series A stage, seeking $5M funding
- AI-powered CRM and customer engagement platform for SMEs
- 200+ active SME customers, 35% MoM growth
- Founded by experienced SaaS operators
- Key differentiator: autonomous AI agents that run campaigns end-to-end

Requirements:
- Subject line must be compelling and specific
- Reference their investment focus and why TruBot AI aligns
- Keep it under 150 words
- Professional but warm tone
- Include a clear call to action (15-min call)
- Do NOT use generic platitudes

Return the email in this exact format:
SUBJECT: <subject line>
BODY:
<email body>""",

    "investor_followup": """You are following up on an unanswered outreach email to an investor.

Original context:
- Investor: {investor_name} at {firm}
- Focus: {investment_focus}
- Days since last email: {days_since}
- Follow-up number: {followup_number}

Write a brief, non-pushy follow-up email that:
- References the original email naturally
- Adds ONE new piece of value (e.g., a recent milestone, metric, or insight)
- Keeps it under 80 words
- Has a softer CTA

Return in this format:
SUBJECT: <subject line>
BODY:
<email body>""",

    "classify_response": """Classify the following investor email reply into exactly one category:
- INTERESTED: They want to learn more, schedule a call, or show positive signals
- NOT_INTERESTED: They decline, say no, or indicate they're not a fit
- NEUTRAL: They acknowledge but don't commit either way, ask generic questions, or are ambiguous

Email reply:
\"{reply_text}\"

Respond with ONLY the category name (INTERESTED, NOT_INTERESTED, or NEUTRAL) and a one-line reason.
Format: CATEGORY | reason""",

    # ---- CRM Campaign Templates ----
    "crm_campaign_active": """Write a customer retention email for an ACTIVE user of TruBot AI.

User profile:
- Name: {user_name}
- Last activity: {last_activity}
- Engagement level: Active (regular usage)
- Key feature used: {feature_used}

Write an email that:
- Thanks them for being an active user
- Highlights a NEW feature or tip they might not know about
- Encourages them to explore advanced capabilities
- Includes a subtle upsell to a higher tier
- Under 120 words, warm and helpful tone

Return in this format:
SUBJECT: <subject line>
BODY:
<email body>""",

    "crm_campaign_dormant": """Write a re-engagement email for a DORMANT user of TruBot AI.

User profile:
- Name: {user_name}
- Last activity: {last_activity} (inactive for a while)
- Previous engagement: {previous_engagement}

Write an email that:
- Acknowledges their absence without guilt-tripping
- Highlights what's new since they left (2-3 improvements)
- Offers an incentive to return (free trial extension, personal onboarding)
- Creates gentle urgency
- Under 120 words

Return in this format:
SUBJECT: <subject line>
BODY:
<email body>""",

    "crm_campaign_high_intent": """Write a conversion-focused email for a HIGH-INTENT user of TruBot AI.

User profile:
- Name: {user_name}
- Last activity: {last_activity}
- Intent signals: {intent_signals}

Write an email that:
- Recognizes their strong engagement
- Addresses likely objections (pricing, complexity, ROI)
- Includes a specific offer (demo, discount, pilot program)
- Has a strong, specific CTA
- Under 120 words, confident but not salesy

Return in this format:
SUBJECT: <subject line>
BODY:
<email body>""",
}


# ---------------------------------------------------------------------------
# Mock responses for demo mode (no API key needed)
# ---------------------------------------------------------------------------

MOCK_RESPONSES = {
    "investor_outreach": [
        {
            "investor_focus_keywords": ["AI", "SaaS", "automation", "enterprise"],
            "response": """SUBJECT: TruBot AI – Autonomous CRM Agents Driving 35% MoM Growth
BODY:
Hi {investor_name},

I noticed {firm}'s strong thesis around {investment_focus} — it's precisely the space we're transforming at TruBot AI.

We've built autonomous AI agents that run end-to-end sales and engagement campaigns for SMEs — no manual intervention needed. Think of it as an AI-native CRM that actually executes, not just tracks.

The traction speaks for itself: 200+ paying SME customers, 35% month-over-month growth, and unit economics that work at scale.

We're raising our Series A ($5M) and I'd love to share how our agentic approach differs from legacy CRM tools.

Would you have 15 minutes this week for a quick call?

Best,
TruBot AI Team""",
        },
        {
            "investor_focus_keywords": ["fintech", "B2B", "marketplace", "growth"],
            "response": """SUBJECT: SME Sales Automation – 200+ Customers, $5M Series A
BODY:
Hi {investor_name},

{firm}'s portfolio in {investment_focus} caught my attention — we're solving a core pain point in that ecosystem.

TruBot AI automates the entire customer engagement lifecycle for SMEs using autonomous AI agents. Our platform handles everything from lead outreach to follow-ups to conversion tracking — tasks that typically require a 3-person sales team.

We're at 200+ active customers with 35% MoM growth and strong retention metrics. Currently raising a $5M Series A to scale our go-to-market.

I'd welcome 15 minutes to walk you through our demo and metrics. Would Thursday or Friday work?

Warm regards,
TruBot AI Team""",
        },
    ],
    "investor_followup": [
        """SUBJECT: Re: Quick follow-up – TruBot AI
BODY:
Hi {investor_name},

Just circling back on my earlier note. Since then, we've onboarded 15 new SME customers this month alone and launched our autonomous follow-up agent — it's driving a 2.3x improvement in reply rates for our customers.

Happy to share a 5-minute demo async if a call doesn't work. Would that be helpful?

Best,
TruBot AI Team""",
        """SUBJECT: Re: TruBot AI – One quick update
BODY:
Hi {investor_name},

Wanted to share a quick update: we just crossed $50K MRR this week, up from $35K last month. Our autonomous agents are handling 10,000+ campaigns daily across our SME customer base.

I know your time is valuable — happy to send a 3-minute Loom walkthrough if that's easier than a call.

Best,
TruBot AI Team""",
    ],
    "classify_response": {
        "positive_keywords": ["love to", "interested", "schedule", "let's chat", "sounds great", "tell me more"],
        "negative_keywords": ["not a fit", "pass", "not interested", "no thanks", "not investing", "decline"],
    },
    "crm_campaign_active": """SUBJECT: {user_name}, unlock this hidden feature in TruBot AI
BODY:
Hi {user_name},

Great to see you actively using TruBot AI! You've been getting solid results with {feature_used}.

Quick tip: Have you tried our new Smart Sequence Builder? It lets you chain multiple AI agents into automated workflows — customers using it are seeing 40% higher conversion rates.

It's available on your dashboard under Automations → Sequences. Takes 2 minutes to set up.

If you're interested in our Pro tier (unlocks advanced analytics + priority support), reply and I'll set up a personalized walkthrough.

Keep crushing it!
TruBot AI Team""",

    "crm_campaign_dormant": """SUBJECT: We've missed you, {user_name} — here's what's new
BODY:
Hi {user_name},

It's been a while since you last logged into TruBot AI, and I wanted to let you know what you're missing:

1. **AI Campaign Agents** — fully autonomous outreach (new!)
2. **Smart Segmentation** — auto-categorizes your contacts
3. **One-Click Integrations** — Gmail, Slack, HubSpot now supported

We'd love to have you back. As a welcome-back offer, I'm extending your trial by 14 days — no strings attached.

Just log in and everything's ready for you.

Cheers,
TruBot AI Team""",

    "crm_campaign_high_intent": """SUBJECT: {user_name}, ready to take TruBot AI to the next level?
BODY:
Hi {user_name},

I've noticed you've been exploring our platform extensively — {intent_signals}. That tells me you're serious about automating your customer engagement.

Here's what the jump to Pro gets you:
- Unlimited AI campaigns (vs. 5/month on Free)
- Advanced analytics dashboard
- Priority support with a dedicated CSM

I'd like to offer you a **30-day Pro pilot at 50% off** so you can see the full ROI before committing.

Want me to activate it? Just reply "Yes" and it's done.

Best,
TruBot AI Team""",
}


class PromptEngine:
    """
    Reusable prompt engine for generating AI-powered messages.
    Both Fundraising and CRM agents use this shared component.
    """

    def __init__(self):
        self.mode = os.environ.get("LLM_MODE", "mock")  # "mock", "groq", or "openai"
        self.model = os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile")  # Groq default model
        self.client = None

        if self.mode == "groq":
            api_key = os.environ.get("GROQ_API_KEY")
            if api_key and GROQ_AVAILABLE:
                self.client = Groq(api_key=api_key)
            elif api_key and OPENAI_AVAILABLE:
                # Fallback: use OpenAI client with Groq's base URL (compatible API)
                self.client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.groq.com/openai/v1"
                )
            else:
                print("⚠️  GROQ_API_KEY not set or groq/openai package missing. Falling back to mock mode.")
                self.mode = "mock"
        elif self.mode == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key and OPENAI_AVAILABLE:
                self.client = OpenAI(api_key=api_key)
            else:
                print("⚠️  OPENAI_API_KEY not set or openai package missing. Falling back to mock mode.")
                self.mode = "mock"

        print(f"🧠 PromptEngine initialized in '{self.mode}' mode (model: {self.model})")

    def generate(self, template_name: str, context: dict) -> str:
        """
        Generate a message using the specified template and context.
        Works in mock, groq, and openai modes.
        """
        if self.mode in ("groq", "openai") and self.client:
            return self._generate_llm(template_name, context)
        else:
            return self._generate_mock(template_name, context)

    def _generate_llm(self, template_name: str, context: dict) -> str:
        """Generate using LLM API (Groq or OpenAI — same interface).
        Includes retry logic for rate limits (Groq free tier: 30 RPM).
        """
        template = TEMPLATES.get(template_name)
        if not template:
            raise ValueError(f"Unknown template: {template_name}")

        prompt = template.format(**context)
        max_retries = 3

        for attempt in range(max_retries):
            try:
                # Rate limit: wait 2.5s between calls to stay under 30 RPM
                if hasattr(self, '_last_call_time'):
                    elapsed = time.time() - self._last_call_time
                    if elapsed < 2.5:
                        time.sleep(2.5 - elapsed)

                self._last_call_time = time.time()

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a professional email copywriter specializing in B2B SaaS outreach."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.7,
                    max_tokens=500,
                )
                return response.choices[0].message.content.strip()

            except Exception as e:
                error_str = str(e)
                if "rate_limit" in error_str.lower() or "429" in error_str:
                    wait_time = (attempt + 1) * 3  # 3s, 6s, 9s
                    print(f"⏳ Rate limited (attempt {attempt + 1}/{max_retries}). Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"⚠️  LLM API error ({self.mode}): {e}. Falling back to mock.")
                    return self._generate_mock(template_name, context)

        print(f"⚠️  Rate limit exceeded after {max_retries} retries. Falling back to mock.")
        return self._generate_mock(template_name, context)

    def _generate_mock(self, template_name: str, context: dict) -> str:
        """Generate using mock responses for demo/testing."""
        if template_name == "investor_outreach":
            options = MOCK_RESPONSES["investor_outreach"]
            chosen = random.choice(options)
            return chosen["response"].format(**context)

        elif template_name == "investor_followup":
            chosen = random.choice(MOCK_RESPONSES["investor_followup"])
            return chosen.format(**context)

        elif template_name == "classify_response":
            reply_text = context.get("reply_text", "").lower()
            pos = MOCK_RESPONSES["classify_response"]["positive_keywords"]
            neg = MOCK_RESPONSES["classify_response"]["negative_keywords"]

            if any(kw in reply_text for kw in pos):
                return "INTERESTED | Positive signals detected in reply"
            elif any(kw in reply_text for kw in neg):
                return "NOT_INTERESTED | Negative signals detected in reply"
            else:
                return "NEUTRAL | No clear positive or negative signals"

        elif template_name.startswith("crm_campaign_"):
            mock = MOCK_RESPONSES.get(template_name, "")
            if isinstance(mock, str):
                return mock.format(**{k: context.get(k, "") for k in context})
            return str(mock)

        return f"[Mock response for template: {template_name}]"

    def classify_response(self, reply_text: str) -> dict:
        """Classify an investor reply. Returns category and reason."""
        result = self.generate("classify_response", {"reply_text": reply_text})
        parts = result.split("|", 1)
        category = parts[0].strip()
        reason = parts[1].strip() if len(parts) > 1 else "No reason provided"
        return {"category": category, "reason": reason}

    def get_available_templates(self) -> list:
        """Return list of available template names."""
        return list(TEMPLATES.keys())
