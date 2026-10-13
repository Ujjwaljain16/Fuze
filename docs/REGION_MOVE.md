# Moving the database next to the backend

**Status: not done.** Everything below is measured and ready; the move itself has not been carried out. It is
listed as a known limitation in the README.

**Why.** The Hugging Face Space measures its own distance to the database
(`GET /health/readiness?timing=1`):

| From the Space to | Round trip |
|---|---|
| Supabase project (`ap-southeast-1`, Singapore) | **213-228 ms** |
| Upstash Redis (replicated near the Space) | 2-3.5 ms |

Every SQL statement, plus `BEGIN`/`ROLLBACK`, pays that 215 ms. A semantic search made about 10 of them
(2.7 s measured on the live Space); after the round-trip reduction in `hybrid_search.py` and
`db_pool.py` it makes about 5. In the same region it would cost 5 x ~2 ms. The code can only halve the
cost of distance; moving the database removes it.

**Target region: US East (N. Virginia), `us-east-1`.** HF does not document its Space region. 215 ms from
Singapore is what US East looks like (US West would be ~170 ms, Europe ~160 ms), and the 294 ms from
India to the Space agrees. Step 6 confirms it with a measurement before anything is deleted; if the
number is not close to 1-10 ms, point the secrets back (step 10) and try the next-closest region.

Redis needs no move. Supabase cannot change a project's region in place
([their guide](https://supabase.com/docs/guides/troubleshooting/change-project-region-eWJo5Z)):
a new project is created and the data copied. Free plan: 500 MB per project, at most 2 active projects (the old and the new project make 2; check
the dashboard for others), and projects pause after a week without activity (the keep-alive workflow
covers that). This database is 36 MB.

Time: about 45 minutes, of which the Space is paused (nobody can use it) for about 10.

## What changes

| Where | What |
|---|---|
| Supabase | create the new project; enable Google sign-in; copy URL, anon key, pooler string |
| New database | `alembic upgrade head`, then `scripts/copy_database.py` |
| Google Cloud Console | add the new project's callback URL to the OAuth client |
| Hugging Face Space | secrets `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY` |
| Vercel (frontend) | env `VITE_SUPABASE_URL` (and the anon key if set), then redeploy |
| GitHub Actions secrets | `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY` (+ `BACKUP_DATABASE_URL` if set) |
| local `.env` | the same three values |

Passwords and keys are passed to the copy script through environment variables, never on the command line.

## Steps

1. **Create the project.** Supabase dashboard, New project: region **East US (North Virginia)**, a new
   strong database password. Save the password in a password manager.
2. **Collect three values** from the new project: Project URL (`https://<ref>.supabase.co`), the anon
   key, and the **session pooler** connection string (Connect, "Session pooler", port **5432**, host
   `aws-0-us-east-1.pooler.supabase.com`, user `postgres.<ref>`). Not the transaction pooler (6543):
   Fuze sets per-connection options that need session mode.
3. **Build the schema** from the project's own migrations (CI tests them, including downgrades). In a
   shell from the repo root:

   ```
   set DATABASE_URL=<new session pooler string>
   python -m alembic -c alembic.ini upgrade head
   ```

   It must end at revision `0014 (head)`.
4. **Dry run** (reads the old database, changes nothing):

   ```
   set SOURCE_DATABASE_URL=<old string>
   set TARGET_DATABASE_URL=<new string>
   python scripts/copy_database.py --dry-run
   ```

   It prints every table with its row count and refuses if the revisions differ or the target has data.
5. **Cutover.** Pause the Space (Settings, Pause) and stop any local backend and worker, so nothing writes.
   Then:

   ```
   python scripts/copy_database.py
   ```

   It copies in one transaction (all or nothing), resets the ID counters, and compares the row count and an
   id checksum of every table. Exit code 0 means every table matches.
6. **Switch the app and measure before trusting it.** Set the three Hugging Face secrets, unpause the
   Space, wait for it to restart, then:

   ```
   curl "https://ujjwaljain16-fuze-backend.hf.space/health/readiness?timing=1"
   ```

   `database_round_trip_ms` should be **under ~10**. If it is still ~200, the region guess was wrong:
   go to step 10 and try another region.
7. **Google sign-in.** In the new project: Authentication, Providers, Google: paste the same Client ID and
   secret. Authentication, URL configuration: same Site URL and redirect URLs as the old project, and
   "Confirm email" on. In Google Cloud Console, add `https://<ref>.supabase.co/auth/v1/callback` to the
   OAuth client's authorized redirect URIs.
8. **Frontend.** Set `VITE_SUPABASE_URL` (and `VITE_SUPABASE_ANON_KEY` if the project uses it) in Vercel and
   redeploy.
9. **Everything else that holds the old URL:** the GitHub Actions secrets above (the nightly backup, the
   weekly restore drill and the keep-alive all use them), and the local `.env`. Then run the
   "Database backup" workflow once and check it is green.
10. **Verify and roll back if needed.** Run `python scripts/bench_live.py --ask 0 --no-ramp` and compare with
    `docs/perf/`. Sign in with Google and with a password, save a bookmark, run a search. **Rollback** takes
    a minute: put the old `DATABASE_URL` (and Supabase values) back in the Space secrets. The old project is
    never modified by any step, so it stays a working fallback.
11. **Retire the old project** after a week of normal use: download a final backup first, then delete it.
    Until then leave it alone (it pauses itself after a week of inactivity).

## Expected result

Database round trip 215 ms to under 10 ms. Semantic search (measured 3.0 s p50 before any change):
about 1.5 s after the code change alone, and about 0.5 s with the database in the same region.
The measured numbers go in `docs/perf/`.
