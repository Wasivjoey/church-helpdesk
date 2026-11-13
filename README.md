# ChurchDesk — IT Service Management & Help Desk

A colourful, easy-to-run help desk and ITSM tool for churches. Works as a
website **and** an installable PWA (add to home screen, offline app shell).
Self-contained Flask + SQLite — no setup beyond `pip install`.

## What it does
- **Public portal** (`/`) — anyone can submit a request with no account and gets
  a reference (e.g. `CD-1001`) to track it at `/track`.
- **Tickets** — list, search, filter, a Kanban **workflow board**, assignment,
  priority, category, SLA due-dates, public replies + internal notes.
- **Assets** — track kit (mics, laptops, projectors, printers) with tag,
  status, location; link assets to tickets.
- **Changes** — change requests with risk, approval status, and scheduling.
- **Team** — admins add agents/admins and activate/deactivate accounts.
- **Settings** — church name + 5 colour themes, pick without touching code.
- **Email in** — email a mailbox to open a ticket (IMAP poll at
  `/tasks/fetch-email`, called on a schedule).
- **Email out** — new tickets auto-send the requester a confirmation with the
  reference, details and a tracking link (SMTP).

## Run it
```bash
cd churchdesk
pip install -r requirements.txt
python3 app.py            # http://localhost:8001
```
First login (seeded): **admin@church.local** / **changeme** — change it in
Settings. Demo tickets, assets and a change are seeded so it's usable at once.

## Deploy (Render, Railway, Fly, any host)
```bash
gunicorn 'app:create_app()' --bind 0.0.0.0:$PORT
```
Env vars (all optional): `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`,
`ORG_NAME`, `DATABASE_PATH`, `PUBLIC_URL`. Serve over HTTPS so the PWA installs
and the service worker registers.

**Outbound email** (confirmation replies): `SMTP_HOST`, `SMTP_PORT`,
`SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `EMAIL_FROM_NAME`.

**Inbound email** (email-to-ticket): `IMAP_HOST`, `IMAP_PORT`, `IMAP_USER`,
`IMAP_PASSWORD`, `IMAP_FOLDER`, `INBOUND_SECRET`. Schedule a call to
`/tasks/fetch-email?key=$INBOUND_SECRET` every few minutes. See `MANUAL.md` §10.

## Test
```bash
python3 test_smoke.py     # 12 end-to-end checks, exit 0 = all good
```
