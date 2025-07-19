#!/usr/bin/env python3
"""
Test script for recommendations functionality
"""

import requests
import json

# Set these as needed
API_URL = 'http://localhost:5000/api/recommendations'
JWT_TOKEN = 'YOUR_JWT_TOKEN_HERE'  # Replace with a valid token for user_id=1

HEADERS = {
    'Authorization': f'Bearer {JWT_TOKEN}',
    'Content-Type': 'application/json',
}

def test_general_recommendations():
    url = f'{API_URL}/general'
    resp = requests.get(url, headers=HEADERS)
    print('\n--- General Recommendations ---')
    print('Status:', resp.status_code)
    print(json.dumps(resp.json(), indent=2))

def test_project_recommendations(project_id):
    url = f'{API_URL}/project/{project_id}'
    resp = requests.get(url, headers=HEADERS)
    print(f'\n--- Project Recommendations for project_id={project_id} ---')
    print('Status:', resp.status_code)
    print(json.dumps(resp.json(), indent=2))

if __name__ == '__main__':
    test_general_recommendations()
    test_project_recommendations(project_id=1)  # Change project_id as needed 