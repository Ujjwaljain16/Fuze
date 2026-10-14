# Fuze - AI-Powered Intelligent Content Manager

<div align="center">

 <img src="frontend/src/assets/logo1.svg" alt="Fuze Logo" width="280" height="100" /> 

**Transform your saved scattered content into an intelligent knowledge base with AI-powered semantic search and personalized recommendations.**

> [!NOTE]
> **This project is actively under development with ongoing iterations and improvements.** Features and interfaces may evolve as we continue to enhance the user experience and add new capabilities.

> [!NOTE]
> **Hosting:** the reference deployment runs the backend on a Hugging Face Space (Docker SDK), the frontend on Vercel, Postgres on Supabase and Redis on Upstash, all on free tiers. Hugging Face forbids browser automation, so the image has none: the app fetches only the page a user saves, over plain HTTP, and recovers harder pages through a remote reader and the Wayback Machine ([details](docs/CONTENT_ACQUISITION.md)). Features removed only for that host are listed in [`docs/RE_ENABLE_ON_NEW_HOST.md`](docs/RE_ENABLE_ON_NEW_HOST.md), and a self-hosted fallback (Caddy + Docker Compose) is in [`deploy/`](deploy/). You can always run the full stack locally with the [Quick Start](#-quick-start).

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.1-green?logo=flask)
![React](https://img.shields.io/badge/React-19-blue?logo=react)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [API](docs/API_ARCHITECTURE.md) • [Contributing](#-contributing)

</div>

---

## ✨ Features

### 🧠 AI-Powered Intelligence
- **Semantic Search**: Find content by meaning, not just keywords
- **Ask Your Bookmarks**: Ask a question in plain language and get an answer written only from your saved pages, with numbered citations linking to the bookmarks it used (and an honest "not in your bookmarks" when they don't cover it)
- **Smart Recommendations**: Your own saved content, surfaced for the project, task or subtask you're working on
- **Content Analysis**: Automatic extraction and analysis using Gemini AI
- **Intent Understanding**: Understands what you're trying to do from your own words, refined by Gemini in the background

### 🎯 Project Organization
- **Project-Based Workflow**: Organize projects and tasks
- **Task Management**: Break down projects into actionable tasks with AI assistance
- **Contextual Recommendations**: Get relevant content suggestions for your active projects

### 🔍 Advanced Search
- **Multi-Modal Search**: Text, semantic, and hybrid search capabilities
- **Vector Similarity**: pgvector-powered semantic matching
- **Fast Queries**: Optimized database indexes for instant results

### ⚡ Performance & Reliability
- **Shared Caching**: Redis caching for fast responses, with fail-fast timeouts so a slow Redis can't hang requests
- **Background Processing**: One RQ job per bookmark and stage, plus a reconciler that re-enqueues anything lost or deferred
- **Connection Pooling**: Efficient database connection management
- **Explicit Failure Handling**: transient failures retry, a reconciler re-enqueues lost work, failed fetches are recorded as such, and the container refuses to start on a failed migration

### 🔌 Integrations
- **Chrome Extension**: One-click bookmarking from any webpage
- **LinkedIn Integration**: Save and analyze LinkedIn posts and articles
- **PWA Support**: Install as a mobile app with share functionality
- **Bulk Import**: Import existing bookmarks from Chrome

---
## 📸 Demo

### Landing Page
<div align="center">
<img width="1919" height="927" alt="Screenshot 2025-11-24 035836" src="https://github.com/user-attachments/assets/0ff4d2b5-3724-4913-85c0-71e18bd4fbdd" />


*Welcome to Fuze - Your intelligent content manager*

</div>

### Dashboard
<div align="center">

<img width="1920" height="1080" alt="Screenshot 2025-11-24 025912" src="https://github.com/user-attachments/assets/d35f995f-60a7-48f2-bb42-4d3ce8cedc39" />


*Overview of your bookmarks, projects, and statistics*

</div>

### Bookmarks Management
<div align="center">

<img width="1920" height="1080" alt="Screenshot 2025-11-24 035358" src="https://github.com/user-attachments/assets/6c691cba-efe6-4561-b1c2-82feed461e90" />


*Organize and search through your saved content with AI-powered semantic search*

</div>

### Projects & Tasks
<div align="center">

<img width="1920" height="1080" alt="Screenshot 2025-11-24 035415" src="https://github.com/user-attachments/assets/48d89e18-98fb-4af3-aebd-72973aa0813a" />


*Organize projects and break them down into actionable tasks*

</div>

### AI Recommendations
<div align="center">

<img width="1920" height="1080" alt="Screenshot 2025-11-24 035434" src="https://github.com/user-attachments/assets/2796a560-bc06-4308-87a6-b51a25a5cb8b" />

<img width="1920" height="1080" alt="Screenshot 2025-11-24 035000" src="https://github.com/user-attachments/assets/a72f7e0c-6fda-4933-95bc-d50e7067b9f1" />
<img width="1920" height="1080" alt="Screenshot 2025-11-24 035010" src="https://github.com/user-attachments/assets/fb66fd51-2780-430a-90e4-dee25b03ab2a" />



*Get personalized content recommendations based on your projects and interests*

</div>

### Profile & Settings
<div align="center">

<img width="1920" height="1080" alt="Screenshot 2025-11-24 035443" src="https://github.com/user-attachments/assets/341d5a7e-0458-470e-a488-cc26610f374c" />


*Manage your profile, API keys, and preferences*

</div>

---
## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (with pgvector extension)
- Redis (Upstash or local)
- Node.js 20+ (for frontend)

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/Ujjwaljain16/Fuze.git
cd Fuze

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (requirements-dev.txt = requirements.txt + test tools)
pip install -r requirements-dev.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration; keep APP_ENV=development for local work

# Create the schema (PostgreSQL with the pgvector extension)
python -m alembic -c alembic.ini upgrade head

# Start the server
cd backend
python run_production.py

# Tests: SQLite by default; set TEST_DATABASE_URL to a local Postgres with pgvector
# (e.g. postgresql://postgres:test@localhost:55432/fuze_test) for the full lane
pytest
```

Dependencies: `requirements.txt` holds the exact pins; the Docker image installs
`requirements.lock` (every transitive package, hash-checked). After editing
`requirements.txt`, run `scripts/lock-requirements.sh` and commit both files.

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Environment Variables

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/fuze

# Redis (rediss:// for TLS, as Upstash gives it)
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# AI Services
GEMINI_API_KEY=your-gemini-api-key

# Application: development | testing | production (unset = production, which
# refuses to start with missing, default or short SECRET_KEY / JWT_SECRET_KEY)
APP_ENV=development
DEBUG=true
# Extra exact origins only; the local dev servers are allowed outside production
CORS_ORIGINS=
```

The frontend reads `VITE_API_URL` (the backend origin; default `http://127.0.0.1:5000`) and, for Google sign-in,
`VITE_SUPABASE_URL`; see [`frontend/.env.example`](frontend/.env.example). See [`.env.example`](.env.example)
for every backend setting the code reads.

---

## 📚 Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

- **[Documentation Index](docs/README.md)** - Complete documentation overview and quick links
- **[Architecture](docs/ARCHITECTURE.md)** - System architecture and design
- **[API Documentation](docs/API_ARCHITECTURE.md)** - Complete API reference
- **[User Flows](docs/USERFLOW.md)** - Feature walkthroughs
- **[Testing Guide](docs/TESTING.md)** - Testing setup and examples
- **[Recommendations](docs/RECOMMENDATIONS.md)** - How the intent engine ranks your saved content
- **[Optimizations](docs/OPTIMIZATIONS.md)** - Performance work, with measurements
- **[Performance data](docs/perf/README.md)** - Raw live-benchmark results and what they show
- **[Decision records](docs/adr/README.md)** - Why the architecture is the way it is
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Complete deployment instructions
- **[Operations Runbook](docs/OPERATIONS.md)** - Backups, restore drill, rollback, pipeline health and secret rotation
- **[PWA Guide](docs/PWA.md)** - Progressive Web App features and setup
- **[Content acquisition](docs/CONTENT_ACQUISITION.md)** - How pages are fetched without a browser

---

## 🛠️ Tech Stack

### Backend
- **Framework**: Flask 3.1
- **Database**: PostgreSQL 15 with pgvector
- **Caching**: Redis (Upstash)
- **ML/AI**: 
  - Sentence Transformers (bge-small-en-v1.5, chosen by benchmark)
  - Google Gemini API
- **Task Queue**: RQ (Redis Queue)
- **Authentication**: JWT (Flask-JWT-Extended)

### Frontend
- **Framework**: React 19
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: React Context + Hooks
- **PWA**: Service Worker + Web App Manifest

### Infrastructure
- **Deployment**: Vercel (frontend) and Hugging Face Spaces, Docker SDK (backend) — both live; see the hosting note above for the fallback-host plan
- **Containerization**: Docker (image builds and runs correctly, verified via CI)
- **CI/CD**: GitHub Actions

---

## 🏆 Key Innovations & Achievements

### 🚀 Technical Innovations

#### **Intent × Content Engine** ([how it works](docs/RECOMMENDATIONS.md))
- **Content understanding**: every saved item is split into overlapping passages (the whole text, not just what fits in the embedding model's window) and given a validated Gemini *content profile* — summary, what it teaches or solves, key concepts, and when it's useful — which is embedded alongside the passages
- **Intent understanding**: what you're doing right now is built from your own words (search text, or project → task → subtask); Gemini refines it in the background into an intent statement plus concrete information needs, cached per context so requests never wait on the LLM
- **Ranking by meaning only**: multi-query nearest-passage search over pgvector (HNSW, per-user filtered), optional cross-encoder rerank, then MMR so the top results aren't near-duplicates — no keyword lists, hand-tuned boosts or rule-based fallbacks
- **Grounded explanations**: each recommendation shows the passage that matched; on demand Gemini explains how the item helps with your current task
- **Measured, not assumed**: an end-to-end retrieval benchmark (`backend/scripts/eval_retrieval.py`) runs the production search code against BEIR SciFact (300 queries) in a real Postgres + pgvector database. On the standard corpus nDCG@10 is **0.718** against **0.652** for a BM25 baseline I re-ran (published: 0.665). On a synthetic long-document stress test, where the relevant text sits past the embedding model's input window, the previous one-vector-per-bookmark search scored **0.016** with the same bge-small model; passage search scores **0.504**, which ties BM25 (0.5035) there. Switching MiniLM → bge-small-en-v1.5 (same 384 dims) added **+10% nDCG@10** (0.652 → 0.718). A cross-encoder reranker was measured and left off: no quality gain for ~700 ms extra per query ([results](docs/RECOMMENDATIONS.md))

#### **Model Caching & Performance Optimization**
- **Model Loaded Once Per Process**: a thread-safe singleton in the web workers; RQ workers load it in the parent before forking, so jobs share it instead of reloading it
- **Single-flight Token Refresh**: concurrent 401s share one refresh request, so a burst of calls never triggers several refreshes
- **Redis Caching**: Shared per-user caches (keys built in one place, `core/cache_keys.py`)
- **Responsive gevent Workers**: psycogreen makes Postgres queries yield (5 concurrent `pg_sleep(1)`: 5.05 s unpatched, 1.01 s patched) and CPU-bound encode/bcrypt run on gevent's thread pool
- **Query Result Caching**: Intelligent TTL-based caching for expensive database queries

#### **Per-User API Key Management System**
- **Encrypted Storage**: Fernet encryption for user API keys with an HKDF-derived, purpose-specific key; values encrypted under the previous key are migrated on read
- **Individual Rate Limiting**: Per-user rate limits (15/min, 1500/day, 45000/month) with usage tracking
- **Shared System Key, Capped**: users without their own key share the system key, up to `SYSTEM_GEMINI_DAILY_LIMIT_PER_USER` uses a day each (default 30); after that they're asked to add a key and background analysis waits
- **API Key Validation**: Built-in testing and validation endpoints for user API keys

#### **Semantic Search with pgvector**
- **Passage-level search**: queries are matched against passages and content profiles, and the best-matching passage is shown as the snippet
- **Versioned embeddings**: every vector records the model that produced it, so a model change never mixes incompatible vectors

### 🎯 Unique Features

#### **Bulk Import with Real-Time Progress Tracking**
- **Redis-Based Progress**: Real-time progress updates for Chrome extension bulk imports, kept in Redis and pushed over Server-Sent Events
- **Optimized Deduplication**: Smart URL matching prevents duplicate bookmarks during bulk import
- **Background Processing**: Async content analysis pipeline that doesn't block user requests
- **Error Recovery**: Graceful handling of failed imports with detailed error reporting

#### **Project-Centric Knowledge Management**
- **Context-Aware Recommendations**: AI understands your active projects and suggests relevant content from your bookmarks
- **Task-Based Organization**: Break down projects into tasks with AI-powered task breakdown suggestions
- **Project-Specific Recommendations**: Get content recommendations tailored to specific project needs

#### **PWA Share Target Integration**
- **Native Mobile Experience**: Install as mobile app with share functionality from any app (LinkedIn, Twitter, browsers)
- **Automatic URL Extraction**: Intelligent URL extraction from shared text, title, and content fields
- **One-Click Bookmarking**: Save bookmarks directly from share menu without opening the app

#### **LinkedIn Specialized Scraper**
- **Enhanced Content Extraction**: Specialized scraper for LinkedIn posts with quality scoring (1-10 scale)
- **Activity URL Handling**: Handles complex LinkedIn activity URLs with encoded parameters
- **Content Analysis**: Automatic extraction of post text, author, and metadata

### 📊 Performance Achievements

- **Measured**: 5 concurrent 1-second queries on one gevent worker take 1.01 s with psycogreen vs 5.05 s without; the ML stack upgrade left embeddings unchanged (cosine 1.0)
- **Retrieval quality**: nDCG@10 on BEIR SciFact recorded in `backend/eval/results/`
- **Live latency, measured on the deployed Space** (`scripts/bench_live.py`, 30 samples per endpoint from India, results in [`docs/perf/`](docs/perf/)): semantic search p50 fell from **3.0 s to about 1.7 s** by cutting the database round trips per search from about 10 to 1 (returning less passage text was tried too and made no difference); keyword search from 1.24 s to about 0.95 s. The server reports where the time went (`X-Server-Timing: 1`): embedding is about 15 ms and the database statement about 1.1 s, of which Postgres itself accounts for about 2 ms. The rest is the link to the database and is not fully explained (see Known Limitations and [`docs/perf/`](docs/perf/README.md)). Cached reads add a few milliseconds to the network floor when Redis is healthy
- **Found by measuring**: the Space reported a 215 ms round trip to its database against 2 ms to Redis (`/health/readiness?timing=1`), which explained why every database-backed request was slow even though the queries themselves take only a few milliseconds inside Postgres
- **Automated tests**: 800+ backend tests (a 74% coverage floor enforced in CI) run on every change, once on SQLite and once on Postgres + pgvector, plus ruff and mypy gates; 79 frontend and 52 extension tests
- **Stateless Processes**: web and worker processes keep no state of their own; everything shared lives in Postgres and Redis
- **Gated Deployments**: the HF Space is deployed only after Backend CI passes on that exact commit, and the container refuses to serve if migrations fail

---

## 🏗️ Project Structure

```
Fuze/
├── backend/                 # Flask backend
│   ├── blueprints/         # API route handlers
│   ├── core/               # Cross-cutting pieces: cache keys, locks, quotas, server timing, feature flags
│   ├── services/           # Business logic and the background pipeline (reconciler, search, Ask)
│   ├── ml/                 # Intent engine and ranking
│   ├── scrapers/           # Page acquisition: HTTP fetch, extractors, reader and archive tiers
│   ├── repositories/ uow/  # Data access and unit of work
│   ├── utils/              # Shared helpers (config, DB pool, embeddings, LLM provider)
│   ├── alembic/            # Database migrations (alembic.ini is at the repo root)
│   ├── eval/               # Retrieval benchmark results
│   ├── scripts/            # Maintenance and evaluation scripts
│   ├── tests/              # Test suite
│   ├── worker.py           # RQ worker entry point
│   └── run_production.py   # App factory and server entry point
├── frontend/                # React frontend (Vite)
├── BookmarkExtension/       # Browser extension (git submodule)
├── deploy/                  # Self-hosted fallback: Caddy + Docker Compose
├── scripts/                 # Benchmarks, DB copy, usage sampler, extension packaging
└── docs/                    # Documentation
```

---

## ⚠️ Known Limitations & Scope for Improvement

What is not good enough yet, with the evidence, so the next step is obvious.

**Performance**
- **The database is in the wrong region.** The backend (a Hugging Face Space) measures a **215 ms round trip** to Supabase in Singapore, against 2 ms to Redis. Every SQL statement pays it, so semantic search sits at about 1.7 s (p50) even though Postgres runs the query in about 2 ms (the measured cost per statement is higher than one round trip, and about 900 ms is not yet explained). Moving Supabase next to the backend (US East is the likely region; Hugging Face does not document it) should remove most of that, but it has not been tried, so no new figure is claimed. The runbook, a verified copy tool (`scripts/copy_database.py`) and the measurements are ready: [docs/REGION_MOVE.md](docs/REGION_MOVE.md). It is deliberately not done yet.
- **Where the time goes now.** The `X-Server-Timing: 1` request header returns `total`, `embed`, `db` and the number of SQL statements. A semantic search spends about 2 ms embedding and 1.1 s in one database statement that Postgres itself runs in about 2 ms, so almost all of it is distance and transfer between the Space and the database, which the region move removes.
- **Throughput under load is not measured.** The app rate-limits clients to 50 requests a minute by default, which is right for production but stops a naive load test. A proper capacity test needs a dedicated limit exemption for the test client.
- **Ask your bookmarks is not benchmarked on the live Space** yet (needs the LLM provider secrets on the Space). Locally an LLM call takes 4-9 s through the router.

**Infrastructure and cost**
- Free tiers throughout: a shared-CPU Space, Supabase free (500 MB, pauses after a week idle, kept alive by a scheduled workflow), Upstash free. The free Gemini key allows 20 requests a day, so the LLM provider can be switched to any OpenAI-compatible service (`LLM_PROVIDER`), which is how the analysis of a 238-bookmark import ran for about 7 cents.
- The Space needs `SECRET_KEY`, `JWT_SECRET_KEY` and the data-store URLs as secrets before it boots; there is no staging environment, so local development points at the same database and queue as production.

**Content acquisition**
- No browser runs on the server by design (the host flagged browser automation). Pages that need one are recovered through official APIs, a remote reader and the Wayback Machine, but some stay thin: Reddit blocks its JSON endpoint (title only), YouTube playlists and login-walled pages have no readable text unless saved from the extension, which sends the rendered page.
- `robots.txt` disallows are respected, so some sites are deliberately not fetched. The one exception is public LinkedIn posts a user saves (one plain request, switchable with `LINKEDIN_PUBLIC_FETCH_ENABLED`); see [docs/CONTENT_ACQUISITION.md](docs/CONTENT_ACQUISITION.md).

**Quality evidence still missing**
- Recommendation quality is measured offline on a public benchmark, not on real users' feedback. Feedback is stored per project (`user_feedback.project_id`) and `backend/scripts/export_feedback_eval.py` turns it into a BEIR-format evaluation set, but only a handful of ratings exist so far.
- The browser extension has unit tests (52) but has not been exercised end to end in a real Chrome against the deployed backend.

---

## 🚀 Roadmap

- [ ] Move the database next to the backend ([runbook](docs/REGION_MOVE.md))
- [ ] More sources: GitHub, YouTube transcripts, Medium/Dev.to
- [ ] Shared projects for small teams
- [ ] Firefox and Edge extensions
- [ ] A capacity test with a rate-limit exemption for the test client

---

## 🤝 Contributing

Issues and pull requests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) for setup, the checks CI runs and
the commit conventions, and [SECURITY.md](SECURITY.md) to report a vulnerability privately.

## 📄 License

[MIT](LICENSE) © Ujjwal Jain

---

## 🙏 Acknowledgments

- [Sentence Transformers](https://www.sbert.net/) for semantic embeddings
- [pgvector](https://github.com/pgvector/pgvector) for vector similarity search
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [React](https://react.dev/) for the frontend framework

---

<div align="center">

<img src="frontend/src/assets/logo1.svg" alt="Fuze Logo" width="280" height="100" />

**Made with ❤️ by [Ujjwal Jain](https://github.com/Ujjwaljain16)**

</div>
