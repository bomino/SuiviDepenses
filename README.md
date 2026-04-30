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

### Option 2: Local server (shared SQLite storage)

```bash
pip install -r requirements.txt
python server.py
```

Open `http://localhost:5000`. All users on the network see the same database.

> **Security note:** the server has no authentication. It binds to `0.0.0.0`, so anyone on the LAN can read, modify, or wipe expenses. Run it only on a trusted network, or put it behind a reverse proxy with auth. Bind to `127.0.0.1` (edit `server.py`) if you only need single-machine access.

## Files

| File | Purpose |
|---|---|
| `index.html` | PWA frontend with dark UI |
| `manifest.json` | PWA manifest |
| `sw.js` | Service worker for offline caching |
| `server.py` | Flask + SQLite API backend |
| `requirements.txt` | Python dependency (Flask) |

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