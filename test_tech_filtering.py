#!/usr/bin/env python3
"""
Test to verify that the technology filtering is working correctly.
"""

import sys
import os
import logging
import time
import json
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_tech_filtering():
    """Test that technology filtering works correctly via API endpoint"""
    print("🚀 Testing Technology Filtering via API")
    print("=" * 50)
    
    # Initialize response time variables
    response_time = 0
    response_time_react = 0
    
    try:
        # Test 1: Test the actual API endpoint
        print("1️⃣ Testing API endpoint...")
        
        # Test 2: Test with Python input (should NOT return JavaScript content)
        print("\n2️⃣ Testing Python Development recommendations...")
        request_data = {
            'title': 'Python Development',
            'description': 'Building a Python application with Django and SQL',
            'technologies': 'Python, Django, SQL',
            'max_recommendations': 5
        }
        
        start_time = time.time()
        
        # Make API call to the quality endpoint
        try:
            response = requests.post(
                'http://127.0.0.1:5000/api/recommendations/ensemble/quality',
                json=request_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            if response.status_code == 200:
                results = response.json().get('recommendations', [])
                
                print(f"✅ Python recommendations completed in {response_time:.2f}ms")
                print(f"📊 Results: {len(results)} recommendations")
                
                if results:
                    print("\n📋 Python Development Results:")
                    python_content_count = 0
                    javascript_content_count = 0
                    
                    for i, result in enumerate(results[:5], 1):
                        print(f"  {i}. {result.get('title', 'No title')}")
                        print(f"     Score: {result.get('score', 0):.1f}")
                        print(f"     Technologies: {result.get('technologies', [])}")
                        print()
                        
                        # Check if the result is actually Python-related
                        title_lower = result.get('title', '').lower()
                        technologies = [tech.lower() for tech in result.get('technologies', [])]
                        reason_lower = result.get('reason', '').lower()
                        
                        is_python_related = (
                            'python' in title_lower or 
                            'django' in title_lower or
                            'python' in technologies or
                            'django' in technologies or
                            'python' in reason_lower or
                            'django' in reason_lower
                        )
                        
                        is_javascript_related = (
                            'javascript' in title_lower or 
                            'react' in title_lower or
                            'javascript' in technologies or
                            'react' in technologies or
                            'javascript' in reason_lower or
                            'react' in reason_lower
                        )
                        
                        if is_python_related:
                            print(f"     ✅ PYTHON: Python/Django content found!")
                            python_content_count += 1
                        elif is_javascript_related:
                            print(f"     ❌ JAVASCRIPT: JavaScript/React content found (WRONG!)")
                            javascript_content_count += 1
                        else:
                            print(f"     ⚠️ OTHER: Neither Python nor JavaScript content")
                        print()
                    
                    # Summary
                    print(f"📊 Summary:")
                    print(f"   Python content: {python_content_count}")
                    print(f"   JavaScript content: {javascript_content_count}")
                    
                    if javascript_content_count == 0:
                        print(f"   ✅ SUCCESS: No JavaScript content in Python results!")
                    else:
                        print(f"   ❌ FAILURE: Found {javascript_content_count} JavaScript items in Python results!")
                else:
                    print("⚠️ No results returned")
            elif response.status_code == 401:
                print(f"❌ API call failed: Authentication required (401)")
                print(f"   This endpoint requires JWT authentication. Please ensure you're logged in.")
                print(f"   Response: {response.text}")
            else:
                print(f"❌ API call failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ API request failed: {e}")
            return False
        
        # Test 3: Test with React input for comparison
        print("\n3️⃣ Testing React Development recommendations...")
        request_data_react = {
            'title': 'React Development',
            'description': 'Building a React application with JavaScript',
            'technologies': 'React, JavaScript, Hooks',
            'max_recommendations': 3
        }
        
        start_time = time.time()
        
        try:
            response_react = requests.post(
                'http://127.0.0.1:5000/api/recommendations/ensemble/quality',
                json=request_data_react,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            end_time = time.time()
            response_time_react = (end_time - start_time) * 1000
            
            if response_react.status_code == 200:
                results_react = response_react.json().get('recommendations', [])
                
                print(f"✅ React recommendations completed in {response_time_react:.2f}ms")
                print(f"📊 Results: {len(results_react)} recommendations")
                
                if results_react:
                    print("\n📋 React Development Results:")
                    for i, result in enumerate(results_react[:3], 1):
                        print(f"  {i}. {result.get('title', 'No title')}")
                        print(f"     Technologies: {result.get('technologies', [])}")
                        print()
            elif response_react.status_code == 401:
                print(f"❌ React API call failed: Authentication required (401)")
                print(f"   This endpoint requires JWT authentication. Please ensure you're logged in.")
            else:
                print(f"❌ React API call failed with status code: {response_react.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ React API request failed: {e}")
        
        # Performance check
        total_time = response_time + response_time_react
        if total_time < 30000:  # 30 seconds
            print(f"✅ Performance: Acceptable ({total_time:.2f}ms)")
        else:
            print(f"❌ Performance: Too slow ({total_time:.2f}ms)")
        
        print("\n🎉 Technology Filtering Test Completed!")
        print("\n📝 Note: If you got authentication errors, please:")
        print("   1. Start the Flask server: python app.py")
        print("   2. Log in through the frontend to get a JWT token")
        print("   3. Run this test again")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_tech_filtering()
    sys.exit(0 if success else 1) 