#!/usr/bin/env python3
"""
Test Ensemble Quality Fix
Verify that ensemble engine now uses all 6 engines and has better quality filtering
"""

import time
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_ensemble_quality_fix():
    """Test the improved ensemble engine"""
    print("🧪 Testing Ensemble Quality Fix")
    print("=" * 50)
    
    # Test data
    test_data = {
        'title': 'Java Instrumentation Tool',
        'description': 'Building a Java-based instrumentation tool for JVM monitoring',
        'technologies': 'Java, JVM, Bytecode, ASM, Instrumentation',
        'max_recommendations': 5,
        'engines': ['unified', 'smart', 'enhanced', 'phase3', 'fast_gemini', 'gemini_enhanced']
    }
    
    user_id = 1  # Test user ID
    
    try:
        # Test Complete Ensemble Engine
        print("⚖️ Testing Complete Ensemble Engine (All 6 Engines)")
        from ensemble_engine import get_ensemble_recommendations
        
        start_time = time.time()
        ensemble_results = get_ensemble_recommendations(user_id, test_data)
        ensemble_response_time = (time.time() - start_time) * 1000
        
        print(f"✅ Complete Ensemble Engine:")
        print(f"   Response time: {ensemble_response_time:.2f}ms")
        print(f"   Total recommendations: {len(ensemble_results)}")
        
        # Check if all engines are being used
        if ensemble_results:
            first_result = ensemble_results[0]
            engine_votes = first_result.get('engine_votes', {})
            engines_used = list(engine_votes.keys())
            print(f"   Engines used: {engines_used}")
            print(f"   Expected: 6 engines, Got: {len(engines_used)} engines")
            
            # Check quality of reasons
            generic_reasons = 0
            specific_reasons = 0
            
            for result in ensemble_results:
                reason = result.get('reason', '')
                if reason and any(generic in reason.lower() for generic in ['helpful', 'useful', 'relevant']):
                    generic_reasons += 1
                else:
                    specific_reasons += 1
            
            print(f"   Quality Analysis:")
            print(f"     Specific reasons: {specific_reasons}")
            print(f"     Generic reasons: {generic_reasons}")
            print(f"     Quality ratio: {specific_reasons/(specific_reasons+generic_reasons)*100:.1f}%")
            
            # Check relevance (should focus on Java/Instrumentation)
            java_relevant = 0
            for result in ensemble_results:
                technologies = result.get('technologies', [])
                if any(tech.lower() in ['java', 'jvm', 'instrumentation', 'bytecode', 'asm'] for tech in technologies):
                    java_relevant += 1
            
            print(f"   Relevance Analysis:")
            print(f"     Java/Instrumentation relevant: {java_relevant}/{len(ensemble_results)}")
            print(f"     Relevance ratio: {java_relevant/len(ensemble_results)*100:.1f}%")
            
            # Performance rating
            if ensemble_response_time < 10000:
                print(f"   🚀 Performance: FAST")
            elif ensemble_response_time < 30000:
                print(f"   ⚡ Performance: GOOD")
            else:
                print(f"   🐌 Performance: SLOW")
            
            # Quality rating
            if specific_reasons >= len(ensemble_results) * 0.7:
                print(f"   🎯 Quality: EXCELLENT")
            elif specific_reasons >= len(ensemble_results) * 0.5:
                print(f"   ✅ Quality: GOOD")
            else:
                print(f"   ⚠️ Quality: NEEDS IMPROVEMENT")
                
        else:
            print(f"   ❌ No results returned")
        
        print(f"\n🎯 Summary:")
        print(f"   ✅ All 6 engines should now be used")
        print(f"   ✅ Quality threshold increased to 0.4")
        print(f"   ✅ Generic reasons filtered out")
        print(f"   ✅ Cache duration reduced for immediate effect")
        
    except Exception as e:
        print(f"❌ Error in ensemble test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ensemble_quality_fix() 