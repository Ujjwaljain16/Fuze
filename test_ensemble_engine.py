#!/usr/bin/env python3
"""
Test script for Ensemble Recommendation Engine
"""

import requests
import json
import time

def test_ensemble_engine():
    """Test ensemble recommendation engine"""
    
    base_url = "http://localhost:5000"
    
    print("🚀 Testing Ensemble Recommendation Engine")
    print("=" * 60)
    
    # Test payload for ensemble
    test_payload = {
        "title": "React Web Application with Advanced Features",
        "description": "Building a modern web application using React hooks, Redux for state management, TypeScript for type safety, and advanced features like real-time updates, authentication, and responsive design.",
        "technologies": "React, TypeScript, Redux, Node.js, MongoDB, WebSocket",
        "user_interests": "Frontend development, state management, modern JavaScript frameworks, real-time applications",
        "project_id": 1,
        "max_recommendations": 8,
        "engines": ["unified", "smart", "enhanced"],  # Use multiple engines
        "ensemble_method": "weighted_voting"
    }
    
    print("📊 Testing Ensemble Engine with Multiple Engines")
    print("-" * 50)
    print(f"Engines to use: {test_payload['engines']}")
    print(f"Ensemble method: {test_payload['ensemble_method']}")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{base_url}/api/recommendations/ensemble",
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=60  # Longer timeout for ensemble
        )
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Ensemble engine working")
            print(f"   Response time: {response_time:.2f}ms")
            print(f"   Total recommendations: {data.get('total_recommendations', 0)}")
            print(f"   Engine used: {data.get('engine_used', 'Unknown')}")
            
            # Show performance metrics
            if 'performance_metrics' in data:
                metrics = data['performance_metrics']
                print(f"   Engines used: {metrics.get('ensemble_engines_used', [])}")
            
            # Show first recommendation details
            recommendations = data.get('recommendations', [])
            if recommendations:
                first_rec = recommendations[0]
                print(f"\n📌 Sample Ensemble Recommendation:")
                print(f"   Title: {first_rec.get('title', 'N/A')}")
                print(f"   Ensemble Score: {first_rec.get('ensemble_score', 0):.3f}")
                print(f"   Original Score: {first_rec.get('score', 0):.2f}")
                print(f"   Reason: {first_rec.get('reason', 'N/A')}")
                print(f"   Technologies: {', '.join(first_rec.get('technologies', [])[:3])}")
                
                # Show engine votes
                engine_votes = first_rec.get('engine_votes', {})
                if engine_votes:
                    print(f"   Engine Votes:")
                    for engine, vote in engine_votes.items():
                        print(f"     {engine}: {vote:.3f}")
                
        elif response.status_code == 401:
            print("❌ Authentication required - need valid JWT token")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing ensemble engine: {e}")
    
    # Test different engine combinations
    print("\n🔧 Testing Different Engine Combinations")
    print("-" * 50)
    
    engine_combinations = [
        {
            "name": "Unified + Smart",
            "engines": ["unified", "smart"]
        },
        {
            "name": "Unified + Enhanced", 
            "engines": ["unified", "enhanced"]
        },
        {
            "name": "Smart + Enhanced",
            "engines": ["smart", "enhanced"]
        },
        {
            "name": "All Three Engines",
            "engines": ["unified", "smart", "enhanced"]
        }
    ]
    
    for combo in engine_combinations:
        print(f"\n🧪 Testing: {combo['name']}")
        print(f"   Engines: {combo['engines']}")
        
        test_payload["engines"] = combo['engines']
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{base_url}/api/recommendations/ensemble",
                json=test_payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                recommendations = data.get('recommendations', [])
                print(f"   ✅ Success ({response_time:.2f}ms)")
                print(f"   Recommendations: {len(recommendations)}")
                
                # Show top result ensemble score
                if recommendations:
                    top_score = recommendations[0].get('ensemble_score', 0)
                    print(f"   Top Ensemble Score: {top_score:.3f}")
                
            elif response.status_code == 401:
                print(f"   🔐 Authentication required")
            else:
                print(f"   ❌ Error: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    # Compare with single engine
    print("\n📊 Comparing Ensemble vs Single Engine")
    print("-" * 50)
    
    # Test single engine (unified orchestrator)
    single_engine_payload = {
        "title": test_payload["title"],
        "description": test_payload["description"],
        "technologies": test_payload["technologies"],
        "user_interests": test_payload["user_interests"],
        "project_id": test_payload["project_id"],
        "max_recommendations": test_payload["max_recommendations"],
        "engine_preference": "auto"
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{base_url}/api/recommendations/unified-orchestrator",
            json=single_engine_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        single_response_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            single_recommendations = data.get('recommendations', [])
            print(f"✅ Single Engine (Unified Orchestrator):")
            print(f"   Response time: {single_response_time:.2f}ms")
            print(f"   Recommendations: {len(single_recommendations)}")
            
            if single_recommendations:
                top_score = single_recommendations[0].get('score', 0)
                print(f"   Top Score: {top_score:.2f}")
        
    except Exception as e:
        print(f"❌ Error testing single engine: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Ensemble Engine Testing Complete!")
    print("\n💡 Benefits of Ensemble Engine:")
    print("1. **Better Accuracy**: Combines multiple engines for more reliable results")
    print("2. **Diverse Recommendations**: Gets different perspectives from each engine")
    print("3. **Robust Performance**: Falls back gracefully if some engines fail")
    print("4. **Weighted Voting**: Gives more weight to engines that perform better")
    print("5. **Customizable**: Choose which engines to use based on your needs")
    
    print("\n🚀 How to use in your frontend:")
    print("POST /api/recommendations/ensemble")
    print("With payload:")
    print(json.dumps({
        "title": "Your Project",
        "description": "Project description", 
        "technologies": "Tech stack",
        "engines": ["unified", "smart", "enhanced"],
        "max_recommendations": 10
    }, indent=2))

if __name__ == "__main__":
    test_ensemble_engine() 