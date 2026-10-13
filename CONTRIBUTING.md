# Contributing to Fuze

Thanks for helping. This guide covers how to run the project, what CI checks, and how to send a change.

## Set up

Prerequisites: Python 3.11, Node.js 20, PostgreSQL 15+ with the `pgvector` extension, Redis.
The [README quick start](README.md#-quick-start) has the full steps; in short:

```bash
python -m venv venv && source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt                    # the exact pins production runs
cp .env.example .env                                   # keep APP_ENV=development
python -m alembic -c alembic.ini upgrade head
cd backend && python run_production.py

cd frontend && npm ci && npm run dev
```

**Install the pinned versions.** Production runs the versions in `requirements.txt` / `requirements.lock`
(for example `rq==1.15.1`). A newer library on your machine can hide a bug that only appears in production,
so test against the pins.

Local runs read `.env`. Point `DATABASE_URL` and `REDIS_URL` at throwaway local services, never at a shared
or production database.

## Checks CI runs (run them before you push)

| Area | Command (from the directory shown) |
|---|---|
| Backend lint | `ruff check .` (`backend/`) |
| Backend types | `mypy` (`backend/`) |
| Backend tests | `pytest` (`backend/`); SQLite by default |
| Backend tests, full lane | set `TEST_DATABASE_URL` to a local Postgres with pgvector, then `pytest` |
| Migrations | `alembic upgrade head && alembic check` (the models and migrations must agree) |
| Frontend lint | `npm run lint -- --max-warnings=0` (`frontend/`) |
| Frontend tests | `npm test -- --run` (`frontend/`) |
| Frontend build | `npm run build` (`frontend/`) |
| Extension tests | `node --test` (`BookmarkExtension/`, a git submodule) |

Backend coverage must stay at or above the floor set in `.github/workflows/backend-ci.yml`.
See [docs/TESTING.md](docs/TESTING.md) for details.

## Making a change

1. Open an issue first for anything larger than a small fix, so the approach can be agreed.
2. Branch from `main`. Keep each commit **atomic**: one logical change that builds and passes on its own.
3. Write the test with the change. A bug fix includes a test that fails without the fix, and that test should
   build the real object it covers (a test that only inspects source text will not catch a wrong argument).
4. Schema changes need an Alembic migration (`backend/alembic/versions/`) with a working downgrade; CI runs
   upgrade, downgrade and `alembic check`.
5. Dependencies: edit `requirements.txt`, then run `scripts/lock-requirements.sh` and commit both files.
6. Update the docs that your change makes untrue (README, `docs/`, `.env.example`).

Commit messages follow `type(scope): what and why`, for example
`perf(search): return only the start of each passage`. Types in use: `feat`, `fix`, `perf`, `refactor`,
`chore`, `docs`, `test`, `ci`.

## Project conventions

- **Shared state lives in Postgres and Redis**, never in a process. Web and worker processes are stateless.
- **Redis is metered on free plans** (Upstash allows 500,000 commands a month). Do not add anything that polls
  Redis on a timer; see "Redis command budget" in [docs/OPERATIONS.md](docs/OPERATIONS.md).
- **Every SQL statement is a network round trip** between the backend and Supabase. Prefer one statement that
  does the job; `backend/tests/test_ann_round_trips.py` pins the statement count of a search.
- **No browser automation in the Docker image.** The hosting provider forbids it; see
  [docs/CONTENT_ACQUISITION.md](docs/CONTENT_ACQUISITION.md).
- **Secrets** are never committed. `.env` is git-ignored; `.env.example` lists every variable the code reads.

## Reporting bugs and security issues

Bugs and feature requests: open a GitHub issue using the templates. Security problems: see
[SECURITY.md](SECURITY.md) and do not open a public issue.
