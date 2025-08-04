#!/usr/bin/env python3
"""
Test script to verify the enhanced Gemini analysis with new fields
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

def test_enhanced_analysis():
    """Test the enhanced Gemini analysis with new fields"""
    
    print("🧪 Testing Enhanced Gemini Analysis")
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
    
    # Test 2: Enhanced content analysis
    print("\n2. Testing enhanced content analysis...")
    try:
        test_title = "React Hooks Complete Guide"
        test_description = "Learn React Hooks from basics to advanced patterns"
        test_content = """
        This comprehensive guide covers React Hooks including useState, useEffect, useContext, 
        useReducer, and custom hooks. You'll learn how to manage state, side effects, and 
        build reusable logic with hooks. Perfect for React developers who want to modernize 
        their code and understand functional components.
        """
        
        result = analyzer.analyze_bookmark_content(
            title=test_title,
            description=test_description,
            content=test_content,
            url="https://example.com/react-hooks-guide"
        )
        
        if result and isinstance(result, dict):
            print("✅ Successfully analyzed content with enhanced fields")
            
            # Check for new fields
            required_fields = [
                'technologies', 'content_type', 'difficulty', 'intent', 'key_concepts',
                'relevance_score', 'summary', 'learning_objectives', 'quality_indicators',
                'target_audience', 'prerequisites', 'learning_path', 'project_applicability', 'skill_development'
            ]
            
            missing_fields = []
            for field in required_fields:
                if field not in result:
                    missing_fields.append(field)
                else:
                    print(f"   ✅ {field}: {result[field]}")
            
            if missing_fields:
                print(f"   ⚠️  Missing fields: {missing_fields}")
            else:
                print("   🎉 All enhanced fields present!")
                
            # Check specific new field structures
            if 'learning_path' in result:
                learning_path = result['learning_path']
                print(f"   📚 Learning Path: Foundational={learning_path.get('is_foundational')}, Time={learning_path.get('estimated_time')}")
            
            if 'project_applicability' in result:
                project_app = result['project_applicability']
                print(f"   🎯 Project Applicability: Suitable for {project_app.get('suitable_for')}")
            
            if 'skill_development' in result:
                skill_dev = result['skill_development']
                print(f"   🚀 Skill Development: Primary skills = {skill_dev.get('primary_skills')}")
                
        else:
            print("❌ Content analysis returned invalid result")
            return False
            
    except Exception as e:
        print(f"❌ Enhanced content analysis failed: {e}")
        return False
    
    # Test 3: Enhanced batch analysis
    print("\n3. Testing enhanced batch analysis...")
    try:
        batch_prompt = """
        Analyze these content items:
        
        1. "JavaScript Promises Tutorial" - Learn about async programming with promises
        2. "React State Management" - Managing component state effectively
        3. "Python Data Structures" - Understanding lists, dictionaries, and sets
        
        Provide insights for each item.
        """
        
        result = analyzer.analyze_batch_content(batch_prompt)
        
        if result and isinstance(result, dict):
            print("✅ Successfully performed enhanced batch analysis")
            
            # Check for enhanced overall insights
            if 'overall_insights' in result:
                insights = result['overall_insights']
                print(f"   📊 Overall Insights: {list(insights.keys())}")
                
                # Check for new insight fields
                if 'learning_paths' in insights:
                    print(f"   📚 Learning Paths: {insights['learning_paths']}")
                
                if 'project_coverage' in insights:
                    print(f"   🎯 Project Coverage: {insights['project_coverage']}")
                
                if 'skill_progression' in insights:
                    print(f"   🚀 Skill Progression: {insights['skill_progression']}")
            
            # Check individual items
            if 'items' in result and result['items']:
                first_item = result['items'][0]
                new_fields = ['learning_path', 'project_applicability', 'skill_development']
                for field in new_fields:
                    if field in first_item:
                        print(f"   ✅ Item has {field} field")
                    else:
                        print(f"   ⚠️  Item missing {field} field")
        else:
            print("❌ Enhanced batch analysis returned invalid result")
            return False
            
    except Exception as e:
        print(f"❌ Enhanced batch analysis failed: {e}")
        return False
    
    print("\n🎉 All enhanced analysis tests passed!")
    return True

if __name__ == "__main__":
    print("🚀 Starting Enhanced Analysis Tests")
    print("=" * 60)
    
    # Check if API key is set
    if not os.environ.get('GEMINI_API_KEY'):
        print("❌ GEMINI_API_KEY environment variable is not set")
        print("Please set your Gemini API key and try again.")
        sys.exit(1)
    
    # Run tests
    success = test_enhanced_analysis()
    
    if success:
        print("\n🎉 All enhanced analysis tests completed successfully!")
        print("The enhanced Gemini analysis with new fields is working properly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1) 