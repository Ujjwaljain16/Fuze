# 🚀 Free Production Deployment Guide for Fuze

Complete guide to deploy Fuze for **FREE** using free-tier services.

## 📋 Overview

This guide covers deploying:
- **Backend**: Flask API (Python)
- **Frontend**: React/Vite app
- **Database**: PostgreSQL with pgvector (Supabase)
- **Cache**: Redis (Upstash)
- **AI**: Gemini API (Google)

---

## 🎯 Free Services We'll Use

### Backend Hosting (Choose ONE)
1. **Render** (Recommended) - Free tier: 750 hours/month
   - Auto-deploy from GitHub
   - Free SSL
   - Sleeps after 15min inactivity (wakes on request)

2. **Railway** - Free tier: $5 credit/month
   - Fast deployments
   - No sleep (always on)

3. **Fly.io** - Free tier: 3 shared VMs
   - Global edge deployment
   - Good performance

### Database
- **Supabase** (Free tier)
  - 500MB database
  - PostgreSQL with pgvector
  - Free SSL

### Redis Cache
- **Upstash** (Free tier)
  - 10,000 commands/day
  - Serverless Redis

### Frontend Hosting
- **Vercel** (Recommended) - Free tier
  - Auto-deploy from GitHub
  - Free SSL
  - Global CDN

- **Netlify** - Free tier
  - Similar to Vercel
  - Good for static sites

---

## 📝 Step-by-Step Deployment

### Step 1: Prepare Your Repository

1. **Push to GitHub** (if not already)
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/fuze.git
   git push -u origin main
   ```

2. **Create `.env.example`** (template for environment variables)
   - Already created by `unified_config.py` - run: `python -c "from unified_config import generate_env_template; generate_env_template()"`

---

### Step 2: Set Up Database (Supabase)

1. **Create Supabase Account**
   - Go to https://supabase.com
   - Sign up (free)
   - Create new project

2. **Enable pgvector Extension**
   ```sql
   -- Run in Supabase SQL Editor
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

3. **Get Database URL**
   - Go to Project Settings → Database
   - Copy "Connection string" (URI format)
   - Format: `postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres`

4. **Note Your Credentials**
   - Database URL
   - Project URL
   - Anon key (for frontend if needed)

---

### Step 3: Set Up Redis (Upstash)

1. **Create Upstash Account**
   - Go to https://upstash.com
   - Sign up (free)
   - Create Redis database

2. **Get Redis URL**
   - Copy "REST URL" or "Redis URL"
   - Format: `redis://default:[PASSWORD]@[HOST]:[PORT]`

---

### Step 4: Get Gemini API Key

1. **Get API Key**
   - Go to https://makersuite.google.com/app/apikey
   - Create new API key
   - Copy the key

---

### Step 5: Deploy Backend (Render)

1. **Create Render Account**
   - Go to https://render.com
   - Sign up with GitHub

2. **Create New Web Service**
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Select the `fuze` repository

3. **Configure Service**
   - **Name**: `fuze-backend` (or your choice)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn wsgi:app --bind 0.0.0.0:$PORT`
   - **Plan**: Free

4. **Set Environment Variables** (in Render dashboard)
   ```
   ENVIRONMENT=production
   DEBUG=false
   
   DATABASE_URL=postgresql://postgres:...@db.xxx.supabase.co:5432/postgres
   DB_SSL_MODE=require
   
   REDIS_URL=rediss://default:...@xxx.upstash.io:6379
   # Note: Use rediss:// (double 's') for TLS/SSL (required by Upstash)
   # OR use separate variables:
   REDIS_HOST=xxx.upstash.io
   REDIS_PORT=6379
   REDIS_PASSWORD=...
   REDIS_SSL=true
   
   SECRET_KEY=<generate-random-string>
   JWT_SECRET_KEY=<generate-random-string>
   
   GEMINI_API_KEY=your-gemini-api-key
   
   CORS_ORIGINS=https://your-frontend.vercel.app,https://your-frontend.netlify.app
   ```

5. **Generate Secret Keys**
   ```bash
   # Run locally to generate secure keys:
   python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
   python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
   ```

6. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (5-10 minutes)
   - Your backend URL: `https://fuze-backend.onrender.com`

---

### Step 6: Deploy Frontend (Vercel)

1. **Create Vercel Account**
   - Go to https://vercel.com
   - Sign up with GitHub

2. **Import Project**
   - Click "Add New" → "Project"
   - Import your GitHub repository
   - **Root Directory**: `frontend`

3. **Configure Build**
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

4. **Set Environment Variables**
   ```
   VITE_API_URL=https://fuze-backend.onrender.com
   ```

5. **Deploy**
   - Click "Deploy"
   - Your frontend URL: `https://fuze.vercel.app`

6. **Update CORS in Backend**
   - Go back to Render
   - Update `CORS_ORIGINS` to include your Vercel URL

---

### Step 7: Initialize Database

1. **Run Database Initialization**
   - Option 1: Use Render Shell
     - Go to Render dashboard → Your service → Shell
     - Run: `python init_db.py`
   
   - Option 2: Run locally (with production DATABASE_URL)
     ```bash
     export DATABASE_URL="your-supabase-url"
     python init_db.py
     ```

---

## 🔧 Alternative: Railway Deployment

### Backend on Railway

1. **Create Railway Account**
   - Go to https://railway.app
   - Sign up with GitHub

2. **Create New Project**
   - Click "New Project"
   - "Deploy from GitHub repo"
   - Select your repository

3. **Configure**
   - Railway auto-detects Python
   - Add `Procfile` (see below)
   - Set environment variables (same as Render)

4. **Deploy**
   - Auto-deploys on push
   - Get URL: `https://fuze-production.up.railway.app`

---

## 📄 Required Files for Deployment

### 1. Create `Procfile` (for Render/Railway)
```bash
web: gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

### 2. Create `runtime.txt` (optional, specify Python version)
```
python-3.11.0
```

### 3. Update `frontend/vite.config.js` (if needed)
```javascript
export default {
  // ... existing config
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
}
```

---

## ✅ Post-Deployment Checklist

- [ ] Backend health check: `https://your-backend.onrender.com/api/health`
- [ ] Frontend loads: `https://your-frontend.vercel.app`
- [ ] Database connection works
- [ ] Redis connection works
- [ ] Gemini API works
- [ ] CORS configured correctly
- [ ] Environment variables set
- [ ] Database initialized
- [ ] SSL/HTTPS enabled (automatic on Render/Vercel)

---

## 🔍 Troubleshooting

### Backend Issues

1. **Application Crashes**
   - Check Render logs
   - Verify all environment variables are set
   - Check database connection

2. **Database Connection Fails**
   - Verify `DATABASE_URL` is correct
   - Check Supabase connection pooling settings
   - Ensure `DB_SSL_MODE=require` for Supabase

3. **Redis Connection Fails**
   - Verify Redis URL/credentials
   - Check Upstash dashboard for connection status

### Frontend Issues

1. **API Calls Fail**
   - Check `VITE_API_URL` is set correctly
   - Verify CORS allows your frontend domain
   - Check browser console for errors

2. **Build Fails**
   - Check Vercel build logs
   - Ensure all dependencies in `package.json`
   - Verify Node.js version compatibility

---

## 💰 Free Tier Limits

### Render
- 750 hours/month (enough for always-on)
- Sleeps after 15min (wakes on request, ~30s delay)
- 100GB bandwidth/month

### Supabase
- 500MB database
- 2GB bandwidth/month
- 50,000 monthly active users

### Upstash
- 10,000 commands/day
- 256MB storage

### Vercel
- Unlimited deployments
- 100GB bandwidth/month
- Free SSL

---

## 🚀 Quick Deploy Commands

### Generate Environment Template
```bash
python -c "from unified_config import generate_env_template; generate_env_template('.env.example')"
```

### Test Production Locally
```bash
export ENVIRONMENT=production
export DATABASE_URL="your-supabase-url"
export REDIS_URL="your-redis-url"
gunicorn wsgi:app --bind 0.0.0.0:5000
```

---

## 📚 Additional Resources

- [Render Docs](https://render.com/docs)
- [Vercel Docs](https://vercel.com/docs)
- [Supabase Docs](https://supabase.com/docs)
- [Upstash Docs](https://docs.upstash.com)

---

## 🎉 You're Ready!

Once deployed, your app will be live at:
- **Backend**: `https://your-backend.onrender.com`
- **Frontend**: `https://your-frontend.vercel.app`

Update your Chrome extension to use the production backend URL!

