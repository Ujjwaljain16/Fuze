#!/usr/bin/env python3
"""
Re-encrypt every stored Gemini API key with the current encryption key
(API_KEY_ENCRYPTION_KEY when set, else the SECRET_KEY-derived key).

Run after setting API_KEY_ENCRYPTION_KEY and before rotating SECRET_KEY, with the
same environment the app uses. Keys are otherwise moved only when next used.
Safe to re-run: keys already on the current key are left alone.

Usage (from backend/):
    python scripts/reencrypt_api_keys.py
"""

import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv()


def main():
    from run_production import create_app
    from services.multi_user_api_manager import MultiUserAPIManager

    app = create_app()
    with app.app_context():
        counts = MultiUserAPIManager().reencrypt_all_stored_keys()
    print(f"already current: {counts['current']}, re-encrypted: {counts['reencrypted']}, "
          f"undecryptable: {counts['undecryptable']}")
    if counts['undecryptable']:
        print("Undecryptable keys were encrypted with a key this environment doesn't have; "
              "those users must re-enter them.")


if __name__ == "__main__":
    main()
