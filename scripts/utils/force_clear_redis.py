#!/usr/bin/env python3
"""
Force Clear Redis - Aggressive Redis clearing script
This will clear ALL Redis data using multiple methods
"""

import os
import subprocess
import time

def clear_redis_via_cli():
    """Clear Redis using redis-cli command"""
    print("🧹 Clearing Redis via redis-cli...")
    
    try:
        # Try redis-cli flushall
        result = subprocess.run(['redis-cli', 'flushall'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("   ✅ Redis cleared via redis-cli flushall")
            return True
        else:
            print(f"   ⚠️ redis-cli failed: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("   ❌ redis-cli not found in PATH")
        return False
    except subprocess.TimeoutExpired:
        print("   ❌ redis-cli timeout")
        return False
    except Exception as e:
        print(f"   ❌ redis-cli error: {e}")
        return False

def clear_redis_via_python():
    """Clear Redis using Python redis package"""
    print("🧹 Clearing Redis via Python redis package...")
    
    try:
        import redis
        
        # Try multiple connection methods
        connection_configs = [
            {'host': 'localhost', 'port': 6379},
            {'host': '127.0.0.1', 'port': 6379},
            {'host': 'localhost', 'port': 6380},
            {'host': '127.0.0.1', 'port': 6380}
        ]
        
        for config in connection_configs:
            try:
                r = redis.Redis(**config, socket_connect_timeout=5, socket_timeout=5)
                r.ping()
                print(f"   ✅ Connected to Redis at {config['host']}:{config['port']}")
                
                # Get all keys first
                all_keys = r.keys('*')
                print(f"   📊 Found {len(all_keys)} keys to clear")
                
                if all_keys:
                    # Try flushall first
                    try:
                        r.flushall()
                        print(f"   ✅ Flushed all Redis data")
                        return True
                    except Exception as flush_error:
                        print(f"   ⚠️ flushall failed: {flush_error}")
                        
                        # Fallback: delete keys in batches
                        try:
                            batch_size = 1000
                            for i in range(0, len(all_keys), batch_size):
                                batch = all_keys[i:i + batch_size]
                                r.delete(*batch)
                                print(f"   🔄 Deleted batch {i//batch_size + 1}")
                            
                            print(f"   ✅ Deleted all keys in batches")
                            return True
                        except Exception as batch_error:
                            print(f"   ❌ Batch deletion failed: {batch_error}")
                            return False
                else:
                    print("   ✅ Redis already empty")
                    return True
                    
            except Exception as conn_error:
                print(f"   ⚠️ Connection failed to {config['host']}:{config['port']}: {conn_error}")
                continue
        
        print("   ❌ Could not connect to Redis via Python")
        return False
        
    except ImportError:
        print("   ❌ Python redis package not available")
        return False
    except Exception as e:
        print(f"   ❌ Python Redis clear failed: {e}")
        return False

def clear_redis_via_system_commands():
    """Clear Redis using system commands"""
    print("🧹 Clearing Redis via system commands...")
    
    # Try to restart Redis service
    try:
        # Windows - try to stop/start Redis service
        if os.name == 'nt':
            print("   🔄 Attempting to restart Redis service on Windows...")
            
            # Stop Redis service
            stop_result = subprocess.run(['net', 'stop', 'Redis'], 
                                       capture_output=True, text=True, timeout=10)
            
            if stop_result.returncode == 0:
                print("   ✅ Redis service stopped")
            else:
                print(f"   ⚠️ Could not stop Redis service: {stop_result.stderr}")
            
            time.sleep(2)
            
            # Start Redis service
            start_result = subprocess.run(['net', 'start', 'Redis'], 
                                        capture_output=True, text=True, timeout=10)
            
            if start_result.returncode == 0:
                print("   ✅ Redis service restarted")
                return True
            else:
                print(f"   ⚠️ Could not start Redis service: {start_result.stderr}")
                return False
                
        else:
            # Linux/Mac - try systemctl
            print("   🔄 Attempting to restart Redis service on Linux/Mac...")
            
            restart_result = subprocess.run(['sudo', 'systemctl', 'restart', 'redis'], 
                                          capture_output=True, text=True, timeout=10)
            
            if restart_result.returncode == 0:
                print("   ✅ Redis service restarted")
                return True
            else:
                print(f"   ⚠️ Could not restart Redis service: {restart_result.stderr}")
                return False
                
    except Exception as e:
        print(f"   ❌ System command failed: {e}")
        return False

def clear_redis_via_docker():
    """Clear Redis if running in Docker"""
    print("🧹 Clearing Redis via Docker...")
    
    try:
        # Check if Redis is running in Docker
        result = subprocess.run(['docker', 'ps', '--filter', 'name=redis'], 
                              capture_output=True, text=True, timeout=10)
        
        if 'redis' in result.stdout.lower():
            print("   🐳 Redis container found, clearing data...")
            
            # Execute flushall in container
            flush_result = subprocess.run(['docker', 'exec', 'redis', 'redis-cli', 'flushall'], 
                                        capture_output=True, text=True, timeout=10)
            
            if flush_result.returncode == 0:
                print("   ✅ Docker Redis cleared")
                return True
            else:
                print(f"   ❌ Docker Redis clear failed: {flush_result.stderr}")
                return False
        else:
            print("   ⚠️ No Redis Docker container found")
            return False
            
    except FileNotFoundError:
        print("   ❌ Docker not available")
        return False
    except Exception as e:
        print(f"   ❌ Docker Redis clear failed: {e}")
        return False

def verify_redis_clear():
    """Verify that Redis is actually cleared"""
    print("\n🔍 Verifying Redis is cleared...")
    
    try:
        import redis
        
        # Try to connect and check
        r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=5)
        r.ping()
        
        # Check if there are any keys
        keys = r.keys('*')
        
        if not keys:
            print("   ✅ VERIFIED: Redis is completely empty")
            return True
        else:
            print(f"   ❌ FAILED: Redis still has {len(keys)} keys")
            print(f"   📋 Sample keys: {keys[:5]}")
            return False
            
    except Exception as e:
        print(f"   ⚠️ Could not verify Redis status: {e}")
        return False

def main():
    """Main function to force clear Redis"""
    print("🚀 FORCE REDIS CLEARING TOOL")
    print("=" * 50)
    print("⚠️  WARNING: This will clear ALL Redis data!")
    print("⚠️  Make sure you want to do this!")
    print("=" * 50)
    
    # Try multiple clearing methods
    methods = [
        ("Redis CLI", clear_redis_via_cli),
        ("Python Redis", clear_redis_via_python),
        ("System Commands", clear_redis_via_system_commands),
        ("Docker Redis", clear_redis_via_docker)
    ]
    
    successful_methods = []
    
    for method_name, method_func in methods:
        try:
            print(f"\n🔄 Trying {method_name}...")
            result = method_func()
            if result:
                successful_methods.append(method_name)
                print(f"   ✅ {method_name} succeeded!")
            else:
                print(f"   ❌ {method_name} failed")
        except Exception as e:
            print(f"   ❌ {method_name} crashed: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Redis Clearing Results")
    print("=" * 50)
    
    if successful_methods:
        print(f"✅ SUCCESS: {len(successful_methods)} methods worked")
        for method in successful_methods:
            print(f"   ✅ {method}")
        
        # Verify the clear
        time.sleep(2)
        if verify_redis_clear():
            print("\n🎉 SUCCESS! Redis is completely cleared!")
        else:
            print("\n⚠️ Redis may not be fully cleared")
    else:
        print("❌ FAILED: No methods worked")
        print("\n💡 Manual Redis clearing options:")
        print("   1. Stop Redis service completely")
        print("   2. Delete Redis dump files")
        print("   3. Restart Redis service")
    
    print("\n💡 Next steps:")
    print("   1. Restart your Flask application")
    print("   2. All recommendation caches are now fresh")
    print("   3. Test with a new recommendation request")

if __name__ == "__main__":
    main()
