# ChurchDesk — User Manual

A plain-language guide to every feature of the ChurchDesk help desk. ChurchDesk
is an IT Service Management (ITSM) and help desk app for churches. It runs as a
website and as an installable app (PWA) on phones, tablets and computers.

There are two kinds of people who use it:

- **Requesters** — anyone in the church who needs help (volunteers, staff,
  ministry leads). They do **not** need an account.
- **Staff** — the tech / AV team. They log in to work on requests. Staff are
  either **Agents** (work tickets) or **Admins** (everything, plus Team and
  Settings).

---

## 1. The public help desk (no login needed)

### 1.1 Submitting a request — the home page (`/`)
This is the first page anyone sees. The left panel welcomes them; the right
panel is the request form. A requester fills in:

- **Your name** — who is reporting the problem.
- **Email** — so the team can reach them (and so they can look the request up).
- **What's the problem? (summary)** — a one-line description.
- **Category** — the type of problem (Sound / AV, Computers, Network / WiFi,
  Projection / Screens, Lighting, Phones, Accounts / Login, Facilities,
  Printing, Other).
- **How urgent?** — Low, Medium, High or Urgent. This sets the response target
  (see **SLA** below).
- **Details (optional)** — anything extra: when it started, which room, what
  they already tried.

When they press **Send request**, the ticket is created and they are shown a
**reference number** such as `CD-1001`. Tell requesters to keep this number —
it's how they track progress.

### 1.2 Tracking a request — `/track`
Reached from **Track a request** in the top bar, or automatically after
submitting. The requester types their reference number (e.g. `CD-1001`) and
presses **Check status**. They then see:

- the request's current **status**,
- its category and priority,
- all **public updates** the team has posted.

Internal staff notes are never shown here — only replies the team marked as
public. If the number is wrong, a friendly "no request found" message appears.

---

## 2. Logging in (staff)

**Staff login** in the top bar opens `/login`. Enter your email and password.

- On the very first run the app creates one admin account:
  **admin@church.local** with password **changeme**. A warning banner shows on
  the login page until that default password is changed (do it in **Settings**).
- Wrong details show "Wrong email or password."
- **Log out** is in the top bar once you're signed in.

---

## 3. Dashboard (staff home)

After login you land on the **Dashboard** — a quick picture of where things
stand. It has:

- **Four coloured tiles**: Open tickets, Overdue (SLA), Unassigned, and Assets
  tracked. Each tile is a link that jumps to the matching list.
- **Open by priority** — how many active tickets sit at each priority, plus a
  line showing change requests in flight and assets in repair.
- **By status** — a count of tickets in each workflow stage; click a status to
  filter the ticket list to it.
- **Recent activity** — the eight most recently updated tickets. Click any row
  to open it.
- **+ New ticket** button — for logging a request on someone's behalf.

---

## 4. Tickets

A ticket is one request for help. Tickets move through a **workflow** of six
stages: **New → Open → In Progress → On Hold → Resolved → Closed**. The first
four are "active"; Resolved and Closed are "done".

### 4.1 Ticket list — `/tickets`
A searchable, filterable table of every ticket. Controls at the top:

- **Search** — matches the reference, subject, or requester name.
- **Status** — any status, "Open (active)", or one specific stage.
- **Priority** — filter to Low / Medium / High / Urgent.
- **Mine** — tick to show only tickets assigned to you.

Each row shows the reference, subject + requester, category, priority, status,
assignee and the **due date**. A due date in red means the ticket is **overdue**
against its SLA target. Click any row to open the ticket.

### 4.2 Workflow board — `/tickets/board`
The same tickets shown as a **Kanban board**: one column per stage, each ticket
a card. Good for a visual sweep of the team's workload. Click a card to open and
update it. Use **List view** to switch back to the table.

### 4.3 Ticket detail — open a ticket
The detail page has three parts:

- **Details** — the full description, category, priority, and an "⚠ Overdue"
  flag if it's past its SLA target while still active.
- **Conversation** — the thread of replies. Each reply shows the author and
  time. Use the box at the bottom to post a reply. Tick **Internal note** to
  make it staff-only (highlighted, and hidden from the requester's tracking
  page). Leave it unticked for a public update the requester will see.
- **Manage** (right side) — change the **Status**, **Priority**, **Category**,
  **Assigned to** (any staff member, or Unassigned), and **Linked asset** (tie
  the ticket to a piece of equipment). Press **Save changes**. Moving a ticket
  to Resolved or Closed stamps the time it was resolved; moving it back to an
  active stage clears that. Changing priority recalculates the SLA target.

### 4.4 New ticket — `/tickets/new`
For staff logging a request on behalf of a walk-up or phone call. Same fields as
the public form, plus optional requester name/email. New tickets created here
start at **Open**. After saving you go straight to the ticket.

### 4.5 SLA / due dates
Every active ticket has a **due target** based on its priority:

| Priority | Respond within |
|----------|----------------|
| Urgent   | 4 hours        |
| High     | 24 hours       |
| Medium   | 48 hours       |
| Low      | 72 hours       |

Past the target while still active, the ticket is **overdue** — shown in red in
the list and counted on the Dashboard. This is a visual prompt only; nothing is
auto-closed or auto-escalated.

---

## 5. Assets — `/assets`

A register of the equipment the tech team looks after. The left side is the
searchable list; the right side is one form used for both adding and editing.

Each asset has:

- **Tag** — a unique label, e.g. `AV-030` (used to link assets to tickets).
- **Name** — e.g. "Lobby TV".
- **Category** — Laptop, Desktop, Tablet, Phone, Microphone, Mixer, Speaker,
  Camera, Projector, Screen, Printer, Network Gear, Other.
- **Status** — In Use, Spare, In Repair, Retired.
- **Location** — where it lives, e.g. "Sanctuary".
- **Assigned to** — the ministry or person responsible.
- **Notes** — anything useful.

To add: fill the form and press **Save asset**. To edit: press **Edit** on a
row — it loads that asset into the form; change what you need and save. **Clear**
empties the form for a fresh entry. Only **Admins** can delete an asset. Each
tag must be unique; a duplicate is rejected with a message.

---

## 6. Changes — `/changes`

A register of planned work on systems and equipment (change management). Use it
to record, approve and schedule changes before they happen — e.g. replacing a
router or upgrading the WiFi.

Each change has:

- **Title** and **Description**.
- **Risk** — Low, Medium, High.
- **Status** — Requested → Approved → Scheduled → Done (or Rejected).
- **Requested by**.
- **Scheduled for** — the planned date.

Add and edit work the same way as Assets: fill the form and **Save change**, or
press **Edit** on a row to load it. Done and Rejected changes sort to the bottom
of the list.

---

## 7. Team — `/team` (Admins only)

Manage who can log in.

- The table lists every staff member with their role and active/inactive state.
- **Add team member** — enter name, email, role (**Agent** or **Admin**) and a
  temporary password (defaults to `changeme`). The new person signs in with that
  and should change it in Settings.
- **Deactivate / Activate** — turn an account off without deleting it. A
  deactivated person can't log in. You can't deactivate your own account.

**Agent** vs **Admin**: Agents can do everything with tickets, assets and
changes. Only Admins see the **Team** and **Settings** menus and can delete
assets.

---

## 8. Settings — `/settings` (Admins only)

Make the app your own:

- **Church / organisation name** — shown in the header, footer, the installed
  app name and the page titles.
- **Logo** — upload your church's logo (PNG, JPG, SVG, WebP or GIF, up to 1 MB).
  It replaces the default headset everywhere: the header, the browser tab icon
  and the installed app icon. A small preview shows the current logo; tick
  **Remove logo** to go back to the default.
- **Colour theme** — five options (Violet, Ocean, Sunrise, Forest, Rose). The
  coloured dots preview each one. The choice re-themes the whole app instantly.
- **Change your password** — set a new password for your own account. Leave
  blank to keep the current one. This is where the first admin clears the
  default `changeme` warning.

Press **Save settings**.

---

## 9. Installing as an app (PWA)

ChurchDesk is installable on any device, so it opens like a normal app and works
offline for the pages you've already visited.

- **Phone / tablet (iOS Safari)**: open the site, tap **Share → Add to Home
  Screen**.
- **Android / Chrome**: open the site, use the **Install app** prompt or the
  browser menu → **Install**.
- **Desktop (Chrome / Edge)**: click the **install** icon in the address bar.

For install and offline to work, the site must be served over **HTTPS** (any
normal host does this). On a local test machine it works over `http://localhost`
too.

---

## 10. Email features

ChurchDesk can take requests by email and automatically reply to new tickets.
Both are optional and switch on once their settings are present.

### 10.1 Submit a ticket by email
Point ChurchDesk at a mailbox (for example `help@yourchurch.org`). Anyone who
emails that address gets a ticket created automatically:

- The email **subject** becomes the ticket summary.
- The email **body** becomes the details.
- The **sender's name and address** become the requester.
- New email tickets start at **New**, Medium priority, category **Other** — the
  team then triages them like any other ticket.

How it works: the app polls the mailbox over IMAP at the `/tasks/fetch-email`
address. Have a scheduler (a free cron job, Render Cron, etc.) call that address
every few minutes. Each already-read message is skipped, so nothing is
duplicated. Configure it with these environment variables:

| Variable        | What it is                                           |
|-----------------|------------------------------------------------------|
| `IMAP_HOST`     | mail server, e.g. `imap.gmail.com`                   |
| `IMAP_USER`     | the mailbox login                                    |
| `IMAP_PASSWORD` | the mailbox password / app-password                  |
| `IMAP_FOLDER`   | folder to read (default `INBOX`)                     |
| `INBOUND_SECRET`| a secret you choose; the poll URL must include it    |

Call it as `https://yourapp/tasks/fetch-email?key=YOUR_INBOUND_SECRET`.

### 10.2 Automatic confirmation reply
Whenever a ticket is created — from the web form, by staff, or by email — the
requester is automatically emailed a confirmation containing the **reference
number, summary, category, priority, status**, and a **link to track it**. This
needs outbound email set up:

| Variable         | What it is                                   |
|------------------|----------------------------------------------|
| `SMTP_HOST`      | mail server, e.g. `smtp.gmail.com`           |
| `SMTP_PORT`      | usually `587` (default)                      |
| `SMTP_USER`      | login for sending                            |
| `SMTP_PASSWORD`  | password / app-password                      |
| `SMTP_FROM`      | the "from" address shown to requesters       |
| `EMAIL_FROM_NAME`| the sender name, e.g. "Grace Help Desk"      |
| `PUBLIC_URL`     | your site's address, for the tracking link   |

If outbound email isn't configured, ticket creation still works — the
confirmation is simply skipped.

---

## 11. Tips for running it smoothly

- Change the default admin password the first time you log in (Settings).
- Give each real tech volunteer their own Agent account (Team) rather than
  sharing one login — the "Assigned to" field and reply authors then make sense.
- Use **Internal notes** for team-only chatter and plain replies for anything
  the requester should see on their tracking page.
- Keep the **Assets** register current and link equipment to tickets — over
  time you'll see which gear causes the most problems.
- Watch the **Overdue (SLA)** tile on the Dashboard to stay on top of promises.
