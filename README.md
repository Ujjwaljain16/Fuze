# Fuze - Intelligent Bookmark & Project Management API

A powerful, AI-driven backend for managing bookmarks, projects, and tasks with semantic search and intelligent recommendations.

## 🚀 Features

- **JWT Authentication** - Secure user management
- **Project Management** - Create and organize projects with tasks
- **Smart Bookmarks** - Save URLs with automatic content extraction
- **Semantic Search** - AI-powered search across all your content
- **Intelligent Recommendations** - Get relevant content suggestions for projects
- **Feedback System** - Improve recommendations with user feedback
- **Supabase Integration** - PostgreSQL with pgvector for embeddings

## 🛠️ Tech Stack

- **Backend**: Flask, SQLAlchemy
- **Database**: PostgreSQL (Supabase) with pgvector
- **AI**: SentenceTransformers for embeddings
- **Authentication**: JWT
- **Content Extraction**: readability-lxml, BeautifulSoup

## 📋 API Endpoints

### Authentication
```
POST /api/auth/register - Register new user
POST /api/auth/login - Login user
```

### Projects
```
POST /api/projects - Create project
GET /api/projects/{user_id} - Get user projects (paginated)
```

### Tasks
```
POST /api/tasks - Create task
GET /api/tasks/project/{project_id} - Get tasks for project
```

### Bookmarks
```
POST /api/bookmarks - Save bookmark (with content extraction)
GET /api/bookmarks - List bookmarks (paginated)
DELETE /api/bookmarks/{id} - Delete bookmark
```

### Search
```
POST /api/search/semantic - Semantic search
GET /api/search/text - Text search
```

### Recommendations
```
GET /api/recommendations/project/{project_id} - Get project recommendations
GET /api/recommendations/task/{task_id} - Get task recommendations
```

### Feedback
```
POST /api/feedback - Submit feedback on recommendations
```

### Profile
```
GET /api/profile - Get user profile
PUT /api/profile - Update user interests
```

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Clone repository
git clone <your-repo>
cd fuze

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "DATABASE_URL=your-supabase-url" > .env
echo "SECRET_KEY=your-secret-key" >> .env
echo "JWT_SECRET_KEY=your-jwt-secret" >> .env
```

### 2. Setup Database
```bash
# Initialize database
python init_db.py
```

### 3. Run Application
```bash
python app.py
```

### 4. Test API
```bash
python test_api.py
```

## 📝 Usage Examples

### Register and Login
```bash
# Register
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "password123"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "password123"}'
```

### Save Bookmark
```bash
curl -X POST http://localhost:5000/api/bookmarks \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "title": "Example Article",
    "description": "A great article about AI"
  }'
```

### Semantic Search
```bash
curl -X POST http://localhost:5000/api/search/semantic \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning algorithms"}'
```

## 🔧 Configuration

### Environment Variables
- `DATABASE_URL` - Supabase PostgreSQL connection string
- `SECRET_KEY` - Flask secret key
- `JWT_SECRET_KEY` - JWT signing key

### Database Setup
1. Create Supabase project
2. Enable pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector;`
3. Update DATABASE_URL in .env

## 🏗️ Architecture

```
fuze/
├── app.py                 # Main application
├── models.py             # Database models
├── config.py             # Configuration
├── requirements.txt      # Dependencies
├── blueprints/           # Modular endpoints
│   ├── auth.py          # Authentication
│   ├── projects.py      # Project management
│   ├── tasks.py         # Task management
│   ├── bookmarks.py     # Bookmark system
│   ├── search.py        # Search functionality
│   ├── recommendations.py # AI recommendations
│   ├── feedback.py      # User feedback
│   └── profile.py       # User profiles
└── tests/               # Test files
```

## 🧪 Testing

Run the comprehensive test suite:
```bash
python test_api.py
```

## 🚀 Deployment

### Railway (Recommended)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway init
railway up
```

### Render
1. Connect GitHub repository
2. Set environment variables
3. Deploy automatically

## 📈 Future Enhancements

- [ ] Chrome extension integration
- [ ] Mobile app
- [ ] Advanced analytics
- [ ] Content summarization
- [ ] Collaborative features
- [ ] API rate limiting
- [ ] Webhook support

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

For issues and questions:
- Create GitHub issue
- Check documentation
- Review test examples 