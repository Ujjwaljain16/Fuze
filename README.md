---
title: Fuze - Intelligent Bookmark Manager
emoji: 🔖
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
app_port: 7860
sdk_version: 4.36.0
---

# Fuze - Intelligent Bookmark Manager

AI-powered bookmark management with semantic search, intelligent recommendations, and seamless Chrome extension integration.

## Features

- 🧠 **AI-Powered Intelligence**: Semantic search understands context, not just keywords
- 📊 **Content Analysis**: Automatic extraction and analysis of webpage content
- 🎯 **Smart Recommendations**: Personalized content suggestions
- 🔍 **Multi-Modal Search**: Text, semantic, and hybrid search capabilities
- 📁 **Project Organization**: Organize bookmarks by projects and tasks
- ⚡ **High Performance**: Multi-layer caching and optimized queries
- 🔌 **Chrome Extension**: Seamless one-click bookmarking
- 📱 **PWA Support**: Install as mobile app with share functionality

## Tech Stack

- **Backend**: Flask (Python 3.11)
- **Database**: PostgreSQL with pgvector
- **Caching**: Redis (Upstash)
- **ML**: Sentence Transformers (MiniLM-L6-v2)
- **Frontend**: React + Vite
- **Deployment**: Hugging Face Spaces (Docker)

## Environment Variables

Set these in Hugging Face Spaces settings:

   ```env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=rediss://your-upstash-redis-url
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=https://your-frontend.vercel.app
GEMINI_API_KEY=your-gemini-key
```

## Resources

- **CPU**: 2 vCPUs (free tier)
- **RAM**: Up to 16GB (free tier)
- **Storage**: Persistent storage available

## API Endpoints

- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `GET /api/bookmarks` - List bookmarks
- `POST /api/bookmarks` - Save bookmark
- `POST /api/recommendations/unified-orchestrator` - Get recommendations

## License

MIT License
