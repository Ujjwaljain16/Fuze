# Operations

How to keep Fuze's data safe and its pipeline healthy in production.

## Backups

Supabase takes daily backups on paid plans only. On the free plan, take your own:

```bash
# Full logical backup (schema + data), compressed. Use the session pooler or direct URL.
pg_dump "$DATABASE_URL" --format=custom --no-owner --no-privileges --file "fuze-$(date +%F).dump"
```

- Run it at least weekly, and before every migration that drops or rewrites data.
- Keep backups off the database host (another cloud bucket or an encrypted local drive).
- The dump holds users' saved content, hashed passwords and encrypted Gemini keys: treat it as secret.

## Restore drill

A backup you have never restored is a hope, not a backup. Once a month, restore the newest dump into
a scratch database and check it:

```bash
docker run -d --name fuze-restore -e POSTGRES_PASSWORD=x -p 55433:5432 pgvector/pgvector:pg15
createdb -h localhost -p 55433 -U postgres fuze_restore
pg_restore -h localhost -p 55433 -U postgres -d fuze_restore --no-owner "fuze-YYYY-MM-DD.dump"
DATABASE_URL=postgresql://postgres:x@localhost:55433/fuze_restore APP_ENV=development \
  python -m alembic -c alembic.ini current      # should print the expected head
psql -h localhost -p 55433 -U postgres -d fuze_restore -c "select count(*) from saved_content"
docker rm -f fuze-restore
```

## Migrations

- `start.sh` runs `alembic upgrade head` on every boot and refuses to start if it fails. Each
  revision runs in its own transaction, so a failure leaves the database at the last good revision.
- `/health/readiness` returns 503 until the database is at the head this build expects.
- Every revision has a working downgrade except 0001 (it would drop every table). CI checks that
  `downgrade 0001` followed by `upgrade head` lands on exactly the schema in `models.py`.
- To roll back a bad release: deploy the previous image, then `alembic downgrade <its head>`.
  If data was destroyed, restore a backup instead.

## Pipeline health

- Bookmarks move through `scrape_status` and `embedding_status`. Anything stuck is picked up by the
  reconciler in the default RQ worker every 5 minutes (see `services/pipeline_reconciler.py`).
- Once a day the same loop deletes `bookmark_events` rows older than `BOOKMARK_EVENTS_RETENTION_DAYS`
  (default 30, `0` keeps them forever), 5000 rows per statement.
- `GET /api/health/queue` (with `X-Internal-Token: $INTERNAL_HEALTH_TOKEN`) shows queue depth,
  failed jobs and active workers.
- Useful queries:

```sql
-- what the pipeline is waiting on
select scrape_status, embedding_status, count(*) from saved_content group by 1, 2 order by 3 desc;
-- fetches that gave up
select id, url, scraped_at from saved_content where scrape_status in ('FAILED_FETCH', 'BLOCKED', 'DISALLOWED');
```

## Embedding model

The Docker image ships with `BAAI/bge-small-en-v1.5` in `HF_HOME=/app/.cache/huggingface`, and
runs with `HF_HUB_OFFLINE=1`, so containers never download a model. If you change
`EMBEDDING_MODEL_NAME` or set `SEARCH_RERANK_ENABLED=true`, add that model to the download step in
the `Dockerfile` (or run with `HF_HUB_OFFLINE=0`). Otherwise it fails to load: embeddings fall back
to hash vectors (logged as `all_embedding_models_failed_using_fallback`) and the reranker stays off.

## Secrets

Production refuses to start unless `SECRET_KEY` and `JWT_SECRET_KEY` are set, at least 16
characters and not a known default. `API_KEY_ENCRYPTION_KEY` is optional; when set it gets the same
checks. Rotating `JWT_SECRET_KEY` signs everyone out.

Users' Gemini keys are stored encrypted. Without `API_KEY_ENCRYPTION_KEY` the encryption key is
derived from `SECRET_KEY`, so rotating `SECRET_KEY` makes every stored key undecryptable and users
must re-enter them. To make `SECRET_KEY` rotatable:

1. Set `API_KEY_ENCRYPTION_KEY` (a new random value of 16+ characters) and deploy, keeping
   `SECRET_KEY` unchanged. New keys are encrypted with it. Existing keys still decrypt with the
   `SECRET_KEY`-derived key and are re-encrypted with the new one the next time they are used.
2. Move the keys nobody has used yet: from `backend/`, with the production environment,
   `python scripts/reencrypt_api_keys.py`. It prints how many were re-encrypted and how many could
   not be decrypted. Safe to re-run.
3. Rotate `SECRET_KEY`.

`API_KEY_ENCRYPTION_KEY` itself cannot be rotated this way: changing or losing it makes the keys
encrypted with it undecryptable.
