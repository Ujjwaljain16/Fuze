# RQ Background Jobs - Quick Start Guide

## What Changed?

Your bookmark saving now uses **RQ (Redis Queue)** for asynchronous background processing instead of simple threading. This provides:

- ✅ **Faster API responses** - Users get immediate feedback
- ✅ **Better reliability** - Jobs survive server restarts
- ✅ **Scalability** - Run workers on separate machines
- ✅ **Automatic retries** - Failed jobs retry automatically
- ✅ **Fallback support** - Still works with threading if Redis unavailable

## Quick Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install `rq==1.15.1` (already added to requirements.txt).

### 2. Ensure Redis is Running

Your existing Redis setup works! The same Redis instance used for caching is used for the task queue.

Check Redis connection:
```python
from services.task_queue import is_rq_available
print(is_rq_available())  # Should be True
```

### 3. Start a Worker

**Development:**
```bash
python backend/worker.py
```

**Production (if Procfile supported):**
The `Procfile` already includes:
```
worker: python backend/worker.py
```

**Manual (if needed):**
Run in a separate terminal/process:
```bash
python backend/worker.py --queue default
```

## How It Works

### User Flow

1. User shares link → Clicks "Save"
2. Frontend calls `/api/bookmarks/quick-save`
3. Backend **immediately** saves bookmark and returns success
4. Backend **enqueues** background job for content processing
5. User is **immediately returned** to previous app
6. **Worker processes** content in background (scraping, embedding, analysis)

### What Happens in Background

The RQ worker automatically:
- Extracts content from URL
- Generates embeddings
- Updates bookmark with full data
- Triggers analysis
- Invalidates caches

## Testing

### Test Quick Save

1. Share a link from another app
2. Click "Save" in Fuze
3. You should **immediately** see success message
4. You should **immediately** be returned to previous app
5. Check dashboard later - bookmark should have full content

### Test Worker

1. Start worker: `python backend/worker.py`
2. Save a bookmark
3. Watch worker logs - you should see:
   ```
   Starting RQ worker for queue: default
   Redis connection: Connected
   Processing job: bookmark_process_123_456
   Background processing started for bookmark 123
   Background processing completed for bookmark 123
   ```

### Verify Jobs Are Processing

Check Redis for queued jobs:
```bash
redis-cli
> KEYS rq:*
> LLEN rq:queue:default
```

## Troubleshooting

### "Falling back to threading"

This means RQ/Redis is unavailable. The system still works, but:
- Jobs won't survive server restarts
- No job status tracking
- No automatic retries

**Fix:** Ensure Redis is running and accessible.

### Worker Not Processing

1. **Check Redis connection:**
   ```python
   from services.task_queue import redis_conn
   redis_conn.ping()  # Should return True
   ```

2. **Check worker is running:**
   ```bash
   python backend/worker.py
   # Should see "Starting RQ worker..."
   ```

3. **Check for errors in worker output**

### Jobs Stuck in Queue

1. Check worker is running
2. Check Redis connection
3. Check worker logs for errors
4. Verify database connection works in worker context

## Production Deployment

### Option 1: Procfile (Heroku, Railway, etc.)

Already configured! Just ensure your platform supports multiple processes:
```
web: gunicorn backend.wsgi:app ...
worker: python backend/worker.py
```

### Option 2: Separate Service/Container

Run worker as separate service:
```bash
# In separate container/VM
python backend/worker.py
```

### Option 3: Process Manager

Use `supervisord` or similar:
```ini
[program:fuze-worker]
command=python backend/worker.py
directory=/path/to/fuze
autostart=true
autorestart=true
```

### Option 4: Systemd Service

Create `/etc/systemd/system/fuze-worker.service`:
```ini
[Unit]
Description=Fuze RQ Worker
After=network.target redis.service

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/fuze
ExecStart=/path/to/venv/bin/python backend/worker.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Scaling

### Multiple Workers

Run multiple workers for parallel processing:

```bash
# Terminal 1
python backend/worker.py --queue default

# Terminal 2
python backend/worker.py --queue default

# Terminal 3
python backend/worker.py --queue default
```

Or use process manager to run multiple instances.

### Queue Priorities

Use `high` queue for urgent tasks:
```python
enqueue_bookmark_processing(bookmark_id, url, user_id, queue_name='high')
```

Then run separate worker for high priority:
```bash
python backend/worker.py --queue high
```

## Monitoring

### Check Job Status

```python
from services.task_queue import get_job_status

status = get_job_status('bookmark_process_123_456')
print(status)
# {'id': '...', 'status': 'finished', 'created_at': '...', ...}
```

### RQ Dashboard (Optional)

Install and run:
```bash
pip install rq-dashboard
rq-dashboard
# Access at http://localhost:9181
```

## No Breaking Changes

✅ **Backward compatible** - Falls back to threading if RQ unavailable  
✅ **Same API** - No frontend changes needed  
✅ **Same behavior** - Users see no difference  
✅ **Gradual migration** - Works immediately, improve over time

## Next Steps

1. ✅ Install RQ (already in requirements.txt)
2. ✅ Start worker process
3. ✅ Test quick-save functionality
4. ✅ Monitor worker logs
5. ✅ Scale workers as needed

For detailed documentation, see `docs/BACKGROUND_JOBS.md`.

