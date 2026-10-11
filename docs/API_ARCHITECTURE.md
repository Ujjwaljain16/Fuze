# API Architecture

Complete API documentation for Fuze - Intelligent Bookmark Manager.

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [Request/Response Format](#requestresponse-format)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)

---

## API Overview

**Base URL**: `/api`

**Architecture**: Blueprint-based modular design

**Authentication**: JWT (JSON Web Tokens)

**Content Type**: `application/json`

**Status Codes**:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `409` - Conflict
- `413` - Payload Too Large (request body over `MAX_REQUEST_BYTES`, 5 MB by default; imports over 5000 items)
- `429` - Too Many Requests
- `500` - Internal Server Error
- `503` - Service Unavailable

---

## Authentication

### JWT Token Flow

```mermaid
sequenceDiagram
    participant Client
    participant API as API Server
    
    Client->>API: POST /api/auth/login<br/>{username, password}
    API-->>Client: {access_token, refresh_token, user}

    Client->>API: GET /api/*<br/>Header: Authorization: Bearer {token}
    API-->>Client: Protected Resource

    Note over Client,API: Access token expires after 1 hour (JWT_ACCESS_TOKEN_EXPIRES_HOURS)
    Client->>API: POST /api/auth/refresh<br/>Header: Authorization: Bearer {refresh_token}
    API-->>Client: {access_token, refresh_token} (rotated)
```

**Token Storage**:
- The web app keeps both tokens in `localStorage['user']`. The SPA is served from a
  different site than the API, so the SameSite=Lax refresh cookie isn't sent on its
  requests; it sends the refresh token in the `Authorization` header instead
  (`/api/auth/refresh` also accepts the cookie)
- Tokens are also set as HTTP-only cookies

**Sessions**: every login starts a token family. A refresh rotates the refresh token;
reusing an old one revokes the whole family. Refresh tokens without a family are
rejected. Revoking a session (logout, password change, reuse) also blocks its
still-valid access tokens through a short-lived `revoked_family` marker the JWT
blocklist checks. Changing the password ends every other session.

**Token Validation**: All protected endpoints validate JWT on every request

---

## API Endpoints

### Authentication (`/api/auth`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/auth/register` | ❌ | Register new user |
| `POST` | `/api/auth/login` | ❌ | Login user |
| `POST` | `/api/auth/refresh` | Refresh token | Rotate tokens |
| `POST` | `/api/auth/logout` | ✅ | Logout user (revokes the session) |
| `GET` | `/api/auth/verify` | ✅ | Verify token; returns a whitelisted profile |
| `POST` | `/api/auth/verify-token` | ✅ | Verify token status |
| `POST` | `/api/auth/check-username` | ❌ | Check username availability |
| `POST` | `/api/auth/bulk-check-usernames` | ❌ | Check several usernames |
| `POST` | `/api/auth/set-password` | ✅ | Set a password (Google-created accounts: needs a sign-in in the last 15 minutes) |
| `POST` | `/api/auth/update-username` | ✅ | Change username |
| `POST` | `/api/auth/supabase-oauth` | ❌ | Exchange a Supabase (Google) access token for a session. Signs in only the account linked to that Google identity; `409 account_link_required` if an unlinked account has the same email |
| `POST` | `/api/auth/link-oauth` | ✅ | Connect Google to the signed-in account (email must match) |

**Login lockout**: failed passwords are counted per (account, client IP): five wrong
guesses block that client, not the owner signing in from elsewhere. The account-wide
lock is at 50 failures (5 when Redis is unavailable). A password lockout doesn't
block Google sign-in.

**Register Request**:
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "SecurePass123"
}
```

**Login Request**:
```json
{
  "username": "johndoe",
  "password": "SecurePass123"
}
```

**Login Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com"
  }
}
```

---

### Bookmarks (`/api/bookmarks`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/bookmarks` | ✅ | Save bookmark |
| `POST` | `/api/bookmarks/quick-save` | ✅ | Quick save bookmark (minimal fields) |
| `GET` | `/api/bookmarks` | ✅ | List bookmarks (paginated) |
| `DELETE` | `/api/bookmarks/<id>` | ✅ | Delete bookmark by ID |
| `DELETE` | `/api/bookmarks/url/<url>` | ✅ | Delete bookmark by URL |
| `DELETE` | `/api/bookmarks/all` | ✅ | Delete all bookmarks |
| `GET` | `/api/bookmarks/dashboard/stats` | ✅ | Get dashboard statistics |
| `POST` | `/api/bookmarks/import` | ✅ | Bulk import bookmarks |
| `POST` | `/api/bookmarks/check-duplicate` | ✅ | Check if URL is duplicate |
| `GET` | `/api/bookmarks/import/progress` | ✅ | Get import progress |
| `GET` | `/api/bookmarks/import/progress/stream` | ✅ | Stream import progress (SSE) |
| `GET` | `/api/bookmarks/analysis/progress` | ✅ | Get analysis progress |
| `GET` | `/api/bookmarks/analysis/progress/stream` | ✅ | Stream analysis progress (SSE) |
| `GET` | `/api/bookmarks/progress/check` | ✅ | One-shot pipeline progress |
| `POST` | `/api/bookmarks/extract-url` | ✅ | Extract content from URL (fetched through the SSRF-safe client) |

Saving never fails because the queue is down: the bookmark is committed as `PENDING`
and the pipeline reconciler enqueues it later. URLs over 2048 bytes are rejected.

### Live Events (`/api/realtime`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/realtime/stream-ticket` | ✅ | Mint a short-lived, single-use ticket for opening the SSE stream |
| `GET` | `/api/realtime/stream` | ✅ or `?ticket=` | Pipeline and domain events for the user (SSE). Also served at `/api/bookmarks/progress/stream` |

`EventSource` can't send an `Authorization` header, so the browser first mints a
ticket and opens the stream with `?ticket=...`; access tokens never go in URLs. The
stream reads the user's Redis Stream (`fuze:events:stream:{user_id}`) with blocking
`XREAD`, and each entry's stream id is the SSE `id`: on reconnect the browser sends
it back as `Last-Event-ID` and reading resumes right after it. The progress SSE
endpoints authenticate with `verify_jwt_in_request` or a stream ticket, so revoked
tokens and refresh tokens are refused.

**Save Bookmark Request**:
```json
{
  "url": "https://example.com/article",
  "title": "Article Title",
  "description": "Optional description",
  "category": "technology",
  "tags": ["python", "web"]
}
```

**List Bookmarks Query Params**:
- `page` (default: 1)
- `per_page` (default: 10, max: 100)
- `search` (optional)
- `category` (optional)

**Bulk Import Request** (at most 5000 items per request; the extension sends 1000 at a time):
```json
[
  {
    "url": "https://example.com/1",
    "title": "Article 1"
  },
  {
    "url": "https://example.com/2",
    "title": "Article 2"
  }
]
```

---

### Projects (`/api/projects`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/projects` | ✅ | List projects (paginated) |
| `POST` | `/api/projects` | ✅ | Create project |
| `GET` | `/api/projects/<id>` | ✅ | Get project by ID |
| `PUT` | `/api/projects/<id>` | ✅ | Update project |
| `DELETE` | `/api/projects/<id>` | ✅ | Delete project |
| `GET` | `/api/projects/<id>/tasks` | ✅ | Get project tasks |

**Create Project Request**:
```json
{
  "title": "My Project",
  "description": "Project description",
  "technologies": "React, Node.js, PostgreSQL"
}
```

**List Projects Query Params**:
- `page` (default: 1)
- `per_page` (default: 10)
- `include_tasks` (default: true)

---

### Recommendations (`/api/recommendations`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/recommendations/unified-orchestrator` | ✅ | **Primary** - Intent × content engine (query or `project_id`/`task_id`/`subtask_id`) |
| `POST` | `/api/recommendations/generate-context` | ✅ | Gemini explanation of how one item helps with the current context |
| `POST` | `/api/recommendations/task/<id>` | ✅ | Task-based recommendations |
| `POST` | `/api/recommendations/subtask/<id>` | ✅ | Subtask-based recommendations |
| `GET` | `/api/recommendations/status` | ✅ | Get engine status |
| `POST` | `/api/recommendations/cache/clear` | ✅ | Clear recommendation cache |
| `POST` | `/api/recommendations/cache/clear-context` | ✅ | Clear context cache |
| `POST` | `/api/recommendations/cache/clear-all-recommendations` | ✅ | Clear all recommendation cache |
| `GET` | `/api/recommendations/analysis/stats` | ✅ | Get analysis statistics |
| `POST` | `/api/recommendations/analysis/analyze-content/<id>` | ✅ | Analyze specific content |
| `POST` | `/api/recommendations/feedback` | ✅ | Submit recommendation feedback (`feedback_data` keys are whitelisted; references to other users' projects/tasks are dropped) |
| `GET` | `/api/recommendations/suggested-contexts` | ✅ | Suggested contexts (only the caller's own projects) |
| `GET` | `/api/recommendations/recent-contexts` | ✅ | Recently used contexts |
| `GET` | `/api/recommendations/gemini-status` | ✅ | Gemini availability for the user |

**Unified Orchestrator Request**:
```json
{
  "user_input": "I want to learn React hooks",
  "context": "general",
  "limit": 10,
  "diversity": true
}
```

**Context Options**:
- `general` - General recommendations
- `project` - Project-specific recommendations
- `task` - Task-specific recommendations

**Response**:
```json
{
  "recommendations": [
    {
      "id": 123,
      "title": "React Hooks Guide",
      "url": "https://example.com/react-hooks",
      "relevance_score": 0.95,
      "reason": "Highly relevant to React hooks learning",
      "context_summary": "Comprehensive guide covering useState, useEffect..."
    }
  ],
  "total": 10,
  "engine_used": "unified_orchestrator",
  "cache_hit": false
}
```

---

### Search (`/api/search`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/search/semantic` | ✅ | Semantic search (vector similarity) |
| `GET` | `/api/search/text` | ✅ | Text search (keyword-based) |

Semantic search ranks passages, and merges in bookmarks that have no chunks yet by
their document embedding, so nothing still processing drops out. It only compares
embeddings from the active model and returns the real cosine similarity. If the
query can't be embedded the endpoint returns 503 rather than a meaningless ranking.

**Semantic Search Request**:
```json
{
  "query": "machine learning tutorials",
  "limit": 10
}
```

**Text Search Query Params**:
- `q` - Search query (required)
- `limit` (default: 10)

---

### Ask your bookmarks (`/api/ask`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/ask` | ✅ | Answer a question only from the user's saved content, with numbered citations |

**Request**: `{"question": "...", "limit": 10}`. The question is 3-500 characters;
`limit` is the number of passages given to the model (1-12, default 10).

**Response**:
```json
{
  "answer": "Raise ef_search for better recall [1]. IVFFlat is the alternative [2].",
  "citations": [
    {"n": 1, "bookmark_id": 42, "title": "HNSW tuning", "url": "https://...", "snippet": "..."}
  ],
  "used_passages": 8
}
```

How it works (`services/ask_service.py`):
- **Retrieval** uses the same meaning-only index as semantic search, with no keyword matching.
  It takes the nearest saved-text passages from `content_chunks` (`hybrid_search.nearest_passages`;
  Gemini's `profile` rows are excluded because they are not the user's own text), and adds
  bookmarks with no chunks yet by their document embedding. Every query is filtered by
  `user_id` and the active embedding model. It allows at most 2 passages per bookmark,
  `limit` passages in total, and a context budget of about 3,500 tokens.
- **No relevant passages**: the endpoint returns an honest "not in your bookmarks" answer
  without calling Gemini or spending quota.
- **Generation** uses the user's key (`get_user_api_key`), with no database session open
  during the call. Passages are wrapped in per-request random delimiters, and the model is
  told to treat them as untrusted data: answer only from them, cite them as `[n]`, and say so
  when they don't contain the answer.
- **Citations** are parsed from the answer. Numbers outside the passages that were sent are
  removed from the text and never returned.

**Errors** (`{"error", "message"}`): `400 invalid_question`; `402 gemini_key_required`
(no usable key); `429 gemini_quota_exceeded` (per-user Gemini quota, or the day's share of
the shared key is used up; includes `Retry-After`); `503 generation_failed` or
`503 ask_unavailable`. The response isn't streamed: answers are short, and a single JSON
response lets citations be validated before anything is shown.

---

### Profile (`/api/profile`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/profile` | ✅ | Get user profile (includes `has_password` and `google_connected`) |
| `PUT` | `/api/profile` | ✅ | Update profile |
| `PUT` | `/api/users/<id>` | ✅ | Update user (compatibility) |
| `PUT` | `/api/users/<id>/password` | ✅ | Change password |

### User API Key (`/api/user`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/user/api-key` | ✅ | Add/update user's API key |
| `GET` | `/api/user/api-key` | ✅ | Get user's API key info |
| `DELETE` | `/api/user/api-key` | ✅ | Delete user's API key |
| `GET` | `/api/user/api-key/status` | ✅ | Get API key status |
| `POST` | `/api/user/api-key/test` | ✅ | Test API key validity |
| `GET` | `/api/user/api-key/usage` | ✅ | Get API key usage statistics |

### Tasks (`/api/tasks`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/tasks` | ✅ | Create task |
| `GET` | `/api/tasks/project/<id>` | ✅ | Get project tasks |
| `POST` | `/api/tasks/ai-breakdown` | ✅ | AI-powered task breakdown |
| `PUT` | `/api/tasks/<id>` | ✅ | Update task |
| `DELETE` | `/api/tasks/<id>` | ✅ | Delete task |
| `POST` | `/api/tasks/<id>/subtasks` | ✅ | Create subtask |
| `GET` | `/api/tasks/<id>/subtasks` | ✅ | Get task subtasks |
| `PUT` | `/api/tasks/subtasks/<id>` | ✅ | Update subtask |
| `DELETE` | `/api/tasks/subtasks/<id>` | ✅ | Delete subtask |

### LinkedIn (`/api/linkedin`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/linkedin/extract` | ✅ | Extract LinkedIn post content |
| `POST` | `/api/linkedin/analyze` | ✅ | Analyze LinkedIn content (same content profile as other bookmarks; 502 when the model returns nothing usable) |
| `POST` | `/api/linkedin/batch-extract` | ✅ | Batch extract LinkedIn posts |
| `GET` | `/api/linkedin/history` | ✅ | Get extraction history |
| `POST` | `/api/linkedin/save-to-bookmarks` | ✅ | Save LinkedIn content to bookmarks |
| `DELETE` | `/api/linkedin/extract/<id>` | ✅ | Delete extraction |
| `GET` | `/api/linkedin/status` | ✅ | Get LinkedIn service status |

### Feedback (`/api/feedback`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/feedback` | ✅ | Submit user feedback |

**Update Profile Request**:
```json
{
  "username": "newusername",
  "technology_interests": "Python, React, AI"
}
```

**Change Password Request**:
```json
{
  "current_password": "OldPass123",
  "new_password": "NewPass123"
}
```

---

### Health Check

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/health` | ❌ | Up/down for database and Redis |
| `GET` | `/health/liveness` | ❌ | Process alive (Docker `HEALTHCHECK`) |
| `GET` | `/health/readiness` | ❌ | 503 unless database, Redis and schema (Alembic head of this build) are ready |
| `GET` | `/api/health/database`, `/api/health/redis` | ❌ | Single-dependency up/down |
| `GET` | `/api/health/queue`, `/api/health/detailed` | `X-Internal-Token` | Queue depth and failed jobs / cache stats; 404 unless `INTERNAL_HEALTH_TOKEN` is set and sent |
| `GET` | `/metrics` | Bearer `METRICS_AUTH_TOKEN` | Prometheus metrics; 404 unless the token is configured |

Public health endpoints report up/down only: no hostnames, error text or environment.

**Response** (`/api/health`):
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": {"connected": true}
}
```

---

## Request/Response Format

### Request Headers

**Required for Protected Endpoints**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Optional**:
```
X-Request-ID: {unique_request_id}  # For request tracking
```

### Response Format

**Success Response**:
```json
{
  "message": "Operation successful",
  "data": { ... }
}
```

**Error Response**:
```json
{
  "message": "Error description",
  "error": "Detailed error message",
  "code": "ERROR_CODE"
}
```

### Pagination

**Paginated Response**:
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "per_page": 10,
  "pages": 10
}
```

---

## Error Handling

### Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Input validation failed |
| `AUTHENTICATION_ERROR` | Invalid or missing token |
| `AUTHORIZATION_ERROR` | Insufficient permissions |
| `NOT_FOUND` | Resource not found |
| `DUPLICATE_ERROR` | Duplicate resource |
| `RATE_LIMIT_ERROR` | Rate limit exceeded |
| `DATABASE_ERROR` | Database operation failed |
| `EXTERNAL_SERVICE_ERROR` | External service unavailable |

### Error Response Example

```json
{
  "message": "Invalid input",
  "error": "Username must be 3-50 characters",
  "code": "VALIDATION_ERROR",
  "field": "username"
}
```

### Comprehensive Error Handling System

Fuze has a robust, user-friendly error handling system that provides consistent error display, proper logging, and actionable user feedback.

#### Error Categories

| Type | Description | User Message |
|------------|-------------|--------------|
| `NETWORK` | Connection issues | "Network connection failed. Please check your internet and try again." |
| `AUTH`  | Authentication problems | "Your session has expired. Please log in again." |
| `VALIDATION` | Input validation errors | "Please check your input and try again." |
| `SERVER`  | Server-side issues | "Server error occurred. Please try again later." |
| `RATE_LIMIT` | Rate limiting | "Too many requests. Please wait a moment before trying again." |
| `UNKNOWN`  | Unexpected errors | "An unexpected error occurred. Please try again." |

#### HTTP Status Code Mapping

- **400**: Validation Error
- **401/403**: Authentication Error
- **404**: Not Found (treated as generic error)
- **409**: Conflict (Validation Error)
- **422**: Unprocessable Entity (Validation Error)
- **429**: Too Many Requests (Rate Limit)
- **5xx**: Server Error

#### Frontend Error Handling

**Components:**
1. **API Error Handler** (`services/api.js`)
   - Central error processing and categorization
   - User-friendly message mapping
   - Retry logic with exponential backoff

2. **Error Handler Hook** (`hooks/useErrorHandler.js`)
   - React hook for consistent error handling in components
   - Automatic toast notifications
   - Context-aware error messages

3. **Error Display Component** (`components/ErrorDisplay.jsx`)
   - Reusable error UI component
   - Different variants (compact, full, card)
   - Visual error categorization

4. **Enhanced Toast System** (`contexts/ToastContext.jsx`)
   - Beautiful, animated notifications
   - Multiple notification types
   - Responsive design

#### Error Logging

- Detailed error information in development console
- Stack traces for debugging
- Context information for error identification
- Full traceback and context in error logs

---

## Rate Limiting

### Rate Limits (Flask-Limiter)

| Endpoint Pattern | Limit | Window | Scope |
|------------------|-------|--------|-------|
| `/api/auth/login`, `/api/auth/set-password`, `PUT /api/users/<id>/password` | 5 requests | 15 minutes | Per user, else per IP |
| `/api/auth/register`, `/api/auth/update-username` | 10 requests | 1 hour | Per user, else per IP |
| `/api/auth/check-username` | 30 requests | 1 minute | Per IP |
| `/api/recommendations/unified-orchestrator` | 15 requests | 1 minute | Per User |
| `/api/recommendations/generate-context` | 10 requests | 1 minute | Per User |
| `/api/search/semantic` | 30 requests | 1 minute | Per User |
| `/api/ask` | 10/min, 100/day | moving window | Per User |
| `/api/linkedin/batch-extract` | 5 requests | 1 minute | Per User |
| All other endpoints | 50/min, 200/hour, 1000/day | moving window | Per user, else per IP |

**Note**: Limits use Redis storage (moving window). In production a missing
`REDIS_URL` or a limiter setup failure aborts startup; in-memory storage is only used
outside production. Development and testing use much higher defaults.

**Gemini usage**: users without their own Gemini key share the system key, up to
`SYSTEM_GEMINI_DAILY_LIMIT_PER_USER` uses a day each (default 30); after that they
are asked to add a key and background analysis waits. Per-user quota counters are
fixed windows (minute/day/month) that reset.

### Rate Limit Headers

**Response Headers**:
```
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 15
X-RateLimit-Reset: 1609459200
```

**Rate Limit Exceeded Response**:
```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Please slow down and try again later.",
  "retry_after": "60"
}
```

**Status Code**: `429 Too Many Requests`

---

## API Architecture Diagram

```mermaid
graph TB
    subgraph Client["CLIENT LAYER"]
        direction LR
        Web["Web Application"]
        Ext["Chrome Extension"]
    end
    
    subgraph "API Layer"
        AuthBP[Auth Blueprint<br/>/api/auth]
        BookBP[Bookmarks Blueprint<br/>/api/bookmarks]
        ProjBP[Projects Blueprint<br/>/api/projects]
        RecBP[Recommendations Blueprint<br/>/api/recommendations]
        SearchBP[Search Blueprint<br/>/api/search]
        AskBP[Ask Blueprint<br/>/api/ask]
        ProfBP[Profile Blueprint<br/>/api/profile]
        UserBP[User API Key Blueprint<br/>/api/user]
        TaskBP[Tasks Blueprint<br/>/api/tasks]
        LinkedBP[LinkedIn Blueprint<br/>/api/linkedin]
        FeedBP[Feedback Blueprint<br/>/api/feedback]
    end
    Web --> Row3
    Web --> Row4
    Web --> Row5
    Web --> Row6
    Ext --> Row1
    Ext --> Row4
    
    AuthBP --> JWT
    BookBP --> JWT
    ProjBP --> JWT
    RecBP --> JWT
    SearchBP --> JWT
    ProfBP --> JWT
    
    %% Middleware chain
    JWT --> RateLimit
    RateLimit --> Validation
    Validation --> CORS
    
    AuthBP --> JWT
    BookBP --> JWT
    ProjBP --> JWT
    RecBP --> JWT
    SearchBP --> JWT
    ProfBP --> JWT
    UserBP --> JWT
    TaskBP --> JWT
    LinkedBP --> JWT
    FeedBP --> JWT

    JWT --> RateLimit
    RateLimit --> Validation
    Validation --> CORS

    AuthBP --> DB
    BookBP --> DB
    ProjBP --> DB
    RecBP --> DB
    SearchBP --> DB
    AskBP --> JWT
    AskBP --> DB
    ProfBP --> DB
    UserBP --> DB
    TaskBP --> DB
    LinkedBP --> DB
    FeedBP --> DB

    BookBP --> Redis
    RecBP --> Redis
    ProjBP --> Redis

    RecBP --> Gemini
    BookBP --> Gemini
    AskBP --> Gemini
    
    classDef clientStyle fill:#667eea,stroke:#5a67d8,stroke-width:3px,color:#fff,font-weight:bold
    classDef authStyle fill:#f093fb,stroke:#c471ed,stroke-width:2px,color:#fff,font-weight:bold
    classDef apiStyle fill:#4facfe,stroke:#00b4d8,stroke-width:2px,color:#fff,font-weight:bold
    classDef aiStyle fill:#fa709a,stroke:#f77089,stroke-width:2px,color:#fff,font-weight:bold
    classDef middlewareStyle fill:#ffa726,stroke:#fb8c00,stroke-width:2px,color:#fff,font-weight:bold
    classDef dbStyle fill:#43e97b,stroke:#38f9d7,stroke-width:3px,color:#fff,font-weight:bold
    
    class Web,Ext clientStyle
    class Row1 authStyle
    class Row2,Row3,Row4,Row5 apiStyle
    class Row6 aiStyle
    class JWT,RateLimit,CORS,Validation middlewareStyle
    class DB,Redis,Gemini dbStyle
```

---


---
Ujjwal Jain


