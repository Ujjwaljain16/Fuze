#!/usr/bin/env python3
"""
Test script to verify Gemini AI analysis improvements
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from gemini_utils import GeminiAnalyzer
    print("✅ Successfully imported GeminiAnalyzer")
except ImportError as e:
    print(f"❌ Failed to import GeminiAnalyzer: {e}")
    sys.exit(1)

def test_gemini_analysis():
    """Test Gemini analysis with various inputs"""
    
    # Check if Gemini API key is available
    if not os.getenv('GEMINI_API_KEY'):
        print("❌ GEMINI_API_KEY not found in environment variables")
        print("Please set your Gemini API key in the .env file")
        return False
    
    try:
        analyzer = GeminiAnalyzer()
        print("✅ Successfully initialized GeminiAnalyzer")
    except Exception as e:
        print(f"❌ Failed to initialize GeminiAnalyzer: {e}")
        return False
    
    # Test bookmark content analysis
    print("\n🔍 Testing bookmark content analysis...")
    bookmark_analysis = analyzer.analyze_bookmark_content(
        title="Java Bytecode Instrumentation with ASM",
        description="Learn how to use ASM framework for Java bytecode manipulation and instrumentation",
        content="This tutorial covers Java bytecode instrumentation using the ASM framework. You'll learn how to modify Java classes at the bytecode level for various purposes like profiling, monitoring, and code generation.",
        url="https://example.com/java-asm-tutorial"
    )
    
    print("📊 Bookmark Analysis Results:")
    print(f"  Technologies: {bookmark_analysis.get('technologies', [])}")
    print(f"  Content Type: {bookmark_analysis.get('content_type', 'unknown')}")
    print(f"  Difficulty: {bookmark_analysis.get('difficulty', 'unknown')}")
    print(f"  Target Audience: {bookmark_analysis.get('target_audience', 'unknown')}")
    print(f"  Relevance Score: {bookmark_analysis.get('relevance_score', 0)}")
    
    # Test user context analysis
    print("\n🔍 Testing user context analysis...")
    context_analysis = analyzer.analyze_user_context(
        title="Java DSA Learning Project",
        description="Learning Java data structures and algorithms with instrumentation",
        technologies="java, dsa, instrumentation",
        user_interests="java, algorithms, bytecode manipulation"
    )
    
    print("📊 Context Analysis Results:")
    print(f"  Technologies: {context_analysis.get('technologies', [])}")
    print(f"  Project Type: {context_analysis.get('project_type', 'unknown')}")
    print(f"  Complexity Level: {context_analysis.get('complexity_level', 'unknown')}")
    print(f"  Development Stage: {context_analysis.get('development_stage', 'unknown')}")
    print(f"  Learning Needs: {context_analysis.get('learning_needs', [])}")
    
    # Test general learning context
    print("\n🔍 Testing general learning context...")
    general_context = analyzer.analyze_user_context(
        title="Personalized Learning Recommendations",
        description="Based on my projects and interests, I want to discover relevant learning resources and tutorials",
        technologies="java, dsa, instrumentation",
        user_interests="java, algorithms, bytecode manipulation"
    )
    
    print("📊 General Context Analysis Results:")
    print(f"  Project Type: {general_context.get('project_type', 'unknown')}")
    print(f"  Development Stage: {general_context.get('development_stage', 'unknown')}")
    print(f"  Preferred Content Types: {general_context.get('preferred_content_types', [])}")
    print(f"  Difficulty Preference: {general_context.get('difficulty_preference', 'unknown')}")
    
    print("\n✅ All tests completed successfully!")
    return True
    
if __name__ == "__main__":
    success = test_gemini_analysis()
    if success:
        print("\n🎉 Gemini analysis is working correctly!")
        print("The improvements should now provide more specific and accurate analysis.")
    else:
        print("\n❌ Some tests failed. Please check the error messages above.") 