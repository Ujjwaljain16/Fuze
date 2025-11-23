# Deployment Guide

Complete deployment guide for Fuze - Intelligent Bookmark Manager.

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

### Recommended: Hugging Face Spaces 🥇

**Why Hugging Face Spaces is Best:**
- ✅ **16GB RAM** (vs 512MB on Render) - Perfect for ML models!
- ✅ **Truly FREE** - No payment method required
- ✅ **JWT Auth Works** - No cookie/iframe issues
- ✅ **HTTPS Included** - PWA ready
- ✅ **Docker Support** - Full control

### Comparison Table

| Platform | Free RAM | PostgreSQL | HTTPS | Ease | Best For |
|----------|----------|------------|-------|------|----------|
| **Hugging Face Spaces** | **16GB** | ❌ External | ✅ | ⭐⭐⭐⭐⭐ | **Best overall** |
| Railway | 512MB+ | ✅ Included | ✅ | ⭐⭐⭐⭐⭐ | Good alternative |
| Fly.io | 768MB | ✅ Available | ✅ | ⭐⭐⭐ | Good alternative |
| Render | 512MB | ✅ | ✅ | ⭐⭐⭐⭐ | Limited by RAM |

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
In your Space, upload these files:
- ✅ `Dockerfile` (updated - runs start.sh)
- ✅ `start.sh` (NEW - runs both processes)
- ✅ `app.py` (entry point)
- ✅ `wsgi.py` (Flask app)
- ✅ `requirements.txt` (includes rq==1.15.1)
- ✅ `backend/` folder (your entire backend code)
- ✅ `README.md` (optional)

**Or use Git:**
```bash
# Install HF CLI
pip install huggingface_hub

# Login
huggingface-cli login

# Clone your space
git clone https://huggingface.co/spaces/your-username/fuze-backend
cd fuze-backend

# Copy files
cp -r /path/to/fuze/backend .
cp /path/to/fuze/requirements.txt .
cp /path/to/fuze/Dockerfile .
cp /path/to/fuze/app.py .
cp /path/to/fuze/wsgi.py .
cp /path/to/fuze/start.sh .

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
3. Test: `https://your-space.hf.space/api/health`
4. Initialize database (one-time):
   - Use Space terminal or HF CLI
   - Run: `python backend/init_db.py`

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
   - Python 3.11 base image
   - Installs all dependencies (including RQ for background jobs)
   - Exposes port 7860 (Hugging Face standard)
   - Uses `start.sh` to run both web server and RQ worker

2. **Created `app.py`**
   - Entry point for Hugging Face Spaces
   - Imports app from `wsgi.py`
   - Compatible with Spaces requirements

3. **Created `start.sh`**
   - Startup script that runs both processes:
     - RQ worker (background) - processes bookmark tasks
     - Gunicorn web server (foreground) - handles API requests
   - Handles graceful shutdown

4. **Background Job Processing ✅**
   - RQ worker runs automatically alongside web server
   - Processes bookmark content extraction, embeddings, and analysis
   - Uses same Redis connection as web server

### Configuration Details

#### Port Configuration
- Hugging Face Spaces uses port **7860**
- Dockerfile configured for this
- App binds to `0.0.0.0:7860`

#### CORS Configuration
Update `CORS_ORIGINS` to include:
- Your frontend URL (Vercel)
- Your Hugging Face Space URL: `https://your-space.hf.space`

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

#### 4. Environment (Required) ✅

```
ENVIRONMENT=production
DEBUG=false
```

#### 5. CORS Origins (Required) ✅

```
CORS_ORIGINS=https://your-frontend.vercel.app,https://your-space.hf.space
```

**Replace `your-frontend.vercel.app` with your actual Vercel URL.**

#### 6. Gemini API Key (Optional) ⚠️

```
GEMINI_API_KEY=your_gemini_api_key_here
```

Only needed if you want Gemini AI features. Can be added later.

### Complete Environment Variables List

Copy-paste this into Hugging Face Spaces Variables (replace with your actual values):

```
DATABASE_URL=postgresql://user:password@host:5432/database
REDIS_URL=rediss://default:password@host:6379
SECRET_KEY=your_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=https://your-frontend.vercel.app,https://your-space.hf.space
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
1. **Starts RQ worker** in the background (processes bookmark tasks)
2. **Starts Gunicorn** in the foreground (handles API requests)
3. **Handles graceful shutdown** when container stops

### Automatic Setup

When you deploy to Hugging Face Spaces:

1. **The Dockerfile automatically**:
   - Copies `start.sh` into the container
   - Makes it executable
   - Runs it as the entry point

2. **The startup script automatically**:
   - Starts RQ worker in background
   - Starts Gunicorn web server
   - Handles both processes

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
   Starting Fuze backend services...
   Starting RQ worker...
   Starting Gunicorn web server...
   ```

### Test Background Processing

1. Save a bookmark via the share handler
2. Check logs - you should see:
   ```
   Enqueued bookmark processing job ...
   Background processing started for bookmark ...
   Background processing completed for bookmark ...
   ```

### Configuration

Same environment variables as before - no changes needed:
- `REDIS_URL` (required for RQ worker)
- Same Redis instance used for caching and task queue

### Troubleshooting

**Worker Not Starting:**
- Verify `REDIS_URL` is set correctly in Space variables
- Check Redis connection is accessible from Spaces

**Jobs Not Processing:**
- Check if worker is running (look for "Starting RQ worker..." in logs)
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
3. Check `CORS_ORIGINS` includes:
   ```
   https://itsfuze.vercel.app,https://Ujjwaljain16-fuze-backend.hf.space
   ```

### Verification Checklist

- [ ] `VITE_API_URL` set in Vercel
- [ ] Environment variable set for **Production**
- [ ] Frontend redeployed after setting variable
- [ ] `CORS_ORIGINS` includes `https://itsfuze.vercel.app`
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

**Start Command:**
```
gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120
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
- Check environment variables
- Verify database connection
- Check Redis connection
- Review logs

### Memory Issues
- 16GB should be plenty on Hugging Face Spaces
- Monitor in Spaces dashboard
- Optimize model loading if needed

### CORS Errors
- Update `CORS_ORIGINS` in environment variables
- Include your frontend URL
- Include Spaces URL

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
- Increase frontend timeout (CSRF: 2s → 10s)
- Increase backend timeout (Gunicorn: 120s → 300s)
- Verify database connection
- Check `DATABASE_URL` is set correctly

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
- Created start.sh (runs web server + worker)
- Updated README.md
- **No backend code changes needed!**
- **RQ worker starts automatically!**

---

**This is the best free option - 16GB RAM and no payment required!** 🚀

