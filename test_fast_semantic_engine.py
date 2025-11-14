#!/usr/bin/env python3
"""
Test for FastSemanticEngine (semantic search over all content)
"""
import os
from dotenv import load_dotenv
load_dotenv()
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from unified_recommendation_orchestrator import FastSemanticEngine, UnifiedDataLayer, UnifiedRecommendationRequest

def test_fast_semantic_engine():
    print("\n=== Testing FastSemanticEngine (semantic search) ===\n")
    data_layer = UnifiedDataLayer()
    fast_engine = FastSemanticEngine(data_layer)
    request = UnifiedRecommendationRequest(
        user_id=1,
        title='Expense Tracker with React Native and UPI Integration',
        description='Build a mobile app to track expenses, visualize spending, and support UPI payments using Expo and React Native.',
        technologies='react native, expo, upi, payments, mobile app',
        user_interests='fintech, personal finance, mobile development',
        max_recommendations=5
    )
    with app.app_context():
        results = fast_engine.get_recommendations([], request)
        print(f"Total recommendations: {len(results)}\n")
        for rec in results[:3]:
            print(f"- {rec.title} (Score: {rec.score:.2f}) | Reason: {rec.reason}")
        assert len(results) > 0, "No recommendations returned!"
        print("\n✅ FastSemanticEngine is working and returns relevant recommendations!\n")

if __name__ == "__main__":
    test_fast_semantic_engine()