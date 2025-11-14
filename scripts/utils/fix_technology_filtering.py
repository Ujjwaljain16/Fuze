#!/usr/bin/env python3
"""
Fix Technology Filtering Script
This script will adjust the overly aggressive technology filtering threshold
to get more recommendations while maintaining quality
"""

import os
import sys
import re

def fix_technology_filtering():
    """Fix the technology filtering threshold to be less aggressive"""
    
    file_path = "unified_recommendation_orchestrator.py"
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    print("🔍 Reading unified_recommendation_orchestrator.py...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"✅ File read successfully ({len(content)} characters)")
        
        # Check current filtering threshold
        threshold_pattern = r'if relevance_score >= 0\.3:  # Configurable threshold'
        threshold_match = re.search(threshold_pattern, content)
        
        if not threshold_match:
            print("❌ Could not find the filtering threshold in the file")
            return False
        
        print("✅ Found current filtering threshold: 0.3")
        print("   This is too aggressive - filtering 106 items down to 1")
        
        # Backup the original file
        backup_path = f"{file_path}.filtering_backup"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Created backup: {backup_path}")
        
        # Fix the filtering threshold
        print("\n🧹 Fixing technology filtering...")
        
        # Option 1: Lower the threshold to 0.1 (more permissive)
        new_threshold = "0.1"
        content = re.sub(
            r'if relevance_score >= 0\.3:  # Configurable threshold',
            f'if relevance_score >= {new_threshold}:  # Configurable threshold - FIXED: was 0.3 (too aggressive)',
            content
        )
        
        # Also improve the scoring logic to be more balanced
        print("   ✅ Lowered threshold from 0.3 to 0.1")
        
        # Option 2: Improve the scoring algorithm to be more balanced
        # Find the technology overlap scoring section
        scoring_pattern = r'# Technology overlap scoring(.*?)# Check content text for technology mentions'
        scoring_match = re.search(scoring_pattern, content, re.DOTALL)
        
        if scoring_match:
            current_scoring = scoring_match.group(1)
            
            # Improve the scoring to be more balanced
            improved_scoring = """
                # Technology overlap scoring - IMPROVED BALANCE
                if content_techs:
                    # Exact matches get highest score (but not too high)
                    exact_matches = set(request_techs).intersection(set(content_techs))
                    relevance_score += len(exact_matches) * 0.25  # Reduced from 0.4
                    
                    # Partial matches (substring matching) - more generous
                    for req_tech in request_techs:
                        for content_tech in content_techs:
                            if req_tech in content_tech or content_tech in req_tech:
                                relevance_score += 0.15  # Reduced from 0.2
                    
                    # Bonus for having any technology match
                    if exact_matches or any(req_tech in content_tech or content_tech in req_tech 
                                         for req_tech in request_techs for content_tech in content_techs):
                        relevance_score += 0.1  # Bonus for any tech relevance
"""
            
            content = content.replace(current_scoring, improved_scoring)
            print("   ✅ Improved scoring algorithm balance")
        
        # Option 3: Add fallback logic for when filtering is too strict
        fallback_logic = """
            # FALLBACK: If filtering is too strict, include more content
            if len(relevant_content) < 5:  # If we have very few results
                logger.info(f"⚠️  Filtering too strict ({len(relevant_content)} results), relaxing criteria...")
                # Include content with lower scores but still some relevance
                for content in content_list:
                    if content not in relevant_content:  # Not already included
                        # Check if content has ANY technology relevance
                        content_techs = content.get('technologies', [])
                        if isinstance(content_techs, str):
                            content_techs = [tech.strip().lower() for tech in content_techs.split(',') if tech.strip()]
                        
                        # Simple relevance check
                        has_tech_relevance = False
                        if content_techs:
                            for req_tech in request_techs:
                                for content_tech in content_techs:
                                    if req_tech in content_tech or content_tech in req_tech:
                                        has_tech_relevance = True
                                        break
                                if has_tech_relevance:
                                    break
                        
                        # Include if there's any tech relevance
                        if has_tech_relevance:
                            content['relevance_score'] = 0.05  # Low but included
                            relevant_content.append(content)
                            if len(relevant_content) >= 10:  # Stop at reasonable number
                                break
                
                logger.info(f"✅ After fallback: {len(relevant_content)} relevant items")
"""
        
        # Insert fallback logic before the return statement
        return_pattern = r'logger\.info\(f"Technology filtering: {len\(content_list\)} → {len\(relevant_content\)} relevant items"\)'
        if re.search(return_pattern, content):
            content = re.sub(
                return_pattern,
                return_pattern + fallback_logic,
                content
            )
            print("   ✅ Added fallback logic for strict filtering")
        
        # Write the modified content back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Successfully fixed technology filtering in unified_recommendation_orchestrator.py")
        
        # Verify the changes
        print("\n🔍 Verifying changes...")
        
        # Check if threshold was changed
        if f'if relevance_score >= {new_threshold}:  # Configurable threshold - FIXED: was 0.3 (too aggressive)' in content:
            print("   ✅ Threshold lowered from 0.3 to 0.1")
        else:
            print("   ❌ Threshold change not applied")
        
        # Check if fallback logic was added
        if "FALLBACK: If filtering is too strict" in content:
            print("   ✅ Fallback logic added")
        else:
            print("   ❌ Fallback logic not added")
        
        print(f"\n🎯 Technology filtering has been fixed!")
        print(f"   Backup created: {backup_path}")
        print(f"   Threshold: 0.3 → 0.1 (more permissive)")
        print(f"   Added fallback logic for when filtering is too strict")
        print(f"   Expected result: More recommendations while maintaining quality")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing technology filtering: {e}")
        import traceback
        traceback.print_exc()
        return False

def restore_original_filtering():
    """Restore original filtering from backup"""
    
    file_path = "unified_recommendation_orchestrator.py"
    backup_path = f"{file_path}.filtering_backup"
    
    if not os.path.exists(backup_path):
        print(f"❌ Backup file not found: {backup_path}")
        return False
    
    try:
        print("🔄 Restoring original filtering from backup...")
        
        # Read backup
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_content = f.read()
        
        # Write backup back to main file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(backup_content)
        
        print("✅ Original filtering has been restored from backup")
        return True
        
    except Exception as e:
        print(f"❌ Error restoring backup: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Technology Filtering Fix Tool")
    print("=" * 50)
    print("Current issue: 106 items → 1 relevant item (too aggressive)")
    print("This tool will:")
    print("  - Lower threshold from 0.3 to 0.1")
    print("  - Improve scoring balance")
    print("  - Add fallback logic for strict filtering")
    print("=" * 50)
    
    action = input("Choose action:\n1. Fix technology filtering\n2. Restore original filtering\nEnter choice (1 or 2): ").strip()
    
    if action == "1":
        success = fix_technology_filtering()
        if success:
            print("\n✅ Technology filtering fixed successfully!")
            print("   You should now get more recommendations")
            print("   Test your recommendations to see the improvement")
        else:
            print("\n❌ Failed to fix technology filtering")
    elif action == "2":
        success = restore_original_filtering()
        if success:
            print("\n✅ Original filtering restored successfully!")
        else:
            print("\n❌ Failed to restore original filtering")
    else:
        print("❌ Invalid choice. Please run again and choose 1 or 2.")
    
    print("\n🎯 All done!")
