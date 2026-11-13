"""Email in and out for ChurchDesk — stdlib only (smtplib + imaplib).

Outbound: an automatic confirmation to the requester when a ticket is created.
Inbound:  poll an IMAP mailbox and turn each new message into a ticket.

Both are no-ops when their config is absent, so the app runs fine with no mail
set up at all — email just switches on once the env vars are present.
"""

import email as emaillib
import imaplib
import smtplib
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import parseaddr

import db


# --------------------------------------------------------------------------
# Outbound
# --------------------------------------------------------------------------
def send_email(cfg, to_addr, subject, body):
    """Send one plain-text email using the SMTP_* config. Returns True on
    success, False if email is off or the send fails (never raises into a
    request — a confirmation that can't go out must not break ticket creation)."""
    if not cfg.get("EMAIL_ENABLED") or not to_addr:
        return False
    msg = EmailMessage()
    msg["From"] = "%s <%s>" % (cfg.get("EMAIL_FROM_NAME", "Help Desk"),
                               cfg["SMTP_FROM"])
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=20) as s:
            if cfg.get("SMTP_TLS", True):
                s.starttls()
            if cfg.get("SMTP_USER"):
                s.login(cfg["SMTP_USER"], cfg.get("SMTP_PASSWORD") or "")
            s.send_message(msg)
        return True
    except Exception as exc:  # noqa: BLE001 — log and carry on
        print("[email] send failed: %s" % exc, flush=True)
        return False


def confirmation_body(cfg, ref, subject, category, priority, status, track_url):
    org = cfg.get("ORG_NAME", "Our Church")
    return (
        "Hi,\n\n"
        "Thanks for contacting the %s help desk. Your request has been logged.\n\n"
        "  Reference: %s\n"
        "  Summary:   %s\n"
        "  Category:  %s\n"
        "  Priority:  %s\n"
        "  Status:    %s\n\n"
        "Keep your reference number — you can check progress any time here:\n"
        "  %s\n\n"
        "The tech team will be in touch.\n\n"
        "— %s Help Desk\n"
        % (org, ref, subject, category, priority, status, track_url, org)
    )


def send_ticket_confirmation(cfg, ticket, track_url):
    """Email the requester the details of a freshly created ticket."""
    body = confirmation_body(
        cfg, ticket["ref"], ticket["subject"], ticket["category"],
        ticket["priority"], ticket["status"], track_url)
    return send_email(cfg, ticket["requester_email"],
                      "[%s] We got your request" % ticket["ref"], body)


# --------------------------------------------------------------------------
# Inbound — poll an IMAP inbox and create a ticket per new message
# --------------------------------------------------------------------------
def _decode(value):
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:  # noqa: BLE001
        return value or ""


def _plain_body(msg):
    """Best-effort plain-text body of an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and \
                    "attachment" not in str(part.get("Content-Disposition", "")):
                try:
                    return part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", "replace").strip()
                except Exception:  # noqa: BLE001
                    continue
        return ""
    try:
        return msg.get_payload(decode=True).decode(
            msg.get_content_charset() or "utf-8", "replace").strip()
    except Exception:  # noqa: BLE001
        return ""


def fetch_inbox(cfg):
    """Connect to the configured IMAP mailbox, turn every unseen message into a
    ticket (status New), send each sender a confirmation, and mark the message
    read. Returns the number of tickets created. No-op without IMAP config.

    shortcut: no Message-ID de-dup — a message read once is flagged \\Seen and
    skipped next poll; upgrade to storing Message-ID if a provider re-delivers.
    """
    if not cfg.get("IMAP_HOST"):
        return 0
    created = 0
    imap = imaplib.IMAP4_SSL(cfg["IMAP_HOST"], cfg.get("IMAP_PORT", 993))
    try:
        imap.login(cfg["IMAP_USER"], cfg["IMAP_PASSWORD"])
        imap.select(cfg.get("IMAP_FOLDER", "INBOX"))
        typ, data = imap.search(None, "UNSEEN")
        if typ != "OK":
            return 0
        ids = data[0].split()
        conn = db.get_db()
        try:
            for mid in ids:
                typ, raw = imap.fetch(mid, "(RFC822)")
                if typ != "OK" or not raw or not raw[0]:
                    continue
                msg = emaillib.message_from_bytes(raw[0][1])
                name, addr = parseaddr(msg.get("From", ""))
                subject = _decode(msg.get("Subject", "")).strip() or "(no subject)"
                body = _plain_body(msg)
                _id, ref = db.create_ticket(
                    conn, subject[:200], body, (name or addr or "Email sender"),
                    addr or "", category="Other", priority="Medium", status="New")
                conn.commit()
                created += 1
                imap.store(mid, "+FLAGS", "\\Seen")
                if addr:
                    ticket = {"ref": ref, "subject": subject, "category": "Other",
                              "priority": "Medium", "status": "New",
                              "requester_email": addr}
                    url = cfg.get("PUBLIC_URL", "").rstrip("/") + "/track?ref=" + ref
                    send_ticket_confirmation(cfg, ticket, url)
        finally:
            conn.close()
    finally:
        try:
            imap.logout()
        except Exception:  # noqa: BLE001
            pass
    return created
