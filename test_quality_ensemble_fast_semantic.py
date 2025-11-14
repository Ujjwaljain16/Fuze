#!/usr/bin/env python3
"""
Test for Quality Ensemble Engine (FastSemanticEngine only)
"""
import os
from dotenv import load_dotenv
load_dotenv()
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from quality_ensemble_engine import get_quality_ensemble_recommendations

# Example test user and project data
TEST_USER_ID = 1
TEST_REQUEST = {
    'user_id': TEST_USER_ID,
    'title': 'Learn advanced Python for data science',
    'description': 'I want to master advanced Python concepts for data science and machine learning.',
    'technologies': 'python, data science, machine learning',
    'max_recommendations': 5
}

def test_quality_ensemble_fast_semantic():
    print("\n=== Testing Quality Ensemble Engine (FastSemanticEngine only) ===\n")
    results = get_quality_ensemble_recommendations(TEST_USER_ID, TEST_REQUEST)
    if not results:
        print("❌ No recommendations returned!")
        return
    print(f"Total recommendations: {len(results)}\n")
    print("Top 3 recommendations:")
    for rec in results[:3]:
        print(f"- {getattr(rec, 'title', '')} (Score: {getattr(rec, 'score', 0):.2f}) | Engines: {list(getattr(rec, 'engine_votes', {}).keys())}")
        assert set(getattr(rec, 'engine_votes', {}).keys()) == {'fast_semantic'}, "Unexpected engine in engine_votes!"
    assert len(results) > 0, "No recommendations returned!"
    print("\n✅ Only FastSemanticEngine was used.")
    print("✅ Quality ensemble engine is working as expected!\n")

if __name__ == "__main__":
    test_quality_ensemble_fast_semantic()