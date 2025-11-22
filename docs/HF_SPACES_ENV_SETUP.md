# Hugging Face Spaces - Environment Variables Setup

## Current Status

Your app is **running** but needs environment variables to function properly.

## Required Environment Variables

Go to your Space → **Settings** → **Variables** and add these:

### 1. Database (Required) ✅

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

### 2. Redis (Required) ✅

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

### 3. Secret Keys (Required) ✅

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

**Example:**
```
SECRET_KEY=abc123xyz456def789ghi012jkl345mno678pqr901stu234vwx567
JWT_SECRET_KEY=xyz789abc012def345ghi678jkl901mno234pqr567stu890vwx123
```

### 4. Environment (Required) ✅

```
ENVIRONMENT=production
DEBUG=false
```

### 5. CORS Origins (Required) ✅

```
CORS_ORIGINS=https://your-frontend.vercel.app,https://Ujjwaljain16-fuze-backend.hf.space
```

**Replace `your-frontend.vercel.app` with your actual Vercel URL.**

### 6. Gemini API Key (Optional) ⚠️

```
GEMINI_API_KEY=your_gemini_api_key_here
```

Only needed if you want Gemini AI features. Can be added later.

---

## Complete Environment Variables List

Copy-paste this into Hugging Face Spaces Variables (replace with your actual values):

```
DATABASE_URL=postgresql://user:password@host:5432/database
REDIS_URL=rediss://default:password@host:6379
SECRET_KEY=your_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=https://your-frontend.vercel.app,https://Ujjwaljain16-fuze-backend.hf.space
GEMINI_API_KEY=your_gemini_key_optional
```

---

## Step-by-Step Setup

### Step 1: Get Database URL

**If you don't have Supabase yet:**

1. Go to [supabase.com](https://supabase.com)
2. Sign up (free)
3. Create new project
4. Wait for database to provision (2-3 minutes)
5. Go to Settings → Database
6. Copy "Connection string" (URI format)
7. Replace `[YOUR-PASSWORD]` with your database password

**Enable pgvector extension:**
```sql
-- Run this in Supabase SQL Editor
CREATE EXTENSION IF NOT EXISTS vector;
```

### Step 2: Get Redis URL

**If you don't have Upstash yet:**

1. Go to [upstash.com](https://upstash.com)
2. Sign up (free)
3. Create new Redis database
4. Choose "Regional" (free tier)
5. Copy "REST URL" or "Redis URL"
6. Format should be: `rediss://default:PASSWORD@ENDPOINT:6379`

### Step 3: Generate Secret Keys

```powershell
# Run this command twice
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the two different keys generated.

### Step 4: Add Variables to Hugging Face

1. Go to: https://huggingface.co/spaces/Ujjwaljain16/fuze-backend
2. Click **Settings** tab
3. Click **Variables** section
4. Click **Add new variable** for each variable
5. Paste the values
6. Click **Save**

### Step 5: Restart Space

1. Still in **Settings**
2. Scroll to bottom
3. Click **Restart this Space**
4. Wait 2-3 minutes

### Step 6: Verify

Check logs again - you should see:
- ✅ Database connection successful
- ✅ Redis connection successful
- ✅ No more "DATABASE_URL is not set" errors

---

## Quick Checklist

- [ ] Supabase database created
- [ ] pgvector extension enabled
- [ ] Upstash Redis database created
- [ ] DATABASE_URL added to Space variables
- [ ] REDIS_URL added to Space variables
- [ ] SECRET_KEY generated and added
- [ ] JWT_SECRET_KEY generated and added
- [ ] ENVIRONMENT=production added
- [ ] DEBUG=false added
- [ ] CORS_ORIGINS added (with your frontend URL)
- [ ] GEMINI_API_KEY added (optional)
- [ ] Space restarted
- [ ] Logs checked - no errors

---

## Troubleshooting

### "DATABASE_URL is not set"
- ✅ Make sure variable name is exactly `DATABASE_URL`
- ✅ Check for typos
- ✅ Restart Space after adding

### "Redis connection failed"
- ✅ Make sure `REDIS_URL` starts with `rediss://` (with double 's' for SSL)
- ✅ Check Upstash URL format
- ✅ Verify password is correct

### "Could not parse SQLAlchemy URL"
- ✅ Make sure DATABASE_URL format is: `postgresql://user:pass@host:port/db`
- ✅ No spaces in the URL
- ✅ Password doesn't contain special characters that need encoding

### Database connection still fails after setup
- ✅ Check Supabase database is running
- ✅ Verify password is correct
- ✅ Check if IP restrictions are enabled (disable for now)
- ✅ Make sure pgvector extension is enabled

---

## After Setup

Once environment variables are set and Space is restarted:

1. ✅ Database will connect automatically
2. ✅ Redis will connect automatically
3. ✅ App will be fully functional
4. ✅ You can test: `https://Ujjwaljain16-fuze-backend.hf.space/api/health`

---

## Need Help?

If you're stuck:
1. Check the logs tab for specific errors
2. Verify all variables are set correctly
3. Make sure Space is restarted after adding variables
4. Test database connection separately if needed

