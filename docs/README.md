# Documentation

Documentation for Fuze, an intelligent bookmark manager.

## Index

### Architecture and design

- **[Architecture](ARCHITECTURE.md)**: what runs where, the database, caching, background processing, ML/AI, and scaling
- **[API Architecture](API_ARCHITECTURE.md)**: endpoints by blueprint, authentication, error format and rate limits
- **[Recommendations](RECOMMENDATIONS.md)**: how saved items are chosen for a project, task, subtask or free-text query
- **[Architecture decision records](adr/README.md)**: index of the decision records in [`adr/`](adr/)
- **[Content Acquisition](CONTENT_ACQUISITION.md)**: how pages are fetched without a browser (adapters, HTTP, remote reader, Wayback Machine)
- **[API Key Revocation](API_KEY_REVOCATION.md)**: how a deleted user API key stops working immediately despite caching
- **[User Flows](USERFLOW.md)**: user journeys and system flows

### Running and deploying

- **[Deployment](DEPLOYMENT.md)**: platform comparison and deployment steps, environment variables, workers and the frontend connection
- **[Operations](OPERATIONS.md)**: repository secrets, backups and the restore drill, migrations, pipeline health, and Redis command budget
- **[Region move](REGION_MOVE.md)**: moving the database next to the backend to cut per-query latency (not carried out)
- **[Re-enabling features on a new host](RE_ENABLE_ON_NEW_HOST.md)**: what was removed only because of Hugging Face and how to restore it
- **[Performance](perf/README.md)**: measurements and the raw benchmark results in [`perf/`](perf/)
- **[Optimizations](OPTIMIZATIONS.md)**: performance changes and what was measured for each

### Development

- **[Testing](TESTING.md)**: backend, frontend and extension tests, the Postgres lane, the smoke test and CI
- **[PWA](PWA.md)**: manifest, service worker, share target and testing
- **[Supabase Google OAuth](SUPABASE_GOOGLE_OAUTH.md)**: configuring "Sign in with Google"

The self-hosted deployment files (Caddy and Docker Compose) are documented in [`../deploy/README.md`](../deploy/README.md).

## Where to start

- Developers: [Architecture](ARCHITECTURE.md), then [API Architecture](API_ARCHITECTURE.md) and [Testing](TESTING.md)
- Operators: [Deployment](DEPLOYMENT.md), then [Operations](OPERATIONS.md)

## Layout

```
docs/
├── README.md                    # This index
├── ARCHITECTURE.md              # System architecture
├── API_ARCHITECTURE.md          # API reference
├── API_KEY_REVOCATION.md        # User API key revocation
├── CONTENT_ACQUISITION.md       # Page fetching tiers
├── DEPLOYMENT.md                # Deployment guide
├── OPERATIONS.md                # Backups, restore, migrations, pipeline health
├── OPTIMIZATIONS.md             # Performance optimizations
├── PWA.md                       # PWA guide
├── RECOMMENDATIONS.md           # Recommendation engine
├── REGION_MOVE.md               # Database region move plan
├── RE_ENABLE_ON_NEW_HOST.md     # Features removed for Hugging Face
├── SUPABASE_GOOGLE_OAUTH.md     # Google sign-in setup
├── TESTING.md                   # Testing guide
├── USERFLOW.md                  # User flows
├── adr/                         # Architecture decision records
└── perf/                        # Benchmark results
```

## Contributing

When adding documentation:
1. Create the markdown file in `docs/`
2. Add it to this index with one line describing it
3. Verify every claim against the code; link to the code rather than restating it
4. Use Mermaid for diagrams
