#!/usr/bin/env python3
"""
Debug the actual content structure to see what fields are available
"""

from app import app
from unified_recommendation_orchestrator import UnifiedRecommendationOrchestrator, UnifiedRecommendationRequest

def debug_content_structure():
    with app.app_context():
        print("🔍 Debugging content structure...")
        
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
        
        if filtered_content:
            print("\n🔍 Content Structure Analysis:")
            first_content = filtered_content[0]
            
            print(f"📋 First content item keys: {list(first_content.keys())}")
            print(f"📋 Sample values:")
            
            for key, value in first_content.items():
                if key in ['title', 'url', 'technologies', 'technology_tags', 'content_type', 'difficulty_level', 'quality_score']:
                    print(f"   {key}: {value}")
            
            print(f"\n🔍 Testing fast content relevance calculation:")
            
            # Test the fast content relevance method directly
            try:
                fast_score = orchestrator.fast_engine._calculate_fast_content_relevance(
                    first_content,
                    request.technologies.split(',') if request.technologies else [],
                    f"{request.title} {request.description}",
                    request
                )
                print(f"   Fast relevance score: {fast_score:.4f}")
                
                # Debug the calculation step by step
                print(f"   🔍 Step-by-step calculation:")
                
                # Check technologies
                content_techs = first_content.get('technologies', [])
                if isinstance(content_techs, str):
                    content_techs = [tech.strip().lower() for tech in content_techs.split(',') if tech.strip()]
                print(f"      Content technologies: {content_techs}")
                
                request_techs = request.technologies.split(',') if request.technologies else []
                print(f"      Request technologies: {request_techs}")
                
                # Check exact matches
                if request_techs and content_techs:
                    exact_matches = set(request_techs).intersection(set(content_techs))
                    print(f"      Exact matches: {exact_matches}")
                    
                    tech_relevance = len(exact_matches) / len(request_techs) if request_techs else 0
                    print(f"      Tech relevance: {tech_relevance:.4f}")
                
                # Check text similarity
                content_text = f"{first_content.get('title', '')} {first_content.get('extracted_text', '')}".lower()
                request_text = f"{request.title} {request.description}".lower()
                print(f"      Content text length: {len(content_text)}")
                print(f"      Request text length: {len(request_text)}")
                
                if request_text and content_text:
                    request_words = set(request_text.split())
                    content_words = set(content_text.split())
                    word_overlap = len(request_words.intersection(content_words))
                    text_relevance = word_overlap / len(request_words) if request_words else 0
                    print(f"      Word overlap: {word_overlap}")
                    print(f"      Text relevance: {text_relevance:.4f}")
                
                # Check quality score
                quality_score = first_content.get('quality_score', 6) / 10.0
                print(f"      Quality score: {quality_score:.4f}")
                
            except Exception as e:
                print(f"   ❌ Fast relevance calculation failed: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    debug_content_structure()
