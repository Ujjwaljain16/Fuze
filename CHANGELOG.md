# Changelog

## Unreleased

- PWA: real PNG icons (192, 512, maskable, apple-touch), so Android installs the app and lists it in the share
  sheet and iOS shows a proper home-screen icon; the service worker is no longer served as immutable for a year (a
  later `*.js` header rule was overriding it); shared links are no longer stored in the service worker's cache.
- LinkedIn posts a user saves (a share from the phone to the PWA, a pasted link) are read again: a LinkedIn adapter
  makes one plain request for the post's public page and reads its structured data. This is a deliberate, documented
  exception to the robots.txt rule, on by default, switchable with `LINKEDIN_PUBLIC_FETCH_ENABLED=false`, and
  untested from the hosted Space's address, where LinkedIn may refuse it.
- Extension 1.1.1: a post the page publishes as structured data (a LinkedIn post, for example) is captured as that
  post alone, without the replies and interface around it, so saving a LinkedIn post from the extension gives the
  same clean text a server fetch would, read from your own browser.
- A bookmark whose page could not be read now says why under its title: a site that forbids automated reading
  (LinkedIn, which also covers `lnkd.in` short links) or a failed read, and what to do (save it with the extension
  while viewing it, or paste the text into the notes). `GET /api/bookmarks` returns `scrape_status` for this.

## 1.0.0 - 2026-10-14

The first release that is documented, measured and deployed end to end: web app on Vercel, API and workers on a
Hugging Face Space, Postgres + pgvector on Supabase, Redis on Upstash, and a Manifest V3 Chrome extension.
Measurements are in [docs/perf/](docs/perf/README.md) and [backend/eval/results/](backend/eval/results/).

### Recommendations and search

- Bookmarks are split into overlapping passages (about 200 words) that are embedded and stored with the embedding
  model that produced them; a bookmark is ranked by its best passage. On BEIR SciFact (300 queries) nDCG@10 is
  0.718, and on long documents 0.504 against 0.016 for one vector per document.
- One Gemini (or OpenAI-compatible) call per bookmark produces a content profile, which is embedded as its own
  searchable row.
- The recommendation engine ranks with embeddings, MMR and an optional cross-encoder only; the earlier rule-based
  stack was removed (ADR-007).
- Results the cross-encoder does not tie to the project or task are marked `weak_match` and folded behind
  "Show N weaker matches". Order is unchanged; `RECOMMENDATION_CONFIDENCE_ENABLED=false` turns it off.
- "General" searches each of the technology interests saved on the profile on its own and interleaves the lists,
  judging every result against its own interest (one blended query matched none of the topics well: 6 of 10
  results strong against 9 of 10 per interest on a real library). "Surprise Me" searches one interest at random.
  With no interests saved a generic sentence is used.
- Feedback (helpful, not relevant, clicked) is stored with the project it was judged for, and can be exported as a
  BEIR-format evaluation set. One current rating is kept per user, bookmark and project, enforced by a unique
  index (migration 0019): rating again replaces it.

### Performance

- Semantic search: p50 3026 to 1661 ms (-45%) and p95 -47% on the live Space (1663 / 1962 ms again on the deployed
  build, `docs/perf/` run 8); SQL statements per search about 10 to 1. HNSW settings are database/role defaults (migrations 0015-0018), related details are joined into the
  passage query, and pooled connections are pinged only after sitting idle.
- Opt-in `X-Server-Timing: 1` header (total, embedding, database, statement count) and `scripts/bench_live.py`.
- Redis use fits the free Upstash plan: no RQ scheduler, one `MGET` per reconciler pass, 30-minute worker
  registration. An idle 10-minute sample read 2 commands.

### Ingestion

- Page text is recovered without a browser on the server: extension capture, official site APIs, HTTP fetch, a
  remote reader, then the Wayback Machine. Private addresses are refused and a robots.txt disallow stops every tier.
- A reconciler re-queues stuck fetches, embeddings and analyses with backoff.
- A processing job always fetches the bookmark's stored URL and refuses a bookmark that is not the job's user's.

### Security and operations

- Dependencies are hash-locked; the container runs as an unprivileged user.
- Request bodies over the limit are refused with 413; performance metrics are scoped to the caller.
- Database-writing evaluation scripts refuse any target except a throwaway local Postgres.
- Runbooks for deployment, backups and restore, the Redis budget, and a database region move
  ([docs/](docs/README.md)).

### Interface

- The dashboard counts bookmarks whose page could not be read ("Couldn't read"), so the pipeline stages add up to the
  total, and no longer shows +100% on both the total and weekly cards.
- Form labels are tied to their inputs; server messages are shown for errors the user can act on.
- The thumbs up and down on a recommendation show the saved rating and say if saving failed, and ignore clicks
  while a rating is being sent.
- Profile page: "Member Since" is fetched from the full profile when the page opens (the sign-in response does not
  carry it). The form saves username and interests with one `PUT /api/profile`, which treats your own username as
  available and checks usernames case-insensitively; the live username check no longer reports your own name, or a
  check that failed, as taken, and says when a name really is taken.

### Removed

- The earlier recommendation stack (domain model, strategy pipeline, shadow-mode rollout, ADR-001 to 006),
  unused modules, one-off scripts and 22 unused dependency pins.
- The `feedback` table and its `/api/feedback` endpoint, which nothing called and production never filled
  (`user_feedback` replaced them), and `saved_content.published_at`, which no code ever wrote (migration 0019).
  The account export no longer has a `feedback` key; `recommendation_feedback` is unchanged.

### Known limitations

- The database (Supabase, Singapore) is in a different region from the backend. Each statement costs about
  215 ms, and about 900 ms of a semantic search is still unexplained. A move is documented in
  [docs/REGION_MOVE.md](docs/REGION_MOVE.md) and deferred.
- Pages that need a login or a browser may come back with little or no text; they show as "Couldn't read".
- Single container on free tiers; horizontal scaling is designed for (stateless web workers, queues) but not tested.
- Feedback is recorded but does not change ranking.
