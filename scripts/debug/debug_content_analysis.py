#!/usr/bin/env python3
"""
Debug why content analysis is returning 0.0000 scores
"""

from app import app
from unified_recommendation_orchestrator import UnifiedRecommendationOrchestrator, UnifiedRecommendationRequest

def debug_content_analysis():
    with app.app_context():
        print("🔍 Debugging content analysis scoring...")
        
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
            print("\n🔍 Testing content analysis for first item:")
            first_content = filtered_content[0]
            
            print(f"📋 Content data:")
            print(f"   ID: {first_content.get('id')}")
            print(f"   Title: {first_content.get('title', 'No title')[:60]}...")
            print(f"   Technologies: {first_content.get('technologies', 'None')}")
            print(f"   Technology Tags: {first_content.get('technology_tags', 'None')}")
            print(f"   Content Type: {first_content.get('content_type', 'None')}")
            print(f"   Difficulty Level: {first_content.get('difficulty_level', 'None')}")
            print(f"   Key Concepts: {first_content.get('key_concepts', 'None')}")
            print(f"   Relevance Score: {first_content.get('relevance_score', 'None')}")
            print(f"   Quality Score: {first_content.get('quality_score', 'None')}")
            
            # Test the content analysis method directly
            try:
                intelligent_context = orchestrator._get_intelligent_context_analysis(request)
                print(f"\n🔍 Intelligent Context: {intelligent_context}")
                
                # Test basic content analysis
                basic_score = orchestrator._analyze_content_basic(first_content, request, intelligent_context)
                print(f"\n📊 Basic Content Analysis Score: {basic_score:.4f}")
                
                # Test step by step
                print(f"\n🔍 Step-by-step analysis:")
                
                # 1. Technology matching
                if request.technologies:
                    request_techs = set(tech.strip().lower() for tech in request.technologies.split(','))
                    print(f"   Request techs: {request_techs}")
                    
                    if first_content.get('technology_tags'):
                        db_techs = set(tech.strip().lower() for tech in first_content.get('technology_tags', '').split(','))
                        tech_overlap = len(request_techs.intersection(db_techs))
                        tech_score = tech_overlap * 0.25
                        print(f"   DB techs: {db_techs}")
                        print(f"   Tech overlap: {tech_overlap}")
                        print(f"   Tech score: {tech_score:.4f}")
                    else:
                        content_techs = set(tech.strip().lower() for tech in first_content.get('technologies', '').split(','))
                        tech_overlap = len(request_techs.intersection(content_techs))
                        tech_score = tech_overlap * 0.20
                        print(f"   Content techs: {content_techs}")
                        print(f"   Tech overlap: {tech_overlap}")
                        print(f"   Tech score: {tech_score:.4f}")
                
                # 2. Content type matching
                if first_content.get('content_type'):
                    content_type = first_content.get('content_type', '').lower()
                    request_text = f"{request.title} {request.description}".lower()
                    print(f"   Content type: {content_type}")
                    print(f"   Request text: {request_text[:100]}...")
                    
                    if 'tutorial' in content_type and any(word in request_text for word in ['learn', 'tutorial', 'guide', 'how']):
                        print(f"   ✅ Tutorial match: +0.15")
                    elif 'documentation' in content_type and any(word in request_text for word in ['reference', 'docs', 'api', 'documentation']):
                        print(f"   ✅ Documentation match: +0.15")
                    elif 'article' in content_type and any(word in request_text for word in ['read', 'article', 'blog', 'news']):
                        print(f"   ✅ Article match: +0.10")
                    else:
                        print(f"   ❌ No content type match")
                
                # 3. Difficulty level matching
                if first_content.get('difficulty_level'):
                    difficulty = first_content.get('difficulty_level', '').lower()
                    request_complexity = intelligent_context.get('complexity', 'intermediate')
                    print(f"   Content difficulty: {difficulty}")
                    print(f"   Request complexity: {request_complexity}")
                    
                    if difficulty == request_complexity:
                        print(f"   ✅ Perfect difficulty match: +0.15")
                    elif (difficulty == 'beginner' and request_complexity == 'intermediate') or \
                         (difficulty == 'intermediate' and request_complexity == 'advanced'):
                        print(f"   ✅ Adjacent difficulty: +0.10")
                    else:
                        print(f"   ❌ No difficulty match")
                
                # 4. Key concepts matching
                if first_content.get('key_concepts'):
                    key_concepts = first_content.get('key_concepts', '')
                    request_text = f"{request.title} {request.description}".lower()
                    
                    # Handle both string and list formats
                    if isinstance(key_concepts, list):
                        concept_matches = sum(1 for concept in key_concepts if concept.lower() in request_text)
                    else:
                        concept_matches = sum(1 for concept in key_concepts.split(',') if concept.strip().lower() in request_text)
                    
                    if concept_matches > 0:
                        concept_score = min(concept_matches * 0.08, 0.20)
                        print(f"   Key concepts: {key_concepts}")
                        print(f"   Concept matches: {concept_matches}")
                        print(f"   Concept score: +{concept_score:.4f}")
                    else:
                        print(f"   ❌ No concept matches")
                
                # 5. Relevance score from DB
                if first_content.get('relevance_score'):
                    db_relevance = first_content.get('relevance_score', 0) / 100.0
                    relevance_score = db_relevance * 0.15
                    print(f"   DB relevance: {first_content.get('relevance_score')}")
                    print(f"   Normalized relevance: {db_relevance:.4f}")
                    print(f"   Relevance score: +{relevance_score:.4f}")
                else:
                    print(f"   ❌ No DB relevance score")
                
                # 6. Text similarity
                request_text = f"{request.title} {request.description}".lower()
                content_text = f"{first_content.get('title', '')} {first_content.get('extracted_text', '')}".lower()
                if request_text and content_text:
                    request_words = set(request_text.split())
                    content_words = set(content_text.split())
                    word_overlap = len(request_words.intersection(content_words))
                    text_score = (word_overlap / len(request_words)) * 0.20 if request_words else 0
                    print(f"   Request words: {len(request_words)}")
                    print(f"   Content words: {len(content_words)}")
                    print(f"   Word overlap: {word_overlap}")
                    print(f"   Text score: +{text_score:.4f}")
                
                # 7. Quality score
                quality_score = first_content.get('quality_score', 6) / 10.0
                quality_boost = quality_score * 0.10
                print(f"   Quality score: {first_content.get('quality_score')}")
                print(f"   Normalized quality: {quality_score:.4f}")
                print(f"   Quality boost: +{quality_boost:.4f}")
                
            except Exception as e:
                print(f"   ❌ Content analysis failed: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    debug_content_analysis()
