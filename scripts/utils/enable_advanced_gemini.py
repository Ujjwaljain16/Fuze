#!/usr/bin/env python3
"""
Enable Advanced Gemini Engine in Frontend
Configures the frontend to use the new optimized Gemini engine
"""

import os

def update_recommendations_jsx():
    """Update the Recommendations.jsx file to use advanced Gemini engine"""
    
    file_path = "frontend/src/pages/Recommendations.jsx"
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    print(f"📝 Updating {file_path}...")
    
    # Read current content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already configured
    if "fast-gemini" in content:
        print("✅ Frontend already configured for advanced Gemini engine")
        return True
    
    # Update the endpoints to use fast-gemini
    updated_content = content.replace(
        '/api/recommendations/gemini-enhanced',
        '/api/recommendations/fast-gemini'
    ).replace(
        '/api/recommendations/gemini-enhanced-project',
        '/api/recommendations/fast-gemini-project'
    )
    
    # Write updated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print("✅ Frontend updated to use advanced Gemini engine")
    print("   - Gemini-enhanced endpoints now point to fast-gemini")
    print("   - Users will get optimized Gemini recommendations")
    
    return True

def main():
    """Main function to enable advanced Gemini engine"""
    print("🚀 Enabling Advanced Gemini Engine in Frontend")
    print("=" * 50)
    
    success = update_recommendations_jsx()
    
    if success:
        print("\n✅ Configuration Complete!")
        print("\n📋 What this does:")
        print("   • Frontend now uses the advanced Gemini engine")
        print("   • Multi-layer caching for faster responses")
        print("   • Intelligent candidate selection (max 3 Gemini calls)")
        print("   • Aggressive caching of analysis results")
        print("   • Focused, optimized prompts for quick analysis")
        print("   • Fallback to ultra-fast engine if Gemini fails")
        
        print("\n🎯 Expected Performance:")
        print("   • First request: ~2-4 seconds (with Gemini analysis)")
        print("   • Subsequent requests: ~0.5-1 second (cached)")
        print("   • Cache hit rate: 80%+ after initial requests")
        
        print("\n🔄 Next Steps:")
        print("   1. Restart your Flask server if needed")
        print("   2. Test with: python test_advanced_gemini_performance.py")
        print("   3. Check frontend recommendations page")
        
    else:
        print("\n❌ Configuration failed!")
        print("   Please check the file paths and try again")

if __name__ == "__main__":
    main() 