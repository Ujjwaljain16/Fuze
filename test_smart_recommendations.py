#!/usr/bin/env python3
"""
Test script for smart recommendations
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from smart_recommendation_engine import get_smart_recommendations

def test_react_native_recommendations():
    """Test React Native project recommendations"""
    print("Testing React Native project recommendations...")
    
    test_project = {
        'title': 'React Native Mobile App',
        'description': 'Building a cross-platform mobile application',
        'technologies': 'react native, javascript',
        'learning_goals': 'Master React Native development and mobile app creation'
    }
    
    recommendations = get_smart_recommendations(1, test_project, 5)
    
    print(f"\nFound {len(recommendations)} recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['title']}")
        print(f"   URL: {rec['url']}")
        print(f"   Match Score: {rec['match_score']:.1f}%")
        print(f"   Technologies: {', '.join(rec['technologies'])}")
        print(f"   Learning Path Fit: {rec['learning_path_fit']:.1f}%")
        print(f"   Project Applicability: {rec['project_applicability']:.1f}%")
        print(f"   Skill Development: {rec['skill_development']:.1f}%")
        print(f"   Reasoning: {rec['reasoning'][:100]}...")

def test_go_recommendations():
    """Test Go language project recommendations"""
    print("\n" + "="*50)
    print("Testing Go language project recommendations...")
    
    test_project = {
        'title': 'Go Backend API',
        'description': 'Building a high-performance backend API',
        'technologies': 'go, golang',
        'learning_goals': 'Master Go programming and backend development'
    }
    
    recommendations = get_smart_recommendations(1, test_project, 5)
    
    print(f"\nFound {len(recommendations)} recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['title']}")
        print(f"   URL: {rec['url']}")
        print(f"   Match Score: {rec['match_score']:.1f}%")
        print(f"   Technologies: {', '.join(rec['technologies'])}")
        print(f"   Learning Path Fit: {rec['learning_path_fit']:.1f}%")
        print(f"   Project Applicability: {rec['project_applicability']:.1f}%")
        print(f"   Skill Development: {rec['skill_development']:.1f}%")
        print(f"   Reasoning: {rec['reasoning'][:100]}...")

if __name__ == "__main__":
    test_react_native_recommendations()
    test_go_recommendations() 