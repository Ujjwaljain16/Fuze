#!/usr/bin/env python3
"""
Clear all caches for a fresh start
"""

import os
import sys
import shutil
import glob
import subprocess

def clear_python_cache():
    """Clear Python cache files"""
    print("🧹 Clearing Python cache...")
    
    # Remove __pycache__ directories
    for root, dirs, files in os.walk('.'):
        for dir_name in dirs:
            if dir_name == '__pycache__':
                cache_path = os.path.join(root, dir_name)
                try:
                    shutil.rmtree(cache_path)
                    print(f"   ✅ Removed: {cache_path}")
                except Exception as e:
                    print(f"   ❌ Failed to remove {cache_path}: {e}")
    
    # Remove .pyc files
    pyc_files = glob.glob('**/*.pyc', recursive=True)
    for pyc_file in pyc_files:
        try:
            os.remove(pyc_file)
            print(f"   ✅ Removed: {pyc_file}")
        except Exception as e:
            print(f"   ❌ Failed to remove {pyc_file}: {e}")
    
    # Remove .pyo files
    pyo_files = glob.glob('**/*.pyo', recursive=True)
    for pyo_file in pyo_files:
        try:
            os.remove(pyo_file)
            print(f"   ✅ Removed: {pyo_file}")
        except Exception as e:
            print(f"   ❌ Failed to remove {pyo_file}: {e}")

def clear_redis_cache():
    """Clear Redis cache"""
    print("🧹 Clearing Redis cache...")
    
    try:
        import redis
        from redis_utils import redis_cache
        
        # Clear all Redis keys
        redis_cache.flushall()
        print("   ✅ Redis cache cleared")
        
    except ImportError:
        print("   ⚠️ Redis not available")
    except Exception as e:
        print(f"   ❌ Failed to clear Redis: {e}")

def clear_file_caches():
    """Clear any file-based caches"""
    print("🧹 Clearing file caches...")
    
    # Remove any cache files
    cache_patterns = [
        '*.cache',
        'cache/*',
        'tmp/*',
        'temp/*',
        '.cache/*'
    ]
    
    for pattern in cache_patterns:
        try:
            files = glob.glob(pattern)
            for file_path in files:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"   ✅ Removed: {file_path}")
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    print(f"   ✅ Removed: {file_path}")
        except Exception as e:
            print(f"   ⚠️ Pattern {pattern}: {e}")

def clear_embedding_cache():
    """Clear sentence transformer cache"""
    print("🧹 Clearing embedding model cache...")
    
    try:
        import sentence_transformers
        cache_dir = sentence_transformers.util.get_cache_dir()
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            print(f"   ✅ Embedding cache cleared: {cache_dir}")
        else:
            print("   ⚠️ No embedding cache found")
    except ImportError:
        print("   ⚠️ Sentence transformers not available")
    except Exception as e:
        print(f"   ❌ Failed to clear embedding cache: {e}")

def clear_browser_cache():
    """Clear browser cache files if they exist"""
    print("🧹 Clearing browser cache...")
    
    # Common browser cache locations
    cache_locations = [
        os.path.expanduser('~/.cache'),
        os.path.expanduser('~/AppData/Local/Google/Chrome/User Data/Default/Cache'),
        os.path.expanduser('~/AppData/Local/Mozilla/Firefox/Profiles/*/cache2'),
    ]
    
    for location in cache_locations:
        if os.path.exists(location):
            try:
                if os.path.isfile(location):
                    os.remove(location)
                else:
                    shutil.rmtree(location)
                print(f"   ✅ Cleared: {location}")
            except Exception as e:
                print(f"   ⚠️ Could not clear {location}: {e}")

def restart_redis():
    """Restart Redis service"""
    print("🔄 Restarting Redis...")
    
    try:
        # Try to restart Redis service
        subprocess.run(['redis-cli', 'shutdown'], capture_output=True, timeout=5)
        print("   ✅ Redis shutdown command sent")
        
        # Wait a moment
        import time
        time.sleep(2)
        
        # Try to start Redis again
        subprocess.run(['redis-server'], capture_output=True, timeout=5)
        print("   ✅ Redis restart command sent")
        
    except Exception as e:
        print(f"   ⚠️ Could not restart Redis: {e}")
        print("   💡 You may need to restart Redis manually")

def main():
    """Main cache clearing function"""
    print("🚀 Clearing All Caches")
    print("=" * 50)
    
    # Clear all types of caches
    clear_python_cache()
    clear_redis_cache()
    clear_file_caches()
    clear_embedding_cache()
    clear_browser_cache()
    
    print("\n" + "=" * 50)
    print("🏁 Cache clearing completed!")
    print("\n💡 Next steps:")
    print("   1. Restart your Flask server")
    print("   2. Test if SSL issues are resolved")
    print("   3. All caches are now fresh")
    
    # Ask if user wants to restart Redis
    try:
        response = input("\n🔄 Restart Redis service? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            restart_redis()
    except KeyboardInterrupt:
        print("\n   ⚠️ Skipped Redis restart")

if __name__ == "__main__":
    main()
