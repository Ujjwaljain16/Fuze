#!/usr/bin/env python3
"""
Quick debug test for bonus calculation
"""

import sys
sys.path.append('.')

def debug_bonus():
    try:
        from app import app
        
        with app.app_context():
            from unified_recommendation_orchestrator import UnifiedRecommendationRequest, get_unified_orchestrator
            
            # Clear cache first
            try:
                import redis_utils
                redis_utils.redis_cache.redis_client.flushdb()
                print("🗑️ Cache cleared")
            except:
                pass
            
            orchestrator = get_unified_orchestrator()
            
            request = UnifiedRecommendationRequest(
                user_id=1,
                title="DSA visualiser",
                description="Test",
                technologies="java,instrumentation,byte buddy,AST,JVM",
                max_recommendations=1
            )
            
            print("🔍 Testing technology bonus calculation...")
            recommendations = orchestrator.get_recommendations(request)
            
            if recommendations:
                rec = recommendations[0]
                print(f"📖 Result: {rec.title}")
                print(f"🔧 Technologies: {rec.technologies}")
                print(f"🔥 Tech Bonus: {rec.metadata.get('tech_alignment_bonus', 0.0)}")
                print("✅ Debug complete - check logs above for tech bonus debug info")
            else:
                print("❌ No recommendations")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_bonus()
