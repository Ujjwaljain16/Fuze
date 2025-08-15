#!/usr/bin/env python3
"""
Database Connection Test Script
Helps troubleshoot database connection issues
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_database_connection():
    """Test database connection and provide troubleshooting info"""
    
    print("🔍 Database Connection Test")
    print("=" * 50)
    
    # Check environment variables
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not found")
        print("💡 Please check your .env file or environment variables")
        return False
    
    print(f"✅ DATABASE_URL found: {database_url[:50]}...")
    
    # Parse database URL
    try:
        if database_url.startswith('postgresql://'):
            # Extract host from PostgreSQL URL
            parts = database_url.split('@')
            if len(parts) > 1:
                host_part = parts[1].split('/')[0]
                host = host_part.split(':')[0]
                print(f"📍 Database Host: {host}")
                
                # Test DNS resolution
                import socket
                try:
                    ip_address = socket.gethostbyname(host)
                    print(f"✅ DNS Resolution: {host} → {ip_address}")
                except socket.gaierror as e:
                    print(f"❌ DNS Resolution Failed: {e}")
                    print("💡 Troubleshooting:")
                    print("   - Check if the hostname is correct")
                    print("   - Verify network connectivity")
                    print("   - Check if VPN is required")
                    print("   - Try using IP address instead of hostname")
                    return False
            else:
                print("⚠️  Could not parse host from DATABASE_URL")
        else:
            print(f"ℹ️  Database type: {database_url.split('://')[0]}")
    
    except Exception as e:
        print(f"⚠️  Error parsing DATABASE_URL: {e}")
    
    # Test actual connection
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        # Parse the URL
        parsed = urlparse(database_url)
        
        # Extract connection parameters
        host = parsed.hostname
        port = parsed.port or 5432
        database = parsed.path[1:]  # Remove leading slash
        username = parsed.username
        password = parsed.password
        
        print(f"🔌 Testing connection to {host}:{port}/{database}")
        
        # Test connection
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password,
            connect_timeout=10
        )
        
        # Test a simple query
        cursor = conn.cursor()
        cursor.execute('SELECT version()')
        version = cursor.fetchone()
        
        print("✅ Database connection successful!")
        print(f"📊 PostgreSQL Version: {version[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except ImportError:
        print("❌ psycopg2 not installed")
        print("💡 Install with: pip install psycopg2-binary")
        return False
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("💡 Troubleshooting:")
        print("   - Check if database server is running")
        print("   - Verify credentials are correct")
        print("   - Check firewall settings")
        print("   - Verify database exists")
        print("   - Check connection limits")
        return False

def test_network_connectivity():
    """Test basic network connectivity"""
    
    print("\n🌐 Network Connectivity Test")
    print("=" * 50)
    
    # Test basic internet connectivity
    try:
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        print("✅ Basic internet connectivity: OK")
    except Exception as e:
        print(f"❌ Basic internet connectivity failed: {e}")
        return False
    
    # Test common ports
    common_ports = [80, 443, 5432]
    for port in common_ports:
        try:
            socket.create_connection(("8.8.8.8", port), timeout=5)
            print(f"✅ Port {port} connectivity: OK")
        except Exception:
            print(f"⚠️  Port {port} connectivity: Limited")
    
    return True

def main():
    """Main test function"""
    
    print("🚀 Fuze Database Connection Test")
    print("=" * 60)
    
    # Test network first
    network_ok = test_network_connectivity()
    
    # Test database connection
    db_ok = test_database_connection()
    
    print("\n" + "=" * 60)
    print("📋 Test Summary:")
    print(f"   🌐 Network: {'✅ OK' if network_ok else '❌ Failed'}")
    print(f"   🗄️  Database: {'✅ OK' if db_ok else '❌ Failed'}")
    
    if not db_ok:
        print("\n🔧 Next Steps:")
        print("   1. Check your .env file for correct DATABASE_URL")
        print("   2. Verify the database server is running")
        print("   3. Check network connectivity to the database host")
        print("   4. Verify database credentials and permissions")
        print("   5. Check if VPN or special network access is required")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main() 