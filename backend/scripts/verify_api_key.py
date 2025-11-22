#!/usr/bin/env python3
"""
Verify and update API key for a user
Usage: python verify_api_key.py <user_id> <api_key>
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def main():
    if len(sys.argv) < 3:
        print("Usage: python verify_api_key.py <user_id> <api_key>")
        sys.exit(1)
    
    user_id = int(sys.argv[1])
    api_key = sys.argv[2]
    
    try:
        from run_production import app
        from services.multi_user_api_manager import add_user_api_key, get_user_api_key
        from models import db, User
        
        with app.app_context():
            from services.multi_user_api_manager import api_manager
            
            # Clear cache for this user to force reload from DB
            if user_id in api_manager.user_api_keys:
                del api_manager.user_api_keys[user_id]
                print(f"Cleared cached API key for user {user_id}")
            
            # Check current API key
            print(f"Checking current API key for user {user_id}...")
            current_key = get_user_api_key(user_id)
            
            if current_key:
                print(f"Current API key (first 10 chars): {current_key[:10]}...")
                if current_key == api_key:
                    print("API key matches! No update needed.")
                    # Still update to ensure it's fresh in cache
                    print("Refreshing cache...")
                else:
                    print("API key differs. Updating...")
            else:
                print("No API key found. Adding new one...")
            
            # Calculate expected hash for verification
            import hashlib
            expected_hash = hashlib.sha256(api_key.encode()).hexdigest()
            print(f"Expected hash (first 10): {expected_hash[:10]}...")
            
            # Add/update API key
            print(f"\nAdding/updating API key for user {user_id}...")
            success = add_user_api_key(user_id, api_key, "User API Key")
            
            # Also directly update database to ensure it's saved
            if success:
                # Get the encrypted key from api_manager to verify it was created
                if user_id in api_manager.user_api_keys:
                    stored_key_obj = api_manager.user_api_keys[user_id]
                    if hasattr(stored_key_obj, 'encrypted_key'):
                        # Directly update database to ensure it's saved
                        user_direct = db.session.query(User).filter_by(id=user_id).first()
                        if user_direct:
                            metadata = dict(user_direct.user_metadata) if user_direct.user_metadata else {}
                            metadata['api_key'] = {
                                'encrypted': stored_key_obj.encrypted_key,
                                'hash': stored_key_obj.api_key_hash,
                                'name': stored_key_obj.api_key_name,
                                'status': stored_key_obj.status.value,
                                'created_at': stored_key_obj.created_at.isoformat(),
                                'last_used': stored_key_obj.last_used.isoformat() if stored_key_obj.last_used else None
                            }
                            user_direct.user_metadata = metadata
                            # Tell SQLAlchemy that the JSON field has been modified
                            from sqlalchemy.orm.attributes import flag_modified
                            flag_modified(user_direct, 'user_metadata')
                            db.session.flush()
                            db.session.commit()
                            db.session.refresh(user_direct)
                            print("Directly updated database to ensure key is saved")
            
            if success:
                print(f"Successfully added API key for user {user_id}")
                
                # Force flush and commit to ensure database is updated
                db.session.flush()
                db.session.commit()
                
                # Force database refresh and clear cache
                from models import db, User
                # Start a new query to get fresh data
                db.session.expire_all()  # Expire all objects
                user = db.session.query(User).filter_by(id=user_id).first()
                if user:
                    # Force refresh from database
                    db.session.refresh(user)
                    print("Refreshed user object from database")
                
                # Clear cache to force reload from database
                if user_id in api_manager.user_api_keys:
                    del api_manager.user_api_keys[user_id]
                    print("Cleared in-memory cache")
                
                # Also reload all keys from database to ensure consistency
                api_manager.load_user_api_keys()
                print("Reloaded all API keys from database")
                
                # Also check database directly with a fresh query
                print("\nChecking database directly (fresh query)...")
                db.session.expire_all()
                user_check = db.session.query(User).filter_by(id=user_id).first()
                if user_check:
                    db.session.refresh(user_check)
                    if user_check.user_metadata:
                        db_api_key_info = user_check.user_metadata.get('api_key', {})
                        if db_api_key_info:
                            db_hash = db_api_key_info.get('hash', '')
                            db_encrypted = db_api_key_info.get('encrypted', '')
                            print(f"   Database has API key: {db_api_key_info.get('name', 'Unknown')}")
                            print(f"   Hash in DB (first 10): {db_hash[:10]}...")
                            print(f"   Expected hash (first 10): {expected_hash[:10]}...")
                            print(f"   Encrypted key length: {len(db_encrypted) if db_encrypted else 0}")
                            
                            # Try to decrypt and verify
                            if db_encrypted:
                                from services.multi_user_api_manager import api_manager
                                decrypted_test = api_manager.decrypt_api_key(db_encrypted)
                                if decrypted_test:
                                    test_hash = hashlib.sha256(decrypted_test.encode()).hexdigest()
                                    print(f"   Decrypted key (first 15): {decrypted_test[:15]}...")
                                    print(f"   Decrypted key hash (first 10): {test_hash[:10]}...")
                                    if test_hash == expected_hash:
                                        print("   Decryption works! Encrypted key is correct.")
                                    else:
                                        print("   Decryption gives wrong key! Encrypted value might be old.")
                            
                            if db_hash == expected_hash:
                                print("   Hash matches! Database has correct key.")
                            else:
                                print("   Hash mismatch! Database might have old key.")
                                print(f"   Full DB hash: {db_hash}")
                                print(f"   Full expected: {expected_hash}")
                
                print("\nVerifying saved API key (fresh from database)...")
                saved_key = get_user_api_key(user_id)
                if saved_key == api_key:
                    print("Verification successful! API key is correctly stored.")
                    print(f"   Key (first 15 chars): {saved_key[:15]}...")
                else:
                    print(f"Warning: Saved key doesn't match!")
                    print(f"   Expected (first 15): {api_key[:15]}...")
                    print(f"   Got (first 15): {saved_key[:15] if saved_key else 'None'}...")
                    print(f"\n   This might indicate:")
                    print(f"   1. Database still has old key (check hash above)")
                    print(f"   2. Encryption/decryption issue")
                    print(f"   3. Cache not cleared properly")
            else:
                print(f"Failed to add API key for user {user_id}")
                sys.exit(1)
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

