# Railway Migration Guide - Step by Step

## Prerequisites
- GitHub account with Fuze repository
- Railway account (sign up at railway.app)

## Step 1: Create Railway Account
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Authorize Railway to access your repositories

## Step 2: Create New Project
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose your Fuze repository
4. Railway will detect it's a Python project

## Step 3: Add PostgreSQL Database
1. In your Railway project, click "New"
2. Select "Database" → "PostgreSQL"
3. Railway will create a PostgreSQL instance
4. Copy the connection string (DATABASE_URL)

## Step 4: Configure Backend Service
1. Railway should auto-detect your backend
2. If not, click "New" → "GitHub Repo" → Select your repo
3. Set the root directory (if needed): `backend/` or root
4. Railway will auto-detect Python

## Step 5: Set Environment Variables
In Railway dashboard, go to your service → Variables tab:

```env
DATABASE_URL=<from_postgres_service>
SECRET_KEY=<generate_random_string>
JWT_SECRET_KEY=<generate_random_string>
ENVIRONMENT=production
DEBUG=false
REDIS_URL=<optional_if_using_redis>
GEMINI_API_KEY=<your_gemini_key_if_needed>
```

**Generate Secret Keys**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Step 6: Configure Start Command
In Railway service settings:
- **Start Command**: `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`
- **Port**: Railway sets `$PORT` automatically

## Step 7: Deploy
1. Railway will auto-deploy on push to main branch
2. Or click "Deploy" button manually
3. Wait for deployment to complete
4. Get your Railway URL (e.g., `fuze-backend.railway.app`)

## Step 8: Initialize Database
1. Get your Railway service URL
2. SSH into service or use Railway CLI:
   ```bash
   railway run python backend/init_db.py
   ```

## Step 9: Deploy Frontend to Vercel
1. Go to [vercel.com](https://vercel.com)
2. Import your GitHub repository
3. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Add Environment Variable:
   - `VITE_API_URL`: `https://your-railway-url.railway.app`
5. Deploy

## Step 10: Update CORS
In your Railway backend, add to environment variables:
```env
CORS_ORIGINS=https://your-app.vercel.app,https://your-app.railway.app
```

## Step 11: Test
1. Visit your Vercel frontend URL
2. Test login/registration
3. Test bookmark saving
4. Test PWA installation
5. Test share functionality

## Troubleshooting

### Memory Issues
- Railway free tier: 512MB RAM
- If still having issues, consider:
  - Using external embedding API
  - Reducing model size
  - Using Supabase for database (separate service)

### Database Connection
- Verify DATABASE_URL is correct
- Check if pgvector extension is enabled
- Run `init_db.py` to set up tables

### CORS Errors
- Verify CORS_ORIGINS includes your frontend URL
- Check backend logs for CORS errors

### Build Failures
- Check Railway build logs
- Verify requirements.txt is correct
- Check Python version compatibility

## Monitoring
- Railway dashboard shows:
  - Memory usage
  - CPU usage
  - Request logs
  - Error logs

## Cost
- **Free Tier**: $5/month credit
- **PostgreSQL**: Included in free tier
- **Usage**: Monitor in Railway dashboard
- **Upgrade**: Only if needed (very affordable)

## Next Steps
1. Set up custom domain (optional)
2. Configure auto-deployments
3. Set up monitoring/alerts
4. Optimize memory usage if needed

