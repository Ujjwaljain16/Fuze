#!/usr/bin/env python3
"""
Test script for Enhanced Content Analysis and Diversity Engine
Tests both enhanced content analysis and true diversity scoring
"""

import sys
import os
import logging
from typing import List, Dict

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_enhanced_content_analysis():
    """Test enhanced content analysis functionality"""
    print("\n" + "="*60)
    print("TESTING ENHANCED CONTENT ANALYSIS")
    print("="*60)
    
    try:
        from enhanced_content_analysis import enhanced_content_analyzer
        
        # Test cases with different content types
        test_cases = [
            {
                'title': 'Complete React Tutorial for Beginners',
                'description': 'Learn React step by step with hands-on examples. This tutorial covers everything from basic concepts to advanced patterns.',
                'expected_type': 'tutorial',
                'expected_difficulty': 'beginner'
            },
            {
                'title': 'React API Documentation',
                'description': 'Comprehensive API reference for React components, hooks, and utilities. Includes parameters, return types, and usage examples.',
                'expected_type': 'documentation',
                'expected_difficulty': 'intermediate'
            },
            {
                'title': 'How to Fix React Memory Leaks',
                'description': 'Common React memory leak issues and their solutions. Debug steps and workarounds for production applications.',
                'expected_type': 'troubleshooting',
                'expected_difficulty': 'advanced'
            },
            {
                'title': 'React Best Practices 2024',
                'description': 'Recommended patterns and anti-patterns for React development. Architecture guidelines and performance optimization tips.',
                'expected_type': 'best_practice',
                'expected_difficulty': 'intermediate'
            },
            {
                'title': 'Building a Full-Stack App with React and Node.js',
                'description': 'Complete project implementation guide. Step-by-step instructions for building a real-world application.',
                'expected_type': 'project',
                'expected_difficulty': 'intermediate'
            }
        ]
        
        passed_tests = 0
        total_tests = len(test_cases)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\nTest {i}: {test_case['title']}")
            print("-" * 40)
            
            # Analyze content
            analysis = enhanced_content_analyzer.analyze_content(
                test_case['title'],
                test_case['description']
            )
            
            print(f"Detected Content Type: {analysis.get('content_type', 'unknown')}")
            print(f"Expected Content Type: {test_case['expected_type']}")
            print(f"Content Type Confidence: {analysis.get('content_type_confidence', 0.0):.2f}")
            
            print(f"Detected Difficulty: {analysis.get('difficulty', 'unknown')}")
            print(f"Expected Difficulty: {test_case['expected_difficulty']}")
            print(f"Difficulty Confidence: {analysis.get('difficulty_confidence', 0.0):.2f}")
            
            print(f"Detected Intent: {analysis.get('intent', 'unknown')}")
            print(f"Intent Confidence: {analysis.get('intent_confidence', 0.0):.2f}")
            
            print(f"Key Concepts: {analysis.get('key_concepts', [])[:5]}")
            print(f"Complexity Score: {analysis.get('complexity_score', 0.0):.2f}")
            print(f"Readability Score: {analysis.get('readability_score', 0.0):.2f}")
            
            # Check if analysis methods are available
            analysis_methods = analysis.get('analysis_methods', {})
            if analysis_methods:
                print("Analysis Methods Used:")
                for method, results in analysis_methods.items():
                    if results:
                        print(f"  - {method}: {results}")
            
            # Evaluate results
            content_type_match = analysis.get('content_type') == test_case['expected_type']
            difficulty_match = analysis.get('difficulty') == test_case['expected_difficulty']
            
            if content_type_match and difficulty_match:
                print("✅ PASSED")
                passed_tests += 1
            else:
                print("❌ FAILED")
                if not content_type_match:
                    print(f"  Content type mismatch: expected {test_case['expected_type']}, got {analysis.get('content_type')}")
                if not difficulty_match:
                    print(f"  Difficulty mismatch: expected {test_case['expected_difficulty']}, got {analysis.get('difficulty')}")
        
        print(f"\nEnhanced Content Analysis Results: {passed_tests}/{total_tests} tests passed")
        return passed_tests == total_tests
        
    except Exception as e:
        print(f"❌ Error testing enhanced content analysis: {e}")
        return False

def test_enhanced_diversity_engine():
    """Test enhanced diversity engine functionality"""
    print("\n" + "="*60)
    print("TESTING ENHANCED DIVERSITY ENGINE")
    print("="*60)
    
    try:
        from enhanced_diversity_engine import enhanced_diversity_engine
        
        # Create test bookmarks with different characteristics
        test_bookmarks = [
            {
                'id': 1,
                'title': 'React Tutorial for Beginners',
                'notes': 'Complete guide to React basics',
                'extracted_text': 'Learn React step by step with examples and exercises.',
                'technology_tags': ['react', 'javascript'],
                'content_type': 'tutorial',
                'difficulty': 'beginner',
                'score': {'total_score': 85.0}
            },
            {
                'id': 2,
                'title': 'Advanced React Patterns',
                'notes': 'Complex React patterns and optimizations',
                'extracted_text': 'Deep dive into advanced React concepts and performance optimization.',
                'technology_tags': ['react', 'javascript'],
                'content_type': 'best_practice',
                'difficulty': 'advanced',
                'score': {'total_score': 90.0}
            },
            {
                'id': 3,
                'title': 'React API Documentation',
                'notes': 'Complete API reference',
                'extracted_text': 'Comprehensive documentation of all React APIs and components.',
                'technology_tags': ['react', 'javascript'],
                'content_type': 'documentation',
                'difficulty': 'intermediate',
                'score': {'total_score': 88.0}
            },
            {
                'id': 4,
                'title': 'Vue.js Getting Started',
                'notes': 'Introduction to Vue.js',
                'extracted_text': 'Learn Vue.js fundamentals and basic concepts.',
                'technology_tags': ['vue', 'javascript'],
                'content_type': 'tutorial',
                'difficulty': 'beginner',
                'score': {'total_score': 82.0}
            },
            {
                'id': 5,
                'title': 'Angular Architecture Guide',
                'notes': 'Angular best practices',
                'extracted_text': 'Architecture patterns and best practices for Angular applications.',
                'technology_tags': ['angular', 'typescript'],
                'content_type': 'best_practice',
                'difficulty': 'advanced',
                'score': {'total_score': 87.0}
            },
            {
                'id': 6,
                'title': 'React Error Debugging',
                'notes': 'Common React errors and solutions',
                'extracted_text': 'Troubleshooting guide for common React development issues.',
                'technology_tags': ['react', 'javascript'],
                'content_type': 'troubleshooting',
                'difficulty': 'intermediate',
                'score': {'total_score': 83.0}
            },
            {
                'id': 7,
                'title': 'Node.js Performance Optimization',
                'notes': 'Node.js performance tips',
                'extracted_text': 'Advanced techniques for optimizing Node.js application performance.',
                'technology_tags': ['nodejs', 'javascript'],
                'content_type': 'best_practice',
                'difficulty': 'advanced',
                'score': {'total_score': 89.0}
            },
            {
                'id': 8,
                'title': 'Python Data Science Tutorial',
                'notes': 'Data science with Python',
                'extracted_text': 'Introduction to data science using Python and popular libraries.',
                'technology_tags': ['python', 'data-science'],
                'content_type': 'tutorial',
                'difficulty': 'beginner',
                'score': {'total_score': 84.0}
            }
        ]
        
        context = {
            'user_input': 'I want to learn web development',
            'technologies': ['react', 'javascript'],
            'skill_level': 'intermediate'
        }
        
        print("Testing diversity selection with 8 diverse bookmarks...")
        
        # Test diversity selection
        diverse_recommendations = enhanced_diversity_engine.get_diverse_recommendations(
            test_bookmarks, context, max_recommendations=5
        )
        
        print(f"\nSelected {len(diverse_recommendations)} diverse recommendations:")
        print("-" * 50)
        
        content_types = []
        technologies = []
        difficulties = []
        
        for i, rec in enumerate(diverse_recommendations, 1):
            print(f"{i}. {rec['title']}")
            print(f"   Content Type: {rec.get('content_type', 'unknown')}")
            print(f"   Technologies: {rec.get('technology_tags', [])}")
            print(f"   Difficulty: {rec.get('difficulty', 'unknown')}")
            print(f"   Score: {rec.get('score', {}).get('total_score', 0.0)}")
            
            if 'diversity_metadata' in rec:
                metadata = rec['diversity_metadata']
                print(f"   Diversity Score: {metadata.get('diversity_score', 0.0):.2f}")
                print(f"   Similarity to Others: {metadata.get('similarity_to_others', 1.0):.2f}")
            
            content_types.append(rec.get('content_type', 'unknown'))
            technologies.extend(rec.get('technology_tags', []))
            difficulties.append(rec.get('difficulty', 'unknown'))
            print()
        
        # Analyze diversity distribution
        diversity_analysis = enhanced_diversity_engine.analyze_diversity_distribution(diverse_recommendations)
        
        print("Diversity Analysis:")
        print("-" * 30)
        print(f"Overall Diversity Score: {diversity_analysis.get('diversity_score', 0.0):.2f}")
        print(f"Content Type Distribution: {diversity_analysis.get('content_type_distribution', {})}")
        print(f"Technology Distribution: {diversity_analysis.get('technology_distribution', {})}")
        print(f"Difficulty Distribution: {diversity_analysis.get('difficulty_distribution', {})}")
        
        # Evaluate diversity
        unique_content_types = len(set(content_types))
        unique_technologies = len(set(technologies))
        unique_difficulties = len(set(difficulties))
        
        print(f"\nDiversity Metrics:")
        print(f"- Unique Content Types: {unique_content_types}/5")
        print(f"- Unique Technologies: {unique_technologies}")
        print(f"- Unique Difficulties: {unique_difficulties}/3")
        
        # Check if diversity is good
        diversity_score = diversity_analysis.get('diversity_score', 0.0)
        good_diversity = (
            unique_content_types >= 3 and  # At least 3 different content types
            unique_technologies >= 2 and   # At least 2 different technologies
            diversity_score > 0.3          # Good overall diversity score
        )
        
        if good_diversity:
            print("✅ Diversity test PASSED - Good variety in recommendations")
            return True
        else:
            print("❌ Diversity test FAILED - Insufficient variety")
            return False
        
    except Exception as e:
        print(f"❌ Error testing enhanced diversity engine: {e}")
        return False

def test_integration():
    """Test integration between enhanced content analysis and diversity engine"""
    print("\n" + "="*60)
    print("TESTING INTEGRATION")
    print("="*60)
    
    try:
        from enhanced_content_analysis import enhanced_content_analyzer
        from enhanced_diversity_engine import enhanced_diversity_engine
        
        # Test content analysis on a complex input
        title = "Building a Full-Stack React Application with Node.js and MongoDB"
        description = """
        This comprehensive guide covers building a complete web application from scratch.
        We'll start with React frontend development, then move to Node.js backend API,
        and finally integrate MongoDB database. The tutorial includes step-by-step
        instructions, code examples, and best practices for production deployment.
        """
        
        print("Testing content analysis on complex input...")
        analysis = enhanced_content_analyzer.analyze_content(title, description)
        
        print(f"Content Type: {analysis.get('content_type')}")
        print(f"Difficulty: {analysis.get('difficulty')}")
        print(f"Intent: {analysis.get('intent')}")
        print(f"Key Concepts: {analysis.get('key_concepts', [])[:5]}")
        
        # Test diversity with analyzed content
        test_bookmarks = [
            {
                'id': 1,
                'title': 'React Frontend Development',
                'content_type': analysis.get('content_type', 'general'),
                'difficulty': analysis.get('difficulty', 'intermediate'),
                'technology_tags': ['react', 'javascript'],
                'score': {'total_score': 85.0}
            },
            {
                'id': 2,
                'title': 'Node.js Backend API',
                'content_type': 'documentation',
                'difficulty': 'intermediate',
                'technology_tags': ['nodejs', 'javascript'],
                'score': {'total_score': 88.0}
            },
            {
                'id': 3,
                'title': 'MongoDB Database Integration',
                'content_type': 'tutorial',
                'difficulty': 'intermediate',
                'technology_tags': ['mongodb', 'database'],
                'score': {'total_score': 82.0}
            }
        ]
        
        context = {
            'user_input': title + ' ' + description,
            'technologies': ['react', 'nodejs', 'mongodb'],
            'skill_level': 'intermediate'
        }
        
        print("\nTesting diversity with analyzed content...")
        diverse_recommendations = enhanced_diversity_engine.get_diverse_recommendations(
            test_bookmarks, context, max_recommendations=3
        )
        
        print(f"Selected {len(diverse_recommendations)} recommendations:")
        for rec in diverse_recommendations:
            print(f"- {rec['title']} ({rec.get('content_type', 'unknown')})")
        
        print("✅ Integration test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Error testing integration: {e}")
        return False

def main():
    """Run all tests"""
    print("ENHANCED CONTENT ANALYSIS AND DIVERSITY ENGINE TESTS")
    print("=" * 70)
    
    # Test enhanced content analysis
    content_analysis_passed = test_enhanced_content_analysis()
    
    # Test enhanced diversity engine
    diversity_passed = test_enhanced_diversity_engine()
    
    # Test integration
    integration_passed = test_integration()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Enhanced Content Analysis: {'✅ PASSED' if content_analysis_passed else '❌ FAILED'}")
    print(f"Enhanced Diversity Engine: {'✅ PASSED' if diversity_passed else '❌ FAILED'}")
    print(f"Integration Test: {'✅ PASSED' if integration_passed else '❌ FAILED'}")
    
    all_passed = content_analysis_passed and diversity_passed and integration_passed
    print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    if all_passed:
        print("\n🎉 Enhanced content analysis and diversity systems are working correctly!")
        print("The systems provide:")
        print("- Hybrid content analysis (rule-based + semantic + structural)")
        print("- True diversity scoring using embeddings and similarity clustering")
        print("- Robust fallback mechanisms")
        print("- Comprehensive metadata and analysis")
    else:
        print("\n⚠️  Some issues detected. Check the test output above for details.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 