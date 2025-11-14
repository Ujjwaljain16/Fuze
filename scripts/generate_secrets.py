#!/usr/bin/env python3
"""
Generate secure secret keys for production deployment
"""

import secrets
import sys

def generate_secret_key():
    """Generate a secure random secret key"""
    return secrets.token_urlsafe(32)

def main():
    print("=" * 60)
    print("🔐 Secret Key Generator for Production")
    print("=" * 60)
    print()
    
    secret_key = generate_secret_key()
    jwt_secret_key = generate_secret_key()
    
    print("Copy these to your production environment variables:")
    print()
    print(f"SECRET_KEY={secret_key}")
    print(f"JWT_SECRET_KEY={jwt_secret_key}")
    print()
    print("=" * 60)
    print("⚠️  IMPORTANT: Keep these keys secure!")
    print("   - Never commit them to git")
    print("   - Store them in your hosting platform's environment variables")
    print("   - Use different keys for each environment")
    print("=" * 60)

if __name__ == "__main__":
    main()


