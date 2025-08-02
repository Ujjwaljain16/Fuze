# Fuze Application Setup Instructions

## Prerequisites
- Python 3.8+
- PostgreSQL database (or Supabase)
- Gemini AI API key

## Setup Steps

### 1. Environment Configuration
1. Copy the `.env` file and update the following variables:
   - `GEMINI_API_KEY`: Get from https://makersuite.google.com/app/apikey
   - `DATABASE_URL`: Your PostgreSQL connection string
   - `SECRET_KEY`: A secure random string for Flask
   - `JWT_SECRET_KEY`: A secure random string for JWT tokens

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize Database
```bash
python init_db.py
```

### 4. Run the Application
```bash
python app.py
```

### 5. Test the Application
```bash
python test_gemini_recommendations.py
```

## Troubleshooting

### Gemini API Issues
- Ensure GEMINI_API_KEY is set correctly
- Check if the API key has proper permissions
- Verify internet connection

### Database Issues
- Ensure PostgreSQL is running
- Check DATABASE_URL format
- Verify database permissions

### Performance Issues
- The application uses caching to improve performance
- Large bookmark collections may take time to process initially
- Consider reducing batch sizes for better performance

## API Endpoints

### Health Check
- GET /api/health

### Authentication
- POST /api/auth/register
- POST /api/auth/login

### Recommendations
- GET /api/recommendations/gemini-status
- POST /api/recommendations/gemini-enhanced
- GET /api/recommendations/gemini-enhanced-project/{project_id}

### Bookmarks
- GET /api/bookmarks
- POST /api/bookmarks
- DELETE /api/bookmarks/{id}

## Support
For issues, check the application logs and ensure all environment variables are properly configured.
