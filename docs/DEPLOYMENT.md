# Deployment Guide

Complete deployment guide for Fuze - Intelligent Bookmark Manager.

> [!WARNING]
> **Update:** the "Hugging Face Spaces is free" claims below are partly **out
> of date**. Hugging Face changed platform policy: creating a new Docker-SDK
> Space on the free `cpu-basic` tier now requires an HF **PRO** subscription
> (~$9/mo) — confirmed via a `402 Payment Required` when provisioning one. The
> existing `fuze-backend` Space was paused twice by HF's abuse detection
> (a browser-automation dependency) and must be unpaused by HF support; it
> can't simply be recreated for free if lost, so
> **"truly free" and "no payment required" no longer hold for new setups.**
> We're evaluating a free/low-cost fallback host (a small VPS such as
> Hetzner, or Fly.io) — see [`gaps_closure_plan.md`](../gaps_closure_plan.md)
> item 12. The image contains no browser-automation tooling and
> fetches only the single page a user saves, over plain HTTP; secrets such as `REDIS_URL` must be set as
> Space **Secrets**, not Variables (a name can't exist as both). This guide
> remains the architecture/env-var reference.

## Table of Contents

1. [Platform Comparison](#platform-comparison)
2. [Hugging Face Spaces Deployment](#hugging-face-spaces-deployment)
3. [Environment Variables Setup](#environment-variables-setup)
4. [RQ Worker Configuration](#rq-worker-configuration)
5. [Frontend-Backend Connection](#frontend-backend-connection)
6. [Other Platforms](#other-platforms)
7. [Troubleshooting](#troubleshooting)

---

## Platform Comparison

### Formerly recommended: Hugging Face Spaces — now requires PRO for Docker SDK

**Why Hugging Face Spaces looked best (still true on paper, minus the pricing):**
- ✅ **16GB RAM** (vs 512MB on Render) - Perfect for ML models!
- ❌ ~~Truly FREE~~ — **Docker SDK on `cpu-basic` now requires HF PRO** (confirmed via a `402 Payment Required` provisioning error)
- ✅ **JWT Auth Works** - No cookie/iframe issues
- ✅ **HTTPS Included** - PWA ready
- ✅ **Docker Support** - Full control (behind the PRO paywall now)

### Comparison Table

| Platform | Free RAM | PostgreSQL | HTTPS | Docker on free tier | Best For |
|----------|----------|------------|-------|------|----------|
| Hugging Face Spaces | 16GB | ❌ External | ✅ | ❌ **Requires PRO** | Only if you're paying for PRO anyway |
| Railway | 512MB+ | ✅ Included | ✅ | ✅ | Good free alternative |
| Fly.io | 768MB | ✅ Available | ✅ | ✅ | Good free alternative |
| Render | 512MB | ✅ | ✅ | ✅ | Limited by RAM |
| Small VPS (Hetzner CX22 etc.) | 4GB+ | ❌ External | ✅ (self-managed) | ✅ | ~€4/mo, full control, no platform-policy risk |

### Recommended Architecture

```
Frontend (Vercel) 
    ↓
Backend (HF Spaces - 16GB RAM!)
    ↓
Database (Supabase - Free PostgreSQL)
    ↓
Redis (Upstash - Free tier)
```

**Cost: $0/month** (all free tiers)

---

## Hugging Face Spaces Deployment

### ✅ Why Hugging Face Spaces?

Your app is **perfectly suited** for Hugging Face Spaces deployment:

1. **Authentication**: ✅ Uses JWT tokens (not cookies) - perfect for iframe limitations
2. **ML Models**: ✅ Embedding models work great (16GB RAM available!)
3. **Flask Backend**: ✅ Full Flask app support via Docker
4. **Resource Limits**: ✅ 2 vCPUs + 16GB RAM (much better than Render!)
5. **Persistent Storage**: ✅ Available for database files
6. **Environment Variables**: ✅ Full support

### Quick Deployment (5 Steps)

#### Step 1: Create Hugging Face Account
1. Go to [huggingface.co](https://huggingface.co)
2. Sign up (free, no credit card)
3. Verify email

#### Step 2: Create Space
1. Go to [huggingface.co/spaces](https://huggingface.co/spaces)
2. Click "Create new Space"
3. Settings:
   - **Name**: `fuze-backend`
   - **SDK**: **Docker** ⚠️ (important!)
   - **Template**: **Blank** ⚠️ (choose blank, not a pre-made template)
   - **Hardware**: **CPU basic** (free: 2 vCPUs, 16GB RAM)
   - **Visibility**: **Private** (recommended) or Public
     - **Private**: Only you can access the Space URL (your frontend can still call it via API)
     - **Public**: Anyone can discover and access your Space
     - Since you have JWT auth, **Private is recommended** for security

#### Step 3: Upload Files
For the existing `fuze-backend` Space this step is automated: the
`sync-to-hf-space.yml` workflow runs only after **Backend CI** passes on a push to
`main`, checks out that exact commit, mirrors `backend/` into the Space with
`rsync --delete` (so a module deleted from the repo also disappears from the Space;
tests, scratch files, logs and `.env*` are excluded) and copies the root files listed
below.

For a new Space, upload these files:
- ✅ `Dockerfile` (builds wheels from `requirements.lock` with `--require-hashes`, runs `start.sh`)
- ✅ `start.sh` (runs migrations, then supervisord)
- ✅ `supervisord.conf` (gunicorn + the `default` and `high` RQ workers)
- ✅ `gunicorn.conf.py` (2 gevent workers, timeout 60 s, psycogreen patch)
- ✅ `alembic.ini` (migrations run on every start)
- ✅ `app.py` (entry point)
- ✅ `wsgi.py` (Flask app)
- ✅ `requirements.txt` and `requirements.lock` (the image installs the lock: every transitive package, hash-checked)
- ✅ `.dockerignore`
- ✅ `backend/` folder (your entire backend code, without `tests/`)

**Or use Git:**
```bash
# Install HF CLI
pip install huggingface_hub

# Login
huggingface-cli login

# Clone your space
git clone https://huggingface.co/spaces/your-username/fuze-backend
cd fuze-backend

# Copy files (--delete so removed modules don't linger in the Space)
rsync -a --delete --exclude '__pycache__/' --exclude 'tests/' --exclude '*.log' --exclude '.env*' \
  /path/to/fuze/backend/ backend/
for f in requirements.txt requirements.lock Dockerfile .dockerignore app.py wsgi.py \
         start.sh supervisord.conf gunicorn.conf.py alembic.ini; do
  cp "/path/to/fuze/$f" .
done

# Commit and push
git add .
git commit -m "Deploy Fuze backend"
git push
```

#### Step 4: Set Environment Variables
See [Environment Variables Setup](#environment-variables-setup) section below.

#### Step 5: Deploy & Test
1. Space will auto-build (takes 5-10 minutes)
2. Check logs for errors
3. Test: `https://your-space.hf.space/api/health` (up/down only) and
   `https://your-space.hf.space/health/readiness` (503 unless the database, Redis
   and the schema are ready; the schema must be at the Alembic head shipped in this build)
4. Database schema: `start.sh` runs `python -m alembic -c alembic.ini upgrade head`
   on every start and **exits non-zero if it fails**, so the container never serves on
   a half-migrated schema. Each revision runs in its own transaction, so a failure
   leaves the last good revision in place.

### Architecture for Hugging Face Spaces

```
┌─────────────────────┐
│  Vercel (Frontend)  │  ← React PWA
│  HTTPS + CDN        │
└──────────┬──────────┘
           │
    ┌──────▼──────────────────────┐
    │  Hugging Face Spaces         │  ← Flask Backend
    │  (Docker, 16GB RAM)          │
    │  https://your-space.hf.space │
    └──────┬───────────────────────┘
           │
    ┌──────▼──────────────────────┐
    │  Supabase (Database)         │  ← PostgreSQL + pgvector
    │  500MB Free                  │
    └──────────────────────────────┘
           │
    ┌──────▼──────────────────────┐
    │  Upstash (Redis)             │  ← Caching
    │  10K commands/day free       │
    └──────────────────────────────┘
```

### Code Changes Made

1. **Created `Dockerfile`**
   - Python 3.11 base image, multi-stage (no compilers in the runtime image)
   - Installs exactly `requirements.lock` (hash-checked; regenerate with
     `scripts/lock-requirements.sh` after editing `requirements.txt`). Test tools
     live in `requirements-dev.txt` and are not in the image
   - Runs as an unprivileged user (UID 1000)
   - Exposes port 7860 (Hugging Face standard)
   - Uses `start.sh` to migrate, then run the web server and RQ workers

2. **Created `app.py`**
   - Entry point for Hugging Face Spaces
   - Imports app from `wsgi.py`
   - Compatible with Spaces requirements

3. **Created `start.sh`**
   - Runs `alembic upgrade head` and refuses to start if it fails
   - Sets `PROMETHEUS_MULTIPROC_DIR` so `/metrics` merges every process
   - Execs supervisord (`supervisord.conf`), which runs:
     - Gunicorn web server (`gunicorn app:app -c gunicorn.conf.py`) - handles API requests
     - RQ worker on the `default` queue (bookmark pipeline + the pipeline reconciler)
     - RQ worker on the `high` queue (login-triggered cache warming)
   - Graceful shutdown: supervisord waits up to 630 s for a running job (`stopwaitsecs`)

4. **Background Job Processing ✅**
   - RQ workers run automatically alongside the web server, started with the RQ
     scheduler so `Retry(interval=...)` retries actually run
   - Processes bookmark content extraction, embeddings, and analysis (one job id
     per bookmark and stage, so re-enqueueing is safe)
   - Uses the same Redis as the web server

### Configuration Details

#### Port Configuration
- Hugging Face Spaces uses port **7860**
- Dockerfile configured for this
- App binds to `0.0.0.0:7860`

#### CORS Configuration
The allowlist lives in `backend/utils/cors_utils.py`. In production it allows only
`https://itsfuze.vercel.app` and this project's Vercel previews
(`https://itsfuze-*.vercel.app`); localhost dev servers are allowed only outside
production. `CORS_ORIGINS` adds extra **exact** origins (e.g. a custom frontend
domain); entries containing wildcards are ignored with a warning. The Chrome
extension uses `host_permissions` and needs no CORS entry (`EXTENSION_ID` pins one
extension origin if a page inside it ever calls the API without them).

If the API moves off `*.hf.space`, also update `connect-src` in the CSP in
`frontend/vercel.json`, or the browser will block the calls.

#### Database Setup
1. Use **Supabase** (free PostgreSQL)
2. Enable pgvector extension:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Set `DATABASE_URL` in Spaces variables

#### Redis Setup
- Keep using **Upstash** (free tier)
- Set `REDIS_URL` in Spaces variables
- No changes needed in code

---

## Environment Variables Setup

### Required Environment Variables

Go to your Space → **Settings** → **Variables** and add these:

#### 1. Database (Required) ✅

```
DATABASE_URL=postgresql://user:password@host:5432/database
```

**Where to get this:**
- If using **Supabase** (recommended):
  1. Go to your Supabase project
  2. Settings → Database
  3. Copy "Connection string" (URI format)
  4. Replace `[YOUR-PASSWORD]` with your actual database password

**Example:**
```
DATABASE_URL=postgresql://postgres.abcdefghijklmnop:your_password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

#### 2. Redis (Required) ✅

```
REDIS_URL=rediss://default:password@host:port
```

**Where to get this:**
- If using **Upstash** (recommended):
  1. Go to your Upstash dashboard
  2. Select your Redis database
  3. Copy "REST URL" or "Redis URL"
  4. Format: `rediss://default:YOUR_PASSWORD@YOUR_ENDPOINT:6379`

**Example:**
```
REDIS_URL=rediss://default:AbCdEf123456@your-redis.upstash.io:6379
```

#### 3. Secret Keys (Required) ✅

Generate two random secret keys:

```powershell
# Run this twice to get two different keys
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Then set:
```
SECRET_KEY=<first_generated_key>
JWT_SECRET_KEY=<second_generated_key>
```

In production the app **refuses to start** if either key is missing, a known
default value, or shorter than 16 characters.

#### 4. Environment (Required) ✅

```
APP_ENV=production
DEBUG=false
```

`APP_ENV` is the single environment selector (`ENVIRONMENT` and `FLASK_ENV` are
read only as fallbacks). Unset means production, so a forgotten variable makes the
app stricter, never looser.

#### 5. CORS Origins (Only for extra origins)

```
CORS_ORIGINS=https://your-custom-domain.example
```

The production app and its Vercel previews are allowed without this; see
[CORS Configuration](#cors-configuration). Wildcards are ignored.

#### 6. Gemini API Key (Optional) ⚠️

```
GEMINI_API_KEY=your_gemini_api_key_here
SYSTEM_GEMINI_DAILY_LIMIT_PER_USER=30
```

Only needed if you want Gemini AI features. Can be added later. Users without their
own key share this one, up to `SYSTEM_GEMINI_DAILY_LIMIT_PER_USER` uses a day each.

#### 7. Operational tokens (Optional)

```
METRICS_AUTH_TOKEN=<random>      # /metrics returns 404 unless this is set and sent as a Bearer token
INTERNAL_HEALTH_TOKEN=<random>   # /api/health/queue and /api/health/detailed need it in X-Internal-Token
```

### Complete Environment Variables List

Copy-paste this into Hugging Face Spaces Variables (replace with your actual values):

```
DATABASE_URL=postgresql://user:password@host:5432/database
REDIS_URL=rediss://default:password@host:6379
SECRET_KEY=your_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here
APP_ENV=production
DEBUG=false
GEMINI_API_KEY=your_gemini_key_optional
```

### Step-by-Step Setup

1. **Get Database URL** - See Supabase setup above
2. **Get Redis URL** - See Upstash setup above
3. **Generate Secret Keys** - Use Python command above
4. **Add Variables to Hugging Face** - Space → Settings → Variables
5. **Restart Space** - Settings → Restart this Space
6. **Verify** - Check logs for successful connections

---

## RQ Worker Configuration

### Overview

For Hugging Face Spaces deployment, the RQ worker runs alongside the web server in the same Docker container. This is handled automatically by the `start.sh` startup script.

### How It Works

The `start.sh` script:
1. **Runs migrations** and exits if they fail
2. **Execs supervisord**, which starts Gunicorn and the `default` and `high` RQ workers
3. **Handles graceful shutdown**: running jobs get up to 630 s to finish

The `default` worker also runs the pipeline reconciler
(`backend/services/pipeline_reconciler.py`) every 5 minutes: it re-enqueues fetches
stuck in `PENDING`, retries `FAILED_FETCH` after 1 h / 6 h / 24 h, and enqueues
embeddings for bookmarks that were fetched but never embedded. A lost enqueue (for
example while Redis was down) is therefore picked up later instead of lost.

### Automatic Setup

When you deploy to Hugging Face Spaces:

1. **The Dockerfile automatically**:
   - Copies `start.sh` into the container
   - Makes it executable
   - Runs it as the entry point

2. **The startup script automatically**:
   - Migrates the database (or stops)
   - Starts supervisord, which supervises Gunicorn and both RQ workers

### No Manual Steps Required! ✅

The worker starts automatically when the Space is deployed. You don't need to:
- ❌ Manually start the worker
- ❌ Configure separate processes
- ❌ Set up process managers
- ❌ Add extra commands

### Verification

After deployment, check the logs in Hugging Face Spaces:

1. Go to your Space → **Logs** tab
2. Look for:
   ```
   Running database migrations (/app/alembic.ini)...
   Starting Fuze processes via supervisord...
   ```
   followed by supervisord reporting `gunicorn`, `rq_worker` and `rq_worker_high` as running.

### Test Background Processing

1. Save a bookmark via the share handler
2. Check the logs for the RQ job running and the bookmark's scrape and embedding
   status moving out of `PENDING` (see [OPERATIONS.md](OPERATIONS.md) for the
   pipeline health queries)

### Configuration

Same environment variables as before - no changes needed:
- `REDIS_URL` (required for RQ worker)
- Same Redis instance used for caching and task queue

### Troubleshooting

**Worker Not Starting:**
- Verify `REDIS_URL` is set correctly in Space variables
- Check Redis connection is accessible from Spaces

**Jobs Not Processing:**
- Check that supervisord reports `rq_worker` as running
- Verify Redis is accessible
- Check worker logs for errors

---

## Frontend-Backend Connection

### Current Setup

**Frontend**: `itsfuze.vercel.app`  
**Backend**: `Ujjwaljain16-fuze-backend.hf.space`

### Step 1: Update Vercel Environment Variable

Your frontend **requires** `VITE_API_URL` to be set in Vercel.

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Select your `itsfuze` project
3. Go to **Settings** → **Environment Variables**
4. Add or update:
   ```
   VITE_API_URL=https://Ujjwaljain16-fuze-backend.hf.space
   ```
5. **Important**: Make sure it's set for **Production** environment
6. Click **Save**

### Step 2: Redeploy Frontend

After updating the environment variable:

1. Go to **Deployments** tab
2. Click **Redeploy** on the latest deployment
3. Or push a new commit to trigger redeploy

**Note**: Environment variables are only available after redeploy!

### Step 3: Update Backend CORS

Make sure your Hugging Face Spaces backend has the correct CORS configuration:

1. Go to: https://huggingface.co/spaces/Ujjwaljain16/fuze-backend
2. **Settings** → **Variables**
3. Nothing to add for `https://itsfuze.vercel.app` or its previews: they are built
   into the production allowlist (`backend/utils/cors_utils.py`). Set `CORS_ORIGINS`
   only for an extra exact origin such as a custom domain.

### Verification Checklist

- [ ] `VITE_API_URL` set in Vercel
- [ ] Environment variable set for **Production**
- [ ] Frontend redeployed after setting variable
- [ ] Frontend origin is on the CORS allowlist (built in for `itsfuze.vercel.app`; otherwise `CORS_ORIGINS`)
- [ ] Backend is running (check logs)
- [ ] Database connected (no errors in logs)
- [ ] Redis connected (no errors in logs)

### How to Verify It's Working

1. Open `https://itsfuze.vercel.app` and press F12
2. Check browser console - should see API calls
3. Check Network tab - API calls should go to `*.hf.space`
4. Try logging in - should work if everything is configured correctly

---

## Other Platforms

### Railway

**Free Tier:**
- ✅ $5/month credit (free)
- ✅ 512MB RAM (can upgrade with credits)
- ✅ PostgreSQL included (free tier)
- ✅ HTTPS included
- ✅ Docker support

**Setup:**
1. Sign up at [railway.app](https://railway.app)
2. Connect GitHub repo
3. Add PostgreSQL service (free)
4. Deploy backend service
5. Set environment variables

**Start Command:** deploy the Dockerfile (its `CMD ["./start.sh"]` migrates, then
runs Gunicorn and the RQ workers). Without Docker, run the same pieces yourself:
```
python -m alembic -c alembic.ini upgrade head
gunicorn app:app -c gunicorn.conf.py          # binds 0.0.0.0:$PORT
python backend/worker.py --queue default
```

### Fly.io

**Free Tier:**
- ✅ 3 shared-cpu VMs (256MB each = 768MB total)
- ✅ 3GB persistent volume
- ✅ PostgreSQL available (separate service)
- ✅ HTTPS included

**Setup:**
1. Sign up at [fly.io](https://fly.io)
2. Install flyctl CLI
3. Create `fly.toml` config
4. Deploy: `fly deploy`
5. Add PostgreSQL: `fly postgres create`

---

## Troubleshooting

### Build Fails
- Check Dockerfile syntax
- Verify requirements.txt
- Check logs for errors

### App Won't Start
- `FATAL: database migration failed; refusing to start.`: fix the migration error
  in the log (the schema stays at the last good revision)
- `Refusing to start in production with unsafe secrets`: set strong
  `SECRET_KEY` / `JWT_SECRET_KEY` (16+ characters, not a default), or
  `APP_ENV=development` for local work
- Check environment variables
- Verify database connection
- Check Redis connection
- Review logs

### Memory Issues
- 16GB should be plenty on Hugging Face Spaces
- Monitor in Spaces dashboard
- Optimize model loading if needed

### CORS Errors
- The production allowlist only contains the app and its Vercel previews; add any
  other frontend origin to `CORS_ORIGINS` as an exact origin (no wildcards)
- localhost origins are rejected when `APP_ENV` is production (or unset)

### 404 Errors on API Calls

**Problem**: Getting 404 when accessing API endpoints

**Possible Causes:**
1. Space not fully deployed - wait for build to complete
2. Wrong URL format - try different URL formats
3. App not binding correctly - check Dockerfile port configuration
4. Space visibility - if Private, may need to make Public for API access

**Solutions:**
1. Check Space status in Logs tab
2. Test root endpoint: `curl https://your-space.hf.space/`
3. Check Space settings (Hardware, Visibility, SDK)
4. Restart Space
5. Check app logs for binding errors

### Dashboard Loading Issues

**Symptoms:**
- Requests showing as "canceled" in browser
- Dashboard data not appearing

**Fixes:**
- Check `/health/readiness`: a 503 names the part that isn't ready (database,
  schema or Redis)
- Verify database connection and that `DATABASE_URL` is set correctly
- Don't raise the Gunicorn timeout: it is 60 s on purpose (each query has a 15 s
  `statement_timeout`), and long work belongs in RQ jobs

### Database Connection Issues

**"DATABASE_URL is not set"**
- Make sure variable name is exactly `DATABASE_URL`
- Check for typos
- Restart Space after adding

**"Could not parse SQLAlchemy URL"**
- Make sure DATABASE_URL format is: `postgresql://user:pass@host:port/db`
- No spaces in the URL
- Password doesn't contain special characters that need encoding

**Database connection still fails**
- Check Supabase database is running
- Verify password is correct
- Check if IP restrictions are enabled (disable for now)
- Make sure pgvector extension is enabled

### Redis Connection Issues

**"Redis connection failed"**
- Make sure `REDIS_URL` starts with `rediss://` (with double 's' for SSL)
- Check Upstash URL format
- Verify password is correct

---

## Summary

### ✅ Perfect Fit for Your App

1. **16GB RAM** - Handles ML models easily
2. **JWT Auth** - No cookie/iframe issues
3. **Docker Support** - Full control
4. **Truly Free** - No payment method needed
5. **HTTPS Included** - PWA ready
6. **Background Jobs** - RQ worker runs automatically

### Setup Required

1. ✅ Create Hugging Face account
2. ✅ Create Docker Space
3. ✅ Push code (Dockerfile, app.py, start.sh, etc.)
4. ✅ Set environment variables (including REDIS_URL)
5. ✅ Initialize database
6. ✅ Deploy frontend to Vercel
7. ✅ Update CORS settings

### Code Changes: Minimal ✅

- Created Dockerfile (with RQ worker support)
- Created app.py entry point
- Created start.sh (migrates, then runs web server + workers via supervisord)
- Updated README.md
- **No backend code changes needed!**
- **RQ worker starts automatically!**

---

**This is the best free option - 16GB RAM and no payment required!** 🚀

