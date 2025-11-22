# Hugging Face Spaces - Quick Start Guide

## ✅ Perfect for Your App!

**Why Hugging Face Spaces is Best:**
- ✅ **16GB RAM** (vs 512MB on Render) - Perfect for ML models!
- ✅ **Truly FREE** - No payment method required
- ✅ **JWT Auth Works** - No cookie/iframe issues
- ✅ **HTTPS Included** - PWA ready
- ✅ **Docker Support** - Full control

---

## Quick Deployment (5 Steps)

### Step 1: Create Hugging Face Account
1. Go to [huggingface.co](https://huggingface.co)
2. Sign up (free, no credit card)
3. Verify email

### Step 2: Create Space
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

### Step 3: Upload Files
In your Space, upload these files:
- ✅ `Dockerfile` (I created this)
- ✅ `app.py` (I created this)
- ✅ `wsgi.py` (already exists)
- ✅ `requirements.txt` (already exists)
- ✅ `backend/` folder (your entire backend code)
- ✅ `README.md` (I updated this)

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

# Commit
git add .
git commit -m "Deploy Fuze backend"
git push
```

### Step 4: Set Environment Variables
In Space → Settings → Variables:

```env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=rediss://your-upstash-redis-url
SECRET_KEY=<generate_random_32_char_string>
JWT_SECRET_KEY=<generate_random_32_char_string>
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=https://your-frontend.vercel.app,https://your-space.hf.space
GEMINI_API_KEY=<your_key_if_needed>
```

**Generate Secret Keys:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 5: Deploy & Test
1. Space will auto-build (takes 5-10 minutes)
2. Check logs for errors
3. Test: `https://your-space.hf.space/api/health`
4. Initialize database (one-time):
   - Use Space terminal or HF CLI
   - Run: `python backend/init_db.py`

---

## Architecture

```
Frontend (Vercel) 
    ↓
Backend (HF Spaces - 16GB RAM!)
    ↓
Database (Supabase - Free PostgreSQL)
    ↓
Redis (Upstash - Free tier)
```

---

## What I Created for You

1. ✅ **Dockerfile** - Ready for HF Spaces
2. ✅ **app.py** - Entry point for Spaces
3. ✅ **README.md** - Spaces configuration
4. ✅ **docs/HUGGINGFACE_SPACES_DEPLOYMENT.md** - Full guide

---

## Your App is Ready! ✅

- ✅ JWT tokens (works in iframes)
- ✅ ML models (16GB RAM handles them)
- ✅ Flask backend (Docker support)
- ✅ External services (Supabase + Upstash)

**No code changes needed** - just deploy!

---

## Cost: $0/month

- HF Spaces: Free (16GB RAM!)
- Supabase: Free (500MB PostgreSQL)
- Upstash: Free (10K commands/day)
- Vercel: Free (frontend)

**Total: $0** 🎉

---

## Next Steps

1. Create HF account
2. Create Docker Space
3. Upload files
4. Set environment variables
5. Deploy frontend to Vercel
6. Update CORS in backend
7. Test!

See `docs/HUGGINGFACE_SPACES_DEPLOYMENT.md` for detailed guide.

