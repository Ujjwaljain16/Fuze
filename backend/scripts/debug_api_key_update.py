#!/usr/bin/env python3
"""
Debug script to test API key update process step by step
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def debug_api_key_update():
    """Debug the API key update process"""
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
            new_api_key = 'AIzaSyAYElAOJ-cnuwL4CphagM5SSXWkNu4d88w'

            print("🔍 DEBUG: Testing API key update process")
            print("=" * 50)

            # Check current state
            user = db.session.query(User).filter_by(id=user_id).first()
            if user and user.user_metadata and 'api_key' in user.user_metadata:
                current_key_info = user.user_metadata['api_key']
                print(f"Current API key in database: {current_key_info.get('name', 'Unknown')}")
                current_decrypted = api_manager.decrypt_api_key(current_key_info.get('encrypted', ''))
                if current_decrypted:
                    print(f"Current decrypted key starts with: {current_decrypted[:12]}...")
                else:
                    print("Failed to decrypt current key")
            else:
                print("No current API key found")

            print("\n" + "=" * 30)
            print("Testing add_user_api_key function...")

            # Test the add_user_api_key function directly
            success = api_manager.add_user_api_key(user_id, new_api_key, 'Debug Test Key')

            print(f"add_user_api_key returned: {success}")

            if success:
                # Check if it was actually saved
                db.session.refresh(user)  # Refresh the user object
                updated_user = db.session.query(User).filter_by(id=user_id).first()

                if updated_user and updated_user.user_metadata and 'api_key' in updated_user.user_metadata:
                    updated_key_info = updated_user.user_metadata['api_key']
                    print(f"Updated API key in database: {updated_key_info.get('name', 'Unknown')}")
                    updated_decrypted = api_manager.decrypt_api_key(updated_key_info.get('encrypted', ''))
                    if updated_decrypted:
                        print(f"Updated decrypted key starts with: {updated_decrypted[:12]}...")
                        if updated_decrypted == new_api_key:
                            print("✅ Key was successfully updated in database!")
                        else:
                            print("❌ Key in database doesn't match what we tried to save")
                            print(f"Expected: {new_api_key[:12]}...")
                            print(f"Got:      {updated_decrypted[:12]}...")
                    else:
                        print("❌ Failed to decrypt updated key")
                else:
                    print("❌ No API key found after update attempt")
            else:
                print("❌ add_user_api_key function failed")

            # Test retrieval
            print("\n" + "=" * 30)
            print("Testing key retrieval...")
            retrieved_key = api_manager.get_user_api_key(user_id)
            if retrieved_key:
                print(f"Retrieved key starts with: {retrieved_key[:12]}...")
                if retrieved_key == new_api_key:
                    print("✅ Retrieved key matches the new key!")
                else:
                    print("❌ Retrieved key doesn't match the new key")
            else:
                print("❌ Failed to retrieve key")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_api_key_update()

