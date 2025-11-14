# Fuze - Intelligent Bookmark Manager

A powerful, intelligent bookmark management system with semantic search, content extraction, and Chrome extension integration.

## 🚀 Features

### Core Features
- **Smart Bookmark Management**: Save and organize web content with intelligent categorization
- **Semantic Search**: Find bookmarks using natural language queries
- **Content Extraction**: Automatically extract and analyze webpage content
- **User Authentication**: Secure JWT-based authentication system
- **Project Organization**: Group bookmarks by projects and tasks
- **Recommendations**: AI-powered content recommendations based on your interests
- **Feedback System**: Rate and provide feedback on saved content

### Chrome Extension Integration
- **Fuze Web Clipper**: One-click bookmarking from any webpage
- **Automatic Sync**: Sync Chrome bookmarks with Fuze automatically
- **Bulk Import**: Import all existing Chrome bookmarks
- **Context Menu**: Right-click to save links directly to Fuze
- **Real-time Notifications**: Get feedback on all operations
- **Smart Categorization**: Organize bookmarks by categories and tags

## 🏗️ Architecture

### Backend (Flask + PostgreSQL)
- **Modular Blueprint Architecture**: Clean, maintainable code structure
- **Supabase Integration**: PostgreSQL database with pgvector for embeddings
- **JWT Authentication**: Secure token-based authentication
- **Content Extraction**: Automatic webpage content analysis
- **Semantic Embeddings**: Vector-based similarity search

### Chrome Extension
- **Manifest V3**: Modern Chrome extension architecture
- **Background Service Worker**: Handles bookmark events and API communication
- **Popup Interface**: User-friendly configuration and bookmark management
- **Context Menu Integration**: Right-click functionality
- **Auto-sync**: Real-time Chrome bookmark synchronization

## 📁 Project Structure

```
fuze/
├── backend/
│   ├── run_production.py           # Main Flask application (dev & production)
│   ├── wsgi.py                     # WSGI entry point for Gunicorn
├── models.py                       # Database models and relationships
├── config.py                       # Configuration settings
├── requirements.txt                # Python dependencies
├── init_db.py                      # Database initialization script
├── .gitignore                      # Git ignore rules
├── README.md                       # This file
├── blueprints/                     # Flask blueprints (modular routes)
│   ├── auth.py                     # Authentication endpoints
│   ├── bookmarks.py                # Bookmark management
│   ├── projects.py                 # Project management
│   ├── tasks.py                    # Task management
│   ├── recommendations.py          # AI recommendations
│   ├── feedback.py                 # User feedback system
│   ├── profile.py                  # User profile management
│   └── search.py                   # Search functionality
└── BookmarkExtension/              # Chrome extension
    ├── MANIFEST.JSON               # Extension manifest
    ├── background.js               # Background service worker
    ├── popup/                      # Extension popup interface
    │   ├── popup.html             # Popup HTML
    │   ├── popup.js               # Popup JavaScript
    │   └── popup.css              # Popup styling
    ├── icons/                      # Extension icons
    └── README.md                   # Extension documentation
```

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.8+
- PostgreSQL with pgvector extension
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
   Create a `.env` file with:
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/fuze_db
   SECRET_KEY=your-secret-key-here
   JWT_SECRET_KEY=your-jwt-secret-key-here
   ```

5. **Initialize database**
   ```bash
   python init_db.py
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

### Chrome Extension Setup

1. **Load the extension**
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked" and select the `BookmarkExtension` folder

2. **Configure the extension**
   - Click the Fuze Web Clipper extension icon
   - Go to Settings
   - Enter your Fuze API URL (e.g., `http://localhost:5000`)
   - Enter your email/username and password
   - Click "Login to Fuze"

## 🧪 Testing

A comprehensive test suite will be developed in the `tests/` directory. For now, you can test the API endpoints using:

- Health check: `GET /api/health`
- Authentication endpoints: `POST /api/auth/register`, `POST /api/auth/login`
- Bookmark endpoints: `POST /api/bookmarks`, `GET /api/bookmarks`
- Chrome extension integration via the extension popup interface

## 📚 API Documentation

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login

### Bookmarks
- `POST /api/bookmarks` - Save bookmark
- `GET /api/bookmarks` - List user bookmarks
- `DELETE /api/bookmarks/{id}` - Delete bookmark
- `POST /api/bookmarks/import` - Bulk import bookmarks

### Projects
- `POST /api/projects` - Create project
- `GET /api/projects` - List user projects
- `PUT /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project

### Search
- `POST /api/search/semantic` - Semantic search
- `GET /api/search` - Text search

### Health Check
- `GET /api/health` - System health status

## 🔧 Configuration

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Flask secret key
- `JWT_SECRET_KEY`: JWT token secret

### Extension Settings
- API URL configuration
- Auto-sync preferences
- Authentication tokens

## 🚀 Deployment

### Backend Deployment
1. Set up PostgreSQL with pgvector extension
2. Configure environment variables
3. Run database migrations
4. Deploy Flask application

### Extension Distribution
1. Package the extension for Chrome Web Store
2. Or distribute as unpacked extension for development

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting sections in documentation (`SETUP_INSTRUCTIONS.md`, `SECURITY_SETUP.md`)
2. Review the API documentation above
3. Check browser console for extension errors
4. Verify backend server status and logs (`production.log`)
5. Check `REPOSITORY_STRUCTURE.md` for project organization details 