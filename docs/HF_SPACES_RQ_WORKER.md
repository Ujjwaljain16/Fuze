# Hugging Face Spaces - RQ Worker Setup

## Overview

For Hugging Face Spaces deployment, the RQ worker runs alongside the web server in the same Docker container. This is handled automatically by the `start.sh` startup script.

## How It Works

The `start.sh` script:
1. **Starts RQ worker** in the background (processes bookmark tasks)
2. **Starts Gunicorn** in the foreground (handles API requests)
3. **Handles graceful shutdown** when container stops

## Files Added/Modified

### 1. `start.sh` (New)
- Startup script that runs both processes
- Handles process management and cleanup
- Makes startup script executable

### 2. `Dockerfile` (Updated)
- Added `COPY start.sh` to include startup script
- Added `RUN chmod +x start.sh` to make it executable
- Changed `CMD` to use `./start.sh` instead of direct gunicorn command

## Deployment

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

## Verification

### Check Worker is Running

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

## Configuration

### Environment Variables

Same environment variables as before - no changes needed:

```env
REDIS_URL=rediss://your-upstash-redis-url
DATABASE_URL=postgresql://...
SECRET_KEY=...
JWT_SECRET_KEY=...
# ... other variables
```

The RQ worker uses the same Redis connection as the web server.

### Worker Settings

The worker runs with default settings:
- **Queue**: `default`
- **Timeout**: 10 minutes per job
- **Retries**: 2 attempts

To customize, modify `backend/worker.py` or pass arguments in `start.sh`.

## Troubleshooting

### Worker Not Starting

**Check logs for errors:**
```
Starting RQ worker...
ERROR: Redis connection not available
```

**Fix:**
- Verify `REDIS_URL` is set correctly in Space variables
- Check Redis connection is accessible from Spaces

### Jobs Not Processing

**Check if worker is running:**
- Look for "Starting RQ worker..." in logs
- Check for worker errors in logs

**Check Redis connection:**
- Verify Redis is accessible
- Check `REDIS_URL` is correct

### Both Processes Not Starting

**Check startup script:**
- Verify `start.sh` is in the repository
- Check Dockerfile includes `COPY start.sh`
- Verify `chmod +x start.sh` is in Dockerfile

## Resource Usage

### Memory

- **Web server**: ~500MB-1GB (with ML models loaded)
- **RQ worker**: ~100-200MB
- **Total**: ~1-1.5GB (well within 16GB limit)

### CPU

- **Web server**: Handles API requests
- **RQ worker**: Processes background jobs
- Both share the 2 vCPUs efficiently

## Scaling

### Single Container (Current Setup)

✅ **Recommended for Hugging Face Spaces**
- One container runs both processes
- Simple and efficient
- Works great for most use cases

### Multiple Workers (If Needed)

If you need more processing power, you can modify `start.sh` to run multiple workers:

```bash
# Start multiple workers
python backend/worker.py --queue default &
python backend/worker.py --queue default &
```

However, with 2 vCPUs, one worker is usually sufficient.

## Advantages

✅ **Automatic**: Worker starts with web server  
✅ **Simple**: No separate configuration needed  
✅ **Efficient**: Both processes share resources  
✅ **Reliable**: Graceful shutdown handling  
✅ **Free**: Uses existing Hugging Face Spaces resources  

## Summary

### What Changed

1. ✅ Added `start.sh` startup script
2. ✅ Updated `Dockerfile` to use startup script
3. ✅ Worker runs automatically on deployment

### What You Need to Do

**Nothing!** The setup is automatic. Just:
1. Deploy to Hugging Face Spaces (as before)
2. Set environment variables (as before)
3. Worker starts automatically ✅

### Benefits

- ✅ Background jobs process automatically
- ✅ No manual worker management
- ✅ Fast API responses (immediate user feedback)
- ✅ Reliable job processing with retries
- ✅ Uses existing Redis connection

Your Hugging Face Spaces deployment now includes automatic background job processing! 🚀

