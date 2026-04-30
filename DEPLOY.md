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

---

## Post-launch hardening

The bare deploy is **functional but unauthenticated** — anyone with the URL can wipe the DB. Pick one before sharing the URL externally.

### Tier 1 — Shared bearer token (~30 min, ~40 LOC)

Set a `ACCESS_TOKEN` env var in Railway. Add a `before_request` hook in `server.py` that requires `Authorization: Bearer $ACCESS_TOKEN` on `/api/*`. Frontend prompts once, stashes in `localStorage`. Good for: 1–5 trusted users sharing a secret.

### Tier 2 — Multi-user (~2 hours, Flask-Login + bcrypt)

Add a `users` table. Use Flask-Login for sessions, bcrypt for password hashing. Add a `/login` page. Good for: 5–20 named users you control.

### Tier 3 — Supabase Auth (~3 hours)

Use Supabase as the identity provider. Frontend uses `@supabase/supabase-js` for login (email + magic link or OAuth). Flask verifies the JWT on every API call using PyJWT and Supabase's JWT secret. Good for: real product, social login, multi-tenant.

> Pick Tier 1 first if you're racing to hand a URL to a foreman tonight. Upgrade later — Tier 1 is a strict subset of every other approach, so no migration cost.

### Other quick wins

- **Rate limiting:** add Flask-Limiter (`pip install Flask-Limiter`), 60 req/min per IP. Stops trivial scraping.
- **Secret scanning:** GitHub has it on by default for public repos. If you ever commit a `DATABASE_URL`, GitHub blocks the push. Don't bypass.
- **HTTPS-only cookies / sessions:** if you add any auth that uses cookies, set `SESSION_COOKIE_SECURE = True` in the Postgres branch of `server.py`.
- **CSP header:** `Content-Security-Policy: default-src 'self'` blocks any future XSS from loading external scripts. One-line Flask response header.

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
