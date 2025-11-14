#!/usr/bin/env python3
"""
Debug the complete recommendation flow to see where content is being lost
"""

from app import app
from unified_recommendation_orchestrator import UnifiedRecommendationOrchestrator, UnifiedRecommendationRequest

def debug_recommendation_flow():
    with app.app_context():
        print("🔍 Debugging complete recommendation flow...")
        
        # Create the same request as your test
        request = UnifiedRecommendationRequest(
            user_id=1,
            title='DSA visualiser',
            description='Looking for DSA visualization resources with Java and JVM instrumentation/AST/Byte Buddy context',
            technologies='java,instrumentation,byte buddy,ast,jvm',
            user_interests='java,jvm,bytecode,visualization,dsa',
            max_recommendations=10,
            engine_preference='intelligent',
            diversity_weight=0.3,
            quality_threshold=6,
            include_global_content=True
        )
        
        print(f"📝 Request: {request.title}")
        print(f"🔧 Technologies: {request.technologies}")
        print(f"🎯 Engine: {request.engine_preference}")
        
        # Initialize orchestrator
        orchestrator = UnifiedRecommendationOrchestrator()
        print(f"✅ Orchestrator initialized with engines: {list(orchestrator.engines.keys())}")
        
        # Get candidate content
        print("\n🔍 Step 1: Getting candidate content...")
        content_list = orchestrator.data_layer.get_candidate_content(request.user_id, request)
        print(f"📊 Raw content from database: {len(content_list)} items")
        
        if content_list:
            print("📋 Sample content titles:")
            for i, content in enumerate(content_list[:5]):
                print(f"   {i+1}. {content.get('title', 'No title')[:60]}...")
                print(f"      Tech: {content.get('technologies', 'None')}")
                print(f"      Quality: {content.get('quality_score', 'None')}")
        
        # Test filtering
        print("\n🔍 Step 2: Testing content filtering...")
        filtered_content = orchestrator._filter_content_by_relevance(content_list, request)
        print(f"📊 After filtering: {len(filtered_content)} items")
        
        if filtered_content:
            print("📋 Filtered content titles:")
            for i, content in enumerate(filtered_content[:5]):
                print(f"   {i+1}. {content.get('title', 'No title')[:60]}...")
                print(f"      Relevance Score: {content.get('relevance_score', 'None')}")
        
        # Test engine execution
        print("\n🔍 Step 3: Testing engine execution...")
        try:
            results = orchestrator._execute_engine_strategy(request, filtered_content)
            print(f"📊 Engine results: {len(results)} recommendations")
            
            if results:
                print("📋 Top recommendations:")
                for i, result in enumerate(results[:3]):
                    print(f"   {i+1}. {result.title[:60]}...")
                    print(f"      Score: {result.score:.2f}")
                    print(f"      Reason: {result.reason[:100]}...")
        except Exception as e:
            print(f"❌ Engine execution failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_recommendation_flow()
