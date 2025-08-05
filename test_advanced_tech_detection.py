#!/usr/bin/env python3
"""
Test script to demonstrate advanced technology detection using spaCy
"""

from advanced_tech_detection import advanced_tech_detector

def test_advanced_technology_detection():
    """Test various scenarios for advanced technology detection"""
    
    test_cases = [
        {
            "title": "Multi-word terms",
            "text": "This tutorial covers machine learning algorithms and deep learning neural networks for data science applications.",
            "expected": ["ai_ml"]
        },
        {
            "title": "Contextual mentions",
            "text": "We used Java for backend development with Spring Framework and implemented authentication using JWT tokens.",
            "expected": ["java", "authentication"]
        },
        {
            "title": "Similar terms",
            "text": "Building a Node.js server with Express.js and implementing React components for the frontend.",
            "expected": ["javascript", "react"]
        },
        {
            "title": "Ambiguous terms",
            "text": "Spring Framework provides excellent dependency injection for Java applications.",
            "expected": ["java"]
        },
        {
            "title": "Data structures and algorithms",
            "text": "Implementing binary search trees and sorting algorithms for efficient data processing.",
            "expected": ["dsa"]
        },
        {
            "title": "Mixed technologies",
            "text": "Building a full-stack application with React frontend, Python Flask backend, and PostgreSQL database.",
            "expected": ["react", "python", "database"]
        },
        {
            "title": "Complex project description",
            "text": "Developing a machine learning model using TensorFlow and PyTorch for natural language processing. The backend is built with Java Spring Boot and uses Redis for caching. Frontend is developed with React and TypeScript.",
            "expected": ["ai_ml", "java", "react", "database"]
        }
    ]
    
    print("Testing Advanced Technology Detection")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['title']}")
        print(f"Text: {test_case['text']}")
        
        # Extract technologies using advanced detection
        detected_techs = advanced_tech_detector.extract_technologies(test_case['text'])
        
        print("Detected technologies:")
        for tech in detected_techs:
            print(f"  - {tech['category']} ({tech['keyword']}) - Confidence: {tech['confidence']:.2f} - Method: {tech['method']}")
        
        # Check if expected technologies were found
        detected_categories = {tech['category'] for tech in detected_techs}
        expected_categories = set(test_case['expected'])
        
        matches = detected_categories.intersection(expected_categories)
        if matches:
            print(f"✅ Found expected technologies: {', '.join(matches)}")
        else:
            print(f"❌ Expected: {', '.join(expected_categories)}, Found: {', '.join(detected_categories)}")
        
        print("-" * 50)

def test_fallback_detection():
    """Test fallback detection when spaCy is not available"""
    print("\nTesting Fallback Detection")
    print("=" * 30)
    
    # Temporarily disable spaCy
    original_nlp = advanced_tech_detector.nlp
    advanced_tech_detector.nlp = None
    
    test_text = "Building a Java application with Spring Framework and machine learning algorithms."
    detected_techs = advanced_tech_detector.extract_technologies(test_text)
    
    print(f"Text: {test_text}")
    print("Detected technologies (fallback):")
    for tech in detected_techs:
        print(f"  - {tech['category']} ({tech['keyword']}) - Confidence: {tech['confidence']:.2f} - Method: {tech['method']}")
    
    # Restore spaCy
    advanced_tech_detector.nlp = original_nlp

def test_confidence_scores():
    """Test confidence scores for different detection methods"""
    print("\nTesting Confidence Scores")
    print("=" * 30)
    
    test_texts = [
        "Machine learning tutorial with TensorFlow",
        "Java Spring Framework development",
        "React components with TypeScript",
        "Python data science with pandas"
    ]
    
    for text in test_texts:
        detected_techs = advanced_tech_detector.extract_technologies(text)
        print(f"\nText: {text}")
        for tech in detected_techs:
            print(f"  {tech['category']}: {tech['confidence']:.2f} confidence ({tech['method']})")

if __name__ == "__main__":
    try:
        test_advanced_technology_detection()
        test_confidence_scores()
        test_fallback_detection()
        print("\n✅ All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc() 