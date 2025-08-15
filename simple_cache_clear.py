#!/usr/bin/env python3
"""
Simple cache clearing script - fixes Redis and embedding cache issues
"""

import os
import shutil
import glob

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

def clear_redis_cache():
    """Clear Redis cache properly"""
    print("🧹 Clearing Redis cache...")
    
    try:
        from redis_utils import redis_cache
        
        # Access the actual Redis client from the RedisCache instance
        if hasattr(redis_cache, 'redis_client') and redis_cache.redis_client:
            redis_client = redis_cache.redis_client
            
            # Check what methods are available on the actual Redis client
            if hasattr(redis_client, 'flushall'):
                redis_client.flushall()
                print("   ✅ Redis cache cleared with flushall")
            elif hasattr(redis_client, 'flushdb'):
                redis_client.flushdb()
                print("   ✅ Redis cache cleared with flushdb")
            elif hasattr(redis_client, 'delete'):
                # Get all keys and delete them
                keys = redis_client.keys('*')
                if keys:
                    redis_client.delete(*keys)
                    print(f"   ✅ Redis cache cleared {len(keys)} keys")
                else:
                    print("   ✅ Redis cache already empty")
            else:
                print("   ⚠️ Redis client has no clear method")
        else:
            print("   ⚠️ Redis client not available")
            
    except ImportError:
        print("   ⚠️ Redis utils not available")
    except Exception as e:
        print(f"   ❌ Failed to clear Redis: {e}")

def clear_embedding_cache():
    """Clear sentence transformer cache properly"""
    print("🧹 Clearing embedding model cache...")
    
    try:
        import sentence_transformers
        
        # Try different ways to get cache directory
        cache_dir = None
        
        # Method 1: Try get_cache_dir
        if hasattr(sentence_transformers.util, 'get_cache_dir'):
            cache_dir = sentence_transformers.util.get_cache_dir()
        
        # Method 2: Try cache_dir attribute
        elif hasattr(sentence_transformers, 'cache_dir'):
            cache_dir = sentence_transformers.cache_dir
        
        # Method 3: Try environment variable
        elif 'TRANSFORMERS_CACHE' in os.environ:
            cache_dir = os.environ['TRANSFORMERS_CACHE']
        
        # Method 4: Default cache location
        else:
            cache_dir = os.path.expanduser('~/.cache/huggingface')
        
        if cache_dir and os.path.exists(cache_dir):
            # Only clear sentence-transformers specific cache
            st_cache = os.path.join(cache_dir, 'sentence-transformers')
            if os.path.exists(st_cache):
                shutil.rmtree(st_cache)
                print(f"   ✅ Embedding cache cleared: {st_cache}")
            else:
                print(f"   ⚠️ No sentence-transformers cache found in {cache_dir}")
        else:
            print("   ⚠️ No embedding cache directory found")
            
    except ImportError:
        print("   ⚠️ Sentence transformers not available")
    except Exception as e:
        print(f"   ❌ Failed to clear embedding cache: {e}")

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

def main():
    """Main cache clearing function"""
    print("🚀 Simple Cache Clearing")
    print("=" * 50)
    
    # Clear all types of caches
    clear_python_cache()
    clear_redis_cache()
    clear_embedding_cache()
    clear_file_caches()
    
    print("\n" + "=" * 50)
    print("🏁 Cache clearing completed!")
    print("\n💡 Next steps:")
    print("   1. Restart your Flask server")
    print("   2. Test if SSL issues are resolved")
    print("   3. All caches are now fresh")

if __name__ == "__main__":
    main()
