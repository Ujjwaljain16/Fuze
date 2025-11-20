#!/usr/bin/env python3
"""
Check if user's API key is working in the content analysis context
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def check_api_key():
    """Check the user's API key in the proper context"""
    try:
        import flask
        from models import db
        from services.multi_user_api_manager import api_manager
        from utils.gemini_utils import GeminiAnalyzer

        # Setup Flask context
        app = flask.Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://localhost/fuze')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(app)

        with app.app_context():
            user_id = 8

            # Get API key (force refresh is handled internally)
            api_key = api_manager.get_user_api_key(user_id)
            if not api_key:
                print("❌ No API key found for user")
                return

            print(f"✅ Retrieved API key for user {user_id}")
            print(f"Key length: {len(api_key)}")
            print(f"Key preview: {api_key[:20]}...")

            # Test the API key
            analyzer = GeminiAnalyzer(api_key=api_key)
            test_result = analyzer._make_gemini_request("Hello")

            if test_result:
                print("✅ API key works in Flask context!")
                print(f"Response: {test_result[:50]}...")
            else:
                print("❌ API key test failed in Flask context")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_api_key()
