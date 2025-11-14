#!/usr/bin/env python3
"""
Enable Fast Gemini Engine by Default
Update frontend to use fast Gemini recommendations by default
"""

def enable_fast_gemini_default():
    """Enable fast Gemini engine by default in the frontend"""
    
    print("🚀 Enabling Fast Gemini Engine by Default")
    print("=" * 50)
    
    # Update frontend to use fast Gemini by default
    frontend_file = "frontend/src/pages/Recommendations.jsx"
    
    try:
        # Read the current file
        with open(frontend_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if fast Gemini is already enabled
        if 'useGemini, setUseGemini] = useState(false)' in content:
            print("✅ Fast Gemini is already set as default (useGemini = false)")
            print("   This means ultra-fast recommendations are used by default")
            print("   Users can still toggle to Gemini-enhanced when needed")
            return True
        
        # Check if Gemini is currently enabled by default
        if 'useGemini, setUseGemini] = useState(true)' in content:
            print("🔄 Changing default from Gemini to Fast Engine...")
            
            # Replace the line
            content = content.replace(
                'const [useGemini, setUseGemini] = useState(true) // Default to Gemini',
                'const [useGemini, setUseGemini] = useState(false) // Default to FAST recommendations'
            )
            
            # Write the updated content
            with open(frontend_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ Successfully updated frontend to use fast recommendations by default")
            print("   Users will now get ultra-fast recommendations immediately")
            print("   They can still toggle to Gemini-enhanced when they want AI analysis")
            return True
        
        else:
            print("⚠️ Could not find the useGemini state line in the file")
            print("   Please check the file manually")
            return False
            
    except Exception as e:
        print(f"❌ Error updating frontend file: {e}")
        return False

def show_current_configuration():
    """Show the current frontend configuration"""
    print("\n📋 Current Frontend Configuration:")
    print("=" * 40)
    
    frontend_file = "frontend/src/pages/Recommendations.jsx"
    
    try:
        with open(frontend_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check current settings
        if 'useGemini, setUseGemini] = useState(false)' in content:
            print("✅ Default: Ultra-Fast Recommendations (no Gemini)")
            print("   - Fastest possible recommendations")
            print("   - No API calls to Gemini")
            print("   - Users can toggle to Gemini-enhanced")
        elif 'useGemini, setUseGemini] = useState(true)' in content:
            print("⚠️ Default: Gemini-Enhanced Recommendations")
            print("   - Slower but more intelligent")
            print("   - Makes API calls to Gemini")
            print("   - Users can toggle to ultra-fast")
        else:
            print("❓ Unknown configuration")
        
        # Check endpoints
        if '/api/recommendations/fast-gemini' in content:
            print("✅ Fast Gemini endpoints are configured")
        else:
            print("⚠️ Fast Gemini endpoints not found")
            
        if '/api/recommendations/optimized' in content:
            print("✅ Ultra-fast endpoints are configured")
        else:
            print("⚠️ Ultra-fast endpoints not found")
            
    except Exception as e:
        print(f"❌ Error reading frontend file: {e}")

def main():
    """Main function"""
    print("🎯 Fast Gemini Engine Configuration")
    print("=" * 50)
    
    # Show current configuration
    show_current_configuration()
    
    # Enable fast Gemini by default
    success = enable_fast_gemini_default()
    
    if success:
        print("\n🎉 Configuration Complete!")
        print("=" * 30)
        print("✅ Fast recommendations are now the default")
        print("✅ Users get instant results")
        print("✅ Gemini-enhanced option is still available")
        print("✅ Best of both worlds!")
        
        print("\n📝 Next Steps:")
        print("1. Restart your frontend development server")
        print("2. Test the recommendations in your browser")
        print("3. Try toggling between fast and Gemini-enhanced")
        print("4. Run test_fast_gemini_performance.py to see the improvement")
    else:
        print("\n❌ Configuration failed")
        print("Please check the file manually")

if __name__ == "__main__":
    main() 