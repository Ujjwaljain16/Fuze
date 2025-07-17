# Fuze Backend Endpoints Summary

This document provides a comprehensive overview of all backend endpoints that support the frontend JSX files.

## ✅ Working Endpoints

### Authentication (`/api/auth`)
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login

### Profile Management (`/api`)
- `GET /api/profile` - Get user profile
- `PUT /api/profile` - Update user profile
- `PUT /api/users/{user_id}` - Update user (compatibility endpoint)
- `PUT /api/users/{user_id}/password` - Change password

### Bookmarks (`/api/bookmarks`)
- `GET /api/bookmarks` - List bookmarks with search and filtering
- `POST /api/bookmarks` - Create new bookmark
- `DELETE /api/bookmarks/{bookmark_id}` - Delete bookmark
- `DELETE /api/bookmarks/url/{url}` - Delete bookmark by URL
- `POST /api/bookmarks/import` - Bulk import bookmarks
- `POST /api/extract-url` - Extract content from URL

### Projects (`/api/projects`)
- `GET /api/projects` - List user projects
- `POST /api/projects` - Create new project
- `GET /api/projects/{project_id}` - Get specific project
- `PUT /api/projects/{project_id}` - Update project
- `DELETE /api/projects/{project_id}` - Delete project
- `GET /api/projects/{user_id}` - Get projects for specific user

### Recommendations (`/api/recommendations`)
- `GET /api/recommendations/general` - Get general recommendations
- `GET /api/recommendations/project/{project_id}` - Get project-specific recommendations
- `GET /api/recommendations/task/{task_id}` - Get task-specific recommendations
- `POST /api/recommendations/feedback` - Submit recommendation feedback

### Search (`/api/search`)
- `GET /api/search/text?q={query}` - Text-based search
- `POST /api/search/semantic` - Semantic search

### Tasks (`/api/tasks`)
- `POST /api/tasks` - Create new task
- `GET /api/tasks/project/{project_id}` - Get tasks for project

### Feedback (`/api/feedback`)
- `POST /api/feedback` - Submit feedback

### System
- `GET /api/health` - Health check endpoint

## Frontend JSX Files and Their Endpoints

### 1. Login.jsx
- `POST /api/auth/login` ✅

### 2. Register.jsx
- `POST /api/auth/register` ✅

### 3. Dashboard.jsx
- `GET /api/bookmarks?per_page=5` ✅
- `GET /api/projects` ✅
- `GET /api/recommendations/general` ✅
- `POST /api/bookmarks` ✅

### 4. Profile.jsx
- `PUT /api/users/{user_id}` ✅
- `PUT /api/users/{user_id}/password` ✅

### 5. Bookmarks.jsx
- `GET /api/bookmarks` (with search/filter params) ✅
- `DELETE /api/bookmarks/{bookmark_id}` ✅

### 6. Projects.jsx
- `GET /api/projects` ✅
- `POST /api/projects` ✅
- `PUT /api/projects/{project_id}` ✅
- `DELETE /api/projects/{project_id}` ✅

### 7. ProjectDetail.jsx
- `GET /api/projects/{project_id}` ✅
- `GET /api/recommendations/project/{project_id}` ✅
- `POST /api/bookmarks` ✅
- `POST /api/recommendations/feedback` ✅

### 8. Recommendations.jsx
- `GET /api/recommendations/general` ✅
- `GET /api/recommendations/project/{project_id}` ✅
- `POST /api/recommendations/feedback` ✅
- `POST /api/bookmarks` ✅

### 9. SaveContent.jsx
- `GET /api/projects` ✅
- `POST /api/extract-url` ✅
- `POST /api/bookmarks` ✅

## Recent Fixes Applied

### 1. Profile Endpoints
- **Issue**: Frontend was calling `/api/users/{user_id}` but backend had `/api/profile`
- **Fix**: Added compatibility endpoints in `blueprints/profile.py`
- **Added**: 
  - `PUT /api/users/{user_id}` - Update user profile
  - `PUT /api/users/{user_id}/password` - Change password

### 2. Extract URL Endpoint
- **Issue**: SaveContent.jsx was calling `/api/extract-url` which didn't exist
- **Fix**: Added endpoint to `blueprints/bookmarks.py`
- **Added**: `POST /api/extract-url` - Extract content from URL

### 3. Bookmarks Search and Filtering
- **Issue**: Bookmarks.jsx expected search and category filtering
- **Fix**: Enhanced `GET /api/bookmarks` endpoint
- **Added**: Support for `search` and `category` query parameters

### 4. AuthContext User Data
- **Issue**: AuthContext wasn't fetching user data after login
- **Fix**: Added `fetchUser()` function and updated login flow
- **Added**: Automatic user data fetching after login

### 5. Profile Field Mapping
- **Issue**: Backend used `interests` but frontend expected `technology_interests`
- **Fix**: Updated profile endpoints to use correct field names
- **Fixed**: Field mapping between frontend and backend

## Database Schema Compatibility

All endpoints are compatible with the current database schema:

```python
class User(Base):
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    technology_interests = Column(TEXT)
    created_at = Column(DateTime, default=func.now())

class SavedContent(Base):
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    url = Column(TEXT, nullable=False)
    title = Column(String(200), nullable=False)
    notes = Column(TEXT)  # Maps to 'description' in API
    category = Column(String(100))
    # ... other fields

class Project(Base):
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(TEXT)
    technologies = Column(TEXT)
    # ... other fields
```

## Testing

Run the comprehensive test script to verify all endpoints:

```bash
python test_all_endpoints.py
```

This will test all endpoints and provide a detailed report of their status.

## Security Features

- JWT authentication required for all endpoints except auth
- User authorization checks (users can only access their own data)
- Input validation and sanitization
- Error handling with appropriate HTTP status codes

## Error Handling

All endpoints include proper error handling:
- 400: Bad Request (invalid input)
- 401: Unauthorized (missing/invalid token)
- 403: Forbidden (user not authorized)
- 404: Not Found (resource doesn't exist)
- 500: Internal Server Error (server issues)

## CORS Configuration

CORS is enabled for all origins in development mode to support the frontend running on a different port. 