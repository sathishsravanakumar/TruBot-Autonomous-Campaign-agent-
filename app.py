"""
TruBot AI - Autonomous Campaign Agents MVP
Main Flask Application

Run: python app.py
Dashboard: http://localhost:5000
"""

import os
import sys
import json
import uuid
from flask import Flask, request, jsonify, render_template, redirect, url_for

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; use env vars directly

# Project root directory (absolute path — works on Windows + Linux)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from shared.prompt_engine import PromptEngine
from shared.memory import MemoryStore
from shared.email_service import EmailService
from fundraising.agent import FundraisingAgent
from crm.agent import CRMAgent
from generate_data import generate_investor_csv, generate_crm_dataset

# ---------------------------------------------------------------------------
# Absolute paths for data files
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(BASE_DIR, "data")
INVESTORS_CSV = os.path.join(DATA_DIR, "investors.csv")
CRM_USERS_CSV = os.path.join(DATA_DIR, "crm_users.csv")
DB_PATH = os.path.join(BASE_DIR, "trubot.db")

# ---------------------------------------------------------------------------
# Initialize app and shared components
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload

# Shared AI Layer — used by both agents
prompt_engine = PromptEngine()
memory = MemoryStore(db_path=DB_PATH)
email_service = EmailService()

# Agents
fundraising_agent = FundraisingAgent(prompt_engine, memory, email_service)
crm_agent = CRMAgent(prompt_engine, memory, email_service)

# Generate sample data on startup if not exists
if not os.path.exists(INVESTORS_CSV):
    generate_investor_csv(filepath=INVESTORS_CSV)
if not os.path.exists(CRM_USERS_CSV):
    generate_crm_dataset(filepath=CRM_USERS_CSV)


# ---------------------------------------------------------------------------
# Helper: safely get JSON from request (never crashes on empty body)
# ---------------------------------------------------------------------------
def get_json():
    """Safely parse request JSON. Returns {} if body is empty or not JSON."""
    try:
        data = request.get_json(silent=True)
        return data if data else {}
    except Exception:
        return {}


def read_investors_csv():
    """Read the investors CSV file."""
    with open(INVESTORS_CSV, "r", encoding="utf-8") as f:
        return f.read()


def read_crm_csv():
    """Read the CRM users CSV file."""
    with open(CRM_USERS_CSV, "r", encoding="utf-8") as f:
        return f.read()


# ===========================================================================
# WEB UI ROUTES
# ===========================================================================

@app.route("/")
def index():
    """Dashboard home page."""
    stats = memory.get_dashboard_stats()
    return render_template("index.html", stats=stats)


@app.route("/fundraising")
def fundraising_page():
    """Fundraising agent page."""
    stats = fundraising_agent.get_stats()
    return render_template("fundraising.html", stats=stats)


@app.route("/crm")
def crm_page():
    """CRM agent page."""
    stats = crm_agent.get_stats()
    return render_template("crm.html", stats=stats)


# ===========================================================================
# FUNDRAISING API ROUTES
# ===========================================================================

@app.route("/api/fundraising/upload-csv", methods=["POST"])
def fundraising_upload_csv():
    """Upload investor CSV and parse it."""
    try:
        if "file" in request.files:
            file = request.files["file"]
            csv_content = file.read().decode("utf-8")
        else:
            data = get_json()
            if "csv_content" in data:
                csv_content = data["csv_content"]
            else:
                csv_content = read_investors_csv()

        investors = fundraising_agent.parse_investor_csv(csv_content)
        fundraising_agent.load_investors(investors)

        return jsonify({
            "status": "success",
            "investors_loaded": len(investors),
            "investors": investors,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/fundraising/generate-emails", methods=["POST"])
def fundraising_generate_emails():
    """Generate personalized emails for investors."""
    try:
        data = get_json()
        investors = data.get("investors")

        if not investors:
            investors = fundraising_agent.parse_investor_csv(read_investors_csv())

        limit = data.get("limit", 5)
        investors = investors[:limit]

        emails = fundraising_agent.generate_emails(investors)
        return jsonify({
            "status": "success",
            "emails_generated": len(emails),
            "emails": emails,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/fundraising/run-campaign", methods=["POST"])
def fundraising_run_campaign():
    """Run a full fundraising campaign."""
    try:
        data = get_json()

        if "csv_content" in data:
            investors = fundraising_agent.parse_investor_csv(data["csv_content"])
        elif "investors" in data:
            investors = data["investors"]
        else:
            investors = fundraising_agent.parse_investor_csv(read_investors_csv())

        limit = data.get("limit", 10)
        investors = investors[:limit]

        result = fundraising_agent.run_campaign(
            investors,
            campaign_name=data.get("campaign_name"),
        )
        return jsonify({"status": "success", **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/fundraising/followups", methods=["POST"])
def fundraising_followups():
    """Generate and send follow-up emails."""
    try:
        followups = fundraising_agent.generate_followups()
        return jsonify({
            "status": "success",
            "followups_sent": len(followups),
            "followups": followups,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/fundraising/simulate-responses", methods=["POST"])
def fundraising_simulate_responses():
    """Simulate investor responses and classify them."""
    try:
        responses = fundraising_agent.simulate_responses()
        return jsonify({
            "status": "success",
            "responses": len(responses),
            "results": responses,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/fundraising/classify", methods=["POST"])
def fundraising_classify():
    """Classify a single investor response."""
    try:
        data = get_json()
        email_addr = data.get("email", "investor@example.com")
        reply_text = data.get("reply_text", "")

        if not reply_text:
            return jsonify({"error": "reply_text is required"}), 400

        result = fundraising_agent.classify_response(email_addr, reply_text)
        return jsonify({"status": "success", **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/fundraising/stats")
def fundraising_stats():
    """Get fundraising statistics."""
    return jsonify(fundraising_agent.get_stats())


@app.route("/api/fundraising/followups/send-real-email", methods=["POST"])
def fundraising_followups_send_real():
    """Send a REAL follow-up email to a specific investor via Gmail SMTP."""
    try:
        data = get_json()
        to_email = data.get("to_email", "")
        to_name = data.get("to_name", "")
        subject = data.get("subject", "")
        body = data.get("body", "")

        if not to_email or not subject or not body:
            return jsonify({"error": "to_email, subject, and body are required"}), 400

        result = email_service.send_real_email(
            to_email=to_email,
            subject=subject,
            body=body,
            to_name=to_name,
        )

        if result["status"] == "sent":
            memory.store_message(
                agent_type="fundraising",
                recipient_email=to_email,
                recipient_name=to_name,
                subject=subject,
                body=body,
                message_type="followup",
                metadata={"mode": "real_email"},
            )

        return jsonify({"status": "success", **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/fundraising/send-real-email", methods=["POST"])
def fundraising_send_real():
    """Send a REAL email to a specific investor via Gmail SMTP."""
    try:
        data = get_json()
        to_email = data.get("to_email", "")
        to_name = data.get("to_name", "")
        subject = data.get("subject", "")
        body = data.get("body", "")

        if not to_email or not subject or not body:
            return jsonify({"error": "to_email, subject, and body are required"}), 400

        result = email_service.send_real_email(
            to_email=to_email,
            subject=subject,
            body=body,
            to_name=to_name,
        )

        # Also store in memory
        if result["status"] == "sent":
            memory.store_message(
                agent_type="fundraising",
                recipient_email=to_email,
                recipient_name=to_name,
                subject=subject,
                body=body,
                message_type="outreach",
                metadata={"mode": "real_email"},
            )

        return jsonify({"status": "success", **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================================================================
# CRM API ROUTES
# ===========================================================================

@app.route("/api/crm/load-dataset", methods=["POST"])
def crm_load_dataset():
    """Load CRM user dataset."""
    try:
        data = get_json()

        if "csv_content" in data:
            csv_content = data["csv_content"]
        else:
            csv_content = read_crm_csv()

        users = crm_agent.parse_user_csv(csv_content)
        crm_agent.load_users(users)

        return jsonify({
            "status": "success",
            "users_loaded": len(users),
            "sample": users[:5],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/crm/segment", methods=["POST"])
def crm_segment():
    """Segment users into Active, Dormant, High-Intent."""
    try:
        data = get_json()
        method = data.get("method", "rule_based")

        users = crm_agent.parse_user_csv(read_crm_csv())
        result = crm_agent.segment_users(users, method=method)
        return jsonify({"status": "success", **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/crm/generate-campaigns", methods=["POST"])
def crm_generate_campaigns():
    """Generate campaign messages per segment."""
    try:
        if not crm_agent.segments:
            users = crm_agent.parse_user_csv(read_crm_csv())
            crm_agent.segment_users(users)

        campaigns = crm_agent.generate_campaign_messages()
        return jsonify({"status": "success", "campaigns": campaigns})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/crm/run-campaign", methods=["POST"])
def crm_run_campaign():
    """Run a full CRM campaign."""
    try:
        data = get_json()
        method = data.get("method", "rule_based")

        users = crm_agent.parse_user_csv(read_crm_csv())
        result = crm_agent.run_campaign(
            campaign_name=data.get("campaign_name"),
            method=method,
            users=users,
        )
        return jsonify({"status": "success", **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/crm/tracking", methods=["POST"])
def crm_tracking():
    """Simulate email tracking metrics."""
    try:
        data = get_json()
        campaign_id = data.get("campaign_id")

        if not crm_agent.segments:
            users = crm_agent.parse_user_csv(read_crm_csv())
            crm_agent.segment_users(users)

        tracking = crm_agent.simulate_tracking(campaign_id)
        return jsonify({"status": "success", "tracking": tracking})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/crm/stats")
def crm_stats():
    """Get CRM statistics."""
    return jsonify(crm_agent.get_stats())


@app.route("/api/crm/send-real-email", methods=["POST"])
def crm_send_real():
    """Send a REAL CRM campaign email via Gmail SMTP."""
    try:
        data = get_json()
        to_email = data.get("to_email", "")
        to_name = data.get("to_name", "")
        subject = data.get("subject", "")
        body = data.get("body", "")

        if not to_email or not subject or not body:
            return jsonify({"error": "to_email, subject, and body are required"}), 400

        result = email_service.send_real_email(
            to_email=to_email,
            subject=subject,
            body=body,
            to_name=to_name,
        )

        if result["status"] == "sent":
            memory.store_message(
                agent_type="crm",
                recipient_email=to_email,
                recipient_name=to_name,
                subject=subject,
                body=body,
                message_type="campaign",
                metadata={"mode": "real_email"},
            )

        return jsonify({"status": "success", **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/smtp-status")
def smtp_status():
    """Check if SMTP is configured for real email sending."""
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    configured = bool(smtp_user and smtp_pass)
    return jsonify({
        "configured": configured,
        "smtp_user": smtp_user[:3] + "***" if smtp_user else "",
        "message": "SMTP ready" if configured else "Set SMTP_USER and SMTP_PASS in .env",
    })


# ===========================================================================
# SHARED ROUTES
# ===========================================================================

@app.route("/api/dashboard")
def api_dashboard():
    """Get overall dashboard stats."""
    return jsonify(memory.get_dashboard_stats())


@app.route("/api/messages")
def api_messages():
    """Get all messages with optional filters."""
    agent_type = request.args.get("agent_type")
    campaign_id = request.args.get("campaign_id")
    limit = int(request.args.get("limit", 50))
    messages = memory.get_messages(agent_type=agent_type, campaign_id=campaign_id, limit=limit)
    return jsonify({"messages": messages, "count": len(messages)})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Reset all data for fresh demo."""
    memory.reset()
    email_service.clear_log()
    crm_agent.segments = {}
    return jsonify({"status": "success", "message": "All data reset"})


# ===========================================================================
# Error Handlers — always return JSON for API routes
# ===========================================================================

@app.errorhandler(400)
def bad_request(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Bad request", "details": str(e)}), 400
    return str(e), 400


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found"}), 404
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error", "details": str(e)}), 500


# ===========================================================================
# Run
# ===========================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  🤖 TruBot AI - Autonomous Campaign Agents MVP")
    print("=" * 60)
    print(f"  📧 Email Mode:  {email_service.mode}")
    print(f"  🧠 LLM Mode:    {prompt_engine.mode}")
    print(f"  💾 Database:     {DB_PATH}")
    print(f"  🌐 Dashboard:   http://localhost:5000")
    print("=" * 60 + "\n")

    app.run(debug=True, host="0.0.0.0", port=5000)
