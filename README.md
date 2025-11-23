# 🔖 Fuze - AI-Powered Intelligent Bookmark Manager

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.1.1-green?logo=flask)
![React](https://img.shields.io/badge/React-18-blue?logo=react)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)
![License](https://img.shields.io/badge/License-MIT-yellow)

**Transform your bookmarks into an intelligent knowledge base with AI-powered semantic search and personalized recommendations.**

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
- **Project-Based Workflow**: Organize bookmarks by projects and tasks
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

- **[Architecture](docs/ARCHITECTURE.md)** - System architecture and design
- **[API Documentation](docs/API_ARCHITECTURE.md)** - Complete API reference
- **[User Flows](docs/USERFLOW.md)** - Feature walkthroughs
- **[Testing Guide](docs/TESTING.md)** - Testing setup and examples
- **[Optimizations](docs/OPTIMIZATIONS.md)** - Performance optimizations

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
- **Deployment**: Hugging Face Spaces, Render, Vercel
- **Containerization**: Docker
- **CI/CD**: GitHub Actions

---

## 📡 API Documentation

### Authentication

```http
POST /api/auth/register
POST /api/auth/login
POST /api/auth/refresh
POST /api/auth/logout
```

### Bookmarks

```http
GET    /api/bookmarks              # List bookmarks (with pagination)
POST   /api/bookmarks              # Save new bookmark
DELETE /api/bookmarks/:id          # Delete bookmark
POST   /api/bookmarks/import       # Bulk import bookmarks
GET    /api/bookmarks/dashboard/stats  # Get statistics
```

### Projects & Tasks

```http
GET    /api/projects               # List projects
POST   /api/projects               # Create project
GET    /api/projects/:id           # Get project details
PUT    /api/projects/:id           # Update project
DELETE /api/projects/:id           # Delete project

POST   /api/tasks                  # Create task
GET    /api/tasks/project/:id      # Get tasks for project
POST   /api/tasks/ai-breakdown     # AI-powered task breakdown
```

### Recommendations

```http
POST /api/recommendations/unified-orchestrator  # Get AI recommendations
POST /api/recommendations/project/:id           # Project-specific recommendations
GET  /api/recommendations/status                # Engine status
```

### Search

```http
POST /api/search/semantic  # Semantic search
GET  /api/search/text      # Text search
```

For complete API documentation, see [API_ARCHITECTURE.md](docs/API_ARCHITECTURE.md).

---

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest --cov=. --cov-report=html -v

# Frontend tests
cd frontend
npm test
```

**Test Coverage**: 56+ tests covering authentication, bookmarks, projects, recommendations, search, and more.

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

## 🚢 Deployment

### Hugging Face Spaces

The backend is configured for Hugging Face Spaces deployment. See [HF_SPACES_DEPLOYMENT.md](docs/HUGGINGFACE_SPACES_DEPLOYMENT.md).

### Render / Railway

1. Connect your GitHub repository
2. Set environment variables
3. Deploy!

### Vercel (Frontend)

```bash
cd frontend
vercel deploy
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Sentence Transformers](https://www.sbert.net/) for semantic embeddings
- [pgvector](https://github.com/pgvector/pgvector) for vector similarity search
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [React](https://react.dev/) for the frontend framework

---

<div align="center">

**Made with ❤️ by [Ujjwal Jain](https://github.com/Ujjwaljain16)**

⭐ Star this repo if you find it helpful!

</div>
