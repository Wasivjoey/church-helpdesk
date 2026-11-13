"""ChurchDesk — a colourful, easy-to-run IT Service Management & help desk for
churches. Public ticket portal + staff console (tickets, assets, changes).

Run locally:   python3 app.py    then open http://localhost:8001
Production:    gunicorn 'app:create_app()' --bind 0.0.0.0:8001
"""

import functools
import os
from datetime import datetime

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, send_from_directory, session, url_for)
from werkzeug.security import check_password_hash
from db import hash_pw as generate_password_hash

import db
import email_util
from db import (ASSET_CATEGORIES, ASSET_STATUSES, CATEGORIES, CHANGE_STATUSES,
                OPEN_STATUSES, PRIORITIES, RISK_LEVELS, TICKET_STATUSES)


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-change-me")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = bool(os.environ.get("DATABASE_URL_SECURE"))

    # Outbound email (auto-confirmation to requesters). All optional: if
    # SMTP_HOST is unset the app runs in "no email" mode and simply skips it.
    app.config["SMTP_HOST"] = os.environ.get("SMTP_HOST")
    app.config["SMTP_PORT"] = int(os.environ.get("SMTP_PORT", "587"))
    app.config["SMTP_USER"] = os.environ.get("SMTP_USER")
    app.config["SMTP_PASSWORD"] = os.environ.get("SMTP_PASSWORD")
    app.config["SMTP_FROM"] = os.environ.get(
        "SMTP_FROM", os.environ.get("SMTP_USER") or "help@church.local")
    app.config["SMTP_TLS"] = os.environ.get("SMTP_TLS", "1") != "0"
    app.config["EMAIL_FROM_NAME"] = os.environ.get("EMAIL_FROM_NAME", "Help Desk")
    app.config["EMAIL_ENABLED"] = bool(app.config["SMTP_HOST"])

    # Inbound email-to-ticket. Point these at the mailbox you want requests
    # sent to (e.g. an IMAP inbox for help@yourchurch.org). The /tasks/fetch-email
    # endpoint, called on a schedule, polls it and creates a ticket per message.
    app.config["IMAP_HOST"] = os.environ.get("IMAP_HOST")
    app.config["IMAP_PORT"] = int(os.environ.get("IMAP_PORT", "993"))
    app.config["IMAP_USER"] = os.environ.get("IMAP_USER")
    app.config["IMAP_PASSWORD"] = os.environ.get("IMAP_PASSWORD")
    app.config["IMAP_FOLDER"] = os.environ.get("IMAP_FOLDER", "INBOX")

    # Shared secret guarding the inbox-poll endpoint (?key= or X-Cron-Key).
    app.config["INBOUND_SECRET"] = os.environ.get("INBOUND_SECRET")
    # Public base URL used to build "track your request" links in emails.
    app.config["PUBLIC_URL"] = os.environ.get("PUBLIC_URL")

    db.init_db()

    def mail_cfg():
        """app.config plus the two per-request values the email module needs."""
        cfg = dict(app.config)
        cfg["ORG_NAME"] = db.get_setting(g.db, "org_name", "Our Church")
        cfg["PUBLIC_URL"] = app.config.get("PUBLIC_URL") or request.url_root
        return cfg

    def _confirm(ticket_id):
        """Email the requester the details of a just-created ticket."""
        t = g.db.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        if t and t["requester_email"]:
            url = mail_cfg()["PUBLIC_URL"].rstrip("/") + "/track?ref=" + t["ref"]
            email_util.send_ticket_confirmation(mail_cfg(), t, url)

    # ---- request-scoped db + current user -------------------------------
    @app.before_request
    def _open_db():
        g.db = db.get_db()

    @app.teardown_request
    def _close_db(exc):
        conn = getattr(g, "db", None)
        if conn is not None:
            conn.close()

    def current_user():
        uid = session.get("uid")
        if not uid:
            return None
        return g.db.execute(
            "SELECT * FROM users WHERE id=? AND is_active=1", (uid,)
        ).fetchone()

    @app.context_processor
    def _inject():
        org = db.get_setting(g.db, "org_name", "Our Church")
        return {
            "current_user": current_user(),
            "org_name": org,
            "theme": db.get_setting(g.db, "theme", "violet"),
            "STATUSES": TICKET_STATUSES, "PRIORITIES": PRIORITIES,
            "CATEGORIES": CATEGORIES,
        }

    # ---- CSRF: refuse cross-origin state changes ------------------------
    @app.before_request
    def _csrf():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            from urllib.parse import urlparse
            src = request.headers.get("Origin") or request.headers.get("Referer")
            if src and urlparse(src).netloc != request.host:
                abort(400)

    def login_required(fn):
        @functools.wraps(fn)
        def wrap(*a, **k):
            if not current_user():
                return redirect(url_for("login", next=request.path))
            return fn(*a, **k)
        return wrap

    def admin_required(fn):
        @functools.wraps(fn)
        def wrap(*a, **k):
            u = current_user()
            if not u or u["role"] != "admin":
                abort(403)
            return fn(*a, **k)
        return wrap

    # ===================================================================
    # Public portal
    # ===================================================================
    @app.route("/")
    def home():
        return render_template("portal.html")

    @app.route("/submit", methods=["POST"])
    def submit_ticket():
        f = request.form
        subject = (f.get("subject") or "").strip()
        name = (f.get("name") or "").strip()
        email = (f.get("email") or "").strip()
        if not (subject and name and email):
            flash("Please fill in your name, email and a short summary.", "error")
            return redirect(url_for("home"))
        tid, ref = db.create_ticket(
            g.db, subject, (f.get("description") or "").strip(), name, email,
            f.get("category"), f.get("priority"), "New")
        g.db.commit()
        _confirm(tid)
        flash("Request submitted! Your reference is %s — keep it to track progress."
              % ref, "success")
        return redirect(url_for("track", ref=ref))

    @app.route("/track")
    def track():
        ref = (request.args.get("ref") or "").strip().upper()
        ticket = None
        if ref:
            ticket = g.db.execute("SELECT * FROM tickets WHERE ref=?", (ref,)).fetchone()
        comments = []
        if ticket:
            comments = g.db.execute(
                "SELECT * FROM comments WHERE ticket_id=? AND internal=0 "
                "ORDER BY created_at", (ticket["id"],)).fetchall()
        return render_template("track.html", ticket=ticket, comments=comments, ref=ref)

    # ===================================================================
    # Auth
    # ===================================================================
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            pw = request.form.get("password") or ""
            row = g.db.execute(
                "SELECT * FROM users WHERE lower(email)=? AND is_active=1", (email,)
            ).fetchone()
            if row and check_password_hash(row["password_hash"], pw):
                session["uid"] = row["id"]
                nxt = request.args.get("next") or url_for("dashboard")
                return redirect(nxt)
            flash("Wrong email or password.", "error")
        default_pw = _default_admin_pw_in_use()
        return render_template("login.html", default_pw=default_pw)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("home"))

    def _default_admin_pw_in_use():
        row = g.db.execute("SELECT password_hash FROM users WHERE role='admin' "
                           "ORDER BY id LIMIT 1").fetchone()
        return bool(row and check_password_hash(row["password_hash"], "changeme"))

    # ===================================================================
    # Staff console
    # ===================================================================
    @app.route("/dashboard")
    @login_required
    def dashboard():
        c = g.db
        qmarks = ",".join("?" * len(OPEN_STATUSES))
        counts = {s: c.execute("SELECT COUNT(*) n FROM tickets WHERE status=?", (s,)
                               ).fetchone()["n"] for s in TICKET_STATUSES}
        open_n = c.execute(
            "SELECT COUNT(*) n FROM tickets WHERE status IN (%s)" % qmarks,
            tuple(OPEN_STATUSES)).fetchone()["n"]
        overdue = c.execute(
            "SELECT COUNT(*) n FROM tickets WHERE status IN (%s) AND due_at < ?"
            % qmarks, tuple(OPEN_STATUSES) + (db.now_iso(),)).fetchone()["n"]
        unassigned = c.execute(
            "SELECT COUNT(*) n FROM tickets WHERE assignee_id IS NULL AND status IN (%s)"
            % qmarks, tuple(OPEN_STATUSES)).fetchone()["n"]
        by_pri = {p: c.execute(
            "SELECT COUNT(*) n FROM tickets WHERE priority=? AND status IN (%s)" % qmarks,
            (p,) + tuple(OPEN_STATUSES)).fetchone()["n"] for p in PRIORITIES}
        recent = c.execute(
            "SELECT t.*, u.name AS assignee FROM tickets t "
            "LEFT JOIN users u ON u.id=t.assignee_id ORDER BY t.updated_at DESC LIMIT 8"
        ).fetchall()
        assets_n = c.execute("SELECT COUNT(*) n FROM assets").fetchone()["n"]
        repair_n = c.execute("SELECT COUNT(*) n FROM assets WHERE status='In Repair'"
                             ).fetchone()["n"]
        changes_open = c.execute(
            "SELECT COUNT(*) n FROM changes WHERE status NOT IN ('Done','Rejected')"
        ).fetchone()["n"]
        return render_template(
            "dashboard.html", counts=counts, open_n=open_n, overdue=overdue,
            unassigned=unassigned, by_pri=by_pri, recent=recent, now=db.now_iso(),
            assets_n=assets_n, repair_n=repair_n, changes_open=changes_open)

    # ---- tickets --------------------------------------------------------
    @app.route("/tickets")
    @login_required
    def tickets():
        c = g.db
        status = request.args.get("status", "")
        pri = request.args.get("priority", "")
        mine = request.args.get("mine")
        q = (request.args.get("q") or "").strip()
        sql = ("SELECT t.*, u.name AS assignee FROM tickets t "
               "LEFT JOIN users u ON u.id=t.assignee_id WHERE 1=1")
        args = []
        if status == "open":
            sql += " AND t.status IN (%s)" % ",".join("?" * len(OPEN_STATUSES))
            args += list(OPEN_STATUSES)
        elif status in TICKET_STATUSES:
            sql += " AND t.status=?"; args.append(status)
        if pri in PRIORITIES:
            sql += " AND t.priority=?"; args.append(pri)
        if mine and current_user():
            sql += " AND t.assignee_id=?"; args.append(current_user()["id"])
        if q:
            sql += " AND (t.subject LIKE ? OR t.ref LIKE ? OR t.requester_name LIKE ?)"
            args += ["%%%s%%" % q] * 3
        sql += " ORDER BY t.updated_at DESC"
        rows = c.execute(sql, args).fetchall()
        return render_template("tickets.html", tickets=rows, now=db.now_iso(),
                               status=status, pri=pri, mine=mine, q=q)

    @app.route("/tickets/board")
    @login_required
    def board():
        c = g.db
        cols = {}
        for s in TICKET_STATUSES:
            cols[s] = c.execute(
                "SELECT t.*, u.name AS assignee FROM tickets t "
                "LEFT JOIN users u ON u.id=t.assignee_id WHERE t.status=? "
                "ORDER BY t.priority DESC, t.updated_at DESC", (s,)).fetchall()
        return render_template("board.html", cols=cols, now=db.now_iso())

    @app.route("/tickets/<int:tid>")
    @login_required
    def ticket_detail(tid):
        c = g.db
        t = c.execute("SELECT t.*, u.name AS assignee FROM tickets t "
                      "LEFT JOIN users u ON u.id=t.assignee_id WHERE t.id=?",
                      (tid,)).fetchone()
        if not t:
            abort(404)
        comments = c.execute("SELECT * FROM comments WHERE ticket_id=? ORDER BY created_at",
                             (tid,)).fetchall()
        agents = c.execute("SELECT id,name FROM users WHERE is_active=1 ORDER BY name"
                           ).fetchall()
        assets = c.execute("SELECT id,tag,name FROM assets ORDER BY tag").fetchall()
        return render_template("ticket_detail.html", t=t, comments=comments,
                               agents=agents, assets=assets, now=db.now_iso())

    @app.route("/tickets/<int:tid>/update", methods=["POST"])
    @login_required
    def ticket_update(tid):
        c = g.db
        t = c.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()
        if not t:
            abort(404)
        f = request.form
        status = f.get("status") if f.get("status") in TICKET_STATUSES else t["status"]
        priority = f.get("priority") if f.get("priority") in PRIORITIES else t["priority"]
        category = f.get("category") if f.get("category") in CATEGORIES else t["category"]
        assignee = f.get("assignee_id") or None
        asset = f.get("asset_id") or None
        resolved_at = t["resolved_at"]
        if status in ("Resolved", "Closed") and not resolved_at:
            resolved_at = db.now_iso()
        if status in OPEN_STATUSES:
            resolved_at = None
        due = t["due_at"] if priority == t["priority"] else db.sla_due(priority)
        c.execute(
            "UPDATE tickets SET status=?,priority=?,category=?,assignee_id=?,asset_id=?,"
            "due_at=?,resolved_at=?,updated_at=? WHERE id=?",
            (status, priority, category, assignee, asset, due, resolved_at,
             db.now_iso(), tid))
        c.commit()
        flash("Ticket updated.", "success")
        return redirect(url_for("ticket_detail", tid=tid))

    @app.route("/tickets/<int:tid>/comment", methods=["POST"])
    @login_required
    def ticket_comment(tid):
        body = (request.form.get("body") or "").strip()
        if body:
            internal = 1 if request.form.get("internal") else 0
            g.db.execute(
                "INSERT INTO comments(ticket_id,author,body,internal,created_at) "
                "VALUES(?,?,?,?,?)",
                (tid, current_user()["name"], body, internal, db.now_iso()))
            g.db.execute("UPDATE tickets SET updated_at=? WHERE id=?", (db.now_iso(), tid))
            g.db.commit()
        return redirect(url_for("ticket_detail", tid=tid))

    @app.route("/tickets/new", methods=["GET", "POST"])
    @login_required
    def ticket_new():
        if request.method == "POST":
            f = request.form
            subject = (f.get("subject") or "").strip()
            if not subject:
                flash("A subject is required.", "error")
                return redirect(url_for("ticket_new"))
            tid, ref = db.create_ticket(
                g.db, subject, (f.get("description") or "").strip(),
                (f.get("requester_name") or "Walk-up").strip(),
                (f.get("requester_email") or "").strip(),
                f.get("category"), f.get("priority"), "Open")
            g.db.commit()
            _confirm(tid)
            return redirect(url_for("ticket_detail", tid=tid))
        return render_template("ticket_new.html")

    # ---- assets ---------------------------------------------------------
    @app.route("/assets")
    @login_required
    def assets():
        q = (request.args.get("q") or "").strip()
        sql = "SELECT * FROM assets WHERE 1=1"
        args = []
        if q:
            sql += " AND (tag LIKE ? OR name LIKE ? OR location LIKE ?)"
            args += ["%%%s%%" % q] * 3
        sql += " ORDER BY tag"
        rows = [dict(r) for r in g.db.execute(sql, args).fetchall()]
        return render_template("assets.html", assets=rows, q=q,
                               cats=ASSET_CATEGORIES, statuses=ASSET_STATUSES)

    @app.route("/assets/save", methods=["POST"])
    @login_required
    def asset_save():
        f = request.form
        aid = f.get("id")
        tag = (f.get("tag") or "").strip()
        name = (f.get("name") or "").strip()
        if not (tag and name):
            flash("Asset tag and name are required.", "error")
            return redirect(url_for("assets"))
        cat = f.get("category") if f.get("category") in ASSET_CATEGORIES else "Other"
        st = f.get("status") if f.get("status") in ASSET_STATUSES else "In Use"
        fields = (name, cat, st, (f.get("location") or "").strip(),
                  (f.get("assigned_to") or "").strip(), (f.get("notes") or "").strip())
        try:
            if aid:
                g.db.execute(
                    "UPDATE assets SET tag=?,name=?,category=?,status=?,location=?,"
                    "assigned_to=?,notes=? WHERE id=?", (tag,) + fields + (aid,))
            else:
                g.db.execute(
                    "INSERT INTO assets(tag,name,category,status,location,assigned_to,"
                    "notes,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (tag,) + fields + (db.now_iso(),))
            g.db.commit()
            flash("Asset saved.", "success")
        except Exception:
            flash("That asset tag is already in use.", "error")
        return redirect(url_for("assets"))

    @app.route("/assets/<int:aid>/delete", methods=["POST"])
    @admin_required
    def asset_delete(aid):
        g.db.execute("DELETE FROM assets WHERE id=?", (aid,))
        g.db.commit()
        flash("Asset deleted.", "success")
        return redirect(url_for("assets"))

    # ---- changes --------------------------------------------------------
    @app.route("/changes")
    @login_required
    def changes():
        rows = [dict(r) for r in g.db.execute(
            "SELECT * FROM changes ORDER BY "
            "CASE status WHEN 'Done' THEN 1 WHEN 'Rejected' THEN 1 "
            "ELSE 0 END, updated_at DESC").fetchall()]
        return render_template("changes.html", changes=rows, risks=RISK_LEVELS,
                               statuses=CHANGE_STATUSES)

    @app.route("/changes/save", methods=["POST"])
    @login_required
    def change_save():
        f = request.form
        cid = f.get("id")
        title = (f.get("title") or "").strip()
        if not title:
            flash("A change title is required.", "error")
            return redirect(url_for("changes"))
        risk = f.get("risk") if f.get("risk") in RISK_LEVELS else "Low"
        status = f.get("status") if f.get("status") in CHANGE_STATUSES else "Requested"
        vals = ((f.get("description") or "").strip(), risk, status,
                (f.get("requested_by") or "").strip(),
                (f.get("scheduled_for") or "").strip() or None)
        if cid:
            g.db.execute(
                "UPDATE changes SET title=?,description=?,risk=?,status=?,requested_by=?,"
                "scheduled_for=?,updated_at=? WHERE id=?",
                (title,) + vals + (db.now_iso(), cid))
        else:
            ts = db.now_iso()
            g.db.execute(
                "INSERT INTO changes(title,description,risk,status,requested_by,"
                "scheduled_for,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (title,) + vals + (ts, ts))
        g.db.commit()
        flash("Change saved.", "success")
        return redirect(url_for("changes"))

    # ---- team + settings (admin) ---------------------------------------
    @app.route("/team")
    @admin_required
    def team():
        rows = g.db.execute("SELECT * FROM users ORDER BY role,name").fetchall()
        return render_template("team.html", users=rows)

    @app.route("/team/save", methods=["POST"])
    @admin_required
    def team_save():
        f = request.form
        name = (f.get("name") or "").strip()
        email = (f.get("email") or "").strip().lower()
        if not (name and email):
            flash("Name and email are required.", "error")
            return redirect(url_for("team"))
        role = "admin" if f.get("role") == "admin" else "agent"
        pw = f.get("password") or "changeme"
        try:
            g.db.execute(
                "INSERT INTO users(name,email,password_hash,role,created_at) "
                "VALUES(?,?,?,?,?)",
                (name, email, generate_password_hash(pw), role, db.now_iso()))
            g.db.commit()
            flash("Team member added. Temporary password: %s" % pw, "success")
        except Exception:
            flash("That email is already registered.", "error")
        return redirect(url_for("team"))

    @app.route("/team/<int:uid>/toggle", methods=["POST"])
    @admin_required
    def team_toggle(uid):
        if uid == current_user()["id"]:
            flash("You can't deactivate your own account.", "error")
            return redirect(url_for("team"))
        g.db.execute("UPDATE users SET is_active = 1 - is_active WHERE id=?", (uid,))
        g.db.commit()
        return redirect(url_for("team"))

    @app.route("/settings", methods=["GET", "POST"])
    @admin_required
    def settings():
        if request.method == "POST":
            org = (request.form.get("org_name") or "").strip() or "Our Church"
            theme = request.form.get("theme") or "violet"
            db.set_setting(g.db, "org_name", org)
            db.set_setting(g.db, "theme", theme)
            # Optional: admin changes own password.
            pw = request.form.get("new_password") or ""
            if pw:
                g.db.execute("UPDATE users SET password_hash=? WHERE id=?",
                             (generate_password_hash(pw), current_user()["id"]))
            g.db.commit()
            flash("Settings saved.", "success")
            return redirect(url_for("settings"))
        themes = ["violet", "ocean", "sunrise", "forest", "rose"]
        return render_template("settings.html", themes=themes)

    # ===================================================================
    # PWA plumbing
    # ===================================================================
    @app.route("/sw.js")
    def service_worker():
        resp = send_from_directory(app.static_folder, "sw.js",
                                   mimetype="application/javascript")
        resp.headers["Service-Worker-Allowed"] = "/"
        resp.headers["Cache-Control"] = "no-cache"
        return resp

    @app.route("/manifest.webmanifest")
    def manifest():
        org = db.get_setting(g.db, "org_name", "Our Church")
        return jsonify({
            "name": "%s Help Desk" % org, "short_name": "ChurchDesk",
            "start_url": "/", "scope": "/", "display": "standalone",
            "background_color": "#0f172a", "theme_color": "#7c3aed",
            "description": "IT service management & help desk",
            "icons": [{"src": url_for("static", filename="icon.svg"),
                       "sizes": "any", "type": "image/svg+xml",
                       "purpose": "any maskable"}],
        })

    @app.route("/tasks/fetch-email", methods=["GET", "POST"])
    def fetch_email_task():
        """Poll the IMAP inbox and create a ticket per new message. Call it on a
        schedule (e.g. a cron job every few minutes), authenticated with
        INBOUND_SECRET as ?key= or an X-Cron-Key header."""
        secret = app.config.get("INBOUND_SECRET")
        provided = request.args.get("key") or request.headers.get("X-Cron-Key")
        if not secret or provided != secret:
            abort(403)
        created = email_util.fetch_inbox(mail_cfg())
        return jsonify({"created": created})

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}, 200

    @app.template_filter("dt")
    def _dt(value):
        if not value:
            return ""
        try:
            return datetime.fromisoformat(value).strftime("%b %-d, %Y · %-I:%M %p")
        except ValueError:
            return value

    @app.template_filter("overdue")
    def _overdue(due):
        try:
            return bool(due) and datetime.fromisoformat(due) < datetime.now()
        except ValueError:
            return False

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    app.run(host="0.0.0.0", port=port, debug=bool(os.environ.get("FLASK_DEBUG")))
