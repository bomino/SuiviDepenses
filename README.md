# Construction Expense Tracker

A bilingual (EN/FR) PWA for tracking construction project expenses. Works standalone via localStorage or with a Flask + SQLite backend for shared multi-user access. Deployable on GitHub Pages.

## Features

- Add, edit, delete expenses with category, amount, date, paid-by, status, and notes
- Construction-specific categories: Materials, Labor, Equipment, Permits, Subcontractors, Transport, Utilities, Misc
- Status tracking: Paid, Pending, Unpaid
- Dashboard with live totals (total, paid, unpaid, pending)
- Filter by category, status, date range, and text search
- CSV export with translated headers
- Bilingual EN/FR toggle — French mode displays amounts in FCFA
- PWA installable on mobile and desktop
- Hybrid storage: auto-detects SQLite backend; falls back to localStorage

## Quickstart

### Option 1: GitHub Pages (zero setup)

Push `index.html`, `manifest.json`, and `sw.js` to a repo with GitHub Pages enabled. Open the URL — data persists in the browser (localStorage; per-device, no shared state).

### Option 2: Local server (SQLite, single machine or LAN)

```bash
pip install -r requirements.txt
python server.py
```

Open `http://localhost:5000`. Data goes to `expenses.db` next to `server.py`. Anyone on the network can hit the server.

### Option 3: Production deploy (Railway + Postgres)

The same `server.py` switches to Postgres automatically when `DATABASE_URL` is set in the environment. On Railway:

1. Connect the GitHub repo and add a Postgres plugin — Railway injects `DATABASE_URL` for you.
2. The included `Procfile` runs `gunicorn` with two workers.
3. First boot creates the schema (`CREATE TABLE IF NOT EXISTS`).

Locally you can mimic prod by exporting `DATABASE_URL=postgres://...` before running, or just leave it unset to use SQLite.

> **Security note:** there is no authentication. Once on a public URL, anyone with the URL can read, modify, or wipe expenses. Add an auth layer (shared bearer token, basic auth, or a real identity provider) before sharing the URL.

## Files

| File | Purpose |
|---|---|
| `index.html` | PWA frontend with dark UI |
| `manifest.json` | PWA manifest |
| `sw.js` | Service worker for offline caching |
| `server.py` | Flask API backend (SQLite locally, Postgres if `DATABASE_URL` set) |
| `Procfile` | Production process declaration (`gunicorn`) |
| `requirements.txt` | Python dependencies (Flask, gunicorn, psycopg) |
| `scripts/make_icons.py` | Build-time icon regenerator (Pillow, not a runtime dep) |

## API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/expenses` | List all expenses |
| POST | `/api/expenses` | Create expense |
| PUT | `/api/expenses/<id>` | Update expense |
| DELETE | `/api/expenses/<id>` | Delete expense |
| DELETE | `/api/expenses/clear` | Delete all expenses |
| GET | `/api/project` | Get project name |
| PUT | `/api/project` | Set project name |