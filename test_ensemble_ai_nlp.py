#!/usr/bin/env python3
"""
Test for AI/NLP-Powered Ensemble Engine (SmartRecommendationEngine + FastGeminiEngine)
"""
import os
from dotenv import load_dotenv
load_dotenv()
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ensemble_engine import get_ensemble_recommendations

# Example test user and project data
TEST_USER_ID = 1
TEST_REQUEST = {
    'user_id': TEST_USER_ID,
    'title': 'Build a React Native mobile app with Firebase authentication',
    'description': 'I want to learn how to build a cross-platform mobile app using React Native and add user authentication with Firebase.',
    'technologies': 'react native, firebase, mobile, authentication',
    'max_recommendations': 5
}

def test_ai_nlp_ensemble():
    print("\n=== Testing AI/NLP Ensemble Engine ===\n")
    print(f"GEMINI_API_KEY loaded: {os.environ.get('GEMINI_API_KEY') is not None}")
    results = get_ensemble_recommendations(TEST_USER_ID, TEST_REQUEST)
    if not results:
        print("❌ No recommendations returned!")
        return
    print(f"Total recommendations: {len(results)}\n")
    print("Top 3 recommendations:")
    for rec in results[:3]:
        print(f"- {rec.get('title','')} (Score: {rec.get('score',0):.2f}) | Engines: {list(rec.get('engine_votes',{}).keys())}")
        assert set(rec.get('engine_votes',{}).keys()) <= {'smart','fast_gemini'}, "Unexpected engine in engine_votes!"
    assert len(results) > 0, "No recommendations returned!"
    print("\n✅ Only SmartRecommendationEngine and FastGeminiEngine were used.")
    print("✅ AI/NLP ensemble engine is working as expected!\n")

if __name__ == "__main__":
    test_ai_nlp_ensemble()