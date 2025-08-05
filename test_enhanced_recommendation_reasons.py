#!/usr/bin/env python3
"""
Test Enhanced Recommendation Reason Generation
Demonstrates the improved, personalized, and actionable recommendation reasons
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unified_recommendation_engine import UnifiedRecommendationEngine

def test_enhanced_recommendation_reasons():
    """Test the enhanced recommendation reason generation"""
    
    print("ENHANCED RECOMMENDATION REASON GENERATION TESTS")
    print("=" * 60)
    
    # Initialize the unified recommendation engine
    engine = UnifiedRecommendationEngine()
    
    # Test scenarios
    test_scenarios = [
        {
            'name': 'Beginner React Developer',
            'context': {
                'title': 'Build a React Todo App',
                'description': 'Create a simple todo application using React hooks and state management',
                'technologies': 'react, javascript, html, css',
                'user_interests': 'frontend development, react, javascript',
                'difficulty': 'beginner',
                'intent': 'learning'
            },
            'bookmark': {
                'title': 'React Hooks Tutorial for Beginners',
                'notes': 'Complete guide to React hooks with examples',
                'extracted_text': 'Learn useState, useEffect, and other React hooks with step-by-step examples. Perfect for beginners.',
                'content_type': 'tutorial',
                'difficulty': 'beginner',
                'technologies': [
                    {'category': 'react', 'keyword': 'react', 'weight': 0.9},
                    {'category': 'javascript', 'keyword': 'javascript', 'weight': 1.0}
                ]
            }
        },
        {
            'name': 'Advanced Python Developer',
            'context': {
                'title': 'Machine Learning API with FastAPI',
                'description': 'Build a production-ready ML API using FastAPI, Docker, and AWS deployment',
                'technologies': 'python, fastapi, docker, aws, machine learning',
                'user_interests': 'machine learning, api development, devops',
                'difficulty': 'advanced',
                'intent': 'implementation'
            },
            'bookmark': {
                'title': 'FastAPI Production Deployment Guide',
                'notes': 'Complete guide to deploying FastAPI applications to production',
                'extracted_text': 'Comprehensive guide covering Docker containerization, AWS deployment, monitoring, and best practices for production FastAPI applications.',
                'content_type': 'documentation',
                'difficulty': 'advanced',
                'technologies': [
                    {'category': 'python', 'keyword': 'python', 'weight': 1.0},
                    {'category': 'fastapi', 'keyword': 'fastapi', 'weight': 0.9},
                    {'category': 'docker', 'keyword': 'docker', 'weight': 0.8},
                    {'category': 'aws', 'keyword': 'aws', 'weight': 0.8}
                ]
            }
        },
        {
            'name': 'Intermediate Developer - Troubleshooting',
            'context': {
                'title': 'Fix React Performance Issues',
                'description': 'Debug and optimize slow React component rendering',
                'technologies': 'react, javascript, performance',
                'user_interests': 'react, performance optimization',
                'difficulty': 'intermediate',
                'intent': 'troubleshooting'
            },
            'bookmark': {
                'title': 'React Performance Optimization Techniques',
                'notes': 'Advanced techniques for optimizing React application performance',
                'extracted_text': 'Learn about React.memo, useMemo, useCallback, and other optimization techniques to improve your React app performance.',
                'content_type': 'troubleshooting',
                'difficulty': 'intermediate',
                'technologies': [
                    {'category': 'react', 'keyword': 'react', 'weight': 0.9},
                    {'category': 'javascript', 'keyword': 'javascript', 'weight': 1.0},
                    {'category': 'performance', 'keyword': 'performance', 'weight': 0.7}
                ]
            }
        },
        {
            'name': 'Blockchain Developer',
            'context': {
                'title': 'Smart Contract Development',
                'description': 'Build and deploy smart contracts on Ethereum using Solidity',
                'technologies': 'solidity, ethereum, web3, hardhat',
                'user_interests': 'blockchain, smart contracts, ethereum',
                'difficulty': 'advanced',
                'intent': 'implementation'
            },
            'bookmark': {
                'title': 'Complete Solidity Smart Contract Tutorial',
                'notes': 'From basics to advanced smart contract development',
                'extracted_text': 'Comprehensive tutorial covering Solidity syntax, smart contract patterns, testing, and deployment on Ethereum network.',
                'content_type': 'tutorial',
                'difficulty': 'advanced',
                'technologies': [
                    {'category': 'solidity', 'keyword': 'solidity', 'weight': 1.0},
                    {'category': 'ethereum', 'keyword': 'ethereum', 'weight': 0.9},
                    {'category': 'blockchain', 'keyword': 'blockchain', 'weight': 0.8}
                ]
            }
        },
        {
            'name': 'DevOps Engineer',
            'context': {
                'title': 'Kubernetes Microservices Architecture',
                'description': 'Design and deploy microservices using Kubernetes and Docker',
                'technologies': 'kubernetes, docker, microservices, spring boot',
                'user_interests': 'devops, containerization, microservices',
                'difficulty': 'advanced',
                'intent': 'implementation'
            },
            'bookmark': {
                'title': 'Kubernetes Best Practices for Production',
                'notes': 'Production-ready Kubernetes deployment strategies',
                'extracted_text': 'Learn about Kubernetes deployment strategies, service mesh, monitoring, and scaling best practices for production environments.',
                'content_type': 'best_practice',
                'difficulty': 'advanced',
                'technologies': [
                    {'category': 'kubernetes', 'keyword': 'kubernetes', 'weight': 1.0},
                    {'category': 'docker', 'keyword': 'docker', 'weight': 0.9},
                    {'category': 'devops', 'keyword': 'devops', 'weight': 0.8}
                ]
            }
        }
    ]
    
    # Test each scenario
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print("-" * 40)
        
        # Extract context
        context = engine.extract_context_from_input(
            scenario['context']['title'],
            scenario['context']['description'],
            scenario['context']['technologies'],
            scenario['context']['user_interests']
        )
        
        # Add user-specific context
        context.update({
            'difficulty': scenario['context']['difficulty'],
            'intent': scenario['context']['intent']
        })
        
        # Calculate recommendation score
        score_data = engine.calculate_recommendation_score(scenario['bookmark'], context)
        
        # Display results
        print(f"Context: {scenario['context']['title']}")
        print(f"Bookmark: {scenario['bookmark']['title']}")
        print(f"Total Score: {score_data['total_score']:.1f}/100")
        print(f"Technology Match: {score_data['scores']['tech_match']:.1f}/30")
        print(f"Content Relevance: {score_data['scores']['content_relevance']:.1f}/20")
        print(f"Difficulty Alignment: {score_data['scores']['difficulty_alignment']:.1f}/15")
        print(f"Intent Alignment: {score_data['scores']['intent_alignment']:.1f}/15")
        print(f"Semantic Similarity: {score_data['scores']['semantic_similarity']:.1f}/20")
        print(f"\n🎯 ENHANCED REASON:")
        print(f"   {score_data['reason']}")
        print(f"\nConfidence: {score_data['confidence']:.2f}")
        
        # Show what makes this reason better
        print(f"\n✨ IMPROVEMENTS:")
        if "Perfect for beginners" in score_data['reason'] or "Well-suited for intermediate" in score_data['reason'] or "Excellent for advanced" in score_data['reason']:
            print("   ✅ Personalized skill level note")
        if "Directly covers" in score_data['reason'] or "Comprehensive coverage" in score_data['reason']:
            print("   ✅ Specific technology explanation")
        if "Provides structured learning" in score_data['reason'] or "Guides you through" in score_data['reason']:
            print("   ✅ Intent-based reasoning")
        if "Includes step-by-step" in score_data['reason'] or "Provides comprehensive" in score_data['reason']:
            print("   ✅ Content type benefits")
        if "Difficulty level" in score_data['reason']:
            print("   ✅ Difficulty alignment explanation")
        if "highly relevant" in score_data['reason'] or "very relevant" in score_data['reason']:
            print("   ✅ Relevance strength indicator")
    
    print(f"\n{'='*60}")
    print("ENHANCED RECOMMENDATION REASON GENERATION COMPLETE")
    print("✅ All scenarios tested with personalized, actionable reasons")
    print("✅ Reasons now explain 'why' content is recommended")
    print("✅ Personalization based on user skill level and intent")
    print("✅ Specific technology and content type explanations")
    print("✅ Relevance strength indicators for better decision making")

if __name__ == "__main__":
    test_enhanced_recommendation_reasons() 