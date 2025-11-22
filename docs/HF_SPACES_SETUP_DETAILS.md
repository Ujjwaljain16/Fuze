# Hugging Face Spaces - Setup Details

## Visibility: Public vs Private

### ❓ Do You Need Public Visibility?

**Answer: NO - Private is recommended!**

### Private (Recommended) ✅
- **What it means**: Only you (and collaborators) can access the Space URL directly
- **Your frontend can still call it**: Yes! Your Vercel frontend can make API calls to a Private Space
- **Security**: Better - your backend API isn't publicly discoverable
- **Use case**: Perfect for production apps with authentication

### Public
- **What it means**: Anyone can discover and access your Space
- **Use case**: Good for demos, open-source projects, or if you want public discovery
- **Security**: Less secure - anyone can see your Space exists (but JWT auth still protects endpoints)

### Recommendation for Your App
**Choose PRIVATE** because:
1. ✅ You have JWT authentication (access control is handled in-app)
2. ✅ Your frontend (Vercel) can still call the API
3. ✅ Better security - backend not publicly discoverable
4. ✅ No one can access your Space URL directly without auth

---

## Docker Template Selection

### ❓ What Template to Choose?

**Answer: Choose "Blank" template**

### Template Options:
1. **Blank** ✅ **CHOOSE THIS**
   - Full control with your custom `Dockerfile`
   - Perfect for Flask apps
   - You define everything

2. **Pre-made templates** ❌ Don't choose these
   - Examples: "Python", "Node.js", etc.
   - These are for simpler apps
   - Won't work well with your Flask setup

### Why Blank?
- You already have a custom `Dockerfile` (I created it for you)
- Blank template lets you use your own Dockerfile
- Full control over the environment

---

## Step-by-Step Space Creation

1. **Go to**: [huggingface.co/spaces](https://huggingface.co/spaces)
2. **Click**: "Create new Space"
3. **Fill in**:
   ```
   Space name: fuze-backend
   SDK: Docker
   Template: Blank ← IMPORTANT!
   Hardware: CPU basic (free tier)
   Visibility: Private ← Recommended
   ```
4. **Click**: "Create Space"
5. **Upload files** (or use Git):
   - `Dockerfile`
   - `app.py`
   - `wsgi.py`
   - `requirements.txt`
   - `backend/` folder
   - `README.md`

---

## Visual Guide

### When Creating Space:

```
┌─────────────────────────────────────┐
│  Create a new Space                 │
├─────────────────────────────────────┤
│  Space name: [fuze-backend]         │
│                                     │
│  SDK: [Docker ▼]                    │
│                                     │
│  Template: [Blank ▼] ← Choose this!│
│                                     │
│  Hardware: [CPU basic ▼]           │
│                                     │
│  Visibility: [Private ▼] ← Choose!  │
│                                     │
│  [Create Space]                     │
└─────────────────────────────────────┘
```

---

## Common Questions

### Q: Can my frontend call a Private Space?
**A: Yes!** Private only means the Space URL isn't publicly discoverable. Your frontend can still make API calls to it.

### Q: Will CORS work with Private Space?
**A: Yes!** CORS is configured via environment variables (`CORS_ORIGINS`). Private/Public doesn't affect CORS.

### Q: Can I change visibility later?
**A: Yes!** You can change from Private to Public (or vice versa) in Space Settings anytime.

### Q: What if I choose a pre-made template?
**A: It won't work well** - pre-made templates expect different file structures. Always choose "Blank" for custom Flask apps.

---

## Summary

✅ **Visibility**: Choose **Private** (recommended) or Public  
✅ **Template**: Choose **Blank** (required for custom Dockerfile)  
✅ **SDK**: Choose **Docker** (required)  
✅ **Hardware**: Choose **CPU basic** (free tier)

Your frontend will work fine with a Private Space! 🔒

