#!/usr/bin/env python3
"""
Setup script for Gemini API key
"""

import os
import sys

def setup_gemini():
    """Setup Gemini API key"""
    print("🔧 Setting up Gemini API Key")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"✅ Found existing .env file")
        
        # Check if GEMINI_API_KEY is already set
        with open(env_file, 'r') as f:
            content = f.read()
            if 'GEMINI_API_KEY=' in content:
                print("✅ GEMINI_API_KEY is already configured")
                return True
    else:
        print(f"📝 Creating new .env file")
    
    print("\n📋 To use Gemini enhanced recommendations, you need a Gemini API key:")
    print("1. Go to https://makersuite.google.com/app/apikey")
    print("2. Create a new API key")
    print("3. Copy the API key")
    
    api_key = input("\n🔑 Enter your Gemini API key (or press Enter to skip): ").strip()
    
    if not api_key:
        print("⚠️  Skipping Gemini setup. Enhanced recommendations will not be available.")
        return False
    
    # Create or update .env file
    env_content = f"""# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/fuze_db

# Flask Configuration
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
FLASK_ENV=development
FLASK_DEBUG=True

# Environment Settings
FLASK_ENV=development

# Security Settings
HTTPS_ENABLED=False
CSRF_ENABLED=False

# CORS Origins
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Gemini AI Configuration
GEMINI_API_KEY={api_key}

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_TABLE=saved_content
"""
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"✅ Created {env_file} with Gemini API key")
    print("🔄 Please restart your Flask application for changes to take effect")
    
    return True

def test_gemini_setup():
    """Test if Gemini is working after setup"""
    print("\n🧪 Testing Gemini Setup")
    print("=" * 30)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key or api_key == 'your-gemini-api-key-here':
        print("❌ GEMINI_API_KEY not properly configured")
        return False
    
    print("✅ GEMINI_API_KEY is configured")
    
    # Test Gemini analyzer
    try:
        from gemini_utils import GeminiAnalyzer
        analyzer = GeminiAnalyzer()
        print("✅ GeminiAnalyzer initialized successfully")
        
        # Test a simple analysis
        result = analyzer.analyze_bookmark_content(
            title="Test",
            description="Test description",
            content="Test content",
            url=""
        )
        
        if result and isinstance(result, dict):
            print("✅ Gemini API is working correctly")
            return True
        else:
            print("❌ Gemini API returned invalid response")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Gemini: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Gemini Setup Script")
    print("=" * 50)
    
    success = setup_gemini()
    
    if success:
        print("\n🔍 Testing setup...")
        test_success = test_gemini_setup()
        
        if test_success:
            print("\n🎉 Gemini setup completed successfully!")
            print("✨ You can now use Gemini enhanced recommendations")
        else:
            print("\n⚠️  Setup completed but testing failed")
            print("🔧 Please check your API key and try again")
    else:
        print("\n⚠️  Setup skipped")
        print("🔧 You can run this script again later to set up Gemini") 