#!/usr/bin/env python3
"""
Test script for Gemini batch processing and performance metrics fixes
"""

import requests
import json
import os
from pathlib import Path

def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path(".env")
    if env_file.exists():
        print("📁 Loading environment variables from .env file...")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print("✅ Environment variables loaded successfully!")
    else:
        print("⚠️  .env file not found")

# Load environment variables at module level
load_env_file()

def get_auth_token():
    """Get authentication token by logging in"""
    try:
        login_data = {
            "email": "jainujjwal1609@gmail.com",
            "password": "Jainsahab@16"
        }
        
        response = requests.post(
            'http://127.0.0.1:5000/api/auth/login',
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('access_token')
        else:
            print(f"❌ Login failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Login exception: {e}")
        return None

def test_performance_metrics():
    """Test performance metrics endpoint"""
    print("🔍 Testing Performance Metrics Fix")
    print("=" * 40)
    
    token = get_auth_token()
    if not token:
        print("❌ Could not get authentication token")
        return
    
    try:
        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        response = requests.get(
            'http://127.0.0.1:5000/api/recommendations/performance-metrics',
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Performance metrics retrieved successfully!")
            
            if 'metrics' in result:
                metrics = result['metrics']
                print(f"📊 Smart Match Accuracy: {metrics.get('smart_match', {}).get('accuracy', 'N/A')}%")
                print(f"📊 Power Boost Accuracy: {metrics.get('power_boost', {}).get('accuracy', 'N/A')}%")
                print(f"📊 Genius Mode Accuracy: {metrics.get('genius_mode', {}).get('accuracy', 'N/A')}%")
                print(f"📊 Overall Accuracy: {metrics.get('overall', {}).get('average_accuracy', 'N/A')}%")
                print(f"📊 User Satisfaction: {metrics.get('overall', {}).get('user_satisfaction', 'N/A')}%")
                
                # Check for NaN values
                has_nan = False
                for phase in ['smart_match', 'power_boost', 'genius_mode', 'overall']:
                    if phase in metrics:
                        for key, value in metrics[phase].items():
                            if isinstance(value, (int, float)) and (value != value or str(value).lower() == 'nan'):
                                has_nan = True
                                print(f"⚠️  Found NaN in {phase}.{key}: {value}")
                
                if not has_nan:
                    print("✅ No NaN values found in performance metrics!")
                else:
                    print("❌ Found NaN values in performance metrics")
            else:
                print("❌ No metrics found in response")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_gemini_batch_processing():
    """Test Gemini batch processing in Phase 3"""
    print("\n🧠 Testing Gemini Batch Processing")
    print("=" * 40)
    
    token = get_auth_token()
    if not token:
        print("❌ Could not get authentication token")
        return
    
    # Test data for DSA visualizer project
    test_data = {
        "project_title": "DSA Visualizer",
        "project_description": "I want to build an interactive data structure and algorithm visualizer",
        "technologies": "javascript, html, css, canvas",
        "learning_goals": "Master data structures and algorithms through interactive visualization",
        "content_type": "all",
        "difficulty": "all",
        "max_recommendations": 5,
        "use_phase1": False,
        "use_phase2": False,
        "use_phase3": True,
        "use_gemini": True
    }
    
    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        response = requests.post(
            'http://127.0.0.1:5000/api/recommendations/unified',
            json=test_data,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Gemini batch processing test completed!")
            
            recommendations = result.get('recommendations', [])
            print(f"📊 Generated {len(recommendations)} recommendations")
            
            # Check for Gemini-enhanced recommendations
            gemini_enhanced = 0
            for rec in recommendations:
                if rec.get('algorithm_used') == 'phase3_gemini_enhanced_genius_mode':
                    gemini_enhanced += 1
                    print(f"🧠 Gemini Enhanced: {rec.get('title', 'No title')}")
                    print(f"   Score: {rec.get('score', 0):.1f}")
                    print(f"   Reasoning: {rec.get('reasoning', 'No reasoning')[:100]}...")
                    print()
            
            if gemini_enhanced > 0:
                print(f"✅ Found {gemini_enhanced} Gemini-enhanced recommendations!")
            else:
                print("⚠️  No Gemini-enhanced recommendations found (may be using fallback)")
            
            # Check for enhanced scores (above 10.0)
            enhanced_scores = [rec.get('score', 0) for rec in recommendations if rec.get('score', 0) > 10.0]
            if enhanced_scores:
                print(f"✅ Found {len(enhanced_scores)} recommendations with enhanced scores (>10.0)")
                print(f"   Score range: {min(enhanced_scores):.1f} - {max(enhanced_scores):.1f}")
            else:
                print("⚠️  No enhanced scores found (all scores ≤ 10.0)")
                
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_performance_metrics()
    test_gemini_batch_processing() 