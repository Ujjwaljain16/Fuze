#!/usr/bin/env python3
"""
Redis Keep-Alive Ping Script

This script performs a simple Redis health check to prevent Upstash
from pausing due to inactivity. It's designed to be run periodically
via GitHub Actions or cron jobs.

Usage:
    python scripts/ping_redis.py

Environment Variables:
    REDIS_URL - Redis connection string (supports redis:// and rediss://)
    REDIS_HOST, REDIS_PORT, REDIS_PASSWORD - Alternative connection params
"""

import os
import sys
import time
import ssl
from datetime import datetime

# Load environment variables from .env file (for local testing)
try:
    from dotenv import load_dotenv
    # Try to load from project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_root, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"📁 Loaded environment variables from: {env_path}")
    else:
        load_dotenv()  # Try to load from current directory
except ImportError:
    # python-dotenv not installed, assume env vars are set externally
    pass

try:
    import redis
except ImportError:
    print("❌ Error: redis is not installed")
    print("Install it with: pip install redis")
    sys.exit(1)


def get_redis_client():
    """Create a Redis client based on environment variables."""
    redis_url = os.environ.get('REDIS_URL')
    
    if redis_url:
        # Upstash requires TLS but provides redis:// URLs sometimes
        if 'upstash.io' in redis_url and redis_url.startswith('redis://'):
            redis_url = redis_url.replace('redis://', 'rediss://', 1)
            print("🔄 Converted Upstash URL to use TLS (rediss://)")
        
        # SSL context options for cloud providers
        ssl_context = None
        if redis_url.startswith('rediss://'):
             # Don't verify certificates for broad compatibility with cloud providers
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        try:
            # redis-py handles rediss:// automatically, but we can be explicit with strict Client if needed
            # Using from_url is generally robust
            client = redis.Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=10,
                ssl_cert_reqs=None # Helper for redis-py to relax SSL
            )
            return client
        except Exception as e:
            print(f"❌ Error creating client from URL: {e}")
            return None
    else:
        # Fallback to individual params
        host = os.environ.get('REDIS_HOST', 'localhost')
        port = int(os.environ.get('REDIS_PORT', 6379))
        password = os.environ.get('REDIS_PASSWORD')
        use_ssl = os.environ.get('REDIS_SSL', 'false').lower() == 'true'
        
        # Auto-detect TLS
        if not use_ssl and any(p in host for p in ['upstash.io', 'redislabs.com', 'redis.cache']):
            use_ssl = True
            print("🔄 Auto-detected TLS requirement")
            
        try:
            client = redis.Redis(
                host=host,
                port=port,
                password=password,
                ssl=use_ssl,
                ssl_cert_reqs=None,
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=10
            )
            return client
        except Exception as e:
            print(f"❌ Error creating client from params: {e}")
            return None


def ping_redis():
    """
    Perform a simple Redis health check.
    
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"⏰ Timestamp: {datetime.utcnow().isoformat()}Z")
    
    client = get_redis_client()
    
    if not client:
        print("❌ Failed to initialize Redis client")
        return False
        
    try:
        start_time = time.time()
        
        # Simple PING
        print("🔄 Pinging Redis...")
        response = client.ping()
        
        elapsed_time = time.time() - start_time
        
        if response:
            print(f"✅ Redis ping successful!")
            print(f"   Response: {response}")
            print(f"   Response Time: {elapsed_time:.3f}s")
            
            # Optional: Get some info to show it's working
            info = client.info(section='server')
            if info:
                version = info.get('redis_version', 'unknown')
                print(f"   Redis Version: {version}")
                
            return True
        else:
            print("❌ Redis ping failed: No response")
            return False
            
    except redis.AuthenticationError:
        print("❌ Authentication failed. Check REDIS_URL or password.")
        return False
    except redis.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        try:
            client.close()
            print("🔌 Connection closed")
        except:
            pass


def main():
    """Main entry point"""
    print("=" * 60)
    print("Redis Keep-Alive Ping Script")
    print("=" * 60)
    
    success = ping_redis()
    
    print("=" * 60)
    
    if success:
        print("✅ Ping completed successfully")
        sys.exit(0)
    else:
        print("❌ Ping failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
