# Production Deployment Guide

End-to-end walkthrough for taking this app live on **Railway** with a managed **Postgres** database. Total time: ~15 minutes for the first deploy, then `git push` for every change after that.

---

## Table of contents

1. [What you'll end up with](#what-youll-end-up-with)
2. [Prerequisites](#prerequisites)
3. [Step 1 — Create the Railway project](#step-1--create-the-railway-project)
4. [Step 2 — Add the Postgres database](#step-2--add-the-postgres-database)
5. [Step 3 — First deploy](#step-3--first-deploy)
6. [Step 4 — Verify the deploy](#step-4--verify-the-deploy)
7. [Step 5 — Custom domain (optional)](#step-5--custom-domain-optional)
8. [Continuous delivery: every `git push`](#continuous-delivery-every-git-push)
9. [Monitoring & logs](#monitoring--logs)
10. [Backup, restore, direct DB access](#backup-restore-direct-db-access)
11. [Rollback](#rollback)
12. [Troubleshooting](#troubleshooting)
13. [Post-launch hardening](#post-launch-hardening)
14. [Cost expectations](#cost-expectations)

---

## What you'll end up with

| Piece | Hosted on | URL pattern |
|---|---|---|
| Flask API + PWA shell | Railway (gunicorn) | `https://<service>.up.railway.app` |
| Postgres database | Railway plugin | private network only |
| Source of truth | GitHub | `https://github.com/bomino/SuiviDepenses` |

Auto-deploy: every push to `main` rebuilds and replaces the running container with **zero downtime** (Railway uses the `/health` endpoint to gate traffic).

---

## Prerequisites

- A Railway account: https://railway.com — sign up with the same GitHub account that owns the repo. The free Trial tier is enough to validate the deploy; the **Hobby** plan ($5/mo with $5 of usage credit) is the minimum for keeping a service running 24/7.
- The repo `bomino/SuiviDepenses` already has the deployment artifacts:
  - `Procfile` → `web: gunicorn -b 0.0.0.0:$PORT -w 2 --access-logfile - server:app`
  - `requirements.txt` → Flask, gunicorn, psycopg
  - `.python-version` → `3.12`
  - `server.py` → reads `DATABASE_URL` and switches engine

If you're starting with a fresh fork, push it to GitHub first.

---

## Step 1 — Create the Railway project

1. Open https://railway.com/dashboard → **New Project**.
2. Choose **Deploy from GitHub repo**.
3. The first time you do this, Railway will prompt you to install the **Railway** GitHub app. Grant it access to `bomino/SuiviDepenses` (or all your repos — your call).
4. Pick the repo. Railway clones it and starts a Nixpacks build.

What Nixpacks does, automatically:

- Detects Python via `.python-version` and `requirements.txt`.
- Runs `pip install -r requirements.txt`.
- Reads `Procfile` and uses its `web:` line as the start command.

You don't need to write a Dockerfile.

> **First build will fail.** That's expected — there's no `DATABASE_URL` yet. The next step fixes it.

---

## Step 2 — Add the Postgres database

1. In the project view, click **+ New** → **Database** → **Add PostgreSQL**.
2. Railway provisions a Postgres 16 instance in the same project.
3. Click on the **service** (your app, not the database) → **Variables** tab.
4. Click **+ New Variable** → **Add Reference** → pick the Postgres service → **`DATABASE_URL`**. Railway will inject it as a *reference*, so if you ever rotate the DB credentials it updates automatically.

After saving, Railway redeploys the service. This time:

- `DATABASE_URL` is set, so `server.py` flips into Postgres mode.
- `init_db()` runs `CREATE TABLE IF NOT EXISTS` — schema is ready on first boot.
- gunicorn boots two workers, each opening a connection pool of 1–5 connections.

---

## Step 2.5 — Set required environment variables

Still in the service's **Variables** tab, add these three:

| Variable | Value | Why |
|---|---|---|
| `SECRET_KEY` | a long random string (e.g. `python -c "import secrets; print(secrets.token_hex(32))"`) | Signs the session cookies. **Required in production** — `server.py` refuses to boot without it when `DATABASE_URL` is set. |
| `INITIAL_USERNAME` | the first admin's username (e.g. `lawry`) | One-time bootstrap. After the first user exists, this var is ignored on subsequent boots. |
| `INITIAL_PASSWORD` | a strong password for that user | Same — read once on the very first boot, then irrelevant. |

After the first deploy succeeds, you may delete `INITIAL_USERNAME` / `INITIAL_PASSWORD` from Railway — they're not read again. **Do not** delete `SECRET_KEY`; rotating it logs everyone out (sessions become invalid).

To rotate `SECRET_KEY` later, generate a new value and replace it. All existing sessions become invalid; users re-login.

---

## Step 3 — First deploy

Railway auto-builds whenever you push to `main`, but the **first time** you'll trigger it manually:

1. **Settings** tab on the service → **Networking** section → click **Generate Domain**. You get `https://<something>.up.railway.app`.
2. **Deployments** tab → if the last deploy is still showing the failed build from Step 1, click **Deploy** → **Redeploy** to use the new variables.
3. Watch the build log. Successful boot looks like:

```
==> Building with Nixpacks
   ✓ pip install -r requirements.txt (Flask, gunicorn, psycopg, psycopg-pool)
==> Starting Container
[INFO] Starting gunicorn 23.x.x
[INFO] Listening at: http://0.0.0.0:8080 (1)
[INFO] Using worker: sync
[INFO] Booting worker with pid: 7
[INFO] Booting worker with pid: 8
```

---

## Step 4 — Verify the deploy

Three checks:

```bash
APP=https://<your-service>.up.railway.app

# 1. Health endpoint should report engine=postgres
curl $APP/health
# → {"engine":"postgres","ok":true}

# 2. The frontend HTML loads
curl -s $APP/ -o /dev/null -w "%{http_code}\n"
# → 200

# 3. API works (will be empty array on first deploy)
curl $APP/api/expenses
# → []
```

Open `$APP` in your browser. The DB indicator pill in the header should switch from `local` to `SQLite` (the label is generic — both Postgres and SQLite show as the "shared backend" mode). The PWA install banner appears after ~3 seconds.

---

## Step 5 — Custom domain (optional)

If you have your own domain (e.g. `expenses.yoursite.com`):

1. Service → **Settings** → **Networking** → **Custom Domain** → enter the hostname.
2. Railway shows you a CNAME target like `xxxxx.up.railway.app`.
3. In your DNS provider (Cloudflare, Namecheap, etc.) create a CNAME record:
   - Host: `expenses` (or `@` for an apex)
   - Target: the railway domain Railway showed you
4. Wait ~1–10 minutes for DNS to propagate. Railway issues a free Let's Encrypt cert automatically.
5. Service Manifest will display **Active** with HTTPS.

If you want apex (root domain like `yoursite.com`) you'll need an ALIAS / ANAME record (Cloudflare CNAME flattening works) — most providers don't support CNAME on apex.

---

## Continuous delivery: every `git push`

```bash
# Make changes locally
git add -A
git commit -m "..."
git push
```

Railway watches the `main` branch. Within ~2 minutes:

1. New build starts.
2. Nixpacks rebuilds (uses cached pip layer if `requirements.txt` is unchanged).
3. New container boots. Gunicorn loads the app, `init_db()` runs (idempotent — `CREATE TABLE IF NOT EXISTS`).
4. `/health` returns 200 → Railway flips traffic to the new container.
5. Old container drains in-flight requests, then exits.

No downtime, no data migration step needed for additive schema changes (because `init_db` only adds tables/columns, never drops). For destructive migrations, see [Backup, restore, direct DB access](#backup-restore-direct-db-access) below.

---

## Monitoring & logs

- **Logs:** service → **Logs** tab. Combined stdout/stderr from gunicorn (`--access-logfile -` in the Procfile sends access logs to stdout). Searchable, paginated.
- **Metrics:** service → **Metrics** tab. CPU, memory, network I/O, request rate. The free tier keeps ~7 days of history.
- **Build status:** **Deployments** tab shows every deploy with status, logs, and a one-click rollback button.
- **Email alerts:** Project settings → **Notifications** → enable build/crash alerts.

Want a third-party watcher (UptimeRobot, BetterStack)? Point it at `https://<app>/health`. Alert if `ok != true` or status ≠ 200 for >2 minutes.

---

## Backup, restore, direct DB access

### Backups

Railway **does not** auto-backup Postgres on the Hobby plan. You must take manual snapshots — or upgrade to Pro for daily automated backups.

To grab a snapshot manually:

```bash
# 1. Get the public connection string (the inside-VPC one won't work from your laptop)
#    Postgres service → Connect tab → "Public Network" connection string
PGURL="postgres://postgres:xxx@xxx.proxy.rlwy.net:1234/railway"

# 2. Dump
pg_dump "$PGURL" > backup-$(date +%Y%m%d).sql
```

Restore:

```bash
psql "$PGURL" < backup-20260430.sql
```

If you want this on a cron, run it on your laptop weekly or use a GitHub Actions scheduled workflow that uses `secrets.PGURL`.

### Direct DB access

Use the public connection string above with `psql`, DBeaver, TablePlus, etc. **The internal `DATABASE_URL` only works from inside the Railway network** — your app uses that one; you use the public one.

---

## Rollback

Two ways, both fast:

**A. From the Railway UI (recommended):**
Service → **Deployments** → find the last known-good deploy → click the menu → **Redeploy**. Container swap takes ~30s.

**B. From git:**

```bash
git revert <bad-commit-sha>
git push
```

This creates a new commit that undoes the bad one and triggers a fresh deploy. Preferred if the bad change has been live for a while because it preserves a clean linear history.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Build fails: `psycopg-binary` wheel not found | Python version drift | Check `.python-version` is `3.12`. Wheels exist for 3.10–3.13. |
| Build succeeds, container restarts in a loop | `DATABASE_URL` not set, or pointing at a dead DB | Variables tab → confirm reference to Postgres service exists. |
| `/health` returns 503 with `connection refused` | Postgres still booting (rare, only on first provision) | Wait 60s. If persistent, restart the Postgres service. |
| `/health` returns 503 with `password authentication failed` | DB credentials rotated but app cached old ones | Service → **Restart**. Variable references auto-refresh. |
| Frontend shows `local` indicator instead of detecting backend | `detectBackend()` got a non-2xx | Hit `/api/expenses` directly. If 200, hard-reload the page (the SW may have cached a stale shell). |
| Push doesn't trigger a build | GitHub app permissions revoked | https://github.com/settings/installations → Railway → Configure → Repository access. |
| `502 Bad Gateway` on first request after deploy | gunicorn workers still booting | Normal for ~5–10s after a new deploy. Should self-resolve. |
| `OperationalError: too many connections` | Pool size × workers > Postgres limit | Lower `DB_POOL_MAX` env var (default 5) or reduce gunicorn workers in `Procfile` (`-w 1`). Hobby Postgres has ~20 connection cap. |
| Login screen never appears after auth deploy | Service worker is serving the pre-auth HTML from cache | Hard-reload once (Ctrl/Cmd+Shift+R). Or DevTools → Application → Storage → Clear site data → reload. The cache version was bumped to `v4` to force this on next visit. |
| Login form shows "Invalid credentials" with the bootstrap user | Trailing whitespace in `INITIAL_PASSWORD` (paste artifact), or the user was created with a different password than you remember | `railway run python scripts/add_user.py <username> <new_password>` — overrides the password in place. Bootstrap is one-shot; only `add_user.py` resets passwords after the first user exists. |
| Locked out — every admin demoted, or last admin deleted at the DB level | Self-protection in the UI prevents this normally, but direct SQL or CLI edits could still strand the org | `railway run python scripts/add_user.py <user> <pass> --admin` — creates a new admin (or promotes an existing user) bypassing the in-app panel. |

---

## Managing users

Auth is **Flask-Login + bcrypt** (Tier 2) — session cookies, server-side password hashing, no third-party identity provider. The first user is bootstrapped via `INITIAL_USERNAME` / `INITIAL_PASSWORD` (Step 2.5) and **automatically receives admin rights**.

There are two ways to manage users after that — the in-app panel (preferred) and the CLI fallback.

### Roles

- **Admin** — sees every expense across the whole crew, can add/delete/rename users, can rename the project, can edit or delete anyone's expenses.
- **Worker** (default) — sees only their own expenses. Can add, edit, delete their own rows. Cannot see other users' data and cannot manage users.

The bootstrap user is admin; everyone they create is a worker by default unless the admin checks the "Make this user an admin" box.

### In-app panel (preferred)

After the bootstrap admin logs in, a **Manage Users** button appears in the header (visible only to admins). Click it:

- **Add user** — fill the form (username, password ≥6 chars, optional admin checkbox) → click *Add User*.
- **Reset password** — click the *Reset password* button next to a user → enter the new password in the prompt.
- **Promote / demote** — *Make admin* / *Make worker* button toggles their role.
- **Delete user** — red *Delete* button removes the user and **all their expenses** (cascade).

Self-protection: you cannot delete yourself or remove your own admin role from the panel. To recover from accidental lockout, see the CLI fallback below.

### CLI fallback (`scripts/add_user.py`)

Useful when:
- You haven't logged in yet (first deploy without `INITIAL_USERNAME`/`INITIAL_PASSWORD`).
- You demoted/locked yourself out of the panel and need to re-promote.
- You're scripting bulk onboarding.

```bash
# Locally (SQLite)
python scripts/add_user.py supervisor sitepass99
python scripts/add_user.py supervisor sitepass99 --admin   # create or update as admin

# On Railway (Postgres) — link to the WEB service first:
railway link    # Workspace → Project → Environment → web (NOT Postgres)
railway run python scripts/add_user.py supervisor sitepass99
railway run python scripts/add_user.py supervisor newpass99 --admin
```

The script doubles as a password reset — if the username exists, it updates the password (and, with `--admin`, promotes them).

### Force everyone to re-login

Rotate `SECRET_KEY` in Railway and let the service redeploy. All previously issued session cookies become invalid signatures and users see the login screen on next request.

---

## Further hardening (optional)

The deploy as documented is safe for trusted multi-user use. If you're going public-internet, stack these on top:

### Rate limiting

Install Flask-Limiter (`pip install Flask-Limiter`), wrap the app, then:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per minute"])

@app.route('/api/login', methods=['POST'])
@limiter.limit("5 per minute")
def api_login(): ...
```

That throttles brute-force login attempts to 5/min/IP. **Add `werkzeug.middleware.proxy_fix.ProxyFix`** when behind Railway's proxy so the limiter sees the real client IP, not the proxy's:

```python
from werkzeug.middleware.proxy_fix import ProxyFix
if USE_POSTGRES:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
```

### CSP header

One-liner blocks any future XSS from loading external scripts:

```python
@app.after_request
def csp(resp):
    resp.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'"
    return resp
```

### Secret scanning

GitHub scans public repos by default. If you ever commit a `DATABASE_URL` or other token, the push is blocked. Don't bypass with `--no-verify`. For private repos: enable Push Protection in repo Settings → Code security.

### Backups (paid Pro tier or DIY cron)

See [Backup, restore, direct DB access](#backup-restore-direct-db-access). At a minimum, schedule a weekly `pg_dump` to local disk before sharing the URL.

---

## Cost expectations

Railway's pricing is usage-based (CPU-seconds, RAM-seconds, network egress). Rough monthly estimates for this app:

| Component | Idle (no traffic) | ~100 req/day | ~10k req/day |
|---|---|---|---|
| App service (1 instance, 256 MB) | ~$2 | ~$3 | ~$5 |
| Postgres (1 GB storage) | ~$1 | ~$1 | ~$2 |
| Network egress | $0 | <$0.10 | ~$1 |
| **Total** | **~$3/mo** | **~$4/mo** | **~$8/mo** |

The Hobby plan's $5 included credit covers idle + light traffic. Heavy traffic, you'll pay overage on the credit. There's a usage-cap setting (Settings → **Usage Limits**) to prevent surprise bills.

If the app is genuinely zero-traffic for hours at a time, set the service to **Sleep** mode (Settings → **Sleep**) — Railway hibernates the container when idle and cold-starts on the next request (~3s wake). Cuts cost roughly in half for low-traffic apps.

---

## Reference

- Railway docs: https://docs.railway.com
- Nixpacks (the auto-builder): https://nixpacks.com
- psycopg pool tuning: https://www.psycopg.org/psycopg3/docs/advanced/pool.html
- gunicorn worker math: https://docs.gunicorn.org/en/stable/design.html#how-many-workers
