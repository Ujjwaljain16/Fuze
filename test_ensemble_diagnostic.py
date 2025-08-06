#!/usr/bin/env python3
"""
Ensemble Engine Diagnostic Test
Detailed test to identify why engines are returning 0 results
"""

import time
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_ensemble_diagnostic():
    """Detailed diagnostic test for ensemble engines"""
    print("🔍 Ensemble Engine Diagnostic Test")
    print("=" * 50)
    
    # Test data
    test_data = {
        'title': 'React Development',
        'description': 'Building modern web applications with React',
        'technologies': 'React, JavaScript, TypeScript',
        'max_recommendations': 5,
        'engines': ['unified', 'smart', 'enhanced']
    }
    
    user_id = 1  # Test user ID
    
    print("📊 Testing Engine Availability...")
    
    try:
        # Test 1: Check if engines can be imported
        print("\n🔧 Test 1: Engine Import Test")
        
        try:
            from fast_ensemble_engine import get_fast_ensemble_recommendations
            print("✅ Fast ensemble engine imported successfully")
        except ImportError as e:
            print(f"❌ Fast ensemble engine import failed: {e}")
            return
        
        try:
            from ensemble_engine import get_ensemble_recommendations
            print("✅ Optimized ensemble engine imported successfully")
        except ImportError as e:
            print(f"❌ Optimized ensemble engine import failed: {e}")
            return
        
        try:
            from quality_ensemble_engine import get_quality_ensemble_recommendations
            print("✅ Quality ensemble engine imported successfully")
        except ImportError as e:
            print(f"❌ Quality ensemble engine import failed: {e}")
            return
        
        # Test 2: Test Fast Ensemble Engine
        print("\n🔥 Test 2: Fast Ensemble Engine Detailed Test")
        
        start_time = time.time()
        fast_results = get_fast_ensemble_recommendations(user_id, test_data)
        fast_response_time = (time.time() - start_time) * 1000
        
        print(f"   Response time: {fast_response_time:.2f}ms")
        print(f"   Results type: {type(fast_results)}")
        print(f"   Results length: {len(fast_results) if fast_results else 0}")
        
        if fast_results:
            print(f"   First result: {fast_results[0] if len(fast_results) > 0 else 'None'}")
        else:
            print("   ❌ No results returned")
        
        # Test 3: Test Optimized Ensemble Engine
        print("\n⚖️ Test 3: Optimized Ensemble Engine Detailed Test")
        
        start_time = time.time()
        optimized_results = get_ensemble_recommendations(user_id, test_data)
        optimized_response_time = (time.time() - start_time) * 1000
        
        print(f"   Response time: {optimized_response_time:.2f}ms")
        print(f"   Results type: {type(optimized_results)}")
        print(f"   Results length: {len(optimized_results) if optimized_results else 0}")
        
        if optimized_results:
            print(f"   First result: {optimized_results[0] if len(optimized_results) > 0 else 'None'}")
        else:
            print("   ❌ No results returned")
        
        # Test 4: Test Quality Ensemble Engine
        print("\n⭐ Test 4: Quality Ensemble Engine Detailed Test")
        
        start_time = time.time()
        quality_results = get_quality_ensemble_recommendations(user_id, test_data)
        quality_response_time = (time.time() - start_time) * 1000
        
        print(f"   Response time: {quality_response_time:.2f}ms")
        print(f"   Results type: {type(quality_results)}")
        print(f"   Results length: {len(quality_results) if quality_results else 0}")
        
        if quality_results:
            print(f"   First result: {quality_results[0] if len(quality_results) > 0 else 'None'}")
        else:
            print("   ❌ No results returned")
        
        # Test 5: Check underlying engines
        print("\n🔧 Test 5: Underlying Engine Test")
        
        try:
            from unified_recommendation_orchestrator import get_unified_orchestrator, UnifiedRecommendationRequest
            
            orchestrator = get_unified_orchestrator()
            unified_request = UnifiedRecommendationRequest(
                user_id=user_id,
                title=test_data['title'],
                description=test_data['description'],
                technologies=test_data['technologies'],
                max_recommendations=5,
                engine_preference='fast'
            )
            
            unified_results = orchestrator.get_recommendations(unified_request)
            print(f"   Unified orchestrator results: {len(unified_results)}")
            
        except Exception as e:
            print(f"   ❌ Unified orchestrator test failed: {e}")
        
        # Test 6: Check database connection
        print("\n🗄️ Test 6: Database Connection Test")
        
        try:
            from models import SavedContent, ContentAnalysis
            from app import app, db
            
            # Create application context
            with app.app_context():
                total_content = SavedContent.query.count()
                total_analysis = ContentAnalysis.query.count()
                
                print(f"   Total saved content: {total_content}")
                print(f"   Total content analysis: {total_analysis}")
                
        except Exception as e:
            print(f"   ❌ Database test failed: {e}")
            print(f"   This might be due to database connection issues")
        
        # Summary
        print(f"\n📊 Summary:")
        print(f"   Fast Engine: {len(fast_results) if fast_results else 0} results")
        print(f"   Optimized Engine: {len(optimized_results) if optimized_results else 0} results")
        print(f"   Quality Engine: {len(quality_results) if quality_results else 0} results")
        
        if not fast_results and not optimized_results and not quality_results:
            print(f"\n❌ All engines returned 0 results!")
            print(f"   This suggests a fundamental issue with:")
            print(f"   - Database connection")
            print(f"   - Content availability")
            print(f"   - Engine configuration")
        else:
            print(f"\n✅ At least one engine is working")
        
    except Exception as e:
        print(f"❌ Error in diagnostic test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ensemble_diagnostic() 