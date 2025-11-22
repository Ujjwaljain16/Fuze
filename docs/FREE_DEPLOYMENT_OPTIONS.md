# Free Deployment Options for Fuze

## Current Issue
- **Render Free Tier**: 512MB RAM (insufficient for ML models)
- **Memory Usage**: Embedding models + Flask app need ~1-2GB RAM
- **Solution**: Migrate to platforms with better free tiers

## Recommended Free Deployment Options

### 🥇 Option 1: Railway (BEST CHOICE)
**Why**: Best free tier, easy setup, supports everything you need

**Free Tier**:
- ✅ $5/month credit (free)
- ✅ 512MB RAM (can upgrade with credits)
- ✅ PostgreSQL included (free tier)
- ✅ HTTPS included
- ✅ Docker support
- ✅ Environment variables
- ✅ Auto-deploy from GitHub

**Setup**:
1. Sign up at [railway.app](https://railway.app)
2. Connect GitHub repo
3. Add PostgreSQL service (free)
4. Deploy backend service
5. Set environment variables
6. Deploy frontend to Vercel (separate)

**Pros**:
- ✅ Most generous free tier
- ✅ PostgreSQL included
- ✅ Easy to use
- ✅ Good documentation
- ✅ Supports Docker

**Cons**:
- ⚠️ $5 credit may run out (but resets monthly)
- ⚠️ Need to monitor usage

**Memory Optimization**:
- Use 1 worker (you already do)
- Lazy load ML models
- Use Redis for caching (optional)

---

### 🥈 Option 2: Fly.io
**Why**: Good free tier, supports PostgreSQL, Docker

**Free Tier**:
- ✅ 3 shared-cpu VMs (256MB each = 768MB total)
- ✅ 3GB persistent volume
- ✅ PostgreSQL available (separate service)
- ✅ HTTPS included
- ✅ Global edge network

**Setup**:
1. Sign up at [fly.io](https://fly.io)
2. Install flyctl CLI
3. Create `fly.toml` config
4. Deploy: `fly deploy`
5. Add PostgreSQL: `fly postgres create`

**Pros**:
- ✅ Good free tier
- ✅ Global edge network
- ✅ Docker support
- ✅ PostgreSQL available

**Cons**:
- ⚠️ More complex setup
- ⚠️ Need CLI tool
- ⚠️ PostgreSQL is separate service

---

### 🥉 Option 3: Split Deployment (RECOMMENDED FOR PWA)
**Why**: Best performance, each service optimized

**Architecture**:
```
Frontend (Vercel) → Backend (Railway/Fly.io) → Database (Supabase)
```

**Frontend**: Vercel (Free)
- ✅ Unlimited bandwidth
- ✅ HTTPS included
- ✅ Global CDN
- ✅ Auto-deploy from GitHub
- ✅ Perfect for React apps

**Backend**: Railway or Fly.io
- ✅ Handles Flask + ML models
- ✅ Can scale memory as needed

**Database**: Supabase (Free)
- ✅ 500MB PostgreSQL (free)
- ✅ pgvector extension available
- ✅ Auto-backups
- ✅ REST API included

**Setup**:
1. Deploy frontend to Vercel
2. Deploy backend to Railway/Fly.io
3. Create Supabase project
4. Update environment variables
5. Connect all services

**Pros**:
- ✅ Best performance
- ✅ Each service optimized
- ✅ Better scalability
- ✅ Free tier for all

**Cons**:
- ⚠️ More services to manage
- ⚠️ Need to configure CORS

---

## Memory Optimization Strategies

### 1. Reduce Gunicorn Workers
**Current**: 1 worker ✅ (already optimized)

### 2. Lazy Load ML Models
**Current**: Already implemented ✅
- Models load on first use
- Cached in memory
- Single instance per worker

### 3. Use External Services
- **Embedding Model**: Consider using API (OpenAI, Cohere) instead of local
- **Redis**: ✅ Already using Upstash Redis (free tier: 10,000 commands/day)
- **Database**: Use Supabase (managed PostgreSQL) or Railway PostgreSQL

### 4. Optimize Dependencies
- Remove unused packages
- Use lighter alternatives
- Optimize imports

---

## Quick Migration Guide

### Railway Migration

1. **Create Railway Account**
   ```bash
   # Sign up at railway.app
   ```

2. **Create Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your Fuze repo

3. **Add PostgreSQL**
   - Click "New" → "Database" → "PostgreSQL"
   - Railway will provide connection string

4. **Deploy Backend**
   - Click "New" → "GitHub Repo"
   - Select backend directory or root
   - Set start command: `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 1`
   - Set environment variables

5. **Environment Variables**
   ```
   DATABASE_URL=<railway_postgres_url>
   SECRET_KEY=<your_secret_key>
   JWT_SECRET_KEY=<your_jwt_secret>
   ENVIRONMENT=production
   DEBUG=false
   REDIS_URL=<optional_redis_url>
   ```

6. **Deploy Frontend to Vercel**
   - Import GitHub repo
   - Framework: Vite
   - Build command: `npm run build`
   - Output directory: `dist`
   - Add environment variable: `VITE_API_URL=<railway_backend_url>`

---

## Comparison Table

| Platform | Free RAM | PostgreSQL | HTTPS | Ease | Best For |
|----------|----------|------------|-------|------|----------|
| **Railway** | 512MB+ | ✅ Included | ✅ | ⭐⭐⭐⭐⭐ | Best overall |
| **Fly.io** | 768MB | ✅ Available | ✅ | ⭐⭐⭐ | Good alternative |
| **Vercel** | N/A | ❌ | ✅ | ⭐⭐⭐⭐⭐ | Frontend only |
| **Supabase** | N/A | ✅ 500MB | ✅ | ⭐⭐⭐⭐⭐ | Database only |
| **Render** | 512MB | ✅ | ✅ | ⭐⭐⭐⭐ | Current (memory issues) |

---

## Recommended Setup for PWA

### Architecture
```
┌─────────────────┐
│  Vercel (Frontend) │  ← React PWA
│  HTTPS + CDN    │
└────────┬────────┘
         │
    ┌────▼──────────────────┐
    │  Railway (Backend)    │  ← Flask + ML
    │  512MB+ RAM          │
    └────┬──────────────────┘
         │
    ┌────▼──────────────────┐
    │  Supabase (Database)  │  ← PostgreSQL + pgvector
    │  500MB Free           │
    └───────────────────────┘
```

### Why This Setup?
1. **Vercel**: Perfect for React, free HTTPS, global CDN
2. **Railway**: Handles ML models, flexible memory
3. **Supabase**: Free PostgreSQL, pgvector support, managed

### Cost
- **Total**: $0/month (all free tiers)
- **Scalability**: Easy to upgrade when needed

---

## Step-by-Step Migration

### Step 1: Set Up Supabase Database
1. Go to [supabase.com](https://supabase.com)
2. Create new project
3. Get connection string
4. Enable pgvector extension:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

### Step 2: Deploy Backend to Railway
1. Sign up at [railway.app](https://railway.app)
2. Create new project
3. Add PostgreSQL service (or use Supabase)
4. Deploy backend service
5. Set environment variables

### Step 3: Deploy Frontend to Vercel
1. Go to [vercel.com](https://vercel.com)
2. Import GitHub repo
3. Configure build settings
4. Set `VITE_API_URL` environment variable
5. Deploy

### Step 4: Update CORS
Update backend CORS to allow Vercel domain:
```python
CORS_ORIGINS=https://your-app.vercel.app,https://your-app.railway.app
```

---

## Memory Optimization Tips

1. **Use 1 Worker** (already done ✅)
2. **Lazy Load Models** (already done ✅)
3. **Use Redis for Caching** (optional but helpful)
4. **Optimize Imports** (remove unused)
5. **Consider API-based Embeddings** (if memory still issues)

---

## Testing After Migration

1. ✅ Test API endpoints
2. ✅ Test database connections
3. ✅ Test ML model loading
4. ✅ Test PWA installation
5. ✅ Test share functionality
6. ✅ Monitor memory usage

---

## Support Resources

- **Railway Docs**: https://docs.railway.app
- **Fly.io Docs**: https://fly.io/docs
- **Vercel Docs**: https://vercel.com/docs
- **Supabase Docs**: https://supabase.com/docs

---

## Recommendation

**For your use case (PWA + ML models)**, I recommend:

1. **Frontend**: Vercel (free, perfect for React)
2. **Backend**: Railway (best free tier for ML)
3. **Database**: Supabase (free PostgreSQL with pgvector)

This gives you:
- ✅ Free deployment
- ✅ Better memory allocation
- ✅ HTTPS for PWA
- ✅ Scalability when needed
- ✅ Easy to set up

