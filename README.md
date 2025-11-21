# Fuze - Intelligent Bookmark Manager

> AI-powered bookmark management with semantic search, intelligent recommendations, and seamless Chrome extension integration.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18+-61dafb.svg)](https://reactjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🎯 Overview

Fuze is a next-generation bookmark management system that goes beyond simple link storage. It intelligently extracts, analyzes, and organizes web content using AI-powered semantic search, personalized recommendations, and advanced content understanding.

### What Makes Fuze Different?

- **🧠 AI-Powered Intelligence**: Semantic search understands context, not just keywords
- **📊 Content Analysis**: Automatic extraction and analysis of webpage content using advanced scraping
- **🎯 Smart Recommendations**: Personalized content suggestions based on your projects, tasks, and learning goals
- **🔍 Multi-Modal Search**: Text, semantic, and hybrid search capabilities
- **📁 Project Organization**: Organize bookmarks by projects and tasks with intelligent context
- **⚡ High Performance**: Multi-layer caching, optimized queries, and background processing
- **🔌 Chrome Extension**: Seamless one-click bookmarking from any webpage

---

## ✨ Key Features

### Core Functionality
- **Smart Bookmarking**: Save bookmarks with automatic content extraction and metadata
- **Semantic Search**: Find content using natural language queries powered by vector embeddings
- **Content Analysis**: Background AI analysis of saved content (key concepts, difficulty, topics)
- **Project Management**: Organize bookmarks into projects with tasks and subtasks
- **User Feedback**: Rate and provide feedback on saved content to improve recommendations

### AI & Recommendations
- **Unified Recommendation Engine**: Multi-strategy recommendation system combining:
  - Semantic similarity matching
  - Intent analysis
  - Project-based recommendations
  - Task-specific suggestions
  - Quality and difficulty scoring
- **Personalized Learning Paths**: Recommendations adapt to your skill level and goals
- **Context-Aware Suggestions**: Get recommendations based on current projects or tasks

### Chrome Extension
- **One-Click Saving**: Save bookmarks directly from any webpage
- **Bulk Import**: Import all existing Chrome bookmarks with automatic deduplication
- **Auto-Sync**: Real-time synchronization between Chrome and Fuze
- **Context Menu**: Right-click to save links instantly
- **Progress Tracking**: Real-time import and analysis progress updates

### Performance & Scalability
- **Multi-Layer Caching**: Redis + in-memory caching for 70-80% faster responses
- **Background Processing**: Non-blocking content analysis and scraping
- **Optimized Database**: Comprehensive indexing with pgvector for fast similarity search
- **Request Deduplication**: Automatic deduplication of concurrent requests
- **Connection Pooling**: Efficient database connection management

---

## 🛠️ Tech Stack

### Backend
- **Framework**: Flask (Python 3.8+)
- **Database**: PostgreSQL 14+ with pgvector extension
- **Caching**: Redis
- **AI/ML**: 
  - Google Gemini AI (content analysis, recommendations)
  - Sentence Transformers (MiniLM-L6-v2 for embeddings)
- **Web Scraping**: Scrapling (enhanced content extraction)
- **Authentication**: JWT (Flask-JWT-Extended)
- **Deployment**: Gunicorn + WSGI

### Frontend
- **Framework**: React 18+ with Vite
- **Styling**: Tailwind CSS
- **State Management**: React Context API
- **Routing**: React Router
- **HTTP Client**: Axios
- **PWA**: Service Worker for offline support

### Chrome Extension
- **Manifest**: V3
- **Architecture**: Background service worker + popup interface
- **Storage**: Chrome Storage API

### DevOps & Tools
- **Testing**: Pytest (backend), Vitest + React Testing Library (frontend), Playwright (E2E)
- **Code Quality**: ESLint, Pylint
- **Database Migrations**: SQLAlchemy ORM

---

## 🏗️ Architecture Overview

Fuze is built as a scalable, multi-tenant system with the following architecture:

### Current Deployment
```
┌─────────────────┐
│   Web App       │  Chrome Extension
│   (React)       │  (Manifest V3)
└────────┬────────┘
         │
    ┌────▼──────────────────┐
    │  Flask App             │
    │  (Gunicorn, 1 worker)  │
    └────┬──────────────────┘
         │
    ┌────▼──────────────────┐
    │  Redis Cache           │
    │  PostgreSQL + pgvector │
    └───────────────────────┘
```

### Scalable Architecture (Future)
The system is designed to scale horizontally with:
- **Load Balancer**: Nginx/Cloudflare for request distribution
- **Multiple Workers**: Multiple Gunicorn instances across servers
- **Database Replicas**: Read replicas for improved performance
- **Redis Cluster**: High-availability caching

### Key Architectural Principles
- **Stateless Design**: Ready for horizontal scaling with multiple workers
- **Multi-Layer Caching**: Redis + in-memory for optimal performance
- **Background Processing**: Async content analysis
- **User Isolation**: Complete data separation per user
- **Graceful Degradation**: System works even when components fail

For detailed architecture documentation including scaling strategies, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL 14+ with pgvector extension
- Redis (optional, for caching)
- Node.js 18+ (for frontend)
- Chrome browser (for extension)

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fuze
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   Create a `.env` file in the `backend/` directory:
   ```env
   DATABASE_URL=postgresql://username:password@localhost:5432/fuze_db
   SECRET_KEY=your-secret-key-here
   JWT_SECRET_KEY=your-jwt-secret-key-here
   REDIS_URL=redis://localhost:6379/0  # Optional
   GEMINI_API_KEY=your-gemini-api-key  # Optional, users can add their own
   ```

5. **Initialize database**
   ```bash
   cd backend
   python init_db.py
   python utils/database_indexes.py  # Create performance indexes
   ```

6. **Run the backend**
   ```bash
   python run_production.py
   ```
   Backend will be available at `http://localhost:5000`

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure API URL**
   Update `src/services/api.js` with your backend URL if different from default.

4. **Run development server**
   ```bash
   npm run dev
   ```
   Frontend will be available at `http://localhost:5173`

### Chrome Extension Setup

1. **Load the extension**
   - Open Chrome and navigate to `chrome://extensions/`
   - Enable "Developer mode" (toggle in top-right)
   - Click "Load unpacked"
   - Select the `BookmarkExtension` folder

2. **Configure the extension**
   - Click the Fuze extension icon in Chrome toolbar
   - Enter your backend API URL (e.g., `http://localhost:5000`)
   - Login with your Fuze account credentials
   - Start bookmarking!

For detailed setup instructions, see [docs/TESTING.md](docs/TESTING.md).

---

## 📁 Project Structure

```
fuze/
├── backend/                    # Flask backend application
│   ├── blueprints/            # Modular route handlers
│   │   ├── auth.py            # Authentication endpoints
│   │   ├── bookmarks.py       # Bookmark management
│   │   ├── recommendations.py # AI recommendations
│   │   ├── projects.py        # Project management
│   │   └── ...
│   ├── ml/                    # Machine learning components
│   │   ├── unified_recommendation_orchestrator.py
│   │   ├── intent_analysis_engine.py
│   │   └── ...
│   ├── scrapers/             # Web scraping modules
│   │   └── scrapling_enhanced_scraper.py
│   ├── services/             # Background services
│   ├── utils/                # Utility functions
│   ├── models.py             # Database models
│   └── run_production.py     # Main application entry
│
├── frontend/                  # React frontend application
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Page components
│   │   ├── contexts/         # React contexts
│   │   └── services/         # API services
│   └── ...
│
├── BookmarkExtension/         # Chrome extension
│   ├── background.js         # Service worker
│   ├── popup/                # Extension popup UI
│   └── MANIFEST.JSON         # Extension manifest
│
└── docs/                     # Comprehensive documentation
    ├── ARCHITECTURE.md       # System architecture
    ├── API_ARCHITECTURE.md   # API documentation
    ├── USERFLOW.md           # User journey flows
    ├── OPTIMIZATIONS.md      # Performance optimizations
    └── TESTING.md            # Testing guide
```

---

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Architecture](docs/ARCHITECTURE.md)** - Complete system architecture, scaling strategies, and deployment
- **[API Architecture](docs/API_ARCHITECTURE.md)** - All API endpoints, request/response formats, authentication
- **[User Flows](docs/USERFLOW.md)** - Detailed user journey diagrams and workflows
- **[Optimizations](docs/OPTIMIZATIONS.md)** - Performance optimizations and improvements
- **[Testing Guide](docs/TESTING.md)** - Backend, frontend, and E2E testing instructions

---

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

### E2E Tests
```bash
cd frontend
npm run test:e2e
```

For detailed testing documentation, see [docs/TESTING.md](docs/TESTING.md).

---

## 🔌 API Overview

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `GET /api/auth/verify` - Verify JWT token

### Bookmarks
- `POST /api/bookmarks` - Save bookmark
- `GET /api/bookmarks` - List user bookmarks
- `DELETE /api/bookmarks/{id}` - Delete bookmark
- `POST /api/bookmarks/import` - Bulk import bookmarks

### Recommendations
- `POST /api/recommendations/unified-orchestrator` - Get AI recommendations
- `POST /api/recommendations/project-based` - Project-specific recommendations

### Search
- `POST /api/search/semantic` - Semantic search
- `GET /api/search` - Text search

For complete API documentation, see [docs/API_ARCHITECTURE.md](docs/API_ARCHITECTURE.md).

---

## 🎯 Key Capabilities

### What Fuze Can Do

✅ **Intelligent Content Extraction**: Advanced web scraping extracts clean, structured content from any webpage  
✅ **Semantic Understanding**: Vector embeddings enable natural language search  
✅ **AI-Powered Analysis**: Automatic content analysis using Gemini AI (key concepts, difficulty, topics)  
✅ **Personalized Recommendations**: Multi-strategy recommendation engine adapts to your needs  
✅ **Project Organization**: Organize bookmarks by projects with tasks and context  
✅ **Background Processing**: Non-blocking analysis and scraping operations  
✅ **High Performance**: Multi-layer caching and optimized database queries  
✅ **Chrome Integration**: Seamless bookmarking from browser with auto-sync  

### What Fuze Will Do (Future)

🔮 **Mobile Apps**: Native iOS and Android applications  
🔮 **Collaboration**: Share projects and bookmarks with teams  
🔮 **Advanced Analytics**: Learning progress tracking and insights  
🔮 **Browser Extensions**: Support for Firefox, Edge, Safari  
🔮 **API Access**: Public API for third-party integrations  

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

Please read our contributing guidelines and code of conduct before submitting PRs.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🆘 Support

- **Documentation**: Check the [docs/](docs/) directory for detailed guides
- **Issues**: Open an issue on GitHub for bugs or feature requests
- **Questions**: Check existing issues or create a new discussion

---

## 🙏 Acknowledgments

- **Google Gemini AI** for content analysis capabilities
- **Sentence Transformers** for semantic embeddings
- **Scrapling** for robust web scraping
- **PostgreSQL + pgvector** for vector similarity search
- **React & Flask** communities for excellent frameworks

---

**Built with ❤️ for intelligent content management**
