#!/usr/bin/env python3
"""
Test script for simple text-based recommendations (no embeddings required)
"""

import requests
import json
import os
from datetime import datetime

# Configuration
API_BASE = 'http://localhost:5000/api'
JWT_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc1MzUxNjczNiwianRpIjoiYmM2NWMzNzAtMmEzMi00M2I5LTgzY2UtYTI0YzE1ZDQ2ZTQ0IiwidHlwZSI6ImFjY2VzcyIsInN1YiI6IjEiLCJuYmYiOjE3NTM1MTY3MzYsImV4cCI6MTc1MzUxNzYzNn0.I_8voB95gWPsbkRl8k4Yqdo24nzFaOKyVAjJcnMmNv4'

HEADERS = {
    'Authorization': f'Bearer {JWT_TOKEN}',
    'Content-Type': 'application/json',
}

def test_simple_general_recommendations():
    """Test the new simple general recommendations endpoint"""
    print("\n" + "="*60)
    print("TESTING SIMPLE GENERAL RECOMMENDATIONS")
    print("="*60)
    
    url = f'{API_BASE}/recommendations/simple-general'
    
    try:
        resp = requests.get(url, headers=HEADERS)
        print(f'Status Code: {resp.status_code}')
        
        if resp.status_code == 200:
            data = resp.json()
            print(f'Total bookmarks analyzed: {data.get("analysis", {}).get("total_bookmarks", 0)}')
            print(f'Relevant bookmarks found: {data.get("analysis", {}).get("relevant_bookmarks", 0)}')
            print(f'User interests: {data.get("analysis", {}).get("user_interests", "None")}')
            
            recommendations = data.get('recommendations', [])
            print(f'\nFound {len(recommendations)} recommendations:')
            
            for i, rec in enumerate(recommendations[:5], 1):  # Show top 5
                print(f'\n{i}. {rec["title"]}')
                print(f'   Score: {rec["score"]}%')
                print(f'   Reason: {rec["reason"]}')
                print(f'   URL: {rec["url"]}')
                if rec.get("analysis"):
                    analysis = rec["analysis"]
                    print(f'   Interest Similarity: {analysis.get("interest_similarity", 0)}%')
                    print(f'   Technologies: {", ".join(analysis.get("technologies", []))}')
        else:
            print(f'Error: {resp.text}')
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the API. Make sure the Flask app is running on localhost:5000")
    except Exception as e:
        print(f"ERROR: {e}")

def test_simple_project_recommendations(project_id=1):
    """Test the new simple project recommendations endpoint"""
    print("\n" + "="*60)
    print(f"TESTING SIMPLE PROJECT RECOMMENDATIONS (Project ID: {project_id})")
    print("="*60)
    
    url = f'{API_BASE}/recommendations/simple-project/{project_id}'
    
    try:
        resp = requests.get(url, headers=HEADERS)
        print(f'Status Code: {resp.status_code}')
        
        if resp.status_code == 200:
            data = resp.json()
            project_analysis = data.get("project_analysis", {})
            print(f'Project: {project_analysis.get("title", "Unknown")}')
            print(f'Project Technologies: {", ".join(project_analysis.get("technologies", []))}')
            print(f'Total bookmarks analyzed: {project_analysis.get("total_bookmarks_analyzed", 0)}')
            print(f'Relevant bookmarks found: {project_analysis.get("relevant_bookmarks_found", 0)}')
            
            recommendations = data.get('recommendations', [])
            print(f'\nFound {len(recommendations)} recommendations:')
            
            for i, rec in enumerate(recommendations[:5], 1):  # Show top 5
                print(f'\n{i}. {rec["title"]}')
                print(f'   Score: {rec["score"]}%')
                print(f'   Reason: {rec["reason"]}')
                print(f'   URL: {rec["url"]}')
                if rec.get("analysis"):
                    analysis = rec["analysis"]
                    print(f'   Text Similarity: {analysis.get("text_similarity", 0)}%')
                    print(f'   Tech Overlap: {analysis.get("tech_overlap", 0)}%')
                    print(f'   Bookmark Technologies: {", ".join(analysis.get("bookmark_technologies", []))}')
        else:
            print(f'Error: {resp.text}')
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the API. Make sure the Flask app is running on localhost:5000")
    except Exception as e:
        print(f"ERROR: {e}")

def test_health_check():
    """Test if the API is running"""
    print("\n" + "="*60)
    print("TESTING API HEALTH CHECK")
    print("="*60)
    
    try:
        resp = requests.get(f'{API_BASE}/health')
        print(f'Status Code: {resp.status_code}')
        if resp.status_code == 200:
            data = resp.json()
            print(f'API Status: {data.get("status")}')
            print(f'Database: {data.get("database")}')
            print(f'Version: {data.get("version")}')
        else:
            print(f'Error: {resp.text}')
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the API. Make sure the Flask app is running on localhost:5000")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == '__main__':
    print("Simple Text-Based Recommendations Test")
    print("="*60)
    print(f"Testing at: {datetime.now()}")
    
    # Test health first
    test_health_check()
    
    # Test simple recommendations
    test_simple_general_recommendations()
    test_simple_project_recommendations(project_id=1)
    
    print("\n" + "="*60)
    print("TEST COMPLETED")
    print("="*60) 