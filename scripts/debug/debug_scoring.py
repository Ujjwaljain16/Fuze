#!/usr/bin/env python3
"""
Debug the individual engine scores to see why they're all the same
"""

from app import app
from unified_recommendation_orchestrator import UnifiedRecommendationOrchestrator, UnifiedRecommendationRequest

def debug_scoring():
    with app.app_context():
        print("🔍 Debugging individual engine scores...")
        
        # Create the same request
        request = UnifiedRecommendationRequest(
            user_id=1,
            title='Master relevant technologies and improve skills',
            description='I want to learn new technologies and apply them to real-world projects. Focus on practical skills and advanced concepts.',
            technologies='react,python,ai,machine learning,cloud,devops',
            user_interests='Master relevant technologies and improve skills',
            max_recommendations=10,
            engine_preference='intelligent',
            diversity_weight=0.3,
            quality_threshold=6,
            include_global_content=True
        )
        
        # Initialize orchestrator
        orchestrator = UnifiedRecommendationOrchestrator()
        
        # Get candidate content
        content_list = orchestrator.data_layer.get_candidate_content(request.user_id, request)
        filtered_content = orchestrator._filter_content_by_relevance(content_list, request)
        
        print(f"📊 Working with {len(filtered_content)} filtered content items")
        
        # Test individual engine scoring
        print("\n🔍 Testing individual engine scores...")
        
        # Test vector similarity scores
        print("1️⃣ Vector Similarity Scores:")
        try:
            vector_scores = orchestrator._get_vector_similarity_scores(filtered_content[:5], request)
            for content_id, score in list(vector_scores.items())[:3]:
                print(f"   Content ID {content_id}: {score:.4f}")
        except Exception as e:
            print(f"   ❌ Vector scoring failed: {e}")
        
        # Test context-aware scores
        print("\n2️⃣ Context-Aware Scores:")
        try:
            intelligent_context = orchestrator._get_intelligent_context_analysis(request)
            context_scores = orchestrator._get_context_aware_scores(filtered_content[:5], request, intelligent_context)
            for content_id, score in list(context_scores.items())[:3]:
                print(f"   Content ID {content_id}: {score:.4f}")
        except Exception as e:
            print(f"   ❌ Context scoring failed: {e}")
        
        # Test content analysis scores
        print("\n3️⃣ Content Analysis Scores:")
        try:
            intelligent_context = orchestrator._get_intelligent_context_analysis(request)
            content_scores = orchestrator._get_content_analysis_scores(filtered_content[:5], request, intelligent_context)
            for content_id, score in list(content_scores.items())[:3]:
                print(f"   Content ID {content_id}: {score:.4f}")
        except Exception as e:
            print(f"   ❌ Content analysis scoring failed: {e}")
        
        # Test the combination
        print("\n4️⃣ Testing Score Combination:")
        try:
            # Get all scores
            intelligent_context = orchestrator._get_intelligent_context_analysis(request)
            vector_scores = orchestrator._get_vector_similarity_scores(filtered_content[:5], request)
            context_scores = orchestrator._get_context_aware_scores(filtered_content[:5], request, intelligent_context)
            content_scores = orchestrator._get_content_analysis_scores(filtered_content[:5], request, intelligent_context)
            
            # Test combination for first item
            if filtered_content:
                first_content = filtered_content[0]
                content_id = first_content.get('id', 0)
                
                vector_score = vector_scores.get(content_id, 0.0)
                context_score = context_scores.get(content_id, 0.0)
                content_score = content_scores.get(content_id, 0.0)
                
                print(f"   📊 Individual scores for '{first_content.get('title', 'No title')[:50]}...':")
                print(f"      Vector: {vector_score:.4f}")
                print(f"      Context: {context_score:.4f}")
                print(f"      Content: {content_score:.4f}")
                
                # Test intelligent combination
                final_score = orchestrator._calculate_intelligent_combination(
                    vector_score, context_score, content_score, 
                    intelligent_context, first_content, request
                )
                print(f"      Final: {final_score:.4f}")
                
        except Exception as e:
            print(f"   ❌ Combination failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_scoring()
