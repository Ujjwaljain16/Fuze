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
- `GET /api/health/queue` (with `X-Internal-Token: $INTERNAL_HEALTH_TOKEN`) shows queue depth,
  failed jobs and active workers.
- Useful queries:

```sql
-- what the pipeline is waiting on
select scrape_status, embedding_status, count(*) from saved_content group by 1, 2 order by 3 desc;
-- fetches that gave up
select id, url, scraped_at from saved_content where scrape_status in ('FAILED_FETCH', 'BLOCKED', 'DISALLOWED');
```

## Secrets

Production refuses to start unless `SECRET_KEY` and `JWT_SECRET_KEY` are set, at least 16
characters and not a known default. Rotating `JWT_SECRET_KEY` signs everyone out. Rotating
`SECRET_KEY` makes stored Gemini keys undecryptable: users must re-enter them.
