#!/usr/bin/env python3
"""
Test script to verify improved technology matching
"""

import re
from difflib import SequenceMatcher

def extract_technologies_from_text(text):
    """Extract technology keywords from text with improved precision"""
    if not text:
        return []
    
    tech_keywords = {
        'java': ['java', 'jvm', 'spring', 'maven', 'gradle', 'bytecode', 'asm', 'byte buddy'],
        'javascript': ['javascript', 'js', 'es6', 'es7', 'node', 'nodejs', 'node.js', 'react', 'reactjs', 'react.js', 'vue', 'vuejs', 'angular'],
        'python': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy', 'scipy'],
        'react': ['react', 'reactjs', 'react.js', 'react native', 'rn', 'jsx'],
        'react_native': ['react native', 'rn', 'expo', 'metro'],
        'mobile': ['mobile', 'ios', 'android', 'app', 'application', 'native', 'hybrid'],
        'web': ['web', 'html', 'css', 'frontend', 'backend', 'api', 'rest', 'graphql'],
        'database': ['database', 'sql', 'nosql', 'mongodb', 'postgresql', 'mysql', 'redis'],
        'ai_ml': ['ai', 'machine learning', 'ml', 'tensorflow', 'pytorch', 'neural', 'model'],
        'devops': ['devops', 'docker', 'kubernetes', 'ci/cd', 'deployment', 'aws', 'cloud'],
        'blockchain': ['blockchain', 'crypto', 'ethereum', 'bitcoin', 'smart contract', 'web3'],
        'payment': ['payment', 'stripe', 'paypal', 'upi', 'gateway', 'transaction'],
        'authentication': ['auth', 'authentication', 'oauth', 'jwt', 'login', 'signup'],
        'instrumentation': ['instrumentation', 'byte buddy', 'asm', 'bytecode', 'jvm'],
        'dsa': ['data structure', 'algorithm', 'dsa', 'sorting', 'searching', 'tree', 'graph']
    }
    
    text_lower = text.lower()
    found_techs = []
    
    # First pass: look for exact matches (longer keywords first)
    for tech_category, keywords in tech_keywords.items():
        # Sort keywords by length (longest first) to avoid partial matches
        sorted_keywords = sorted(keywords, key=len, reverse=True)
        
        for keyword in sorted_keywords:
            # Use word boundaries to avoid partial matches
            if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                found_techs.append(tech_category)
                break  # Only add each category once
    
    return list(set(found_techs))

def calculate_text_similarity(text1, text2):
    """Calculate similarity between two text strings using multiple methods with improved precision"""
    if not text1 or not text2:
        return 0.0
    
    # Method 1: Sequence matcher (good for overall similarity)
    sequence_similarity = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    # Method 2: Word overlap with better word extraction
    words1 = set(re.findall(r'\b\w+\b', text1.lower()))
    words2 = set(re.findall(r'\b\w+\b', text2.lower()))
    
    if not words1 or not words2:
        word_overlap = 0.0
    else:
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        word_overlap = len(intersection) / len(union) if union else 0.0
    
    # Method 3: Technology keyword matching (improved precision)
    tech_keywords = {
        'java': ['java', 'jvm', 'spring', 'maven', 'gradle', 'bytecode', 'asm', 'byte buddy'],
        'javascript': ['javascript', 'js', 'es6', 'es7', 'node', 'nodejs', 'node.js'],
        'react': ['react', 'reactjs', 'react.js', 'react native', 'rn'],
        'python': ['python', 'django', 'flask', 'fastapi'],
        'mobile': ['mobile', 'ios', 'android', 'app'],
        'web': ['web', 'html', 'css', 'frontend', 'backend'],
        'database': ['database', 'sql', 'nosql', 'mongodb', 'postgresql'],
        'ai_ml': ['ai', 'machine learning', 'ml', 'tensorflow', 'pytorch'],
        'dsa': ['data structure', 'algorithm', 'dsa', 'sorting', 'searching'],
        'instrumentation': ['instrumentation', 'byte buddy', 'asm', 'bytecode']
    }
    
    text1_lower = text1.lower()
    text2_lower = text2.lower()
    
    tech_matches = 0
    total_techs_found = 0
    
    for tech_category, keywords in tech_keywords.items():
        # Check if this technology appears in both texts
        tech_in_text1 = any(re.search(r'\b' + re.escape(kw) + r'\b', text1_lower) for kw in keywords)
        tech_in_text2 = any(re.search(r'\b' + re.escape(kw) + r'\b', text2_lower) for kw in keywords)
        
        if tech_in_text1 or tech_in_text2:
            total_techs_found += 1
            if tech_in_text1 and tech_in_text2:
                tech_matches += 1
    
    # Calculate technology similarity
    tech_score = tech_matches / max(1, total_techs_found) if total_techs_found > 0 else 0.0
    
    # Combine all methods (weighted average)
    final_similarity = (sequence_similarity * 0.3 + word_overlap * 0.3 + tech_score * 0.4)
    
    return final_similarity

def test_tech_extraction():
    """Test technology extraction with various texts"""
    print("="*60)
    print("TESTING TECHNOLOGY EXTRACTION")
    print("="*60)
    
    test_cases = [
        {
            "text": "DSA visualiser with java bytecode instrumentation using byte buddy",
            "expected": ["java", "instrumentation", "dsa"]
        },
        {
            "text": "React Native mobile app with JavaScript ES6 features",
            "expected": ["javascript", "react", "react_native", "mobile"]
        },
        {
            "text": "Java application with JVM bytecode manipulation",
            "expected": ["java"]
        },
        {
            "text": "JavaScript React application for web development",
            "expected": ["javascript", "react", "web"]
        },
        {
            "text": "Python Django web application with database",
            "expected": ["python", "web", "database"]
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}:")
        print(f"Text: {test_case['text']}")
        extracted = extract_technologies_from_text(test_case['text'])
        print(f"Extracted: {extracted}")
        print(f"Expected: {test_case['expected']}")
        print(f"✅ PASS" if set(extracted) == set(test_case['expected']) else "❌ FAIL")

def test_similarity_calculation():
    """Test similarity calculation between different tech stacks"""
    print("\n" + "="*60)
    print("TESTING SIMILARITY CALCULATION")
    print("="*60)
    
    # Your DSA project
    dsa_project = "DSA visualiser with java bytecode instrumentation using byte buddy"
    
    # Different bookmarks
    test_bookmarks = [
        {
            "title": "Java Bytecode Tutorial",
            "text": "Learn how to manipulate Java bytecode using ASM and Byte Buddy",
            "expected_high": True
        },
        {
            "title": "JavaScript React Tutorial", 
            "text": "Build a React application with JavaScript ES6 features",
            "expected_high": False
        },
        {
            "title": "Data Structures in Java",
            "text": "Implement data structures and algorithms in Java",
            "expected_high": True
        },
        {
            "title": "React Native Mobile App",
            "text": "Create mobile apps with React Native and JavaScript",
            "expected_high": False
        }
    ]
    
    print(f"Project: {dsa_project}")
    project_techs = extract_technologies_from_text(dsa_project)
    print(f"Project Technologies: {project_techs}")
    
    for i, bookmark in enumerate(test_bookmarks, 1):
        print(f"\nBookmark {i}: {bookmark['title']}")
        print(f"Text: {bookmark['text']}")
        
        bookmark_techs = extract_technologies_from_text(bookmark['text'])
        print(f"Bookmark Technologies: {bookmark_techs}")
        
        similarity = calculate_text_similarity(dsa_project, bookmark['text'])
        print(f"Similarity Score: {similarity:.3f} ({similarity*100:.1f}%)")
        
        is_high = similarity > 0.3
        expected = bookmark['expected_high']
        print(f"High Similarity (>30%): {is_high}")
        print(f"Expected High: {expected}")
        print(f"{'✅ PASS' if is_high == expected else '❌ FAIL'}")

if __name__ == '__main__':
    test_tech_extraction()
    test_similarity_calculation()
    print("\n" + "="*60)
    print("TEST COMPLETED")
    print("="*60) 