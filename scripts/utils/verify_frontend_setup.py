#!/usr/bin/env python3
"""
Frontend Setup Verification
Verifies that all frontend configurations and dependencies are properly set up
"""
import os
import json

def verify_frontend_setup():
    """Verify frontend setup"""
    print("🔧 Frontend Setup Verification")
    print("=" * 35)
    
    # Check if frontend directory exists
    frontend_dir = "frontend"
    if not os.path.exists(frontend_dir):
        print("❌ Frontend directory not found")
        return False
    
    print("✅ Frontend directory exists")
    
    # Check package.json
    package_json_path = os.path.join(frontend_dir, "package.json")
    if not os.path.exists(package_json_path):
        print("❌ package.json not found")
        return False
    
    print("✅ package.json exists")
    
    # Check if node_modules exists
    node_modules_path = os.path.join(frontend_dir, "node_modules")
    if not os.path.exists(node_modules_path):
        print("⚠️ node_modules not found - run 'npm install' in frontend directory")
        return False
    
    print("✅ node_modules exists")
    
    # Check API configuration
    api_js_path = os.path.join(frontend_dir, "src", "services", "api.js")
    if not os.path.exists(api_js_path):
        print("❌ api.js not found")
        return False
    
    print("✅ api.js exists")
    
    # Check Recommendations component
    recommendations_path = os.path.join(frontend_dir, "src", "pages", "Recommendations.jsx")
    if not os.path.exists(recommendations_path):
        print("❌ Recommendations.jsx not found")
        return False
    
    print("✅ Recommendations.jsx exists")
    
    # Check if backend is running
    print("\n🌐 Backend Connectivity Check")
    print("-" * 30)
    
    try:
        import requests
        response = requests.get("http://127.0.0.1:5000/api/auth/csrf-token", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running and accessible")
        else:
            print(f"⚠️ Backend responded with status: {response.status_code}")
    except Exception as e:
        print(f"❌ Backend not accessible: {e}")
        print("   Make sure to run: python run_production.py")
        return False
    
    # Check environment variables
    print("\n🔐 Environment Variables Check")
    print("-" * 30)
    
    required_env_vars = [
        "GEMINI_API_KEY",
        "JWT_SECRET_KEY",
        "DATABASE_URL"
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️ Missing environment variables: {', '.join(missing_vars)}")
        print("   Make sure these are set in your .env file")
    else:
        print("✅ All required environment variables are set")
    
    # Check Redis connection
    print("\n📦 Redis Connection Check")
    print("-" * 25)
    
    try:
        from redis_utils import redis_cache
        if redis_cache.connected:
            print("✅ Redis is connected")
        else:
            print("❌ Redis is not connected")
            print("   Make sure Redis is running")
    except Exception as e:
        print(f"❌ Redis connection error: {e}")
    
    # Frontend build check
    print("\n🏗️ Frontend Build Check")
    print("-" * 25)
    
    dist_path = os.path.join(frontend_dir, "dist")
    if os.path.exists(dist_path):
        print("✅ Frontend is built (dist folder exists)")
        print("   To rebuild: cd frontend && npm run build")
    else:
        print("⚠️ Frontend not built (dist folder missing)")
        print("   To build: cd frontend && npm run build")
    
    # Development server check
    print("\n🚀 Development Server Instructions")
    print("-" * 35)
    print("To start frontend development server:")
    print("1. cd frontend")
    print("2. npm run dev")
    print("3. Open http://localhost:5173")
    
    print("\n🔧 Backend Server Instructions")
    print("-" * 35)
    print("To start backend production server:")
    print("1. python run_production.py")
    print("2. Backend will run on http://127.0.0.1:5000")
    
    print("\n" + "=" * 35)
    print("✅ Frontend Setup Verification Complete!")
    print("=" * 35)
    
    return True

if __name__ == "__main__":
    verify_frontend_setup() 