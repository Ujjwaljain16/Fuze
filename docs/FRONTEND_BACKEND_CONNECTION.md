# Frontend-Backend Connection Setup

## Current Status

**Frontend**: `itsfuze.vercel.app`  
**Backend**: `Ujjwaljain16-fuze-backend.hf.space`

## ✅ What You Need to Do

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

---

## Step 3: Update Backend CORS

Make sure your Hugging Face Spaces backend has the correct CORS configuration:

1. Go to: https://huggingface.co/spaces/Ujjwaljain16/fuze-backend
2. **Settings** → **Variables**
3. Check `CORS_ORIGINS` includes:
   ```
   https://itsfuze.vercel.app,https://Ujjwaljain16-fuze-backend.hf.space
   ```

---

## Verification Checklist

### Frontend Configuration ✅
- [ ] `VITE_API_URL` set in Vercel
- [ ] Environment variable set for **Production**
- [ ] Frontend redeployed after setting variable

### Backend Configuration ✅
- [ ] `CORS_ORIGINS` includes `https://itsfuze.vercel.app`
- [ ] Backend is running (check logs)
- [ ] Database connected (no errors in logs)
- [ ] Redis connected (no errors in logs)

### Testing ✅
- [ ] Open `https://itsfuze.vercel.app`
- [ ] Check browser console (F12) - should see API calls
- [ ] Try logging in
- [ ] Check Network tab - API calls should go to `*.hf.space`

---

## How to Verify It's Working

### 1. Check Browser Console

Open `https://itsfuze.vercel.app` and press F12:

**If working correctly:**
- No errors about `VITE_API_URL`
- API calls visible in Network tab
- Calls going to `Ujjwaljain16-fuze-backend.hf.space`

**If not working:**
- Error: "API URL not configured"
- Error: "CORS policy blocked"
- Network requests failing

### 2. Test API Connection

Open browser console and run:
```javascript
fetch('https://Ujjwaljain16-fuze-backend.hf.space/api/health')
  .then(r => r.json())
  .then(console.log)
```

Should return: `{"status": "ok"}` or similar

### 3. Test Login

1. Go to `https://itsfuze.vercel.app/login`
2. Try logging in
3. Check Network tab - should see requests to `*.hf.space`
4. Should work if everything is configured correctly

---

## Common Issues

### Issue 1: "API URL not configured"

**Cause**: `VITE_API_URL` not set in Vercel

**Fix**: 
1. Add `VITE_API_URL` in Vercel Settings → Environment Variables
2. Redeploy frontend

### Issue 2: CORS Errors

**Cause**: Backend CORS not configured for frontend domain

**Fix**:
1. Update `CORS_ORIGINS` in Hugging Face Spaces
2. Include: `https://itsfuze.vercel.app`
3. Restart Space

### Issue 3: Network Errors

**Cause**: Backend not running or wrong URL

**Fix**:
1. Check backend logs in Hugging Face Spaces
2. Verify backend URL is correct
3. Test backend health endpoint directly

---

## Quick Setup Commands

### For Vercel (via CLI):

```bash
# Set environment variable
vercel env add VITE_API_URL production

# When prompted, enter:
https://Ujjwaljain16-fuze-backend.hf.space

# Redeploy
vercel --prod
```

### For Hugging Face Spaces:

Update `CORS_ORIGINS` variable:
```
https://itsfuze.vercel.app,https://Ujjwaljain16-fuze-backend.hf.space
```

---

## Summary

**Your frontend is NOT ready yet** - you need to:

1. ✅ Set `VITE_API_URL` in Vercel
2. ✅ Update `CORS_ORIGINS` in Hugging Face Spaces
3. ✅ Redeploy frontend
4. ✅ Test connection

Once these are done, your frontend will be ready to interact with the new backend! 🚀

