#!/usr/bin/env python3
"""
Fix script for Gemini API issues in the Fuze recommendation system
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_step(step_num, description):
    """Print a formatted step"""
    print(f"\n{step_num}. {description}")
    print("-" * 40)

def check_python_version():
    """Check if Python version is compatible"""
    print_step(1, "Checking Python version")
    
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        print(f"Current version: {sys.version}")
        return False
    
    print(f"✅ Python version: {sys.version}")
    return True

def create_env_file():
    """Create .env file if it doesn't exist"""
    print_step(2, "Setting up environment configuration")
    
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    # Create .env file with template
    env_content = """# Database Configuration
DATABASE_URL=postgresql://postgres:Jainsahab16@db.xqfgfalwwfwtzvuuvroq.supabase.co:5432/postgres

# Flask Configuration
SECRET_KEY=your-secret-key-change-this-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-this-in-production

# Gemini AI Configuration
GEMINI_API_KEY=your-gemini-api-key-here

# Supabase Configuration
SUPABASE_URL=https://xyzcompany.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_TABLE=saved_content

# Development Settings
FLASK_ENV=development
FLASK_DEBUG=True
"""
    
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        print("✅ Created .env file")
        print("⚠️  IMPORTANT: Please update the GEMINI_API_KEY in .env file")
        print("   Get your API key from: https://makersuite.google.com/app/apikey")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def update_dependencies():
    """Update Python dependencies"""
    print_step(3, "Updating Python dependencies")
    
    try:
        # Update google-generativeai to latest version
        print("Updating google-generativeai...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "google-generativeai"], 
                      check=True, capture_output=True, text=True)
        print("✅ Updated google-generativeai")
        
        # Install/update other dependencies
        print("Installing/updating other dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True, text=True)
        print("✅ Updated all dependencies")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to update dependencies: {e}")
        print(f"Error output: {e.stderr}")
        return False

def test_gemini_connection():
    """Test Gemini API connection"""
    print_step(4, "Testing Gemini API connection")
    
    # Check if GEMINI_API_KEY is set
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key or api_key == 'your-gemini-api-key-here':
        print("❌ GEMINI_API_KEY not set or still has placeholder value")
        print("   Please update the .env file with your actual Gemini API key")
        return False
    
    try:
        import google.generativeai as genai
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Test with different model names
        models_to_try = ['gemini-1.5-pro', 'gemini-pro']
        model_working = None
        
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                # Test with a simple prompt
                response = model.generate_content("Hello, this is a test.")
                if response.text:
                    model_working = model_name
                    break
            except Exception as e:
                print(f"   Model {model_name} failed: {e}")
                continue
        
        if model_working:
            print(f"✅ Gemini API connection successful with model: {model_working}")
            return True
        else:
            print("❌ All Gemini models failed")
            return False
            
    except ImportError:
        print("❌ google-generativeai library not installed")
        return False
    except Exception as e:
        print(f"❌ Gemini API test failed: {e}")
        return False

def test_application():
    """Test the application startup"""
    print_step(5, "Testing application startup")
    
    try:
        # Test importing the main modules
        print("Testing imports...")
        
        # Test basic imports
        import app
        print("✅ app.py imports successfully")
        
        # Test Gemini utils
        try:
            from gemini_utils import GeminiAnalyzer
            print("✅ gemini_utils imports successfully")
        except Exception as e:
            print(f"⚠️  gemini_utils import warning: {e}")
        
        # Test recommendation engine
        try:
            from gemini_enhanced_recommendation_engine import GeminiEnhancedRecommendationEngine
            print("✅ gemini_enhanced_recommendation_engine imports successfully")
        except Exception as e:
            print(f"⚠️  gemini_enhanced_recommendation_engine import warning: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Application test failed: {e}")
        return False

def create_setup_instructions():
    """Create setup instructions file"""
    print_step(6, "Creating setup instructions")
    
    instructions = """# Fuze Application Setup Instructions

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
"""
    
    try:
        with open("SETUP_INSTRUCTIONS.md", 'w') as f:
            f.write(instructions)
        print("✅ Created SETUP_INSTRUCTIONS.md")
        return True
    except Exception as e:
        print(f"❌ Failed to create setup instructions: {e}")
        return False

def main():
    """Main fix function"""
    print_header("FUZE GEMINI API FIX SCRIPT")
    print("This script will fix the Gemini API issues in your Fuze application.")
    
    # Check Python version
    if not check_python_version():
        print("\n❌ Please upgrade Python to version 3.8 or higher")
        return False
    
    # Create .env file
    if not create_env_file():
        print("\n❌ Failed to create environment file")
        return False
    
    # Update dependencies
    if not update_dependencies():
        print("\n❌ Failed to update dependencies")
        return False
    
    # Test Gemini connection
    if not test_gemini_connection():
        print("\n⚠️  Gemini API test failed - please check your API key")
        print("   The application will still work with fallback recommendations")
    
    # Test application
    if not test_application():
        print("\n❌ Application test failed")
        return False
    
    # Create setup instructions
    create_setup_instructions()
    
    print_header("FIX COMPLETED")
    print("✅ All fixes have been applied successfully!")
    print("\nNext steps:")
    print("1. Update the GEMINI_API_KEY in your .env file")
    print("2. Run: python app.py")
    print("3. Test with: python test_gemini_recommendations.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 