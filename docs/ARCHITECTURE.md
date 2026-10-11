# System Architecture - Scalable Design

Complete scalable architecture documentation for Fuze - Intelligent Content Manager.

## ⚠️ Important: Current Implementation vs Scalable Design

> [!WARNING]
> **Deployment status:** the hosted backend runs on a Hugging Face Space and
> was paused by HF's abuse detection and is pending unpause. HF now requires a paid PRO subscription to *create* new Docker
> Spaces on the free tier, so a free/low-cost fallback host is being
> evaluated. The image contains no browser-automation tooling;
> scraping is plain HTTP only. See the
> root [`README.md`](../README.md) and
> [`gaps_closure_plan.md`](../gaps_closure_plan.md).

**This document describes both:**
- **Current Implementation**: The single-container design this repo actually runs (whichever host it's deployed to)
- **Scalable Design**: Architecture that supports future scaling (ready for horizontal scaling)

**Key Distinction:**
- **Current**: 2 Gunicorn workers (gevent, sized for a 2-vCPU host), single database, single Redis, RQ workers, no load balancer (platform handles routing)
- **Scalable**: Architecture designed to support multiple workers, load balancers, database replicas, Redis clusters when needed
- **Why**: Stateless design means scaling is just configuration changes, not code changes

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Layers](#architecture-layers)
3. [Database Architecture](#database-architecture)
4. [Caching Architecture](#caching-architecture)
5. [Horizontal Scaling Strategy](#horizontal-scaling-strategy)
6. [Load Distribution](#load-distribution)
7. [Data Isolation & Security](#data-isolation--security)
8. [Background Processing Architecture](#background-processing-architecture)
9. [ML/AI Architecture](#mlai-architecture)
10. [API Architecture](#api-architecture)
11. [Frontend Architecture](#frontend-architecture)
12. [Deployment Architecture](#deployment-architecture)

---

## System Overview

Fuze is built as a scalable, multi-tenant system designed to handle thousands of concurrent users with individual API keys, isolated data, and independent processing pipelines.

### Core Principles

1. **User Isolation**: Complete data isolation per user
2. **Horizontal Scalability**: Stateless design for easy scaling
3. **Shared Caching**: Redis (per-process caches only for feature flags and API keys)
4. **Background Processing**: Non-blocking async operations
5. **Connection Pooling**: Efficient database connection management
6. **Rate Limiting**: Per-user and per-IP rate limits
7. **Graceful Degradation**: System works even when components fail

### High-Level Architecture

**Current Implementation (What's Deployed):**

```mermaid
graph TB
    subgraph "Client Layer"
        WebApp[Web Application<br/>React + Vite]
        Extension[Chrome Extension<br/>Manifest V3]
    end
    
    subgraph "Platform Layer"
        Platform[Hugging Face Spaces<br/>Handles Routing & SSL]
    end
    
    subgraph "Application Layer - Current"
        Worker1[Gunicorn Worker 1<br/>gevent async<br/>1000+ connections]
        RQWorker[RQ Worker<br/>Background Jobs]
    end
    
    subgraph "Shared Services Layer"
        Redis[(Redis Instance<br/>Upstash - Single)]
        Queue[RQ Task Queue<br/>Redis-based]
    end
    
    subgraph "Data Layer"
        PostgreSQL[(PostgreSQL<br/>Supabase - Single<br/>+ pgvector)]
    end
    
    subgraph "External Services"
        Gemini[Google Gemini AI<br/>Per-User API Keys]
        WebContent[Web Scraping<br/>Services]
    end
    
    WebApp --> Platform
    Extension --> Platform
    
    Platform --> Worker1
    
    Worker1 --> Redis
    Worker1 --> PostgreSQL
    
    Worker1 --> Queue
    Queue --> RQWorker
    
    RQWorker --> Redis
    RQWorker --> PostgreSQL
    RQWorker --> Gemini
    RQWorker --> WebContent
    
    Worker1 --> WebContent
    
    style WebApp fill:#4a90e2
    style Extension fill:#4a90e2
    style Platform fill:#cd853f
    style Worker1 fill:#50c878
    style RQWorker fill:#50c878
    style Redis fill:#ff6b6b
    style PostgreSQL fill:#9b59b6
    style Gemini fill:#9b59b6
```

**Scalable Design (Future-Ready Architecture):**

```mermaid
graph TB
    subgraph "Client Layer"
        WebApp[Web Application<br/>React + Vite]
        Extension[Chrome Extension<br/>Manifest V3]
        Mobile[Mobile Apps<br/>Future]
    end
    
    subgraph "Load Balancer Layer"
        LB[Load Balancer<br/>Nginx/Cloudflare]
    end
    
    subgraph "Application Layer - Stateless Workers"
        Worker1[Flask Worker 1<br/>Gunicorn]
        Worker2[Flask Worker 2<br/>Gunicorn]
        WorkerN[Flask Worker N<br/>Gunicorn]
    end
    
    subgraph "Shared Services Layer"
        Redis[(Redis Cluster<br/>Caching & Sessions)]
        Queue[Task Queue<br/>RQ]
    end
    
    subgraph "Data Layer"
        PostgreSQL[(PostgreSQL Primary<br/>+ pgvector)]
        Replica1[(PostgreSQL Replica 1)]
        ReplicaN[(PostgreSQL Replica N)]
    end
    
    subgraph "External Services"
        Gemini[Google Gemini AI<br/>Per-User API Keys]
        WebContent[Web Scraping<br/>Services]
    end
    
    WebApp --> LB
    Extension --> LB
    Mobile --> LB
    
    LB --> Worker1
    LB --> Worker2
    LB --> WorkerN
    
    Worker1 --> Redis
    Worker2 --> Redis
    WorkerN --> Redis
    
    Worker1 --> Queue
    Worker2 --> Queue
    WorkerN --> Queue
    
    Worker1 --> PostgreSQL
    Worker2 --> Replica1
    WorkerN --> ReplicaN
    
    Queue --> PostgreSQL
    Queue --> Gemini
    
    Worker1 --> WebContent
    Worker2 --> WebContent
    
    style WebApp fill:#4a90e2
    style Extension fill:#4a90e2
    style LB fill:#cd853f
    style Worker1 fill:#50c878
    style Worker2 fill:#50c878
    style WorkerN fill:#50c878
    style Redis fill:#ff6b6b
    style PostgreSQL fill:#9b59b6
    style Gemini fill:#9b59b6
```

---

## Architecture Layers

### Layer 1: Client Layer

**Components:**
- Web Application (React + Vite)
- Chrome Extension (Manifest V3)
- Future: Mobile Apps

**Characteristics:**
- Stateless clients
- JWT token-based authentication
- API calls to backend
- Client-side caching

### Layer 2: Load Balancer Layer

**Current Implementation:**
- ❌ **Not Implemented**: No custom load balancer
- ✅ **Platform Handled**: Hugging Face Spaces handles routing, SSL termination, and health checks
- ✅ **Design Ready**: Architecture supports load balancer when needed

**Scalable Design (Future):**
- **Responsibilities:**
  - Request routing
  - SSL termination
  - Rate limiting (first line)
  - Health checks
  - Session affinity (if needed)
- **Implementation:**
  - Nginx or Cloudflare
  - Round-robin or least-connections
  - Health check endpoints

### Layer 3: Application Layer (Stateless Workers)

**Current Implementation:**
- ✅ **2 Gunicorn Workers**: gevent async I/O, sized for the 2-vCPU host
- ✅ **Gevent Worker Class**: up to 1000 connections per worker; psycogreen makes
  Postgres queries yield (5 concurrent `pg_sleep(1)`: 5.05 s unpatched, 1.01 s
  patched), and `model.encode` / bcrypt run on gevent's thread pool
  (`utils/cooperative.py`)
- ✅ **Stateless Design**: No local state, all state in Redis/DB
- ✅ **Connection Pooling**: 5 base, 10 overflow connections, 5 s connect timeout,
  15 s `statement_timeout` per connection, `sslmode=require` in production
- ✅ **RQ Workers**: `default` and `high` queues, supervised next to Gunicorn

**Current Configuration** (`gunicorn.conf.py`, started by `supervisord.conf`):
```python
workers = 2
worker_class = "gevent"
worker_connections = 1000
timeout = 60            # was 2000 s; a stuck worker is recycled within a minute
graceful_timeout = 30
preload_app = False     # each worker opens its own DB/Redis connections after fork

def post_fork(server, worker):
    from psycogreen.gevent import patch_psycopg
    patch_psycopg()
    torch.set_num_threads(1)
```

**Scalable Design (Future):**
- **Multiple Flask workers** (Gunicorn)
- **Stateless design** - no local state
- **Shared Redis** for sessions/cache
- **Connection pooling** to database
- **Scaling:**
  - Add/remove workers dynamically
  - Auto-scaling based on load
  - Each worker handles any request

### Layer 4: Shared Services Layer

**Current Implementation:**
- ✅ **Single Redis Instance**: Upstash (free tier)
- ✅ **RQ Task Queue**: Redis-based task queue (not Celery)
- ✅ **Shared Across Workers**: All workers use same Redis

**Scalable Design (Future):**
- **Redis Cluster** (caching, sessions, rate limiting)
- **Task Queue** (RQ/Background workers - already using RQ)
- **Message Broker** (for async tasks)

### Layer 5: Data Layer

**Current Implementation:**
- ✅ **Single PostgreSQL**: Supabase (single database instance)
- ✅ **pgvector Extension**: For vector search
- ✅ **Connection Pooling**: 5 base, 10 overflow connections
- ✅ **Alembic-Managed Indexes**: Optimized for performance (HNSW for vectors)
- ❌ **No Read Replicas**: All operations to single database

**Scalable Design (Future):**
- **PostgreSQL Primary** (writes)
- **PostgreSQL Replicas** (reads)
- **pgvector extension** for vector search
- **Connection pooling**
- **Read/write splitting** (architecture supports it)

---

## Database Architecture

### Database Schema Design

```mermaid
erDiagram
    USERS ||--o{ SAVED_CONTENT : has
    USERS ||--o{ PROJECTS : has
    USERS ||--o{ USER_FEEDBACK : has
    PROJECTS ||--o{ TASKS : has
    TASKS ||--o{ SUBTASKS : has
    SAVED_CONTENT ||--o| CONTENT_ANALYSIS : analyzed_by
    SAVED_CONTENT ||--o{ USER_FEEDBACK : receives
    
    USERS {
        int id PK
        string username UK
        string email UK
        string password_hash
        json user_metadata
        datetime created_at
    }
    
    SAVED_CONTENT {
        int id PK
        int user_id FK
        text url
        string title
        text extracted_text
        vector embedding
        int quality_score
        datetime saved_at
    }
    
    PROJECTS {
        int id PK
        int user_id FK
        string title
        text description
        text technologies
        vector embedding
        json intent_analysis
        datetime created_at
    }
    
    CONTENT_ANALYSIS {
        int id PK
        int content_id FK
        json analysis_data
        text key_concepts
        string content_type
        string difficulty_level
        text technology_tags
        int relevance_score
    }
```

### Database Indexing Strategy

**Critical Indexes for Performance:**

```sql
-- User Isolation Indexes (CRITICAL for security and performance)
CREATE INDEX idx_saved_content_user_id ON saved_content(user_id);
CREATE INDEX idx_saved_content_user_quality ON saved_content(user_id, quality_score DESC);
CREATE INDEX idx_saved_content_user_saved_at ON saved_content(user_id, saved_at DESC);

-- Vector Search Indexes (pgvector)
CREATE INDEX idx_saved_content_embedding ON saved_content 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_projects_embedding ON projects 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Composite Indexes for Common Queries
CREATE INDEX idx_projects_user_created ON projects(user_id, created_at DESC);
CREATE INDEX idx_tasks_project_created ON tasks(project_id, created_at DESC);

-- Case-Insensitive Lookups
CREATE INDEX idx_users_username_lower ON users(LOWER(username));
CREATE INDEX idx_users_email_lower ON users(LOWER(email));
```

**Index Strategy:**
- **User Isolation First**: All queries filtered by `user_id` - indexes ensure fast lookups
- **Composite Indexes**: Cover common query patterns (user_id + sort column)
- **Vector Indexes**: IVFFlat indexes for fast similarity search
- **Partial Indexes**: Conditional indexes for filtered queries

### Connection Pooling Architecture

```mermaid
graph LR
    subgraph "Application Workers"
        W1[Worker 1]
        W2[Worker 2]
        W3[Worker 3]
        WN[Worker N]
    end
    
    subgraph "Connection Pool Manager"
        Pool[QueuePool<br/>pool_size: 5<br/>max_overflow: 10<br/>pool_recycle: 300s<br/>pool_pre_ping: true]
    end
    
    subgraph "PostgreSQL"
        Primary[(Primary DB<br/>Read/Write)]
        Replica1[(Replica 1<br/>Read Only)]
        Replica2[(Replica 2<br/>Read Only)]
    end
    
    W1 --> Pool
    W2 --> Pool
    W3 --> Pool
    WN --> Pool
    
    Pool -->|Writes| Primary
    Pool -->|Reads| Replica1
    Pool -->|Reads| Replica2
    
    style Pool fill:#cd853f
    style Primary fill:#9b59b6
    style Replica1 fill:#50c878
    style Replica2 fill:#50c878
```

**Connection Pool Configuration:**
- **Pool Size**: 5 connections per worker
- **Max Overflow**: 10 additional connections
- **Pool Recycle**: 300 seconds (prevent stale connections)
- **Pool Pre-ping**: True (verify connections before use)
- **Connection Timeout**: 30 seconds
- **SSL Mode**: Auto-detected and configured

**Benefits:**
- Reuses connections (faster queries)
- Limits total connections (prevents DB overload)
- Automatic connection health checks
- Handles connection failures gracefully

### Read/Write Splitting Strategy

```mermaid
sequenceDiagram
    participant App as Application
    participant Pool as Connection Pool
    participant Primary as PostgreSQL Primary
    participant Replica as PostgreSQL Replica
    
    Note over App,Replica: Write Operations
    App->>Pool: Write Request (INSERT/UPDATE/DELETE)
    Pool->>Primary: Execute Write
    Primary-->>Pool: Commit Result
    Pool-->>App: Success
    
    Note over App,Replica: Read Operations
    App->>Pool: Read Request (SELECT)
    Pool->>Replica: Execute Read
    Replica-->>Pool: Query Results
    Pool-->>App: Data
    
    Note over App,Replica: Replication Lag Handling
    App->>Pool: Read After Write (with consistency flag)
    Pool->>Primary: Read from Primary (strong consistency)
    Primary-->>Pool: Fresh Data
    Pool-->>App: Consistent Data
```

**Read/Write Splitting:**
- **Writes**: Always go to Primary
- **Reads**: Distributed across Replicas
- **Consistency**: Option to read from Primary for critical reads
- **Replication Lag**: Handled with read-after-write patterns

---

## Caching Architecture

### Caching Strategy

```mermaid
graph TB
    subgraph "Redis Cache (shared)"
        RedisUser[Per-user pages<br/>profile · dashboard · bookmarks · projects]
        RedisRecommendations[Recommendation results<br/>keyed by content version]
        RedisEmbedding[Embedding Cache<br/>24 hours TTL]
        RedisAnalysis[Analysis Results]
    end

    subgraph "Database"
        PostgreSQL[(PostgreSQL<br/>Permanent Storage)]
    end

    Request[API Request] --> RedisUser
    Request --> RedisRecommendations
    Request --> RedisEmbedding
    Request --> RedisAnalysis

    RedisUser -->|Miss or Redis down| PostgreSQL
    RedisRecommendations -->|Miss or Redis down| PostgreSQL
    RedisEmbedding -->|Miss| PostgreSQL
    RedisAnalysis -->|Miss or Redis down| PostgreSQL

    style RedisEmbedding fill:#ff6b6b
    style RedisUser fill:#ff6b6b
    style RedisRecommendations fill:#ff6b6b
    style RedisAnalysis fill:#ff6b6b
    style PostgreSQL fill:#9b59b6
```

### Cache Layers Explained

#### In-Process (per worker)

Only values that rarely change: the embedding model instance (singleton), feature
flags (5 s TTL) and decrypted user API keys. User data is never cached per worker.

#### Redis Cache (Shared Across Workers)

**Location**: `backend/utils/redis_utils.py` (`RedisCache`); every per-user key is
built by `backend/core/cache_keys.py`, so readers and invalidators can't drift apart

**Cache Types:**

1. **Per-user pages**
   - Keys: `profile:{user_id}`, `dashboard:v1:summary:{user_id}`, `dashboard:stats:{user_id}`,
     `bookmarks:{user_id}:{page}:{per_page}:{search}:{category}`, `bookmarks:{user_id}:list`,
     `projects:{user_id}:{page}:{per_page}:{include_tasks}`
   - Purpose: fast page loads; the bookmark list also serves import dedup

2. **Recommendation Cache**
   - Keys include a per-user content version that bumps on every change, so stale
     results are never served
   - Purpose: Avoid recomputing recommendations

3. **Embedding Cache**
   - Key: hash of the text (`RedisCache.cache_embedding`)
   - TTL: 24 hours
   - Purpose: Avoid re-encoding identical text

4. **Analysis Cache**
   - Key: `content_analysis:{content_id}`
   - Stores: Gemini analysis results
   - Purpose: Reuse AI analysis

Fetched pages are not cached (the raw-HTML cache was never read, so it was removed).
Redis is optional on the request path: 2 s timeouts, no PING per operation, and a
reconnect attempt at most every 5 s while it is down.

**Cache Invalidation Strategy:**

```mermaid
flowchart TD
    Event[Data Change Event] --> Identify{Event Type}
    
    Identify -->|Content Saved| InvalidateContent[Invalidate Content Cache]
    Identify -->|Content Updated| InvalidateContent
    Identify -->|Content Deleted| InvalidateContent
    Identify -->|Project Created| InvalidateProject[Invalidate Project Cache]
    Identify -->|Analysis Complete| InvalidateAnalysis[Invalidate Analysis Cache]
    
    InvalidateContent --> InvalidateUser[Invalidate User Recommendations]
    InvalidateProject --> InvalidateUser
    InvalidateAnalysis --> InvalidateUser
    
    InvalidateUser --> ClearPatterns[Clear keys from core/cache_keys.py:<br/>- profile / dashboard<br/>- bookmarks:user:*<br/>- projects:user:*<br/>+ bump content version]
    
    ClearPatterns --> UpdateDB[Update Database]
    
    style Event fill:#4a90e2
    style InvalidateUser fill:#ff6b6b
    style ClearPatterns fill:#ff6b6b
```

**Cache Invalidation Service:**
- Location: `backend/services/cache_invalidation_service.py`
- Automatic invalidation on data changes
- Pattern-based invalidation (wildcards), using the same key builders as the readers
- Comprehensive coverage (project lists included); `DELETE /api/bookmarks/all`
  clears synchronously
- Web requests invalidate on a background thread; RQ jobs invalidate inline (work
  horses exit via `os._exit()` and would kill the thread first)

---

## Horizontal Scaling Strategy

### Stateless Application Design

**Key Principle**: No local state in application workers

```mermaid
graph LR
    subgraph "Stateless Workers"
        W1[Worker 1<br/>No Local State]
        W2[Worker 2<br/>No Local State]
        W3[Worker 3<br/>No Local State]
    end
    
    subgraph "Shared State Storage"
        Redis[(Redis<br/>Sessions & Cache)]
        DB[(PostgreSQL<br/>Persistent Data)]
    end
    
    W1 --> Redis
    W2 --> Redis
    W3 --> Redis
    
    W1 --> DB
    W2 --> DB
    W3 --> DB
    
    style W1 fill:#50c878
    style W2 fill:#50c878
    style W3 fill:#50c878
    style Redis fill:#ff6b6b
    style DB fill:#9b59b6
```

**Stateless Components:**
- ✅ JWT tokens (no server-side sessions)
- ✅ All state in Redis or Database
- ✅ No file uploads to workers
- ✅ No per-worker caches of user data (shared Redis instead)
- ✅ Connection pooling (managed by SQLAlchemy)

**Benefits:**
- Any worker can handle any request
- Easy to add/remove workers
- No session affinity required
- Horizontal scaling without limits

### User Isolation Architecture

**Critical for Multi-Tenancy:**

```mermaid
flowchart TD
    Request[API Request] --> ExtractUser[Extract user_id from JWT]
    ExtractUser --> ValidateAuth{Valid JWT?}
    
    ValidateAuth -->|No| Reject[401 Unauthorized]
    ValidateAuth -->|Yes| ApplyFilter[Apply user_id Filter]
    
    ApplyFilter --> QueryDB[Query Database]
    QueryDB --> IndexCheck{Index Used?}
    
    IndexCheck -->|Yes| FastQuery[Fast Indexed Query<br/>O log n]
    IndexCheck -->|No| SlowQuery[Slow Full Scan<br/>O n]
    
    FastQuery --> Results[Return Results]
    SlowQuery --> Results
    
    style ExtractUser fill:#cd853f
    style ApplyFilter fill:#ff6b6b
    style FastQuery fill:#50c878
    style SlowQuery fill:#ff6b6b
```

**User Isolation Implementation:**

1. **Database Level:**
   ```python
   # All queries automatically filtered by user_id
   SavedContent.query.filter_by(user_id=current_user_id).all()
   ```

2. **Index Level:**
   ```sql
   -- Composite indexes ensure fast user-specific queries
   CREATE INDEX idx_saved_content_user_quality 
   ON saved_content(user_id, quality_score DESC);
   ```

3. **Application Level:**
   ```python
   # Security middleware enforces user_id in all queries
   @require_user_context
   def get_user_bookmarks(user_id: int):
       # user_id is guaranteed to be present and valid
   ```

**Benefits:**
- Complete data isolation
- Fast queries (indexed lookups)
- Security at multiple layers
- Scales per-user independently

---

## Load Distribution

### Request Distribution Strategy

```mermaid
graph TB
    LB[Load Balancer] --> Strategy{Distribution Strategy}
    
    Strategy -->|Round Robin| RR[Distribute Equally]
    Strategy -->|Least Connections| LC[Send to Least Busy]
    Strategy -->|IP Hash| IH[Sticky Sessions<br/>if needed]
    
    RR --> W1[Worker 1]
    RR --> W2[Worker 2]
    RR --> W3[Worker 3]
    
    LC --> W1
    LC --> W2
    LC --> W3
    
    IH --> W1
    IH --> W2
    IH --> W3
    
    style LB fill:#cd853f
    style Strategy fill:#cd853f
```

**Distribution Methods:**
- **Round Robin**: Equal distribution (default)
- **Least Connections**: Send to least busy worker
- **IP Hash**: Sticky sessions (if needed, but not required due to stateless design)

### Database Load Distribution

```mermaid
graph TB
    subgraph "Read Operations"
        Read1[Read Request 1] --> Replica1[(Replica 1)]
        Read2[Read Request 2] --> Replica2[(Replica 2)]
        Read3[Read Request 3] --> Replica3[(Replica 3)]
    end
    
    subgraph "Write Operations"
        Write1[Write Request 1] --> Primary[(Primary DB)]
        Write2[Write Request 2] --> Primary
        Write3[Write Request 3] --> Primary
    end
    
    Primary -.->|Replication| Replica1
    Primary -.->|Replication| Replica2
    Primary -.->|Replication| Replica3
    
    style Primary fill:#9b59b6
    style Replica1 fill:#50c878
    style Replica2 fill:#50c878
    style Replica3 fill:#50c878
```

**Read/Write Distribution (Scalable Design - Not Yet Implemented):**
- **Writes**: All to Primary (single source of truth)
- **Reads**: Distributed across Replicas (load balancing)
- **Replication**: Async replication (low latency)
- **Consistency**: Read-after-write uses Primary

**Current Implementation:**
- **All Operations**: Single PostgreSQL database (no replicas)
- **Connection Pooling**: Configured for efficiency
- **Design Ready**: Architecture supports read/write splitting when replicas are added

---

## Data Isolation & Security

### Multi-Tenant Data Isolation

**Three-Layer Isolation:**

```mermaid
graph TB
    subgraph "Layer 1: Application Filtering"
        AppFilter[All Queries Filtered by user_id<br/>@require_user_context decorator]
    end
    
    subgraph "Layer 2: Database Indexes"
        UserIndex[Composite Indexes<br/>user_id + other columns]
    end
    
    subgraph "Layer 3: Row-Level Security"
        RLS[PostgreSQL RLS enabled on every table<br/>no policies: Supabase API roles see no rows]
    end
    
    Request[API Request] --> AppFilter
    AppFilter --> UserIndex
    UserIndex --> RLS
    RLS --> Data[(User's Data Only)]
    
    style AppFilter fill:#ff6b6b
    style UserIndex fill:#cd853f
    style RLS fill:#50c878
```

**Isolation Mechanisms:**

1. **Application Level:**
   - All queries include `user_id` filter
   - Decorators enforce user context
   - Input validation prevents injection

2. **Database Level:**
   - Composite indexes on `user_id`
   - Foreign keys with CASCADE
   - Unique constraints per user
   - Row level security on every table and no `anon`/`authenticated` privileges
     (migration 0013), so Supabase's REST API exposes nothing; the backend connects
     as the table owner

3. **API Level:**
   - JWT token contains `user_id`
   - Token validation on every request
   - No cross-user data access possible

### Security Architecture

```mermaid
graph TB
    Request[Incoming Request] --> ValidateJWT{JWT Valid?}
    
    ValidateJWT -->|No| Reject[401 Unauthorized]
    ValidateJWT -->|Yes| ExtractUser[Extract user_id]
    
    ExtractUser --> SanitizeInput[Sanitize Inputs<br/>SQL Injection Prevention<br/>XSS Prevention]
    SanitizeInput --> RateLimit{Rate Limit OK?}
    
    RateLimit -->|No| RateLimitError[429 Too Many Requests]
    RateLimit -->|Yes| ValidateData{Data Valid?}
    
    ValidateData -->|No| ValidationError[400 Bad Request]
    ValidateData -->|Yes| ApplyUserFilter[Apply user_id Filter]
    
    ApplyUserFilter --> ExecuteQuery[Execute Query]
    ExecuteQuery --> ReturnData[Return User's Data Only]
    
    style ValidateJWT fill:#ff6b6b
    style SanitizeInput fill:#ff6b6b
    style RateLimit fill:#cd853f
    style ApplyUserFilter fill:#ff6b6b
```

---

## Background Processing Architecture

### Async Processing Design

```mermaid
graph TB
    Request[User Request] --> SaveData[Save to Database]
    SaveData --> ReturnResponse[Return 201 Created]
    SaveData --> TriggerAsync[Trigger Background Task]
    
    TriggerAsync --> Queue[Task Queue<br/>Redis/RQ]
    
    Queue --> Worker1[Background Worker 1]
    Queue --> Worker2[Background Worker 2]
    Queue --> WorkerN[Background Worker N]
    
    Worker1 --> ProcessTask[Process Task]
    Worker2 --> ProcessTask
    WorkerN --> ProcessTask
    
    ProcessTask --> UpdateDB[Update Database]
    ProcessTask --> UpdateCache[Update Cache]
    
    style Request fill:#4a90e2
    style ReturnResponse fill:#50c878
    style Queue fill:#ff6b6b
    style ProcessTask fill:#cd853f
```

**Background Services (Current Implementation):**

1. **RQ (Redis Queue) Workers** ⭐ **Primary Background System**
   - Location: `backend/worker.py` and `backend/services/task_queue.py`
   - Processes: Bookmark content extraction, embedding generation, analysis
   - Queue System: Redis-based task queue (`default` and `high`)
   - Runs: supervised by supervisord next to Gunicorn (`start.sh` → `supervisord.conf`)
   - Deployment: one `default` and one `high` worker in the same container as the web server

2. **Pipeline Reconciler**
   - Location: `backend/services/pipeline_reconciler.py`
   - Runs: a thread in the `default` worker, every 5 minutes (a Redis lock keeps it to one pass at a time)
   - Re-enqueues: fetches stuck in `PENDING` for 15+ minutes, `FAILED_FETCH` after
     1 h / 6 h / 24 h backoff, and bookmarks that were fetched but never embedded

3. **Content Analysis**
   - Location: `backend/services/background_analysis_service.py` (`analyze_content`)
   - Runs: at the end of the embedding job, skipped when there is no fetched text
   - Uses: the user's own Gemini key, or the shared system key up to
     `SYSTEM_GEMINI_DAILY_LIMIT_PER_USER` uses a day

4. **Cache Invalidation Service**
   - Location: `backend/services/cache_invalidation_service.py`
   - Processes: Cache invalidation on data changes
   - Runs: on a background thread for web requests, inline inside RQ jobs

5. **Import Processing**
   - Location: `backend/blueprints/bookmarks.py`
   - Processes: Bulk bookmark imports (at most 5000 per request)
   - Progress: kept in Redis (`import_progress:{user_id}`) and pushed over SSE

### RQ Worker Architecture

**How It Works:**

```
User Action → API Endpoint → Enqueue Job → Immediate Response
                                      ↓
                              RQ Worker → Process Content → Update Database
```

**Components:**

1. **Task Queue Service** (`backend/services/task_queue.py`)
   - Manages RQ queues and job enqueueing
   - `enqueue_unique()`: one job id per bookmark and stage, so re-enqueueing is always safe
   - Web enqueues use a 5 s socket timeout; workers get a connection without one
     (they block in BLPOP between jobs)
   - Enqueueing never raises: if Redis is down the bookmark stays `PENDING` and the
     reconciler enqueues it later
   - Queue stats read failures from RQ's `FailedJobRegistry`

2. **Bookmark Processing Tasks** (`backend/services/bookmark_processing_service.py`)
   - `process_bookmark_content_task()`: fetches and extracts the page through the
     acquisition engine (official APIs first, then robots.txt, the per-domain rate
     limit and the SSRF-safe fetch). A failed or blocked fetch keeps the user's title
     and notes and is stored as `FAILED_FETCH`, `BLOCKED` or `DISALLOWED`, never as
     content; transient failures (no response, 5xx, 429, over the domain's rate
     limit) raise so RQ retries them
   - `generate_embedding_task()`: enqueued by `PipelineOrchestrator` when a fetch
     completes (backpressure defers it to the reconciler instead of dropping it);
     stores the document embedding, indexes passage chunks, then runs Gemini analysis

3. **RQ Worker** (`backend/worker.py`)
   - Background process that listens to queues and executes tasks
   - Started `with_scheduler=True`, so `Retry(interval=...)` retries actually run
   - Loads the embedding model once in the parent; forked work horses share it
   - `JobTimeoutException` is re-raised through the fetch/Gemini/analysis paths, so
     a timed-out job really fails
   - supervisord gives a running job up to 630 s to finish on shutdown

**Queue Configuration:**

- **Default Queue**: bookmark fetch and embedding jobs, project intent jobs
- **High Priority Queue**: login-triggered cache warming
- **Retry Logic**: fetch jobs 2 retries (after 1 min, then 5 min); project jobs 3
- **Job Timeout**: 10 minutes per job (cache warming: 30 s)

**Current Deployment (Hugging Face Spaces):**

The RQ workers run automatically:
- ✅ `start.sh` migrates the database (and exits if that fails), then execs supervisord
- ✅ supervisord runs Gunicorn plus the `default` and `high` RQ workers in the same Docker container
- ✅ Workers use the same Redis as the web server
- ✅ No manual configuration needed

**Scalable Deployment (Future):**
- Can run RQ workers on separate machines
- Can scale RQ workers independently
- Multiple workers can process jobs in parallel

**Benefits:**
- Non-blocking user requests
- Parallel processing
- User-specific API key usage
- Progress tracking for long operations
- Jobs survive server restarts (persistent queue)
- Automatic retries on failure
- Better scalability (can run workers on separate machines)

---

## ML/AI Architecture

### Embedding Model Architecture

```mermaid
graph TB
    Request[Generate Embedding] --> CheckCache{Redis Cache?}
    
    CheckCache -->|Hit| ReturnCached[Return Cached Embedding]
    CheckCache -->|Miss| CheckModel{Model Loaded?}
    
    CheckModel -->|No| LoadModel[Load SentenceTransformer<br/>Singleton Pattern]
    CheckModel -->|Yes| UseModel[Use Cached Model]
    
    LoadModel --> UseModel
    UseModel --> GenerateEmbedding[Generate Embedding<br/>384 dimensions]
    GenerateEmbedding --> CacheResult[Cache in Redis<br/>24 hours TTL]
    CacheResult --> ReturnEmbedding[Return Embedding]
    
    style CheckCache fill:#ff6b6b
    style LoadModel fill:#cd853f
    style GenerateEmbedding fill:#cd853f
    style CacheResult fill:#ff6b6b
```

**Model Management:**
- **Model**: `BAAI/bge-small-en-v1.5` (384 dimensions); queries use its query instruction (`embed_query`)
- **Singleton Pattern**: One model instance per process; RQ work horses share the parent's
- **Lazy Loading**: Model loaded on first use (prevents OOM at startup)
- **Thread Safety**: Locking prevents race conditions
- **No Silent Fallback**: if the model can't load, `EmbeddingUnavailable` is raised (embedding
  jobs fail and retry, search returns 503); an encode error raises instead of storing a zero
  vector. Hash vectors exist only as an explicit `DISABLE_EMBEDDINGS` opt-in for local work
- **Redis Caching**: Embeddings cached to avoid regeneration

### Intent × Content Engine

Full design and measurements: [`INTENT_ENGINE_PLAN.md`](INTENT_ENGINE_PLAN.md).

```mermaid
graph TB
    subgraph Write path
        Save[Bookmark saved] --> Acquire[Fetch + extract text]
        Acquire --> Chunk[Overlapping passages]
        Chunk --> PEmb[Passage embeddings]
        Acquire --> Profile[Gemini content profile<br/>summary · use_when · concepts]
        Profile --> ProfEmb[Profile embedding]
        PEmb --> Chunks[(content_chunks<br/>HNSW)]
        ProfEmb --> Chunks
    end
    subgraph Read path
        Req[Query or project/task/subtask] --> Ctx[Intent text<br/>user's own words]
        Ctx --> Stmt{Cached Gemini<br/>intent statement?}
        Stmt -->|yes| Multi[Query vectors:<br/>context + statement + needs]
        Stmt -->|no: schedule job| Multi
        Multi --> ANN[Nearest passages per user]
        Chunks --> ANN
        ANN --> Rerank[Cross-encoder rerank<br/>optional]
        Rerank --> MMR[MMR diversity]
        MMR --> Out[Results + matched passage]
    end
```

**Properties:**
- **No keyword rules**: retrieval and ranking use embeddings and model judgements only
- **Never blocks on Gemini**: intent statements are computed by a background job and cached per context
- **Fresh results**: result cache keys include a per-user content version that bumps on every change
- **Versioned vectors**: chunks record their embedding model; retrieval only compares vectors from the active model

---

## API Architecture

### Blueprint-Based Modular Design

```mermaid
graph TB
    App[Flask Application] --> AuthBP[Auth Blueprint<br/>/api/auth]
    App --> BookmarksBP[Bookmarks Blueprint<br/>/api/bookmarks]
    App --> ProjectsBP[Projects Blueprint<br/>/api/projects]
    App --> RecommendationsBP[Recommendations Blueprint<br/>/api/recommendations]
    App --> SearchBP[Search Blueprint<br/>/api/search]
    App --> ProfileBP[Profile Blueprint<br/>/api/profile]
    
    AuthBP --> AuthMiddleware[JWT Validation]
    BookmarksBP --> AuthMiddleware
    ProjectsBP --> AuthMiddleware
    RecommendationsBP --> AuthMiddleware
    SearchBP --> AuthMiddleware
    ProfileBP --> AuthMiddleware
    
    AuthMiddleware --> SecurityMiddleware[Security Middleware<br/>Input Validation<br/>Rate Limiting]
    
    SecurityMiddleware --> BusinessLogic[Business Logic]
    BusinessLogic --> DataLayer[Data Layer<br/>Models + DB]
    
    style App fill:#4a90e2
    style AuthMiddleware fill:#ff6b6b
    style SecurityMiddleware fill:#ff6b6b
    style BusinessLogic fill:#cd853f
```

**Blueprint Benefits:**
- **Modularity**: Each feature in separate blueprint
- **Maintainability**: Easy to locate and modify code
- **Testability**: Each blueprint can be tested independently
- **Scalability**: Can split blueprints to separate services if needed

### Request Flow Architecture

```mermaid
sequenceDiagram
    participant Client
    participant LB as Platform/Load Balancer
    participant Worker as Flask Worker
    participant Middleware as Security Middleware
    participant Cache as Redis Cache
    participant DB as PostgreSQL
    participant Background as Background Service
    
    Client->>LB: HTTP Request
    LB->>Worker: Route to Worker
    Worker->>Middleware: Validate JWT
    Middleware->>Middleware: Sanitize Input
    Middleware->>Middleware: Check Rate Limit
    
    alt Rate Limit Exceeded
        Middleware-->>Client: 429 Too Many Requests
    else Rate Limit OK
        Middleware->>Cache: Check Cache
        alt Cache Hit
            Cache-->>Worker: Cached Data
            Worker-->>Client: Response (Fast)
        else Cache Miss
            Worker->>DB: Query Database
            DB-->>Worker: Data
            Worker->>Cache: Store in Cache
            Worker->>Background: Trigger Async Task (if needed)
            Worker-->>Client: Response
        end
    end
```

---

## Frontend Architecture

### React Application Structure

```mermaid
graph TB
    subgraph "Entry Point"
        Main[main.jsx] --> App[App.jsx]
    end
    
    subgraph "Context Layer"
        App --> AuthContext[AuthContext<br/>JWT Management]
        App --> ToastContext[ToastContext<br/>Notifications]
    end
    
    subgraph "Routing Layer"
        App --> Router[React Router]
        Router --> Routes[Route Components]
    end
    
    subgraph "Page Components"
        Routes --> Landing[Landing Page]
        Routes --> Login[Login Page]
        Routes --> Dashboard[Dashboard]
        Routes --> Bookmarks[Bookmarks]
        Routes --> Projects[Projects]
        Routes --> Recommendations[Recommendations]
    end
    
    subgraph "Service Layer"
        Pages --> API[API Service<br/>axios + optimizations]
        API --> Cache[API Optimization<br/>Caching + Deduplication]
    end
    
    style Main fill:#4a90e2
    style AuthContext fill:#cd853f
    style API fill:#cd853f
    style Cache fill:#ff6b6b
```

**Frontend Optimizations:**

1. **API Call Optimization**
   - Location: `frontend/src/utils/apiOptimization.js`
   - Features:
     - Request debouncing (300ms)
     - Request batching (50ms window)
     - Response caching (5 minutes TTL)
     - Request deduplication

2. **Code Splitting**
   - React vendor chunk
   - Axios vendor chunk
   - Route-based lazy loading (future)

3. **State Management**
   - React Context for global state
   - Local state for component state
   - No Redux (keeps it simple)

---

## Deployment Architecture

### Current Deployment Stack (What's Actually Running)

```mermaid
graph TB
    subgraph "Client Layer"
        WebApp[Web Application<br/>React + Vite]
        Extension[Chrome Extension]
    end
    
    subgraph "Platform Layer"
        Platform[Hugging Face Spaces<br/>Handles Routing & SSL]
    end
    
    subgraph "Application Container"
        App1[Gunicorn Worker 1<br/>gevent async<br/>1000+ connections]
        RQWorker[RQ Worker<br/>Background Jobs]
    end
    
    subgraph "Cache Layer"
        Redis[(Redis Instance<br/>Upstash - Single)]
    end
    
    subgraph "Database Layer"
        Primary[(PostgreSQL<br/>Supabase - Single<br/>+ pgvector)]
    end
    
    subgraph "External Services"
        Gemini[Google Gemini AI<br/>Per-User API Keys]
    end
    
    WebApp --> Platform
    Extension --> Platform
    
    Platform --> App1
    
    App1 --> Redis
    App1 --> Primary
    App1 --> Gemini
    
    App1 --> RQWorker
    RQWorker --> Redis
    RQWorker --> Primary
    RQWorker --> Gemini
    
    style WebApp fill:#4a90e2
    style Extension fill:#4a90e2
    style Platform fill:#cd853f
    style App1 fill:#50c878
    style RQWorker fill:#50c878
    style Redis fill:#ff6b6b
    style Primary fill:#9b59b6
    style Gemini fill:#9b59b6
```

### Scalable Deployment Stack (Future-Ready Design)

```mermaid
graph TB
    subgraph "CDN & Edge"
        CDN[Cloudflare/CDN<br/>Static Assets]
    end
    
    subgraph "Load Balancer"
        LB[Nginx/Cloudflare<br/>SSL Termination<br/>Rate Limiting]
    end
    
    subgraph "Application Servers"
        App1[Gunicorn Worker 1<br/>4 workers]
        App2[Gunicorn Worker 2<br/>4 workers]
        AppN[Gunicorn Worker N<br/>4 workers]
    end
    
    subgraph "Cache Layer"
        Redis[(Redis Cluster<br/>High Availability)]
    end
    
    subgraph "Database Layer"
        Primary[(PostgreSQL Primary<br/>Write Operations)]
        Replica1[(PostgreSQL Replica 1<br/>Read Operations)]
        Replica2[(PostgreSQL Replica 2<br/>Read Operations)]
    end
    
    subgraph "Background Workers"
        BG1[RQ Worker 1]
        BG2[RQ Worker 2]
    end
    
    CDN --> LB
    LB --> App1
    LB --> App2
    LB --> AppN
    
    App1 --> Redis
    App2 --> Redis
    AppN --> Redis
    
    App1 --> Primary
    App2 --> Replica1
    AppN --> Replica2
    
    BG1 --> Redis
    BG2 --> Redis
    BG1 --> Primary
    BG2 --> Primary
    
    Primary -.->|Replication| Replica1
    Primary -.->|Replication| Replica2
    
    style CDN fill:#4a90e2
    style LB fill:#cd853f
    style App1 fill:#50c878
    style Redis fill:#ff6b6b
    style Primary fill:#9b59b6
```

### Current Deployment Configuration

**Application Servers (Current):**
- **Gunicorn Workers**: 2 workers (gevent async, sized for a 2-vCPU host)
- **Worker Class**: gevent (handles 1000+ concurrent connections per worker)
- **Worker Connections**: 1000 per worker
- **Worker timeout**: 60 s (graceful 30 s); psycogreen patch in `post_fork`
- **Deployment target**: single Docker container (Hugging Face Space), deployed only
  after Backend CI passes on that commit
- **Startup**: `start.sh` runs `alembic upgrade head` and refuses to start if it fails
- **Health Checks**: `/health/readiness` (503 unless DB, Redis and the schema at this
  build's Alembic head are ready), `/health/liveness` (Docker `HEALTHCHECK`), and
  `/api/health` (public up/down only)

**Database (Current):**
- **Connection Pool**: 5 base connections, 10 overflow, `pool_pre_ping`, 5 s connect
  timeout, 15 s `statement_timeout`; one engine configured by `UnifiedConfig`
- **Single Database**: All operations to one PostgreSQL instance
- **Schema**: Alembic is the only source of schema; each revision runs in its own transaction
- **Indexes**: defined in the migrations (HNSW for embeddings and passage chunks)

**Redis (Current):**
- **Single Instance**: Upstash (free tier)
- **Shared**: All workers use same Redis
- **Sufficient**: For current scale

**Background Workers (Current):**
- **RQ Workers**: one on `default` (pipeline + reconciler), one on `high` (cache warming)
- **Queue**: Redis as message broker
- **Deployment**: supervisord runs them in the same container as the web server

### Scalable Design Configuration (Future)

**Application Servers (Scalable):**
- **Gunicorn Workers**: 4+ workers per server
- **Threads**: 2 threads per worker (if needed)
- **Auto-scaling**: Based on CPU/memory metrics
- **Multiple Servers**: With load balancer

**Database (Scalable):**
- **Connection Pool**: 5 base connections per worker, 10 overflow
- **Max Overflow**: 10 additional connections
- **Read Replicas**: Scale horizontally
- **Read/Write Splitting**: Writes to primary, reads from replicas

**Redis (Scalable):**
- **Cluster Mode**: For high availability
- **Replication**: Master-replica setup
- **Persistence**: RDB + AOF (if needed)

**Background Workers (Scalable):**
- **RQ Workers**: Multiple workers (separate from web workers)
- **Queue**: Redis as message broker
- **Scaling**: Independent of web workers
- **Note**: Already using RQ (not Celery) - architecture is correct

---

## Scalability Metrics

### Current Capacity (Actual Implementation)

**Current Deployment (Hugging Face Spaces):**
- **Gunicorn**: 2 workers (gevent async, 1000+ connections per worker)
- **Concurrent Users / Requests per second**: not measured yet (a load test will set these)
- **Database Connections**: up to pool_size + max_overflow per process (see docs/OPERATIONS.md)
- **Background Jobs**: RQ workers process ~10-50 jobs/hour
- **Memory Usage**: ~2-4GB of 16GB available (room for growth)

**Current Performance:**
These targets for a scaled-out deployment (replicas, Redis cluster) are design goals, not
measurements; nothing has been load-tested at that scale.

### Scaling Strategy Summary

**Immediate Scaling (Within Current Platform):**
- **Vertical Scaling**: Upgrade HF Spaces hardware (CPU, RAM)
- **Connection Optimization**: Increase gevent workers or connections per worker
- **Database Optimization**: More aggressive caching, query optimization
- **Background Processing**: Multiple RQ workers in same container

**Horizontal Scaling (Future Architecture):**
- **Application Layer**: Add more HF Spaces containers with load balancer
- **Database Layer**: Add PostgreSQL read replicas for read operations
- **Cache Layer**: Redis cluster with sharding across multiple instances
- **Background Workers**: Distributed RQ workers across multiple containers

**Key Scaling Principles:**
- **Stateless Design**: Any worker can handle any request (no session affinity)
- **Shared Nothing**: Redis/DB provide shared state across all instances
- **Connection Pooling**: Efficient database connection management
- **Circuit Breakers**: Graceful degradation when services are unavailable

---

## Key Scalability Features

### 1. Stateless Design
- ✅ No server-side sessions
- ✅ JWT tokens (self-contained)
- ✅ Shared Redis for state
- ✅ Any worker handles any request

### 2. Connection Pooling
- ✅ Efficient database connections
- ✅ Fail-fast timeouts (connect 5 s, statement 15 s)
- ✅ Configurable pool sizes
- ✅ Health checks (pool_pre_ping)

### 3. Caching
- ✅ Redis cache (shared, key builders in `core/cache_keys.py`)
- ✅ Database (persistent)
- ✅ Smart invalidation

### 4. Background Processing
- ✅ Non-blocking operations
- ✅ User-specific API keys
- ✅ Parallel processing
- ✅ Progress tracking

### 5. Database Optimization
- ✅ Comprehensive indexes
- ✅ Read/write splitting (design only; one database today)
- ✅ Connection pooling
- ✅ Query optimization

### 6. User Isolation
- ✅ Complete data separation
- ✅ Per-user rate limits
- ✅ Independent processing
- ✅ Security at all layers

---

Ujjwal Jain


