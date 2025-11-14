#!/usr/bin/env python3
"""
Disable Recommendation Caching Script
This script will modify the unified_recommendation_orchestrator.py to disable caching
"""

import os
import sys
import re

def disable_recommendation_caching():
    """Disable caching in the unified recommendation orchestrator"""
    
    file_path = "unified_recommendation_orchestrator.py"
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    print("🔍 Reading unified_recommendation_orchestrator.py...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"✅ File read successfully ({len(content)} characters)")
        
        # Check current caching status
        cache_check_pattern = r'cache_key = self\._generate_cache_key\(request\)'
        cache_check_match = re.search(cache_check_pattern, content)
        
        if not cache_check_match:
            print("❌ Could not find cache key generation in the file")
            return False
        
        print("✅ Found cache key generation code")
        
        # Backup the original file
        backup_path = f"{file_path}.backup"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Created backup: {backup_path}")
        
        # Disable caching by commenting out cache-related code
        print("\n🧹 Disabling caching...")
        
        # 1. Comment out cache key generation
        content = re.sub(
            r'cache_key = self\._generate_cache_key\(request\)',
            '# cache_key = self._generate_cache_key(request)  # CACHING DISABLED',
            content
        )
        
        # 2. Comment out cache check
        cache_check_start = '            # FIX: Proper cache check with error handling'
        cache_check_end = '            # OPTIMIZATION 2: Cache miss - proceed with normal processing'
        
        # Find the cache check section
        cache_check_pattern = r'(\s+# FIX: Proper cache check with error handling.*?)(\s+# OPTIMIZATION 2: Cache miss - proceed with normal processing)'
        cache_check_match = re.search(cache_check_pattern, content, re.DOTALL)
        
        if cache_check_match:
            cache_check_section = cache_check_match.group(1)
            # Comment out the entire cache check section
            commented_cache_check = '\n'.join([f'# {line}' if line.strip() and not line.strip().startswith('#') else line for line in cache_check_section.split('\n')])
            content = content.replace(cache_check_section, commented_cache_check)
            print("   ✅ Commented out cache check section")
        
        # 3. Comment out cache miss logging
        content = re.sub(
            r'logger\.info\(f"Cache miss for recommendations: {cache_key}"\)',
            '# logger.info(f"Cache miss for recommendations: {cache_key}")  # CACHING DISABLED',
            content
        )
        
        # 4. Comment out cache miss counter
        content = re.sub(
            r'self\.cache_misses \+= 1',
            '# self.cache_misses += 1  # CACHING DISABLED',
            content
        )
        
        # 5. Comment out cache result storage
        cache_result_pattern = r'(\s+# Cache results with proper error handling.*?)(\s+# Log performance)'
        cache_result_match = re.search(cache_result_pattern, content, re.DOTALL)
        
        if cache_result_match:
            cache_result_section = cache_result_match.group(1)
            # Comment out the entire cache result section
            commented_cache_result = '\n'.join([f'# {line}' if line.strip() and not line.strip().startswith('#') else line for line in cache_result_section.split('\n')])
            content = content.replace(cache_result_section, commented_cache_result)
            print("   ✅ Commented out cache result storage")
        
        # 6. Add a comment at the top indicating caching is disabled
        header_comment = """# CACHING DISABLED - This file has been modified to disable recommendation caching
# All recommendations will be generated fresh each time
# To re-enable caching, restore from backup file

"""
        content = header_comment + content
        
        # Write the modified content back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Successfully disabled caching in unified_recommendation_orchestrator.py")
        
        # Verify the changes
        print("\n🔍 Verifying changes...")
        
        # Check if cache key generation is commented out
        if '# cache_key = self._generate_cache_key(request)  # CACHING DISABLED' in content:
            print("   ✅ Cache key generation disabled")
        else:
            print("   ❌ Cache key generation still active")
        
        # Check if cache check is commented out
        if '# FIX: Proper cache check with error handling' in content:
            print("   ✅ Cache check disabled")
        else:
            print("   ❌ Cache check still active")
        
        # Check if cache result storage is commented out
        if '# Cache results with proper error handling' in content:
            print("   ✅ Cache result storage disabled")
        else:
            print("   ❌ Cache result storage still active")
        
        print(f"\n🎯 Caching has been disabled!")
        print(f"   Backup created: {backup_path}")
        print(f"   All recommendations will now be generated fresh each time")
        
        return True
        
    except Exception as e:
        print(f"❌ Error disabling caching: {e}")
        import traceback
        traceback.print_exc()
        return False

def re_enable_caching():
    """Re-enable caching by restoring from backup"""
    
    file_path = "unified_recommendation_orchestrator.py"
    backup_path = f"{file_path}.backup"
    
    if not os.path.exists(backup_path):
        print(f"❌ Backup file not found: {backup_path}")
        return False
    
    try:
        print("🔄 Restoring caching from backup...")
        
        # Read backup
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_content = f.read()
        
        # Write backup back to main file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(backup_content)
        
        print("✅ Caching has been re-enabled from backup")
        return True
        
    except Exception as e:
        print(f"❌ Error restoring backup: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Recommendation Caching Control Tool")
    print("=" * 50)
    
    action = input("Choose action:\n1. Disable caching\n2. Re-enable caching\nEnter choice (1 or 2): ").strip()
    
    if action == "1":
        success = disable_recommendation_caching()
        if success:
            print("\n✅ Caching disabled successfully!")
            print("   Your recommendations will now be generated fresh each time")
        else:
            print("\n❌ Failed to disable caching")
    elif action == "2":
        success = re_enable_caching()
        if success:
            print("\n✅ Caching re-enabled successfully!")
            print("   Your recommendations will now be cached again")
        else:
            print("\n❌ Failed to re-enable caching")
    else:
        print("❌ Invalid choice. Please run again and choose 1 or 2.")
    
    print("\n🎯 All done!")
