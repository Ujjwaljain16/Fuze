# Documentation

Complete documentation for Fuze - Intelligent Bookmark Manager.

## 📚 Documentation Index

### Core Documentation

- **[Architecture](ARCHITECTURE.md)** - Complete scalable system architecture
  - System overview and layers
  - Database architecture (PostgreSQL + pgvector)
  - Caching architecture (multi-layer)
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
  - Backend optimizations (model caching, request deduplication)
  - Frontend optimizations (debouncing, batching, caching)
  - Database optimizations (indexing, connection pooling)
  - Multi-layer caching strategy
  - Performance metrics and improvements

- **[Testing](TESTING.md)** - Complete testing guide
  - Backend tests (Pytest)
  - Frontend tests (Vitest)
  - E2E tests (Playwright)
  - Test structure and examples
  - Coverage goals
  - Troubleshooting

### Additional Documentation

- **[Scraping Integration Guide](SCRAPLING_INTEGRATION_GUIDE.md)** - Web scraping integration
- **[Deployment Guide](../docs/DEPLOYMENT_GUIDE.md)** - Production deployment (if exists)
- **[Analysis Caching System](../docs/ANALYSIS_CACHING_SYSTEM.md)** - Caching system details (if exists)

## 🚀 Quick Links

### For Developers
- Start with [Architecture](ARCHITECTURE.md) for system overview
- Check [API Architecture](API_ARCHITECTURE.md) for endpoint details
- Review [Testing](TESTING.md) for test setup

### For Users
- See [User Flows](USERFLOW.md) for feature walkthroughs

### For DevOps
- Review [Architecture](ARCHITECTURE.md) for deployment
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
└── SCRAPLING_INTEGRATION_GUIDE.md  # Scraping integration
```

## 🔄 Documentation Status

| Document | Status | Last Updated |
|----------|--------|--------------|
| Architecture | ✅ Complete | 2024 |
| API Architecture | ✅ Complete | 2024 |
| User Flows | ✅ Complete | 2024 |
| Optimizations | ✅ Complete | 2024 |
| Testing | ✅ Complete | 2024 |
| Scraping Guide | ✅ Complete | 2024 |

## 📝 Contributing

When adding new documentation:
1. Create markdown file in `docs/` directory
2. Update this README with link and description
3. Follow existing documentation style
4. Include code examples where relevant
5. Add diagrams using Mermaid syntax

---

*Last Updated: 2024*
