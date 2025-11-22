# Background Job Processing with RQ

This document explains how background job processing works in Fuze using RQ (Redis Queue).

## Overview

When users save bookmarks via the share handler or quick-save endpoint, the system:

1. **Immediately saves** the bookmark with minimal data
2. **Returns a response** to the user right away
3. **Processes content asynchronously** in the background (scraping, embedding, analysis)

This ensures fast user experience while heavy processing happens behind the scenes.

## Architecture

```
User Action → API Endpoint → Enqueue Job → Immediate Response
                                      ↓
                              RQ Worker → Process Content → Update Database
```

### Components

1. **Task Queue Service** (`backend/services/task_queue.py`)
   - Manages RQ queues and job enqueueing
   - Handles Redis connection
   - Provides job status checking

2. **Bookmark Processing Task** (`backend/blueprints/bookmarks.py`)
   - `process_bookmark_content_task()`: The actual task function that RQ workers execute
   - Handles content extraction, embedding generation, and analysis

3. **RQ Worker** (`backend/worker.py`)
   - Background process that listens to queues and executes tasks
   - Can run multiple workers for parallel processing

## Setup

### Prerequisites

- Redis server running and accessible
- RQ installed (`pip install rq`)

### Running Workers

#### Development

```bash
# Start a single worker for default queue
python backend/worker.py

# Start worker for specific queue
python backend/worker.py --queue default

# Run in burst mode (process all jobs and exit)
python backend/worker.py --burst
```

#### Production

For platforms that support multiple processes (Heroku, Railway, etc.), the `Procfile` includes:

```
worker: python backend/worker.py
```

This will automatically start a worker process alongside the web server.

### Manual Worker Start

If your platform doesn't support multiple processes in Procfile, you can:

1. Run worker as a separate service/container
2. Use a process manager like `supervisord`
3. Run worker manually in a separate terminal/SSH session

## How It Works

### 1. User Saves Bookmark

When a user shares a link and clicks "Save":

```javascript
// Frontend calls quick-save endpoint
POST /api/bookmarks/quick-save
{
  "url": "https://example.com",
  "title": "Example",
  "description": "Description"
}
```

### 2. Backend Enqueues Job

The backend:
- Saves bookmark immediately with minimal data
- Enqueues a background job using RQ
- Returns success response immediately

```python
# In bookmarks.py
process_bookmark_content_async(bookmark_id, url, user_id)
  → enqueue_bookmark_processing()  # Uses RQ
  → Returns immediately
```

### 3. Worker Processes Job

RQ worker picks up the job and:
- Extracts content from URL
- Generates embeddings
- Updates bookmark with full data
- Triggers analysis

### 4. Fallback to Threading

If Redis/RQ is unavailable, the system automatically falls back to threading:

```python
# Automatic fallback
if RQ not available:
    → Use threading.Thread (existing behavior)
```

## Queue Configuration

### Default Queue

- **Name**: `default`
- **Purpose**: Normal priority bookmark processing
- **Timeout**: 10 minutes per job
- **Retries**: 2 attempts (after 1min, then 5min)

### High Priority Queue (Optional)

- **Name**: `high`
- **Purpose**: Urgent tasks (can be used for priority bookmarks)
- **Usage**: `enqueue_bookmark_processing(..., queue_name='high')`

## Monitoring

### Check Job Status

```python
from services.task_queue import get_job_status

status = get_job_status(job_id)
# Returns: {'id', 'status', 'created_at', 'started_at', 'ended_at', ...}
```

### RQ Dashboard (Optional)

You can install `rq-dashboard` for a web-based monitoring interface:

```bash
pip install rq-dashboard
rq-dashboard
# Access at http://localhost:9181
```

## Troubleshooting

### Worker Not Processing Jobs

1. **Check Redis connection**:
   ```python
   from services.task_queue import is_rq_available
   print(is_rq_available())  # Should be True
   ```

2. **Check worker is running**:
   ```bash
   # Should see worker output
   python backend/worker.py
   ```

3. **Check Redis keys**:
   ```bash
   redis-cli
   > KEYS rq:*
   ```

### Jobs Failing

- Check worker logs for error messages
- Verify Redis connection is stable
- Ensure database connection is available in worker context
- Check if scraping/embedding services are accessible

### Fallback to Threading

If you see "falling back to threading" messages:
- Redis connection failed
- RQ not properly initialized
- System will still work, but without queue management

## Performance

### Scaling Workers

For high traffic, run multiple workers:

```bash
# Terminal 1
python backend/worker.py --queue default

# Terminal 2
python backend/worker.py --queue default

# Or use process manager
supervisord  # Configure multiple workers
```

### Queue Priorities

- Use `default` queue for normal bookmarks
- Use `high` queue for urgent/priority content
- Workers can listen to multiple queues

## Environment Variables

No additional environment variables needed beyond existing Redis configuration:

- `REDIS_URL` (or `REDIS_HOST`, `REDIS_PORT`, etc.)
- Same Redis instance used for caching and task queue

## Benefits Over Threading

1. **Persistent**: Jobs survive server restarts
2. **Scalable**: Run workers on separate machines
3. **Monitorable**: Track job status and failures
4. **Retry Logic**: Automatic retries on failure
5. **Priority Queues**: Handle urgent tasks first
6. **Resource Management**: Better control over concurrent jobs

## Migration Notes

The system automatically falls back to threading if RQ is unavailable, so:
- ✅ No breaking changes
- ✅ Works immediately with existing setup
- ✅ Gradually migrate to RQ when Redis is available
- ✅ Zero downtime migration

