# TruBot AI — Autonomous Campaign Agents MVP

**AI-powered agents for fundraising outreach and CRM sales campaigns.**

---

## Quick Start

```bash
# 1. Clone and install
git clone <repo-url> && cd trubot-ai-assignment
pip install -r requirements.txt

# 2. Run (mock mode — no API keys needed)
python app.py

# 3. Open dashboard
open http://localhost:5000
```

To enable real AI generation, set `LLM_MODE=groq` and add your `GROQ_API_KEY` in a `.env` file (see `.env.example`). Get a free key at [console.groq.com](https://console.groq.com).

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                    Flask Web App                      │
│              (Dashboard + REST API)                   │
├──────────────┬───────────────────────┤               │
│  Fundraising │    CRM Sales          │               │
│    Agent     │      Agent            │               │
│              │                       │               │
│ • CSV Parse  │ • Dataset Loading     │               │
│ • Email Gen  │ • Segmentation        │               │
│ • Campaign   │   (Rule/ML)           │               │
│ • Follow-ups │ • Campaign Gen        │               │
│ • Classify   │ • Execution           │               │
│   Responses  │ • Tracking Sim        │               │
├──────────────┴───────────────────────┤               │
│         ✦ Shared AI Layer ✦                          │
│  ┌─────────────┬──────────┬──────────────┐          │
│  │ Prompt      │ Memory   │ Email        │          │
│  │ Engine      │ Store    │ Service      │          │
│  │ (LLM/Mock)  │ (SQLite) │ (Mock/SMTP)  │          │
│  └─────────────┴──────────┴──────────────┘          │
└──────────────────────────────────────────────────────┘
```

**Shared AI Layer** — The core reusable module both agents depend on:

| Component        | Purpose                                         | Tech              |
|-----------------|--------------------------------------------------|-------------------|
| **Prompt Engine** | Templated LLM interface for generating personalized messages | OpenAI API / Mock |
| **Memory Store**  | Persistent state: messages sent, contact states, campaign metadata | SQLite |
| **Email Service** | Email dispatch with tracking simulation | Mock / SMTP |

---

## How AI Is Used

1. **Personalized Email Generation** — Each investor/user email is generated via LLM using structured prompts that include the recipient's profile (name, firm, investment focus, engagement signals). The prompt engine uses template interpolation to inject context, producing unique, relevant messages rather than generic mail-merge output.

2. **Response Classification** — Investor replies are classified into INTERESTED / NOT_INTERESTED / NEUTRAL using an LLM classifier prompt. The system extracts the category and reasoning, then updates the contact's state in the memory layer.

3. **User Segmentation** — Two approaches: *Rule-based* (configurable thresholds on recency and engagement) and *ML-based* (K-Means clustering on feature vectors: days inactive, page views, sessions, purchases). The ML approach auto-labels clusters by analyzing centroid characteristics.

4. **Campaign Message Tailoring** — Different prompt templates per segment (active → retention/upsell, dormant → re-engagement, high-intent → conversion). The AI layer adapts tone, urgency, and CTAs based on segment type.

---

## Demo Flow

### Fundraising Agent
1. **Upload CSV** → Parse investor data (name, email, firm, focus)
2. **Generate Emails** → AI creates personalized outreach per investor
3. **Send Campaign** → Batch send (mock) with status tracking
4. **Follow-ups** → Auto-generate follow-up emails for non-responders
5. **Classify Responses** → AI categorizes mock investor replies

### CRM Sales Agent
1. **Load Dataset** → 1000-row mock CRM data with engagement signals
2. **Segment Users** → Rule-based or ML (K-Means) into Active/Dormant/High-Intent
3. **Generate Campaigns** → AI writes segment-specific messages
4. **Execute** → Batch send with per-user tracking
5. **Track** → Simulated open/click/conversion rates per segment

---

## Tech Stack

| Layer     | Choice         | Rationale                        |
|-----------|---------------|----------------------------------|
| Backend   | Python + Flask | Lightweight, fast to prototype   |
| LLM       | Groq / OpenAI / Mock | Groq free tier for demo, fast inference |
| Database  | SQLite         | Zero-config, file-based          |
| Frontend  | Jinja2 + HTML  | No build step, instant rendering |
| ML        | scikit-learn   | K-Means segmentation (optional)  |

---

## Limitations

- **Mock emails**: No real SMTP in default mode (configurable via `.env`)
- **Simulated tracking**: Open/click/conversion rates are randomized within realistic ranges, not connected to real email events
- **No authentication**: MVP has no user auth or multi-tenancy
- **Single-threaded**: Campaign execution is synchronous; production would need async workers (Celery/RQ)
- **Limited error handling**: Minimal retry logic on API failures
- **Mock LLM**: Default mode uses pre-written templates; switch to OpenAI for real generation

## What I'd Add With More Time
- WebSocket-based real-time campaign progress
- A/B testing framework for email variants
- Webhook-based real tracking (SendGrid/Mailgun integration)
- Redis-backed job queue for async campaign execution
- OAuth + multi-tenant support
- Advanced ML: propensity scoring, send-time optimization

---

## Project Structure

```
trubot-ai-assignment/
├── app.py                  # Flask app + all API routes
├── generate_data.py        # Sample data generation
├── requirements.txt        # Python dependencies
├── .env.example            # Config template
├── shared/                 # ✦ Shared AI Layer
│   ├── prompt_engine.py    # LLM interface (mock + OpenAI)
│   ├── memory.py           # SQLite persistence
│   └── email_service.py    # Email dispatch + tracking
├── fundraising/            # Fundraising Agent
│   └── agent.py            # Full agent implementation
├── crm/                    # CRM Sales Agent
│   └── agent.py            # Segmentation + campaigns
├── data/                   # Generated sample datasets
│   ├── investors.csv       # 25 investor records
│   └── crm_users.csv       # 1000 user records
└── templates/              # HTML dashboard
    ├── base.html           # Layout + shared styles
    ├── index.html          # Dashboard home
    ├── fundraising.html    # Fundraising agent UI
    └── crm.html            # CRM agent UI
```
