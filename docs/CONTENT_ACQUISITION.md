# Content acquisition tiers

How the backend gets a bookmarked page's text without running a browser on our servers.
Hugging Face flagged the Space twice for browser automation (Camoufox/Playwright), so the
image stays browser-free (see [`RE_ENABLE_ON_NEW_HOST.md`](RE_ENABLE_ON_NEW_HOST.md)).
The pages that used to need a browser (JavaScript apps, bot-protected and login-walled sites)
are recovered by the tiers below instead.

Code: `backend/scrapers/acquisition_engine.py` (the loop), `decision_engine.py` (when to
escalate), `fetch_policy.py` (which tiers are enabled), `source_adapters.py`,
`fetchers/reader_fetcher.py`, `fetchers/archive_fetcher.py`.

## Order

| # | Tier | Strategy stored | Runs when | Who sees the URL |
|---|---|---|---|---|
| 0 | Extension page capture | (separate work) | The user saves from the browser extension, which sends the text the browser already rendered | Nobody new |
| 1 | Official adapters | `API:<site>` | The URL belongs to a site with a documented public endpoint | That site |
| 2 | Our HTTP fetch | `HTTP` | Always, after the SSRF check, robots.txt and the per-domain rate limit | That site |
| 3 | Remote reader | `READER` | Our fetch was thin, a hydration shell, a challenge page, or 401/403 | Jina (Elastic) |
| 4 | Wayback Machine | `ARCHIVE` | The page is gone (404/410) or blocked, and the reader didn't recover it | Internet Archive |

Before tier 1, any URL whose host resolves to a private, loopback or link-local address is
refused. Before tier 2, a robots.txt disallow ends the pipeline with outcome `disallowed`, and
that also stops tiers 3 and 4. They must not become a way around a disallow. The reader is also
asked to check robots.txt itself (`X-Robots-Txt: FuzeBot`).

### Why this order

- **Extension capture first.** The user's own browser already rendered the page, logged in
  where it has to. It costs nothing, sends nothing to a third party, and is the only tier that
  can read pages behind the user's own login.
- **Official APIs next.** The content is exact (a README, an abstract, a post's text), the
  access is documented and rate-limited, and there is no layout noise to strip.
- **Our own fetch** is free and private. It works for most of the web: server-rendered
  articles, docs and blogs.
- **The reader only when our fetch fell short.** It is a third party with rate limits, so it
  only gets the pages that need a browser.
- **The archive last.** A snapshot may be old, so it is only for pages that no longer exist or
  will not let us in. A thin live page is not sent to the archive: its snapshot is usually
  just as thin.

### Decision rules (`DecisionEngine`)

For a page that was fetched:

| Result | Reader left | Only archive left | Nothing left |
|---|---|---|---|
| Score ≥ 70 | ACCEPT | ACCEPT | ACCEPT |
| Challenge page | ESCALATE → READER | ESCALATE → ARCHIVE | FAIL (`blocked`) |
| Hydration shell (< 100 words) | ESCALATE → READER | as below | as below |
| > 50 words | ACCEPT (best effort) | ACCEPT | ACCEPT |
| ≤ 50 words | ESCALATE → READER | FAIL | FAIL |

For a fetch that produced no page:

| Failure | Next |
|---|---|
| 401/403, or a 403/503 whose body is a bot challenge | READER, then ARCHIVE |
| 404/410 | ARCHIVE (the reader can't render a deleted page) |
| 5xx, 429, timeout, connection error | none: retried later by RQ |

With every escalation tier disabled the plan is `["HTTP"]` and each decision, outcome and
retry flag is the same as before the tiers existed.

### Outcomes and retries

- An accepted tier → `ok`. If no tier is accepted, the best page seen is kept: a page that is
  not a challenge comes first, then the one with the most words. A thin page is stored as
  `ok`, as before. A challenge page is stored as `blocked`.
- No page at all → `failed`. Our fetch's status decides whether it is retryable (no answer,
  5xx, 429), as before.
- **A reader timeout, its 5xx or its 429, or our own reader ceiling, makes the result
  retryable**: a later attempt may get through. A reader refusal (bad key, the target's 4xx,
  a robots.txt refusal) does not.
- Archive trouble never makes a result retryable: a page that is gone stays gone.

## Tier details

### Official adapters (`source_adapters.py`)

Documented, keyless endpoints only:

| Site | Endpoint | Gets |
|---|---|---|
| GitHub | REST API | Repo description and README, or the issue/PR body |
| arXiv | Atom API | Title, abstract, authors |
| Wikipedia | MediaWiki API | Plain-text extract |
| Stack Exchange | API 2.3 | Question and top 3 answers |
| dev.to | Forem API | Article markdown |
| Hacker News | Firebase API | Item text; follows link posts to the article |
| YouTube | `youtube.com/oembed` | Title, channel, thumbnail. The description comes from the watch page's JSON-LD `VideoObject` or its description meta tag, only if robots.txt allows `/watch` (it does today) |
| Reddit | `<post>.json` | Post text, top comments, link-post target |
| Reddit (fallback) | `reddit.com/oembed` | Title, author, subreddit. Reddit has answered unauthenticated `.json` with 403 since mid-2026 (confirmed by the smoke run) |
| Medium | `medium.com/feed/@user`, `/feed/<publication>` | Full HTML of the author's or publication's latest stories. Older stories fall through |
| X/Twitter | `publish.twitter.com/oembed` | Post text, author, date (`dnt=true`, `omit_script=true`) |

Any adapter error, or a reply in an unexpected shape, falls through to tier 2.

### Remote reader (`fetchers/reader_fetcher.py`)

**Service:** [Jina Reader](https://jina.ai/reader/), `https://r.jina.ai/<url>`. Jina AI was
acquired by Elastic in October 2025, and its data processing now falls under Elastic's terms
([jina.ai/legal](https://jina.ai/legal)).

Limits and terms, checked October 2026 on the pricing page and live response headers:

- Without a key: **20 requests/minute per IP** (`x-ratelimit-limit: 20, 20;w=60`). Free.
- With a free key (`READER_API_KEY`): about 500 RPM for the Reader. New keys include 10M free
  tokens, and billing is by output tokens. Failed requests are not charged.
- Cache: repeat requests within minutes get a cached copy. We send `X-No-Cache: true`. An
  uncached probe of `example.com` returned someone else's planted "Test Document" from the
  shared cache.
- `DNT: 1` asks the service not to cache or log the result.
- Jina says it does not train on API inputs or outputs, and that callers are responsible for
  the terms of the sites they read.
- Some domains are blocked for anonymous use after abuse (for example `httpbin.org`, HTTP 403
  `AbuseAlleviationError`). A key lifts that.

**Why Jina:** it renders JavaScript remotely and returns clean markdown with the page's
title, metadata and the target's HTTP status. It works with no key, has headers for
cache-off, do-not-track and robots compliance, and its reader is open source
(github.com/jina-ai/reader), so `READER_BASE_URL` can point at a self-hosted copy later.
Alternatives considered: Firecrawl and ScrapingBee need a key and have small free quotas.
Cloudflare Browser Rendering needs an account and a Worker. Self-hosting a renderer puts a
browser back on our infrastructure, which is exactly what HF banned.

**Default: on** (`ENABLE_READER_FALLBACK=true`). The service receives a public URL that the
user asked us to fetch, and nothing else: no user id, notes, cookies or headers of theirs. On
HF it is the only way to read these pages at all. Guards:

- only URLs that passed `is_safe_url` (never internal addresses), checked again in the fetcher;
- never a URL with credentials, or with a query parameter that looks like a secret (`token`,
  `key`, `code`, `sig`, `session`, `X-Amz-*`, ...): `is_shareable_with_third_party`;
- the fragment is stripped;
- robots.txt is checked by us first, then by the service for our bot name;
- strict timeout (`READER_TIMEOUT_SECONDS`, default 20 s), the same 10 MB cap as our fetch,
  no redirects followed from the service;
- its own circuit breaker (`reader_service`), so an outage doesn't count against the
  bookmarked site;
- one shared ceiling for all workers, under the service's limit (`READER_RPM`, default
  15/min without a key, 300 with one).

Turn it off with `ENABLE_READER_FALLBACK=false` if no third party may see bookmark URLs.

**On HF, use a key.** Without one the limit is per egress IP, and Spaces share theirs.

### Wayback Machine (`fetchers/archive_fetcher.py`)

- Lookup: `https://archive.org/wayback/available?url=<url>` returns the most recent capture.
  Only captures archived with status 200 on `web.archive.org` are used.
- Fetch: `https://web.archive.org/web/<timestamp>id_/<url>` returns the page as archived,
  without the toolbar or rewritten links. It goes through `safe_http` with the 10 MB cap.
  Timeouts are 15 s for the lookup and 15 s for the snapshot.
- The document records `provider_raw_payload["archive"] = {source, snapshot_url, timestamp,
  archived_at}`, and `field_provenance["body"] = "ARCHIVE"`, so the UI can say "from the
  Internet Archive, captured <date>".
- Free with no key. The Internet Archive publishes no rate limit for the availability API, so
  it is used only for pages that are already gone or blocked. Its answers are sometimes slow,
  and it sometimes reports no snapshot for a page it does hold.
- `ENABLE_ARCHIVE_FALLBACK` (default on). archive.org receives the URL only, under the same
  shareability guard as the reader.

## Cost

| Tier | Cost | Limit |
|---|---|---|
| Extension capture | None | None |
| Adapters | None (keyless) | Per API: GitHub 60/h unauthenticated, Stack Exchange 300/day per IP, others generous |
| HTTP | Our egress | Our per-domain limiter: 5 requests per 10 s |
| Reader | Free without a key; free key with 10M tokens; then paid per token | 20 RPM per IP without a key |
| Archive | None | Unpublished: low volume only |

## Which sites each tier helps

Measured with `backend/scripts/smoke_acquisition_tiers.py` on 2026-10-12, run from a home
connection:

| URL | HTTP | Reader | Archive | Engine result |
|---|---|---|---|---|
| excalidraw.com (JS app) | 0 words, hydration shell | 55 words | snapshot | `ok` via READER |
| npmjs.com/package/react | 403 challenge | 146 words | none | `ok` via READER |
| instagram.com/nasa (login wall) | 0 words | robots.txt disallows | robots.txt disallows | `disallowed` |
| youtube.com/watch | 0 words | target 401 | none | `ok` via API:youtube |
| x.com/.../status/20 | 104 words, mostly login prompts | robots.txt disallows | robots.txt disallows | `ok` via API:twitter |
| reddit.com/r/.../comments | 0 words | robots.txt disallows | robots.txt disallows | `ok` via API:reddit (oEmbed) |
| medium.com/@netflixtechblog | 403 challenge or reset | 200 on one run, 403 on the next | none | `failed` or `blocked` (Medium is flaky for both) |
| MDN page removed in 2021 | 404 | target 404 | 2021 snapshot | `ok` via ARCHIVE, 339 words |
| python.org made-up path | 404 | target 404 | none | `failed`, not retryable |

In short:

- **Reader:** client-rendered apps and docs, Cloudflare-style challenges (npm and similar),
  and sites that 403 unknown bots.
- **Adapters:** YouTube, X, Reddit and Medium, where the page is an app or disallows bots but
  a public embed or feed endpoint exists.
- **Archive:** deleted pages, renamed docs and dead blogs.
- **Nothing here:** pages behind the user's own login (Instagram, private Notion and the
  like). Only extension capture can read those.

## Running the smoke test

```bash
cd backend
python scripts/smoke_acquisition_tiers.py                 # the default URL set
python scripts/smoke_acquisition_tiers.py https://...     # your own URLs
python scripts/smoke_acquisition_tiers.py --verbose ...   # with pipeline logs
```

It uses the network, so it is not part of pytest. In the suite, `tests/conftest.py` turns both
tiers off. `tests/test_acquisition_tiers.py`, `tests/test_source_adapters.py` and the
decision-engine tests turn them on with every call mocked.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `ENABLE_READER_FALLBACK` | `true` | Tier 3 on or off |
| `READER_API_KEY` | unset | Jina key: higher limits, no anonymous blocks |
| `READER_TIMEOUT_SECONDS` | `20` | Per-request timeout |
| `READER_RPM` | 15, or 300 with a key | Our shared ceiling |
| `READER_BASE_URL` | `https://r.jina.ai/` | A self-hosted reader (must be a public address) |
| `ENABLE_ARCHIVE_FALLBACK` | `true` | Tier 4 on or off |

## On a host that allows browsers

These tiers stay useful: they are cheaper than a browser, and the reader keeps working when a
headless browser gets fingerprinted. Put a browser tier (STEALTH/DYNAMIC, see
[`RE_ENABLE_ON_NEW_HOST.md`](RE_ENABLE_ON_NEW_HOST.md)) between HTTP and READER, so the reader only gets what our own
browser could not render.

## Sites that forbid automated reading (LinkedIn)

Some sites tell every crawler to stay out. `linkedin.com/robots.txt` says `User-agent: * Disallow: /` (apart from
LinkedIn's own bot), and a `lnkd.in` short link redirects to that file. Fuze honours robots.txt, and a disallow
stops every tier (see Order above), so a LinkedIn link, short or long, is stored with `scrape_status = DISALLOWED`
and no page text. Most LinkedIn posts are also behind a login, which no server-side fetch could pass anyway.

What works: tier 0. Open the post in your browser and save it with the extension while you are looking at it; the
extension sends the text your own browser has rendered, signed in, and nothing third-party sees the URL. A page that
publishes its item as structured data (schema.org JSON-LD, which LinkedIn posts do) is sent as that item alone,
without the replies and interface around it (extension 1.1.1, `lib/capture.js`: a social post always; an article's
`articleBody` only when it is nearly as long as the page, so an excerpt never replaces the real article). Or paste
the text into the bookmark's notes, which are embedded and searched like page text.

The bookmark list says so on the bookmark itself (the `scrape_status` field of `GET /api/bookmarks` feeds a note
under the title) instead of leaving a bare "Untitled" entry.

