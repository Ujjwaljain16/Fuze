# Fuze Production Operations Manual

This document outlines the safety protocols and architectural hardening implemented to ensure the stability and data integrity of the Fuze production environment.

## 🏗️ Core Stability Features (Implemented)

### 1. Database Initialization Safeguards
- **Background Worker Suppression**: `run_production.py` now respects the `SKIP_BACKGROUND_SERVICES` environment variable.
- **Safe Init**: `init_db.py` automatically sets `SKIP_BACKGROUND_SERVICES=true` to prevent the background analysis worker from crashing or locking the database while tables are being created.

### 2. Distributed Locking
- **Lock Management**: `backend/core/distributed_lock.py` uses Redis-backed locking to prevent concurrent analysis tasks from colliding.
- **UUID Ownership**: Locks are owner-tracked via `uuid.uuid4()` to ensure only the process that acquired a lock can release it.

### 3. Maintenance Mode
- **Frontend Guard**: `frontend/src/App.jsx` checks `VITE_MAINTENANCE_MODE`. If set to `true`, all routes are blocked by a premium maintenance page.
- **Illustration**: Custom 3D assets located in `frontend/src/assets/maintenance.png`.

## 🛠️ Maintenance & Safety Protocols

### 💾 Data Safety (Priority #1)
- **Backup Before Migration**: Always perform a Supabase snapshot or `pg_dump` before running any manual database scripts.
- **Record Detection**: Before resetting any versioning, always check `SELECT count(*) FROM users`. If > 0, do NOT drop the `alembic_version` table without a manual backup.

### 🔄 Database Migrations
- **Alembic First**: Never use `db.create_all()` in production after the initial setup. Use `alembic upgrade head` for all schema changes.
- **Lock Recovery**: If migrations hang due to "idle in transaction" locks, use `backend/scratch/kill_my_sessions.py` (archived logic) to safely terminate stuck connections from the same user.

### 🧪 Model Updates
- **Warmup Phase**: The `warm_up_embedding_model()` function in `utils/embedding_utils.py` must be called on startup to prevent latency spikes for the first user.

---
*Last Updated: 2026-04-24*
