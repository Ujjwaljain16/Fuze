# Upload Your Code to Hugging Face Space

## Step-by-Step Guide (Windows PowerShell)

Your Space is created: `Ujjwaljain16/fuze-backend`

---

## Step 1: Get Access Token

1. Go to: https://huggingface.co/settings/tokens
2. Click "New token"
3. Name: `fuze-backend-deploy`
4. Type: **Write** (needed to push code)
5. Click "Generate token"
6. **Copy the token** (you'll need it for git password)

---

## Step 2: Clone Your Space

Open PowerShell in a folder where you want to clone (e.g., Desktop):

```powershell
# Navigate to where you want to clone
cd C:\Users\ujjwa\OneDrive\Desktop

# Clone the Space (use your access token as password when prompted)
git clone https://huggingface.co/spaces/Ujjwaljain16/fuze-backend

# Enter the Space folder
cd fuze-backend
```

**When prompted for password**: Paste your access token (not your HF password!)

---

## Step 3: Copy Your Files

From your main project folder, copy these files to the Space:

```powershell
# Make sure you're in the Space folder
cd C:\Users\ujjwa\OneDrive\Desktop\fuze-backend

# Copy files from your main project
Copy-Item "C:\Users\ujjwa\OneDrive\Desktop\fuze\Dockerfile" -Destination "."
Copy-Item "C:\Users\ujjwa\OneDrive\Desktop\fuze\app.py" -Destination "."
Copy-Item "C:\Users\ujjwa\OneDrive\Desktop\fuze\wsgi.py" -Destination "."
Copy-Item "C:\Users\ujjwa\OneDrive\Desktop\fuze\requirements.txt" -Destination "."
Copy-Item "C:\Users\ujjwa\OneDrive\Desktop\fuze\README.md" -Destination "."

# Copy the entire backend folder
Copy-Item "C:\Users\ujjwa\OneDrive\Desktop\fuze\backend" -Destination "." -Recurse
```

---

## Step 4: Verify Files

Check that all files are there:

```powershell
# List files
ls

# Should see:
# - Dockerfile
# - app.py
# - wsgi.py
# - requirements.txt
# - README.md
# - backend/ (folder)
```

---

## Step 5: Commit and Push

```powershell
# Add all files
git add .

# Commit
git commit -m "Deploy Fuze backend to Hugging Face Spaces"

# Push (use access token as password when prompted)
git push
```

**When prompted for password**: Use your access token again (not your HF password!)

---

## Step 6: Wait for Build

1. Go to your Space: https://huggingface.co/spaces/Ujjwaljain16/fuze-backend
2. Click on the "Logs" tab
3. Watch the build process (takes 5-10 minutes)
4. Wait for: "Your Space is running!"

---

## Step 7: Set Environment Variables

After build completes:

1. Go to Space → **Settings** → **Variables**
2. Add these variables:

```
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=rediss://your-upstash-redis-url
SECRET_KEY=<generate_random_32_char_string>
JWT_SECRET_KEY=<generate_random_32_char_string>
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=https://your-frontend.vercel.app,https://Ujjwaljain16-fuze-backend.hf.space
GEMINI_API_KEY=<your_key_if_needed>
```

**Generate Secret Keys:**
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Run this twice to get two different keys for SECRET_KEY and JWT_SECRET_KEY.

---

## Step 8: Restart Space

After adding environment variables:

1. Go to Space → **Settings**
2. Click **Restart this Space**
3. Wait for it to restart (2-3 minutes)

---

## Step 9: Test Your API

Test the health endpoint:

```
https://Ujjwaljain16-fuze-backend.hf.space/api/health
```

Should return: `{"status": "ok"}` or similar

---

## Troubleshooting

### Git Authentication Issues

If git asks for password repeatedly:

1. Use **access token** (not your HF password)
2. Or set up credential helper:
   ```powershell
   git config --global credential.helper wincred
   ```

### Build Fails

1. Check **Logs** tab in your Space
2. Look for error messages
3. Common issues:
   - Missing files (check Step 4)
   - Wrong Dockerfile format
   - Requirements.txt errors

### Port Issues

Make sure your Dockerfile exposes port 7860:
```dockerfile
EXPOSE 7860
```

And your app binds to 0.0.0.0:7860

---

## Quick Copy-Paste Commands

Here's everything in one block (adjust paths as needed):

```powershell
# 1. Clone Space
cd C:\Users\ujjwa\OneDrive\Desktop
git clone https://huggingface.co/spaces/Ujjwaljain16/fuze-backend
cd fuze-backend

# 2. Copy files
Copy-Item "C:\Users\ujjwa\OneDrive\Desktop\fuze\Dockerfile" -Destination "."
Copy-Item "C:\Users\ujjwa\OneDrive\Desktop\fuze\app.py" -Destination "."
Copy-Item "C:\Users\ujjwa\OneDrive\Desktop\fuze\wsgi.py" -Destination "."
Copy-Item "C:\Users\ujjwa\OneDrive\Desktop\fuze\requirements.txt" -Destination "."
Copy-Item "C:\Users\ujjwa\OneDrive\Desktop\fuze\README.md" -Destination "."
Copy-Item "C:\Users\ujjwa\OneDrive\Desktop\fuze\backend" -Destination "." -Recurse

# 3. Commit and push
git add .
git commit -m "Deploy Fuze backend"
git push
```

---

## Next Steps After Deployment

1. ✅ Set environment variables (Step 7)
2. ✅ Restart Space (Step 8)
3. ✅ Test API (Step 9)
4. ✅ Initialize database (one-time):
   - Use Space terminal or run: `python backend/init_db.py`
5. ✅ Update frontend CORS settings
6. ✅ Test full app flow

---

## Your Space URL

Once deployed, your API will be at:
```
https://Ujjwaljain16-fuze-backend.hf.space
```

Update your frontend's `VITE_API_URL` to point to this URL!

