# Projects API Setup Guide

This guide ensures that the Projects functionality is properly connected to the database and backend.

## 🔧 Backend Setup

### 1. Database Migration
Run the database migration script to add the `updated_at` column to the projects table:

```bash
python update_projects_table.py
```

This script will:
- Add `updated_at` column to the projects table
- Set default values for existing records
- Create a database trigger to automatically update `updated_at` on row modifications

### 2. Verify Backend Endpoints
The following endpoints are now available in the Projects API:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects` | Get all projects for authenticated user |
| POST | `/api/projects` | Create a new project |
| GET | `/api/projects/{id}` | Get a specific project |
| PUT | `/api/projects/{id}` | Update a specific project |
| DELETE | `/api/projects/{id}` | Delete a specific project |

### 3. Test Backend API
Run the comprehensive test script to verify all endpoints:

```bash
python test_projects_api.py
```

This will test:
- ✅ Authentication
- ✅ Create project
- ✅ Read projects (list and individual)
- ✅ Update project
- ✅ Delete project
- ✅ Error handling

## 🎨 Frontend Setup

### 1. API Service Configuration
The frontend API service (`frontend/src/services/api.js`) is properly configured with:
- ✅ Base URL: `http://localhost:5000`
- ✅ JWT token authentication
- ✅ Automatic token injection in headers
- ✅ Error handling for 401 responses

### 2. Projects Component
The Projects component (`frontend/src/pages/Projects.jsx`) includes:
- ✅ Complete CRUD operations
- ✅ Glassmorphic modals for create/edit/delete
- ✅ Proper error handling
- ✅ Loading states
- ✅ Responsive design

### 3. Styling
The Projects styling (`frontend/src/pages/projects-styles.css`) provides:
- ✅ Glassmorphism effects
- ✅ Smooth animations
- ✅ Modern UI components
- ✅ Responsive design
- ✅ Delete confirmation modal

## 🗄️ Database Schema

### Projects Table Structure
```sql
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title VARCHAR(100) NOT NULL,
    description TEXT,
    technologies TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Automatic Triggers
- `updated_at` is automatically set to `CURRENT_TIMESTAMP` on row creation
- `updated_at` is automatically updated to `CURRENT_TIMESTAMP` on row modification

## 🔐 Security Features

### Authentication
- ✅ JWT token required for all endpoints
- ✅ User can only access their own projects
- ✅ Proper error handling for unauthorized access

### Validation
- ✅ Title and description are required
- ✅ Input sanitization and validation
- ✅ SQL injection protection via SQLAlchemy ORM

## 🚀 Usage Examples

### Create Project
```javascript
const response = await api.post('/api/projects', {
  title: 'My New Project',
  description: 'Project description',
  technologies: 'React, Node.js, PostgreSQL'
});
```

### Update Project
```javascript
const response = await api.put(`/api/projects/${projectId}`, {
  title: 'Updated Project Title',
  description: 'Updated description',
  technologies: 'React, Node.js, PostgreSQL, Docker'
});
```

### Delete Project
```javascript
const response = await api.delete(`/api/projects/${projectId}`);
```

## 🧪 Testing

### Manual Testing
1. Start the backend server: `python app.py`
2. Start the frontend: `npm start` (in frontend directory)
3. Login to the application
4. Navigate to Projects page
5. Test create, edit, and delete operations

### Automated Testing
Run the test script: `python test_projects_api.py`

## 🔍 Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check `DATABASE_URL` environment variable
   - Ensure PostgreSQL is running
   - Verify database exists

2. **Authentication Error**
   - Check JWT token in localStorage
   - Verify token hasn't expired
   - Ensure user exists in database

3. **CORS Error**
   - Verify CORS is enabled in Flask app
   - Check frontend URL matches backend CORS settings

4. **Missing updated_at Column**
   - Run the migration script: `python update_projects_table.py`
   - Check database schema

### Debug Commands
```bash
# Check database connection
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.session.execute('SELECT 1')"

# Check API health
curl http://localhost:5000/api/health

# Test authentication
curl -X POST http://localhost:5000/api/auth/login -H "Content-Type: application/json" -d '{"username":"testuser","password":"testpass"}'
```

## 📊 API Response Format

### Success Response (Create/Update)
```json
{
  "message": "Project created successfully",
  "project": {
    "id": 1,
    "title": "My Project",
    "description": "Project description",
    "technologies": "React, Node.js",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
}
```

### Error Response
```json
{
  "message": "Project title is required and must be a non-empty string"
}
```

## ✅ Verification Checklist

- [ ] Database migration completed
- [ ] Backend server running on port 5000
- [ ] Frontend running on port 3000
- [ ] User authentication working
- [ ] Create project functionality working
- [ ] Edit project functionality working
- [ ] Delete project functionality working
- [ ] All API tests passing
- [ ] Frontend modals displaying correctly
- [ ] Responsive design working
- [ ] Error handling working

## 🎉 Success!

Once all items in the checklist are completed, your Projects functionality is fully connected and operational! 