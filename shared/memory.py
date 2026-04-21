"""
Memory Store - Shared AI Layer
SQLite-backed persistence for tracking messages, user states, and campaigns.
Used by both Fundraising and CRM agents.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional


class MemoryStore:
    """
    Shared memory layer that persists:
    - Messages sent (who, what, when, which agent)
    - User/contact state (contacted, followed_up, responded, etc.)
    - Campaign metadata
    """

    def __init__(self, db_path: str = "trubot.db"):
        self.db_path = db_path
        self._init_db()
        print(f"💾 MemoryStore initialized at '{db_path}'")

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = self._get_conn()
        cursor = conn.cursor()

        # Messages sent by agents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_type TEXT NOT NULL,          -- 'fundraising' or 'crm'
                campaign_id TEXT,
                recipient_email TEXT NOT NULL,
                recipient_name TEXT,
                subject TEXT,
                body TEXT,
                message_type TEXT DEFAULT 'outreach',  -- 'outreach', 'followup', 'campaign'
                status TEXT DEFAULT 'sent',            -- 'sent', 'opened', 'clicked', 'replied', 'bounced'
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT                          -- JSON blob for extra data
            )
        """)

        # User/contact states
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contact_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_type TEXT NOT NULL,
                email TEXT NOT NULL,
                name TEXT,
                state TEXT DEFAULT 'new',   -- 'new', 'contacted', 'followed_up', 'responded', 'interested', 'not_interested', 'converted'
                segment TEXT,               -- CRM: 'active', 'dormant', 'high_intent'
                messages_sent INTEGER DEFAULT 0,
                last_contacted TIMESTAMP,
                response_category TEXT,     -- 'INTERESTED', 'NOT_INTERESTED', 'NEUTRAL'
                metadata TEXT,              -- JSON blob
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(agent_type, email)
            )
        """)

        # Campaign tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT UNIQUE NOT NULL,
                agent_type TEXT NOT NULL,
                name TEXT,
                status TEXT DEFAULT 'created',  -- 'created', 'running', 'completed'
                total_recipients INTEGER DEFAULT 0,
                sent_count INTEGER DEFAULT 0,
                open_count INTEGER DEFAULT 0,
                click_count INTEGER DEFAULT 0,
                reply_count INTEGER DEFAULT 0,
                conversion_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                metadata TEXT
            )
        """)

        conn.commit()
        conn.close()

    # -----------------------------------------------------------------------
    # Message operations
    # -----------------------------------------------------------------------

    def store_message(self, agent_type: str, recipient_email: str,
                      subject: str, body: str, recipient_name: str = "",
                      message_type: str = "outreach", campaign_id: str = None,
                      metadata: dict = None) -> int:
        """Store a sent message. Returns the message ID."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (agent_type, campaign_id, recipient_email, recipient_name,
                                  subject, body, message_type, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (agent_type, campaign_id, recipient_email, recipient_name,
              subject, body, message_type, json.dumps(metadata or {})))
        msg_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return msg_id

    def get_messages(self, agent_type: str = None, campaign_id: str = None,
                     recipient_email: str = None, limit: int = 100) -> list:
        """Retrieve messages with optional filters."""
        conn = self._get_conn()
        query = "SELECT * FROM messages WHERE 1=1"
        params = []
        if agent_type:
            query += " AND agent_type = ?"
            params.append(agent_type)
        if campaign_id:
            query += " AND campaign_id = ?"
            params.append(campaign_id)
        if recipient_email:
            query += " AND recipient_email = ?"
            params.append(recipient_email)
        query += " ORDER BY sent_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_message_status(self, message_id: int, status: str):
        """Update status of a specific message."""
        conn = self._get_conn()
        conn.execute("UPDATE messages SET status = ? WHERE id = ?", (status, message_id))
        conn.commit()
        conn.close()

    # -----------------------------------------------------------------------
    # Contact state operations
    # -----------------------------------------------------------------------

    def upsert_contact(self, agent_type: str, email: str, name: str = "",
                       state: str = "new", segment: str = None,
                       metadata: dict = None):
        """Create or update a contact's state."""
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO contact_states (agent_type, email, name, state, segment, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_type, email) DO UPDATE SET
                name = excluded.name,
                state = excluded.state,
                segment = COALESCE(excluded.segment, contact_states.segment),
                metadata = excluded.metadata,
                updated_at = excluded.updated_at
        """, (agent_type, email, name, state, segment,
              json.dumps(metadata or {}), datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def update_contact_state(self, agent_type: str, email: str, state: str,
                             response_category: str = None):
        """Update a contact's state and optionally their response category."""
        conn = self._get_conn()
        if response_category:
            conn.execute("""
                UPDATE contact_states 
                SET state = ?, response_category = ?, updated_at = ?
                WHERE agent_type = ? AND email = ?
            """, (state, response_category, datetime.now().isoformat(), agent_type, email))
        else:
            conn.execute("""
                UPDATE contact_states 
                SET state = ?, updated_at = ?
                WHERE agent_type = ? AND email = ?
            """, (state, datetime.now().isoformat(), agent_type, email))
        conn.commit()
        conn.close()

    def increment_messages_sent(self, agent_type: str, email: str):
        """Increment the message counter for a contact."""
        conn = self._get_conn()
        conn.execute("""
            UPDATE contact_states 
            SET messages_sent = messages_sent + 1,
                last_contacted = ?,
                updated_at = ?
            WHERE agent_type = ? AND email = ?
        """, (datetime.now().isoformat(), datetime.now().isoformat(), agent_type, email))
        conn.commit()
        conn.close()

    def get_contacts(self, agent_type: str = None, state: str = None,
                     segment: str = None) -> list:
        """Retrieve contacts with optional filters."""
        conn = self._get_conn()
        query = "SELECT * FROM contact_states WHERE 1=1"
        params = []
        if agent_type:
            query += " AND agent_type = ?"
            params.append(agent_type)
        if state:
            query += " AND state = ?"
            params.append(state)
        if segment:
            query += " AND segment = ?"
            params.append(segment)
        query += " ORDER BY updated_at DESC"

        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # -----------------------------------------------------------------------
    # Campaign operations
    # -----------------------------------------------------------------------

    def create_campaign(self, campaign_id: str, agent_type: str, name: str,
                        total_recipients: int = 0, metadata: dict = None) -> str:
        """Create a new campaign record."""
        conn = self._get_conn()
        conn.execute("""
            INSERT OR REPLACE INTO campaigns (campaign_id, agent_type, name, total_recipients, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (campaign_id, agent_type, name, total_recipients, json.dumps(metadata or {})))
        conn.commit()
        conn.close()
        return campaign_id

    def update_campaign_stats(self, campaign_id: str, **kwargs):
        """Update campaign statistics (sent_count, open_count, etc.)."""
        conn = self._get_conn()
        updates = []
        params = []
        for key in ["status", "sent_count", "open_count", "click_count",
                     "reply_count", "conversion_count"]:
            if key in kwargs:
                updates.append(f"{key} = ?")
                params.append(kwargs[key])
        if kwargs.get("status") == "completed":
            updates.append("completed_at = ?")
            params.append(datetime.now().isoformat())

        if updates:
            params.append(campaign_id)
            conn.execute(
                f"UPDATE campaigns SET {', '.join(updates)} WHERE campaign_id = ?",
                params
            )
            conn.commit()
        conn.close()

    def get_campaign(self, campaign_id: str) -> Optional[dict]:
        """Get a campaign by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_campaigns(self, agent_type: str = None) -> list:
        """Get all campaigns, optionally filtered by agent type."""
        conn = self._get_conn()
        if agent_type:
            rows = conn.execute(
                "SELECT * FROM campaigns WHERE agent_type = ? ORDER BY created_at DESC",
                (agent_type,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM campaigns ORDER BY created_at DESC"
            ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # -----------------------------------------------------------------------
    # Stats / Dashboard helpers
    # -----------------------------------------------------------------------

    def get_dashboard_stats(self) -> dict:
        """Get aggregate stats for the dashboard."""
        conn = self._get_conn()

        stats = {}

        # Total messages by agent
        rows = conn.execute("""
            SELECT agent_type, COUNT(*) as count FROM messages GROUP BY agent_type
        """).fetchall()
        stats["messages_by_agent"] = {row["agent_type"]: row["count"] for row in rows}

        # Contact states
        rows = conn.execute("""
            SELECT agent_type, state, COUNT(*) as count 
            FROM contact_states GROUP BY agent_type, state
        """).fetchall()
        stats["contact_states"] = [dict(row) for row in rows]

        # Campaign summaries
        rows = conn.execute("""
            SELECT agent_type, COUNT(*) as campaigns,
                   SUM(sent_count) as total_sent,
                   SUM(open_count) as total_opens,
                   SUM(click_count) as total_clicks,
                   SUM(conversion_count) as total_conversions
            FROM campaigns GROUP BY agent_type
        """).fetchall()
        stats["campaign_summary"] = [dict(row) for row in rows]

        conn.close()
        return stats

    def reset(self):
        """Reset all data (for testing/demo)."""
        conn = self._get_conn()
        conn.execute("DELETE FROM messages")
        conn.execute("DELETE FROM contact_states")
        conn.execute("DELETE FROM campaigns")
        conn.commit()
        conn.close()
        print("🗑️  MemoryStore reset complete")
