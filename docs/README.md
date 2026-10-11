# Documentation

Complete documentation for Fuze - Intelligent Bookmark Manager.

## 📚 Documentation Index

### Core Documentation

- **[Architecture](ARCHITECTURE.md)** - Complete scalable system architecture
  - System overview and layers
  - Database architecture (PostgreSQL + pgvector)
  - Caching architecture (Redis)
  - Horizontal scaling strategy
  - ML/AI architecture
  - Deployment architecture

- **[API Architecture](API_ARCHITECTURE.md)** - Complete API documentation
  - All endpoints organized by blueprint
  - Request/response formats
  - Authentication (JWT)
  - Error handling
  - Rate limiting
  - Example usage

- **[User Flows](USERFLOW.md)** - User journey documentation
  - Onboarding flow
  - Bookmark saving
  - Extension import
  - Content analysis
  - Recommendation generation
  - Project-based recommendations
  - Search flows
  - Extension authentication

- **[Optimizations](OPTIMIZATIONS.md)** - Performance optimizations
  - Backend optimizations (model caching, cooperative gevent workers)
  - Frontend optimizations (debouncing, batching, caching, deduplication)
  - Database optimizations (indexing, connection pooling, timeouts)
  - Redis caching strategy
  - Performance metrics and improvements

- **[Testing](TESTING.md)** - Complete testing guide
  - Backend tests (Pytest)
  - Frontend tests (Vitest)
  - Postgres + pgvector test lane, smoke test and CI
  - Test structure and examples
  - Coverage goals
  - Troubleshooting

### Additional Documentation

- **[Deployment](DEPLOYMENT.md)** - Complete deployment guide
  - Platform comparison (Hugging Face Spaces, Railway, Fly.io)
  - Hugging Face Spaces deployment (step-by-step)
  - Environment variables setup
  - RQ worker configuration
  - Frontend-backend connection
  - Troubleshooting

- **[Operations](OPERATIONS.md)** - Running it in production
  - Backups and the monthly restore drill
  - Migrations and rollback
  - Pipeline health queries
  - Secret rotation effects

- **[Intent x Content Engine](INTENT_ENGINE_PLAN.md)** - Recommendation design and benchmark results

- **[Architecture Decision Records](adr/)** - ADR-001 to ADR-006 cover the legacy recommendation stack and are kept as history (superseded)

- **[PWA](PWA.md)** - Progressive Web App guide
  - PWA installation and features
  - Share target functionality
  - Testing guide
  - Troubleshooting


## 🚀 Quick Links

### For Developers
- Start with [Architecture](ARCHITECTURE.md) for system overview
- Check [API Architecture](API_ARCHITECTURE.md) for endpoint details
- Review [Testing](TESTING.md) for test setup

### For Users
- See [User Flows](USERFLOW.md) for feature walkthroughs

### For DevOps
- Start with [Deployment](DEPLOYMENT.md) for deployment guide
- Keep [Operations](OPERATIONS.md) at hand for backups, rollback and pipeline health
- Review [Architecture](ARCHITECTURE.md) for system design
- Check [Optimizations](OPTIMIZATIONS.md) for performance tuning

## 📖 Documentation Structure

```
docs/
├── README.md                    # This file
├── ARCHITECTURE.md             # System architecture
├── API_ARCHITECTURE.md          # API documentation
├── USERFLOW.md                  # User flows
├── OPTIMIZATIONS.md             # Performance optimizations
├── TESTING.md                   # Testing guide
├── DEPLOYMENT.md                # Deployment guide
├── OPERATIONS.md                # Backups, restore, rollback, pipeline health
├── INTENT_ENGINE_PLAN.md        # Recommendation engine design + benchmark
├── PWA.md                       # PWA guide
├── API_KEY_REVOCATION.md        # API key revocation
├── SUPABASE_GOOGLE_OAUTH.md     # Google sign-in setup
└── adr/                         # Architecture decision records
```

## 🔄 Documentation Status

| Document | Status | Last Updated |
|----------|--------|--------------|
| Architecture | ✅ Complete | 2024 |
| API Architecture | ✅ Complete | 2024 |
| User Flows | ✅ Complete | 2024 |
| Optimizations | ✅ Complete | 2024 |
| Testing | ✅ Complete | 2024 |
| Deployment | ✅ Complete | 2024 |
| PWA | ✅ Complete | 2024 |
| Operations | ✅ Complete | 2026 |

## 📝 Contributing

When adding new documentation:
1. Create markdown file in `docs/` directory
2. Update this README with link and description
3. Follow existing documentation style
4. Include code examples where relevant
5. Add diagrams using Mermaid syntax

---

*Last Updated: 2024*
