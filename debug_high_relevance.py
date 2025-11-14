#!/usr/bin/env python3
"""
Debug script to test High Relevance Engine with React input
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from high_relevance_engine import high_relevance_engine

def debug_react_recommendations():
    """Debug React recommendations"""
    print("🔍 Debugging High Relevance Engine for React Input")
    print("=" * 60)
    
    # Test user input (same as in the test)
    user_input = {
        'title': 'React Development',
        'description': 'Building a React application',
        'technologies': 'React, JavaScript',
        'project_id': None
    }
    
    print(f"📝 User Input:")
    print(f"   Title: {user_input['title']}")
    print(f"   Description: {user_input['description']}")
    print(f"   Technologies: {user_input['technologies']}")
    print()
    
    # Analyze user input
    print("🔍 Step 1: Analyzing User Input")
    user_analysis = high_relevance_engine.analyze_user_input(user_input)
    print(f"   Exact Technologies: {user_analysis['exact_technologies']}")
    print(f"   Project Requirements: {user_analysis['project_requirements']}")
    print(f"   Content Type Needed: {user_analysis['content_type_needed']}")
    print(f"   Specific Tasks: {user_analysis['specific_tasks']}")
    print(f"   Urgency: {user_analysis['urgency']}")
    print()
    
    # Test with sample bookmarks
    test_bookmarks = [
        {
            'id': 1,
            'title': 'React Tutorial - Learn React in 2024',
            'url': 'https://example.com/react-tutorial',
            'extracted_text': 'Complete React tutorial with hooks, state management, and modern practices',
            'technologies': ['React', 'JavaScript', 'Hooks'],
            'quality_score': 8.5
        },
        {
            'id': 2,
            'title': 'Python Tutorial - Learn Python Programming',
            'url': 'https://example.com/python-tutorial',
            'extracted_text': 'Complete Python tutorial for beginners and advanced users',
            'technologies': ['Python', 'Programming'],
            'quality_score': 8.0
        },
        {
            'id': 3,
            'title': 'JavaScript Fundamentals',
            'url': 'https://example.com/javascript-fundamentals',
            'extracted_text': 'Learn JavaScript basics, ES6, and modern JavaScript features',
            'technologies': ['JavaScript', 'ES6'],
            'quality_score': 7.5
        },
        {
            'id': 4,
            'title': 'React Hooks Complete Guide',
            'url': 'https://example.com/react-hooks',
            'extracted_text': 'Master React Hooks: useState, useEffect, useContext, and custom hooks',
            'technologies': ['React', 'Hooks', 'JavaScript'],
            'quality_score': 9.0
        },
        {
            'id': 5,
            'title': 'Data Structures and Algorithms',
            'url': 'https://example.com/data-structures',
            'extracted_text': 'Learn data structures and algorithms in Python and JavaScript',
            'technologies': ['Python', 'JavaScript', 'Algorithms'],
            'quality_score': 8.0
        }
    ]
    
    print("🔍 Step 2: Testing with Sample Bookmarks")
    for i, bookmark in enumerate(test_bookmarks, 1):
        print(f"\n   Bookmark {i}: {bookmark['title']}")
        print(f"   Technologies: {bookmark['technologies']}")
        
        # Calculate scores
        scores = high_relevance_engine.calculate_high_relevance_score(bookmark, user_analysis)
        
        print(f"   Scores:")
        print(f"     Exact Tech Match: {scores['exact_tech_match']:.3f}")
        print(f"     Requirements Match: {scores['requirements_match']:.3f}")
        print(f"     Content Type Match: {scores['content_type_match']:.3f}")
        print(f"     Task Relevance: {scores['task_relevance']:.3f}")
        print(f"     Quality/Recency: {scores['quality_recency']:.3f}")
        
        # Calculate total score
        total_score = (
            scores['exact_tech_match'] * 0.35 +
            scores['requirements_match'] * 0.25 +
            scores['content_type_match'] * 0.20 +
            scores['task_relevance'] * 0.15 +
            scores['quality_recency'] * 0.05
        ) * 100
        
        if scores['exact_tech_match'] > 0.8:
            total_score += 20
        if scores['requirements_match'] > 0.7:
            total_score += 15
            
        print(f"     Total Score: {total_score:.1f}")
    
    print("\n🔍 Step 3: Getting Full Recommendations")
    recommendations = high_relevance_engine.get_high_relevance_recommendations(
        test_bookmarks, user_input, max_recommendations=3
    )
    
    print(f"\n📋 Final Recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. {rec['title']}")
        print(f"      Score: {rec['total_score']:.1f}")
        print(f"      Reason: {rec['reason']}")
        print()

if __name__ == "__main__":
    debug_react_recommendations() 