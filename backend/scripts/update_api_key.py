#!/usr/bin/env python3
"""
Update User API Key Script
Updates a user's Gemini API key in the database
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def update_api_key():
    """Update user's API key"""
    try:
        # Get API key from user
        api_key = input("Enter your new Gemini API key: ").strip()

        if not api_key:
            print("❌ No API key provided")
            return

        if not api_key.startswith('AIza') or len(api_key) < 30:
            print("❌ Invalid API key format. Gemini API keys start with 'AIza' and are longer than 30 characters.")
            return

        # Import required modules
        from models import db, User
        import flask
        from services.multi_user_api_manager import add_user_api_key

        # Setup Flask context
        app = flask.Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://localhost/fuze')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(app)

        with app.app_context():
            user_id = 8  # Your user ID
            api_key_name = 'Updated Gemini API Key'

            success = add_user_api_key(user_id, api_key, api_key_name)

            if success:
                print("✅ API key updated successfully!")
                print(f"User ID: {user_id}")
                print(f"API Key Name: {api_key_name}")
                print("\n🎉 Now you can run content analysis with your own API key!")
                print("Run: python scripts/content_analysis_script.py --user-id 8")
            else:
                print("❌ Failed to update API key")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the backend directory with virtual environment activated")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("🔑 Update Gemini API Key")
    print("=" * 40)
    update_api_key()
