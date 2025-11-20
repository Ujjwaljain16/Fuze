#!/usr/bin/env python3
"""
Debug script to check what's stored in the database for user API keys
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def debug_api_key_storage():
    """Debug API key storage and retrieval"""
    try:
        import flask
        from models import db, User
        from services.multi_user_api_manager import api_manager

        # Setup Flask context
        app = flask.Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://localhost/fuze')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(app)

        with app.app_context():
            user_id = 8

            print("🔍 DEBUG: Checking user API key storage")
            print("=" * 50)

            # Check database directly
            user = db.session.query(User).filter_by(id=user_id).first()
            if user:
                print(f"✅ Found user {user_id} in database")
                print(f"User metadata: {user.user_metadata}")

                if user.user_metadata and 'api_key' in user.user_metadata:
                    api_key_info = user.user_metadata['api_key']
                    print(f"API key info in database: {api_key_info}")

                    # Try to decrypt the key
                    decrypted = api_manager.decrypt_api_key(api_key_info.get('encrypted', ''))
                    if decrypted:
                        print(f"✅ Successfully decrypted API key from database")
                        print(f"Decrypted key preview: {decrypted[:20]}...")
                        print(f"Full key starts with: {decrypted[:12]}...")
                    else:
                        print("❌ Failed to decrypt API key from database")
                else:
                    print("❌ No API key found in user metadata")
            else:
                print(f"❌ User {user_id} not found in database")

            print("\n" + "=" * 50)

            # Check what get_user_api_key returns
            print("🔍 DEBUG: Testing get_user_api_key function")
            retrieved_key = api_manager.get_user_api_key(user_id)
            if retrieved_key:
                print(f"✅ Retrieved key from get_user_api_key: {retrieved_key[:20]}...")
                print(f"Retrieved key starts with: {retrieved_key[:12]}...")
            else:
                print("❌ get_user_api_key returned None")

            # Check cache
            print(f"\nCache has user {user_id}: {user_id in api_manager.user_api_keys}")

            # Check default key
            default_key = os.environ.get('GEMINI_API_KEY', '')
            if default_key:
                print(f"Default key starts with: {default_key[:12]}...")
            else:
                print("No default key found")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_api_key_storage()

