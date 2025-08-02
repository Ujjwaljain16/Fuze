#!/usr/bin/env python3
"""
HTTPS Setup Script for Fuze Application
This script helps set up SSL certificates for development and production.
"""

import os
import subprocess
import sys
from pathlib import Path

def generate_self_signed_cert():
    """Generate a self-signed certificate for development"""
    print("🔐 Generating self-signed certificate for development...")
    
    # Create certs directory if it doesn't exist
    certs_dir = Path("certs")
    certs_dir.mkdir(exist_ok=True)
    
    cert_path = certs_dir / "cert.pem"
    key_path = certs_dir / "key.pem"
    
    # Generate self-signed certificate
    cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:4096", "-keyout", str(key_path),
        "-out", str(cert_path), "-days", "365", "-nodes",
        "-subj", "/C=US/ST=State/L=City/O=Organization/CN=localhost"
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Self-signed certificate generated:")
        print(f"   Certificate: {cert_path}")
        print(f"   Private Key: {key_path}")
        
        # Update .env file
        update_env_file(str(cert_path), str(key_path))
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to generate certificate: {e}")
        print("Make sure OpenSSL is installed on your system.")
        return False
    except FileNotFoundError:
        print("❌ OpenSSL not found. Please install OpenSSL:")
        print("   Ubuntu/Debian: sudo apt-get install openssl")
        print("   macOS: brew install openssl")
        print("   Windows: Download from https://slproweb.com/products/Win32OpenSSL.html")
        return False

def update_env_file(cert_path, key_path):
    """Update .env file with certificate paths"""
    env_file = Path(".env")
    
    if env_file.exists():
        # Read existing content
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Update or add certificate paths
        lines = content.split('\n')
        updated_lines = []
        cert_added = False
        key_added = False
        
        for line in lines:
            if line.startswith('SSL_CERT_PATH='):
                updated_lines.append(f'SSL_CERT_PATH={cert_path}')
                cert_added = True
            elif line.startswith('SSL_KEY_PATH='):
                updated_lines.append(f'SSL_KEY_PATH={key_path}')
                key_added = True
            else:
                updated_lines.append(line)
        
        # Add if not found
        if not cert_added:
            updated_lines.append(f'SSL_CERT_PATH={cert_path}')
        if not key_added:
            updated_lines.append(f'SSL_KEY_PATH={key_path}')
        
        # Write back
        with open(env_file, 'w') as f:
            f.write('\n'.join(updated_lines))
        
        print("✅ Updated .env file with certificate paths")
    else:
        print("⚠️  .env file not found. Please add these lines to your .env file:")
        print(f"SSL_CERT_PATH={cert_path}")
        print(f"SSL_KEY_PATH={key_path}")

def setup_production_ssl():
    """Guide for setting up production SSL certificates"""
    print("🌐 Production SSL Certificate Setup Guide:")
    print("\n1. Get SSL Certificate:")
    print("   - Use Let's Encrypt (free): https://letsencrypt.org/")
    print("   - Or purchase from a certificate authority")
    print("\n2. Certificate Types:")
    print("   - Domain Validation (DV): Basic security")
    print("   - Organization Validation (OV): Medium security")
    print("   - Extended Validation (EV): Highest security")
    print("\n3. Let's Encrypt Setup:")
    print("   sudo apt-get install certbot")
    print("   sudo certbot certonly --standalone -d yourdomain.com")
    print("\n4. Certificate Locations:")
    print("   Certificate: /etc/letsencrypt/live/yourdomain.com/fullchain.pem")
    print("   Private Key: /etc/letsencrypt/live/yourdomain.com/privkey.pem")
    print("\n5. Update .env file:")
    print("   SSL_CERT_PATH=/etc/letsencrypt/live/yourdomain.com/fullchain.pem")
    print("   SSL_KEY_PATH=/etc/letsencrypt/live/yourdomain.com/privkey.pem")

def check_ssl_requirements():
    """Check if SSL requirements are met"""
    print("🔍 Checking SSL requirements...")
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        return False
    
    with open(env_file, 'r') as f:
        content = f.read()
    
    required_vars = ['HTTPS_ENABLED', 'SSL_CERT_PATH', 'SSL_KEY_PATH']
    missing_vars = []
    
    for var in required_vars:
        if f'{var}=' not in content:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    # Check if certificate files exist
    for line in content.split('\n'):
        if line.startswith('SSL_CERT_PATH='):
            cert_path = line.split('=')[1].strip()
            if not Path(cert_path).exists():
                print(f"❌ Certificate file not found: {cert_path}")
                return False
        elif line.startswith('SSL_KEY_PATH='):
            key_path = line.split('=')[1].strip()
            if not Path(key_path).exists():
                print(f"❌ Private key file not found: {key_path}")
                return False
    
    print("✅ SSL requirements met")
    return True

def main():
    print("🔐 Fuze HTTPS Setup Script")
    print("=" * 40)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python setup_https.py dev     # Setup development HTTPS")
        print("  python setup_https.py prod    # Show production setup guide")
        print("  python setup_https.py check   # Check SSL requirements")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'dev':
        generate_self_signed_cert()
    elif command == 'prod':
        setup_production_ssl()
    elif command == 'check':
        check_ssl_requirements()
    else:
        print(f"❌ Unknown command: {command}")
        print("Use: dev, prod, or check")

if __name__ == "__main__":
    main() 