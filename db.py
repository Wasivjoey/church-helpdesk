"""ChurchDesk — SQLite data layer.

Single-file schema + helpers. SQLite only (zero-dependency); the file lives at
DATABASE_PATH (defaults to churchdesk.db next to this file). Werkzeug hashes
passwords. First run seeds an admin and demo data so the app is usable at once.
"""

import os
import sqlite3
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash as _gph


def hash_pw(pw):
    # pbkdf2: scrypt needs an OpenSSL build that this Python may lack.
    return _gph(pw, method="pbkdf2:sha256")

DB_PATH = os.environ.get(
    "DATABASE_PATH", os.path.join(os.path.dirname(__file__), "churchdesk.db")
)

# Ticket workflow. Order matters: it drives the board columns and the
# "open vs done" split used on the dashboard.
TICKET_STATUSES = ["New", "Open", "In Progress", "On Hold", "Resolved", "Closed"]
OPEN_STATUSES = {"New", "Open", "In Progress", "On Hold"}
PRIORITIES = ["Low", "Medium", "High", "Urgent"]
# Hours until an open ticket is "due", by priority. Drives the SLA flag only.
SLA_HOURS = {"Low": 72, "Medium": 48, "High": 24, "Urgent": 4}
CATEGORIES = [
    "Sound / AV", "Computers", "Network / WiFi", "Projection / Screens",
    "Lighting", "Phones", "Accounts / Login", "Facilities", "Printing", "Other",
]
ASSET_CATEGORIES = [
    "Laptop", "Desktop", "Tablet", "Phone", "Microphone", "Mixer", "Speaker",
    "Camera", "Projector", "Screen", "Printer", "Network Gear", "Other",
]
ASSET_STATUSES = ["In Use", "Spare", "In Repair", "Retired"]
CHANGE_STATUSES = ["Requested", "Approved", "Scheduled", "Done", "Rejected"]
RISK_LEVELS = ["Low", "Medium", "High"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'agent',   -- 'admin' or 'agent'
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tickets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ref             TEXT NOT NULL UNIQUE,            -- human reference e.g. CD-1042
    subject         TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    requester_name  TEXT NOT NULL,
    requester_email TEXT NOT NULL,
    category        TEXT NOT NULL DEFAULT 'Other',
    priority        TEXT NOT NULL DEFAULT 'Medium',
    status          TEXT NOT NULL DEFAULT 'New',
    assignee_id     INTEGER,                         -- users.id or NULL
    asset_id        INTEGER,                         -- assets.id or NULL
    due_at          TEXT,                            -- SLA target (ISO)
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    resolved_at     TEXT
);

CREATE TABLE IF NOT EXISTS comments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id  INTEGER NOT NULL,
    author     TEXT NOT NULL,
    body       TEXT NOT NULL,
    internal   INTEGER NOT NULL DEFAULT 0,           -- staff-only note
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tag         TEXT NOT NULL UNIQUE,                -- asset tag e.g. AV-012
    name        TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT 'Other',
    status      TEXT NOT NULL DEFAULT 'In Use',
    location    TEXT NOT NULL DEFAULT '',
    assigned_to TEXT NOT NULL DEFAULT '',            -- ministry / person
    notes       TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS changes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    risk          TEXT NOT NULL DEFAULT 'Low',
    status        TEXT NOT NULL DEFAULT 'Requested',
    requested_by  TEXT NOT NULL DEFAULT '',
    scheduled_for TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now_iso():
    return datetime.now().replace(microsecond=0).isoformat()


def get_setting(conn, key, default=None):
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn, key, value):
    conn.execute(
        "INSERT INTO settings(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def next_ref(conn):
    """Next ticket reference CD-N. N tracks the max id so refs stay unique and
    monotonic even after deletions."""
    row = conn.execute("SELECT COALESCE(MAX(id),0) AS m FROM tickets").fetchone()
    return "CD-%d" % (row["m"] + 1001)


def sla_due(priority, created=None):
    base = created or datetime.now()
    if isinstance(base, str):
        base = datetime.fromisoformat(base)
    return (base + timedelta(hours=SLA_HOURS.get(priority, 48))).replace(
        microsecond=0
    ).isoformat()


def create_ticket(conn, subject, description, name, email,
                  category="Other", priority="Medium", status="New"):
    """Insert a ticket and return (id, ref). Shared by the web form, the
    staff "new ticket" screen and the email-ingest poller so the reference,
    SLA target and timestamps are produced the same way everywhere."""
    if priority not in PRIORITIES:
        priority = "Medium"
    if category not in CATEGORIES:
        category = "Other"
    ts = now_iso()
    ref = next_ref(conn)
    cur = conn.execute(
        "INSERT INTO tickets(ref,subject,description,requester_name,requester_email,"
        "category,priority,status,due_at,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (ref, subject, description or "", name, email, category, priority, status,
         sla_due(priority), ts, ts))
    return cur.lastrowid, ref


def init_db():
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        # Seed only once, on an empty users table.
        if conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"] == 0:
            _seed(conn)
            conn.commit()
    finally:
        conn.close()


def _seed(conn):
    """Seed an admin + demo rows so the app is immediately usable. The admin
    password comes from ADMIN_PASSWORD (env) or defaults to 'changeme' — the
    login page warns while the default is in place."""
    admin_pw = os.environ.get("ADMIN_PASSWORD", "changeme")
    ts = now_iso()
    conn.execute(
        "INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
        ("Admin", os.environ.get("ADMIN_EMAIL", "admin@church.local"),
         hash_pw(admin_pw), "admin", ts),
    )
    conn.execute(
        "INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
        ("Tech Volunteer", "tech@church.local",
         hash_pw("changeme"), "agent", ts),
    )
    set_setting(conn, "org_name", os.environ.get("ORG_NAME", "Grace Church"))
    set_setting(conn, "theme", "violet")

    assets = [
        ("AV-001", "Sanctuary Mixing Desk", "Mixer", "In Use", "Sanctuary", "AV Team"),
        ("AV-002", "Wireless Handheld Mic", "Microphone", "In Use", "Sanctuary", "Worship"),
        ("IT-010", "Welcome Desk Laptop", "Laptop", "In Use", "Foyer", "Hospitality"),
        ("IT-011", "Office Printer", "Printer", "In Repair", "Office", "Admin"),
        ("AV-020", "Main Projector", "Projector", "In Use", "Sanctuary", "AV Team"),
    ]
    for tag, name, cat, st, loc, who in assets:
        conn.execute(
            "INSERT INTO assets(tag,name,category,status,location,assigned_to,created_at)"
            " VALUES(?,?,?,?,?,?,?)", (tag, name, cat, st, loc, who, ts))

    demo = [
        ("No sound from stage left speaker", "Sound / AV", "High", "In Progress",
         "Dave (Worship)", "dave@church.local"),
        ("Welcome desk laptop won't connect to WiFi", "Network / WiFi", "Medium", "Open",
         "Sarah", "sarah@church.local"),
        ("Need projector slides advanced during service", "Projection / Screens", "Low", "New",
         "Youth Team", "youth@church.local"),
    ]
    for subj, cat, pri, st, rname, remail in demo:
        ref = next_ref(conn)
        due = sla_due(pri)
        conn.execute(
            "INSERT INTO tickets(ref,subject,description,requester_name,requester_email,"
            "category,priority,status,due_at,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (ref, subj, "Submitted via the help desk.", rname, remail, cat, pri, st,
             due, ts, ts))

    conn.execute(
        "INSERT INTO changes(title,description,risk,status,requested_by,created_at,updated_at)"
        " VALUES(?,?,?,?,?,?,?)",
        ("Upgrade sanctuary WiFi access points",
         "Replace two ageing APs to improve coverage during services.",
         "Medium", "Requested", "AV Team", ts, ts))
