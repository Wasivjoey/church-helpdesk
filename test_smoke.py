"""Self-check for ChurchDesk. Runs against a throwaway SQLite file so it never
touches real data. Run: python3 test_smoke.py  (exit 0 = all good)."""
import os
import tempfile

os.environ["DATABASE_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")
os.environ["SECRET_KEY"] = "test"

import app as appmod  # noqa: E402  (after env is set)

a = appmod.create_app()
a.testing = True
c = a.test_client()


def ok(cond, msg):
    assert cond, "FAIL: " + msg
    print("ok -", msg)


# Public portal loads and a request can be submitted without login.
ok(c.get("/").status_code == 200, "portal loads")
r = c.post("/submit", data={"name": "Pat", "email": "pat@x.org",
                            "subject": "Projector dead", "priority": "High",
                            "category": "Projection / Screens"},
           follow_redirects=True)
ok(r.status_code == 200 and b"CD-" in r.data, "public ticket submitted, ref shown")

# Protected pages redirect to login when logged out.
ok(c.get("/dashboard").status_code == 302, "dashboard needs login")

# Seeded admin can log in.
r = c.post("/login", data={"email": "admin@church.local", "password": "changeme"},
           follow_redirects=True)
ok(b"Dashboard" in r.data or b"stand today" in r.data, "admin login works")
ok(c.get("/dashboard").status_code == 200, "dashboard loads after login")

# The new ticket is listed and can be updated through the workflow.
r = c.get("/tickets")
ok(b"Projector dead" in r.data, "ticket appears in list")
tid = None
with a.app_context():
    import db
    conn = db.get_db()
    tid = conn.execute("SELECT id FROM tickets WHERE subject=?",
                       ("Projector dead",)).fetchone()["id"]
    conn.close()
r = c.post("/tickets/%d/update" % tid,
           data={"status": "Resolved", "priority": "High", "category": "Other"},
           follow_redirects=True)
ok(b"updated" in r.data, "ticket status updated to Resolved")

# Comment posts.
r = c.post("/tickets/%d/comment" % tid, data={"body": "Swapped the bulb."},
           follow_redirects=True)
ok(b"Swapped the bulb." in r.data, "comment posted")

# Asset + change create.
r = c.post("/assets/save", data={"tag": "AV-099", "name": "Test Speaker"},
           follow_redirects=True)
ok(b"AV-099" in r.data, "asset created")
r = c.post("/changes/save", data={"title": "Test change", "risk": "Low",
                                  "status": "Requested"}, follow_redirects=True)
ok(b"Test change" in r.data, "change created")

# PWA plumbing.
ok(c.get("/manifest.webmanifest").status_code == 200, "manifest serves")
ok(c.get("/sw.js").status_code == 200, "service worker serves")

# Inbox-poll endpoint refuses without the shared secret.
ok(c.get("/tasks/fetch-email").status_code == 403, "fetch-email guarded")

# Confirmation email is a safe no-op when SMTP isn't configured.
import email_util  # noqa: E402
ok(email_util.send_email({"EMAIL_ENABLED": False}, "x@y.z", "s", "b") is False,
   "send_email no-op without SMTP config")
body = email_util.confirmation_body(
    {"ORG_NAME": "Grace"}, "CD-1001", "Mic dead", "Sound / AV", "High", "New",
    "http://x/track?ref=CD-1001")
ok("CD-1001" in body and "Mic dead" in body and "track?ref=CD-1001" in body,
   "confirmation body has ref, subject and track link")

# Logo: default serves, upload via settings serves the uploaded bytes.
ok(c.get("/logo").status_code == 200, "default logo serves")
import io  # noqa: E402
png = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
       b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
       b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
r = c.post("/settings", data={"org_name": "Grace", "theme": "violet",
                              "logo": (io.BytesIO(png), "logo.png")},
           content_type="multipart/form-data", follow_redirects=True)
ok(r.status_code == 200, "logo upload accepted")
r = c.get("/logo")
ok(r.status_code == 200 and r.data == png and r.mimetype == "image/png",
   "uploaded logo served from DB")

print("\nAll smoke checks passed.")
