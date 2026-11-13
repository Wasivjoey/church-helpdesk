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

print("\nAll smoke checks passed.")
