# Fuze - AI-Powered Intelligent Content Manager

<div align="center">

 <img src="frontend/src/assets/logo1.svg" alt="Fuze Logo" width="280" height="100" /> 

**Transform your saved scattered content into an intelligent knowledge base with AI-powered semantic search and personalized recommendations.**

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.1.1-green?logo=flask)
![React](https://img.shields.io/badge/React-18-blue?logo=react)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)
![License](https://img.shields.io/badge/License-MIT-yellow)

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [API](#-api-documentation) • [Contributing](#-contributing)

</div>

---

## ✨ Features

### 🧠 AI-Powered Intelligence
- **Semantic Search**: Find content by meaning, not just keywords
- **Smart Recommendations**: Personalized suggestions based on your projects and interests
- **Content Analysis**: Automatic extraction and analysis using Gemini AI
- **Intent Understanding**: Context-aware recommendations that understand what you're building

### 🎯 Project Organization
- **Project-Based Workflow**: Organize projects and tasks
- **Task Management**: Break down projects into actionable tasks with AI assistance
- **Contextual Recommendations**: Get relevant content suggestions for your active projects

### 🔍 Advanced Search
- **Multi-Modal Search**: Text, semantic, and hybrid search capabilities
- **Vector Similarity**: pgvector-powered semantic matching
- **Fast Queries**: Optimized database indexes for instant results

### ⚡ Performance & Reliability
- **Multi-Layer Caching**: Redis + in-memory caching for blazing-fast responses
- **Background Processing**: Async content analysis and processing
- **Connection Pooling**: Efficient database connection management
- **Production-Ready**: Comprehensive error handling and logging

### 🔌 Integrations
- **Chrome Extension**: One-click bookmarking from any webpage
- **LinkedIn Integration**: Save and analyze LinkedIn posts and articles
- **PWA Support**: Install as a mobile app with share functionality
- **Bulk Import**: Import existing bookmarks from Chrome

---
## 📸 Demo

### Landing Page
<div align="center">
<img width="1919" height="927" alt="Screenshot 2025-11-24 035836" src="https://github.com/user-attachments/assets/0ff4d2b5-3724-4913-85c0-71e18bd4fbdd" />


*Welcome to Fuze - Your intelligent content manager*

</div>

### Dashboard
<div align="center">

<img width="1920" height="1080" alt="Screenshot 2025-11-24 025912" src="https://github.com/user-attachments/assets/d35f995f-60a7-48f2-bb42-4d3ce8cedc39" />


*Overview of your bookmarks, projects, and statistics*

</div>

### Bookmarks Management
<div align="center">

<img width="1920" height="1080" alt="Screenshot 2025-11-24 035358" src="https://github.com/user-attachments/assets/6c691cba-efe6-4561-b1c2-82feed461e90" />


*Organize and search through your saved content with AI-powered semantic search*

</div>

### Projects & Tasks
<div align="center">

<img width="1920" height="1080" alt="Screenshot 2025-11-24 035415" src="https://github.com/user-attachments/assets/48d89e18-98fb-4af3-aebd-72973aa0813a" />


*Organize projects and break them down into actionable tasks*

</div>

### AI Recommendations
<div align="center">

<img width="1920" height="1080" alt="Screenshot 2025-11-24 035434" src="https://github.com/user-attachments/assets/2796a560-bc06-4308-87a6-b51a25a5cb8b" />

<img width="1920" height="1080" alt="Screenshot 2025-11-24 035000" src="https://github.com/user-attachments/assets/a72f7e0c-6fda-4933-95bc-d50e7067b9f1" />
<img width="1920" height="1080" alt="Screenshot 2025-11-24 035010" src="https://github.com/user-attachments/assets/fb66fd51-2780-430a-90e4-dee25b03ab2a" />



*Get personalized content recommendations based on your projects and interests*

</div>

### Profile & Settings
<div align="center">

<img width="1920" height="1080" alt="Screenshot 2025-11-24 035443" src="https://github.com/user-attachments/assets/341d5a7e-0458-470e-a488-cc26610f374c" />


*Manage your profile, API keys, and preferences*

</div>

---
## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (with pgvector extension)
- Redis (Upstash or local)
- Node.js 18+ (for frontend)

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/Ujjwaljain16/Fuze.git
cd Fuze

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database
cd backend
python init_db.py

# Run migrations (if any)
python utils/database_indexes.py

# Start the server
python run_production.py
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Environment Variables

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/fuze

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# AI Services
GEMINI_API_KEY=your-gemini-api-key

# Application
FLASK_ENV=development
DEBUG=true
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## 📚 Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

- **[Documentation Index](docs/README.md)** - Complete documentation overview and quick links
- **[Architecture](docs/ARCHITECTURE.md)** - System architecture and design
- **[API Documentation](docs/API_ARCHITECTURE.md)** - Complete API reference
- **[User Flows](docs/USERFLOW.md)** - Feature walkthroughs
- **[Testing Guide](docs/TESTING.md)** - Testing setup and examples
- **[Optimizations](docs/OPTIMIZATIONS.md)** - Performance optimizations
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Complete deployment instructions
- **[PWA Guide](docs/PWA.md)** - Progressive Web App features and setup
- **[Scraping Integration](docs/SCRAPLING_INTEGRATION_GUIDE.md)** - Web scraping integration guide

---

## 🛠️ Tech Stack

### Backend
- **Framework**: Flask 3.1.1
- **Database**: PostgreSQL 15 with pgvector
- **Caching**: Redis (Upstash)
- **ML/AI**: 
  - Sentence Transformers (MiniLM-L6-v2)
  - Google Gemini API
- **Task Queue**: RQ (Redis Queue)
- **Authentication**: JWT (Flask-JWT-Extended)

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: React Context + Hooks
- **PWA**: Service Worker + Web App Manifest

### Infrastructure
- **Deployment**: Hugging Face Spaces, Vercel
- **Containerization**: Docker
- **CI/CD**: GitHub Actions

---

## 🏆 Key Innovations & Achievements

### 🚀 Technical Innovations

#### **Unified Recommendation Orchestrator**
- **Multi-Engine Architecture**: Built a sophisticated orchestrator that intelligently routes between 5+ recommendation strategies (semantic similarity, content-based, collaborative, intent-based, project-contextual)
- **Intent Analysis Engine**: AI-powered intent detection that understands user goals (learning, building, researching) and adapts recommendations accordingly
- **Smart Fallback System**: Automatic fallback chain ensures recommendations always work, even when individual engines fail
- **Per-User Caching**: Cached Gemini analyzers per user with encrypted API key management, reducing API calls by 70%+

#### **Model Caching & Performance Optimization**
- **98% Faster Model Loading**: Reduced SentenceTransformer model loading from 6-7 seconds to 0.1 seconds using singleton pattern with thread-safe locking
- **Request Deduplication**: Prevents duplicate processing of identical concurrent requests, reducing database load by 50%
- **Multi-Layer Caching**: Redis + in-memory caching achieving 70-80% cache hit rate and sub-100ms API response times
- **Query Result Caching**: Intelligent TTL-based caching for expensive database queries

#### **Per-User API Key Management System**
- **Encrypted Storage**: Fernet encryption for user API keys with secure key derivation from SECRET_KEY
- **Individual Rate Limiting**: Per-user rate limits (15/min, 1500/day, 45000/month) with usage tracking
- **Automatic Fallback**: Graceful fallback to default API key when user key unavailable
- **API Key Validation**: Built-in testing and validation endpoints for user API keys

#### **Semantic Search with pgvector**
- **Vector Similarity Search**: Implemented pgvector extension for PostgreSQL enabling semantic search that understands meaning, not just keywords
- **Automatic Embeddings**: Every bookmark automatically generates embeddings using MiniLM-L6-v2 for semantic search
- **Hybrid Search**: Combines text search with vector similarity for best results

### 🎯 Unique Features

#### **Bulk Import with Real-Time Progress Tracking**
- **Redis-Based Progress**: Real-time progress updates for Chrome extension bulk imports using Redis streams
- **Optimized Deduplication**: Smart URL matching prevents duplicate bookmarks during bulk import
- **Background Processing**: Async content analysis pipeline that doesn't block user requests
- **Error Recovery**: Graceful handling of failed imports with detailed error reporting

#### **Project-Centric Knowledge Management**
- **Context-Aware Recommendations**: AI understands your active projects and suggests relevant content from your bookmarks
- **Task-Based Organization**: Break down projects into tasks with AI-powered task breakdown suggestions
- **Project-Specific Recommendations**: Get content recommendations tailored to specific project needs

#### **PWA Share Target Integration**
- **Native Mobile Experience**: Install as mobile app with share functionality from any app (LinkedIn, Twitter, browsers)
- **Automatic URL Extraction**: Intelligent URL extraction from shared text, title, and content fields
- **One-Click Bookmarking**: Save bookmarks directly from share menu without opening the app

#### **LinkedIn Specialized Scraper**
- **Enhanced Content Extraction**: Specialized scraper for LinkedIn posts with quality scoring (1-10 scale)
- **Activity URL Handling**: Handles complex LinkedIn activity URLs with encoded parameters
- **Content Analysis**: Automatic extraction of post text, author, and metadata

### 📊 Performance Achievements

- **98% Model Loading Speed Improvement**: From 6-7 seconds to 0.1 seconds
- **70-80% Cache Hit Rate**: Multi-layer caching strategy achieving high efficiency
- **50% Reduction in Duplicate Requests**: Request deduplication system
- **Sub-100ms API Response Times**: Through optimized queries and caching
- **56+ Comprehensive Tests**: Full test coverage across all major features
- **Production-Ready Architecture**: Horizontal scaling with stateless workers, connection pooling, and graceful degradation
- **Zero-Downtime Deployments**: CI/CD pipeline with automated testing and GitHub Actions workflows

---

## 🏗️ Project Structure

```
Fuze/
├── backend/                 # Flask backend
│   ├── blueprints/         # API route handlers
│   ├── ml/                 # Machine learning models
│   ├── services/           # Background services
│   ├── utils/              # Utility functions
│   ├── tests/              # Test suite
│   └── run_production.py   # Production server
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   └── utils/         # Frontend utilities
│   └── public/            # Static assets
├── BookmarkExtension/      # Chrome extension
└── docs/                  # Documentation
```

---

## 🚀 Future Enhancements

### Short Term (Q1 2025)
- [ ] **Platform Integrations**: Link with other professional and educational platforms
  - GitHub integration for code repositories and documentation
  - Medium/Dev.to for technical articles
  - YouTube for educational videos and tutorials
  - Coursera/Udemy for course content
  - Twitter/X for tech discussions and threads
  - Reddit for community discussions and resources
- [ ] **Collaborative Projects**: Share projects with team members
- [ ] **Advanced Analytics**: Usage insights and content trends
- [ ] **Browser Extension Updates**: Firefox and Edge support
- [ ] **Mobile App**: Native iOS and Android applications
- [ ] **Export/Import**: Backup and restore functionality

### Medium Term (Q2-Q3 2025)
- [ ] **AI Chat Assistant**: Conversational interface for finding content
- [ ] **Content Summarization**: Auto-generate summaries for saved content
- [ ] **Smart Collections**: AI-curated collections based on topics
- [ ] **Integration Hub**: Connect with Notion, Obsidian, and other knowledge management tools
- [ ] **Advanced Search Filters**: Date ranges, content types, relevance scores
- [ ] **Cross-Platform Sync**: Sync bookmarks across devices and platforms

### Long Term (Q4 2025+)
- [ ] **Multi-Modal Search**: Search by images, code snippets, and more
- [ ] **Learning Paths**: AI-generated learning paths from your bookmarks
- [ ] **Knowledge Graph**: Visual representation of content relationships
- [ ] **Team Workspaces**: Organization-level features for teams
- [ ] **API Marketplace**: Third-party integrations and plugins
- [ ] **Community Features**: Share collections and recommendations with the community



---

## 🙏 Acknowledgments

- [Sentence Transformers](https://www.sbert.net/) for semantic embeddings
- [pgvector](https://github.com/pgvector/pgvector) for vector similarity search
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [React](https://react.dev/) for the frontend framework

---

<div align="center">

<img src="frontend/src/assets/logo1.svg" alt="Fuze Logo" width="280" height="100" />

**Made with ❤️ by [Ujjwal Jain](https://github.com/Ujjwaljain16)**

</div>
