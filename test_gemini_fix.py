#!/usr/bin/env python3
"""
Test script to verify the improved Gemini integration
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

def test_gemini_integration():
    """Test the improved Gemini integration"""
    
    print("🧪 Testing Improved Gemini Integration")
    print("=" * 50)
    
    # Test 1: Import and initialization
    print("\n1. Testing import and initialization...")
    try:
        from gemini_utils import GeminiAnalyzer
        print("✅ Successfully imported GeminiAnalyzer")
        
        analyzer = GeminiAnalyzer()
        print("✅ Successfully initialized GeminiAnalyzer")
        
    except Exception as e:
        print(f"❌ Failed to initialize GeminiAnalyzer: {e}")
        return False
    
    # Test 2: Simple content analysis
    print("\n2. Testing simple content analysis...")
    try:
        test_title = "Python Tutorial for Beginners"
        test_description = "Learn Python programming from scratch"
        test_content = "This tutorial covers Python basics, data types, and control structures."
        
        result = analyzer.analyze_bookmark_content(
            title=test_title,
            description=test_description,
            content=test_content,
            url="https://example.com/python-tutorial"
        )
        
        if result and isinstance(result, dict):
            print("✅ Successfully analyzed content")
            print(f"   Technologies: {result.get('technologies', [])}")
            print(f"   Content Type: {result.get('content_type', 'N/A')}")
            print(f"   Difficulty: {result.get('difficulty', 'N/A')}")
        else:
            print("❌ Content analysis returned invalid result")
            return False
            
    except Exception as e:
        print(f"❌ Content analysis failed: {e}")
        return False
    
    # Test 3: User context analysis
    print("\n3. Testing user context analysis...")
    try:
        test_project_title = "Web Development Project"
        test_project_desc = "Building a React application with Node.js backend"
        test_technologies = "React, Node.js, JavaScript, MongoDB"
        
        result = analyzer.analyze_user_context(
            title=test_project_title,
            description=test_project_desc,
            technologies=test_technologies,
            user_interests="web development, full-stack"
        )
        
        if result and isinstance(result, dict):
            print("✅ Successfully analyzed user context")
            print(f"   Project Type: {result.get('project_type', 'N/A')}")
            print(f"   Technologies: {result.get('technologies', [])}")
            print(f"   Complexity: {result.get('complexity_level', 'N/A')}")
        else:
            print("❌ User context analysis returned invalid result")
            return False
            
    except Exception as e:
        print(f"❌ User context analysis failed: {e}")
        return False
    
    # Test 4: Recommendation reasoning
    print("\n4. Testing recommendation reasoning...")
    try:
        test_bookmark = {
            'title': 'React Hooks Tutorial',
            'technologies': ['React', 'JavaScript'],
            'content_type': 'tutorial',
            'difficulty': 'intermediate',
            'key_concepts': ['hooks', 'state management']
        }
        
        test_user_context = {
            'title': 'Web Development Project',
            'technologies': ['React', 'Node.js'],
            'project_type': 'web_app',
            'learning_needs': ['React', 'JavaScript']
        }
        
        reasoning = analyzer.generate_recommendation_reasoning(test_bookmark, test_user_context)
        
        if reasoning and isinstance(reasoning, str) and len(reasoning) > 10:
            print("✅ Successfully generated recommendation reasoning")
            print(f"   Reasoning: {reasoning}")
        else:
            print("❌ Recommendation reasoning returned invalid result")
            return False
            
    except Exception as e:
        print(f"❌ Recommendation reasoning failed: {e}")
        return False
    
    # Test 5: Batch analysis
    print("\n5. Testing batch analysis...")
    try:
        batch_prompt = """
        Analyze these content items:
        
        1. "JavaScript Promises Tutorial" - Learn about async programming
        2. "Python Data Structures" - Understanding lists, dictionaries, and sets
        3. "React State Management" - Managing component state effectively
        
        Provide insights for each item.
        """
        
        result = analyzer.analyze_batch_content(batch_prompt)
        
        if result and isinstance(result, dict):
            print("✅ Successfully performed batch analysis")
            print(f"   Result keys: {list(result.keys())}")
        else:
            print("❌ Batch analysis returned invalid result")
            return False
            
    except Exception as e:
        print(f"❌ Batch analysis failed: {e}")
        return False
    
    print("\n🎉 All tests passed! Gemini integration is working properly.")
    return True

def test_error_handling():
    """Test error handling with invalid inputs"""
    
    print("\n🧪 Testing Error Handling")
    print("=" * 50)
    
    try:
        from gemini_utils import GeminiAnalyzer
        analyzer = GeminiAnalyzer()
        
        # Test with empty content
        print("\n1. Testing with empty content...")
        result = analyzer.analyze_bookmark_content("", "", "", "")
        if result and isinstance(result, dict):
            print("✅ Gracefully handled empty content")
        else:
            print("❌ Failed to handle empty content")
            return False
        
        # Test with very long content
        print("\n2. Testing with very long content...")
        long_content = "This is a very long content " * 1000
        result = analyzer.analyze_bookmark_content("Long Title", "Long Description", long_content, "")
        if result and isinstance(result, dict):
            print("✅ Gracefully handled long content")
        else:
            print("❌ Failed to handle long content")
            return False
        
        # Test with special characters
        print("\n3. Testing with special characters...")
        special_content = "Content with special chars: @#$%^&*()_+{}|:<>?[]\\;'\",./"
        result = analyzer.analyze_bookmark_content("Special Title", "Special Desc", special_content, "")
        if result and isinstance(result, dict):
            print("✅ Gracefully handled special characters")
        else:
            print("❌ Failed to handle special characters")
            return False
        
        print("\n🎉 All error handling tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Gemini Integration Tests")
    print("=" * 60)
    
    # Check if API key is set
    if not os.environ.get('GEMINI_API_KEY'):
        print("❌ GEMINI_API_KEY environment variable is not set")
        print("Please set your Gemini API key and try again.")
        sys.exit(1)
    
    # Run tests
    success1 = test_gemini_integration()
    success2 = test_error_handling()
    
    if success1 and success2:
        print("\n🎉 All tests completed successfully!")
        print("The improved Gemini integration is working properly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1) 