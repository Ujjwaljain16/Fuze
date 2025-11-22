# Quick Deploy to Hugging Face Spaces

## Your Space: `Ujjwaljain16/fuze-backend`

---

## 🚀 Quick Steps (Copy-Paste Ready)

### 1. Get Access Token
- Go to: https://huggingface.co/settings/tokens
- Create token with **Write** permissions
- Copy the token

### 2. Clone & Setup (PowerShell)

```powershell
# Navigate to Desktop
cd C:\Users\ujjwa\OneDrive\Desktop

# Clone your Space (paste access token when asked for password)
git clone https://huggingface.co/spaces/Ujjwaljain16/fuze-backend

# Enter Space folder
cd fuze-backend

# Copy all required files
Copy-Item "C:\Users\ujjwa\OneDrive\Desktop\fuze\Dockerfile" -Destination "."
Copy-Item "C:\Users\ujjwa\OneDrive\Desktop\fuze\app.py" -Destination "."
Copy-Item "C:\Users\ujjwa\OneDrive\Desktop\fuze\wsgi.py" -Destination "."
Copy-Item "C:\Users\ujjwa\OneDrive\Desktop\fuze\requirements.txt" -Destination "."
Copy-Item "C:\Users\ujjwa\OneDrive\Desktop\fuze\README.md" -Destination "."
Copy-Item "C:\Users\ujjwa\OneDrive\Desktop\fuze\backend" -Destination "." -Recurse

# Commit and push
git add .
git commit -m "Deploy Fuze backend to Hugging Face Spaces"
git push
```

**When git asks for password**: Paste your **access token** (not your HF password!)

### 3. Wait for Build
- Go to: https://huggingface.co/spaces/Ujjwaljain16/fuze-backend
- Click "Logs" tab
- Wait 5-10 minutes for build to complete

### 4. Set Environment Variables
After build completes:

1. Go to Space → **Settings** → **Variables**
2. Add these (replace with your actual values):

```
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=rediss://your-upstash-redis-url
SECRET_KEY=<generate_with_python_command_below>
JWT_SECRET_KEY=<generate_with_python_command_below>
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=https://your-frontend.vercel.app,https://Ujjwaljain16-fuze-backend.hf.space
GEMINI_API_KEY=<your_key>
```

**Generate secret keys:**
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
Run twice to get two different keys.

### 5. Restart Space
- Go to Space → **Settings**
- Click **Restart this Space**
- Wait 2-3 minutes

### 6. Test
Visit: `https://Ujjwaljain16-fuze-backend.hf.space/api/health`

Should return: `{"status": "ok"}`

---

## 📝 Files You Need

Make sure these files are in your Space:
- ✅ `Dockerfile`
- ✅ `app.py`
- ✅ `wsgi.py`
- ✅ `requirements.txt`
- ✅ `README.md`
- ✅ `backend/` (entire folder)

---

## 🔗 Your API URL

Once deployed:
```
https://Ujjwaljain16-fuze-backend.hf.space
```

Update your frontend's `VITE_API_URL` to this!

---

## ❓ Troubleshooting

**Build fails?**
- Check Logs tab for errors
- Verify all files are copied correctly
- Check Dockerfile syntax

**Git authentication?**
- Use **access token** (not password)
- Make sure token has **Write** permissions

**Port issues?**
- Dockerfile should expose port 7860
- App should bind to 0.0.0.0:7860

---

## 📚 Full Guide

See `docs/HF_SPACES_UPLOAD_STEPS.md` for detailed instructions.

