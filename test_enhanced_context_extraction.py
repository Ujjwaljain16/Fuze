#!/usr/bin/env python3
"""
Test script for Enhanced Context Extraction
Tests the enhanced context extraction with various scenarios
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

def test_enhanced_context_extraction():
    """Test enhanced context extraction functionality"""
    print("\n" + "="*60)
    print("TESTING ENHANCED CONTEXT EXTRACTION")
    print("="*60)

    try:
        from enhanced_context_extraction import enhanced_context_extractor

        # Test cases with different scenarios
        test_cases = [
            {
                'title': 'Build a React E-commerce App',
                'description': 'Create a full-stack e-commerce application using React, Node.js, and MongoDB. Include user authentication, payment integration, and admin dashboard.',
                'technologies': ['react', 'node', 'mongo', 'js'],
                'user_interests': ['web development', 'fullstack', 'e-commerce'],
                'expected_primary_techs': ['react', 'node.js', 'mongodb', 'javascript'],
                'expected_domains': ['web', 'database', 'authentication']
            },
            {
                'title': 'Machine Learning API with Python',
                'description': 'Develop a REST API for machine learning predictions using FastAPI, scikit-learn, and Docker. Deploy to AWS with CI/CD pipeline.',
                'technologies': ['python', 'fastapi', 'ml', 'docker', 'aws'],
                'user_interests': ['machine learning', 'api development', 'devops'],
                'expected_primary_techs': ['python', 'fastapi', 'machine learning', 'docker', 'aws'],
                'expected_domains': ['data', 'api', 'cloud', 'devops']
            },
            {
                'title': 'Mobile App with React Native',
                'description': 'Build a cross-platform mobile app for task management using React Native, Firebase, and Redux. Include push notifications and offline sync.',
                'technologies': ['react native', 'firebase', 'redux', 'js'],
                'user_interests': ['mobile development', 'react', 'firebase'],
                'expected_primary_techs': ['react native', 'firebase', 'redux', 'javascript'],
                'expected_domains': ['mobile', 'web', 'database']
            },
            {
                'title': 'Blockchain Smart Contract Development',
                'description': 'Create smart contracts for a decentralized application using Solidity, Web3.js, and Ethereum. Include testing with Hardhat and deployment to testnet.',
                'technologies': ['solidity', 'web3', 'ethereum', 'hardhat'],
                'user_interests': ['blockchain', 'smart contracts', 'web3'],
                'expected_primary_techs': ['solidity', 'web3', 'ethereum', 'hardhat'],
                'expected_domains': ['blockchain', 'web3']
            },
            {
                'title': 'Microservices Architecture with Kubernetes',
                'description': 'Design and implement a microservices architecture using Spring Boot, Docker, and Kubernetes. Include service discovery, load balancing, and monitoring.',
                'technologies': ['spring', 'docker', 'k8s', 'java'],
                'user_interests': ['microservices', 'devops', 'java'],
                'expected_primary_techs': ['spring boot', 'docker', 'kubernetes', 'java'],
                'expected_domains': ['cloud', 'devops', 'api']
            }
        ]

        passed_tests = 0
        total_tests = len(test_cases)

        for i, test_case in enumerate(test_cases, 1):
            print(f"\nTest {i}: {test_case['title']}")
            print("-" * 50)

            # Extract context
            extracted_context = enhanced_context_extractor.extract_context(
                test_case['title'],
                test_case['description'],
                test_case['technologies'],
                test_case['user_interests']
            )

            print(f"Primary Technologies: {extracted_context.primary_technologies}")
            print(f"Secondary Technologies: {extracted_context.secondary_technologies}")
            print(f"Core Domains: {extracted_context.core_domains}")
            print(f"Learning Objectives: {extracted_context.learning_objectives}")
            print(f"Complexity Score: {extracted_context.complexity:.2f}")
            print(f"Content Types Needed: {extracted_context.content_types_needed}")
            print(f"Implicit Requirements: {extracted_context.implicit_requirements}")
            print(f"Ambiguous Terms Resolved: {extracted_context.ambiguous_terms_resolved}")
            print(f"Confidence Score: {extracted_context.confidence_score:.2f}")

            # Check analysis metadata
            if hasattr(extracted_context, 'analysis_metadata'):
                print(f"Analysis Methods: {extracted_context.analysis_metadata.get('analysis_methods', [])}")

            # Evaluate results
            primary_tech_match = any(tech in extracted_context.primary_technologies 
                                   for tech in test_case['expected_primary_techs'])
            domain_match = any(domain in extracted_context.core_domains 
                             for domain in test_case['expected_domains'])

            if primary_tech_match and domain_match:
                print("✅ PASSED")
                passed_tests += 1
            else:
                print("❌ FAILED")
                if not primary_tech_match:
                    print(f"  Primary tech mismatch: expected {test_case['expected_primary_techs']}, got {extracted_context.primary_technologies}")
                if not domain_match:
                    print(f"  Domain mismatch: expected {test_case['expected_domains']}, got {extracted_context.core_domains}")

        print(f"\nEnhanced Context Extraction Results: {passed_tests}/{total_tests} tests passed")
        return passed_tests == total_tests

    except Exception as e:
        print(f"❌ Error testing enhanced context extraction: {e}")
        return False

def test_ambiguous_term_resolution():
    """Test ambiguous term resolution"""
    print("\n" + "="*60)
    print("TESTING AMBIGUOUS TERM RESOLUTION")
    print("="*60)

    try:
        from enhanced_context_extraction import enhanced_context_extractor

        # Test ambiguous terms
        ambiguous_terms = [
            'js', 'ts', 'node', 'mongo', 'k8s', 'api', 'auth', 'db', 'orm', 'cicd'
        ]

        print("Testing ambiguous term resolution...")
        resolved_terms = enhanced_context_extractor._resolve_ambiguous_terms(ambiguous_terms)
        resolved_dict = enhanced_context_extractor._resolve_ambiguous_terms_dict(ambiguous_terms)

        print(f"Original terms: {ambiguous_terms}")
        print(f"Resolved terms: {resolved_terms}")
        print(f"Resolution mapping: {resolved_dict}")

        # Check if ambiguous terms were resolved
        expected_resolutions = {
            'js': 'javascript',
            'ts': 'typescript',
            'node': 'node.js',
            'mongo': 'mongodb',
            'k8s': 'kubernetes',
            'api': 'api development',
            'auth': 'authentication',
            'db': 'database',
            'orm': 'object relational mapping',
            'cicd': 'continuous integration'
        }

        correct_resolutions = 0
        total_resolutions = len(ambiguous_terms)

        for original, resolved in resolved_dict.items():
            if resolved == expected_resolutions.get(original, original):
                correct_resolutions += 1

        print(f"Resolution accuracy: {correct_resolutions}/{total_resolutions}")

        if correct_resolutions >= total_resolutions * 0.8:  # 80% accuracy threshold
            print("✅ Ambiguous term resolution PASSED")
            return True
        else:
            print("❌ Ambiguous term resolution FAILED")
            return False

    except Exception as e:
        print(f"❌ Error testing ambiguous term resolution: {e}")
        return False

def test_implicit_requirements_extraction():
    """Test implicit requirements extraction"""
    print("\n" + "="*60)
    print("TESTING IMPLICIT REQUIREMENTS EXTRACTION")
    print("="*60)

    try:
        from enhanced_context_extraction import enhanced_context_extractor

        # Test cases for implicit requirements
        test_cases = [
            {
                'title': 'React Todo App',
                'description': 'Build a todo application with React hooks and local storage',
                'technologies': ['react'],
                'expected_requirements': ['JavaScript/TypeScript knowledge']
            },
            {
                'title': 'Database Design Project',
                'description': 'Design and implement a database schema for an e-commerce system',
                'technologies': ['mongodb', 'postgresql'],
                'expected_requirements': ['Database design understanding']
            },
            {
                'title': 'REST API Development',
                'description': 'Create RESTful APIs for a social media platform',
                'technologies': ['node.js', 'express'],
                'expected_requirements': ['HTTP and REST knowledge']
            },
            {
                'title': 'Production Deployment',
                'description': 'Deploy the application to production with monitoring',
                'technologies': ['docker', 'aws'],
                'expected_requirements': ['Deployment and hosting knowledge']
            }
        ]

        passed_tests = 0
        total_tests = len(test_cases)

        for i, test_case in enumerate(test_cases, 1):
            print(f"\nTest {i}: {test_case['title']}")
            print("-" * 30)

            implicit_reqs = enhanced_context_extractor._extract_implicit_requirements(
                test_case['title'],
                test_case['description'],
                test_case['technologies']
            )

            print(f"Extracted implicit requirements: {implicit_reqs}")
            print(f"Expected requirements: {test_case['expected_requirements']}")

            # Check if expected requirements are found
            found_requirements = sum(1 for req in test_case['expected_requirements'] 
                                  if any(req.lower() in impl_req.lower() for impl_req in implicit_reqs))

            if found_requirements > 0:
                print("✅ PASSED")
                passed_tests += 1
            else:
                print("❌ FAILED")

        print(f"\nImplicit Requirements Extraction Results: {passed_tests}/{total_tests} tests passed")
        return passed_tests >= total_tests * 0.7  # 70% accuracy threshold

    except Exception as e:
        print(f"❌ Error testing implicit requirements extraction: {e}")
        return False

def test_integration_with_unified_engine():
    """Test integration with unified recommendation engine"""
    print("\n" + "="*60)
    print("TESTING INTEGRATION WITH UNIFIED ENGINE")
    print("="*60)

    try:
        from unified_recommendation_engine import UnifiedRecommendationEngine

        # Create unified engine instance
        engine = UnifiedRecommendationEngine()

        # Test context extraction
        title = "Build a Full-Stack React Application"
        description = "Create a complete web application with React frontend, Node.js backend, and MongoDB database"
        technologies = "react, node, mongo, js"
        user_interests = "web development, fullstack, javascript"

        print("Testing context extraction with unified engine...")
        context = engine.extract_context_from_input(title, description, technologies, user_interests)

        print(f"Extracted Context:")
        print(f"- Technologies: {context.get('technologies', [])}")
        print(f"- Content Type: {context.get('content_type', 'unknown')}")
        print(f"- Difficulty: {context.get('difficulty', 'unknown')}")
        print(f"- Intent: {context.get('intent', 'unknown')}")
        print(f"- Key Concepts: {context.get('key_concepts', [])}")
        print(f"- Requirements: {context.get('requirements', [])}")
        print(f"- Complexity Score: {context.get('complexity_score', 0.0):.2f}")

        # Check if enhanced features are available
        enhanced_features = [
            'primary_technologies',
            'secondary_technologies', 
            'core_domains',
            'learning_objectives',
            'content_types_needed',
            'ambiguous_terms_resolved',
            'confidence_score',
            'analysis_metadata'
        ]

        available_features = sum(1 for feature in enhanced_features if feature in context)
        total_features = len(enhanced_features)

        print(f"\nEnhanced Features Available: {available_features}/{total_features}")

        if available_features >= total_features * 0.8:  # 80% of features should be available
            print("✅ Integration test PASSED")
            return True
        else:
            print("❌ Integration test FAILED")
            return False

    except Exception as e:
        print(f"❌ Error testing integration: {e}")
        return False

def main():
    """Run all tests"""
    print("ENHANCED CONTEXT EXTRACTION TESTS")
    print("=" * 70)

    # Test enhanced context extraction
    context_extraction_passed = test_enhanced_context_extraction()

    # Test ambiguous term resolution
    ambiguous_resolution_passed = test_ambiguous_term_resolution()

    # Test implicit requirements extraction
    implicit_requirements_passed = test_implicit_requirements_extraction()

    # Test integration with unified engine
    integration_passed = test_integration_with_unified_engine()

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Enhanced Context Extraction: {'✅ PASSED' if context_extraction_passed else '❌ FAILED'}")
    print(f"Ambiguous Term Resolution: {'✅ PASSED' if ambiguous_resolution_passed else '❌ FAILED'}")
    print(f"Implicit Requirements: {'✅ PASSED' if implicit_requirements_passed else '❌ FAILED'}")
    print(f"Integration Test: {'✅ PASSED' if integration_passed else '❌ FAILED'}")

    all_passed = (context_extraction_passed and ambiguous_resolution_passed and 
                  implicit_requirements_passed and integration_passed)
    print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

    if all_passed:
        print("\n🎉 Enhanced context extraction system is working correctly!")
        print("The system provides:")
        print("- Gemini-powered context analysis")
        print("- Ambiguous term resolution")
        print("- Implicit requirements detection")
        print("- Comprehensive technology mapping")
        print("- Integration with unified recommendation engine")
    else:
        print("\n⚠️  Some issues detected. Check the test output above for details.")

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 