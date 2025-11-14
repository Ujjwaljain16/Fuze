#!/usr/bin/env python3
"""
Comprehensive test to verify ALL enhanced recommendation functionality works together
Tests the complete pipeline: data retrieval → intelligent filtering → context-aware scoring → final ranking
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from unified_recommendation_orchestrator import UnifiedRecommendationOrchestrator, UnifiedRecommendationRequest

def comprehensive_recommendation_test():
    """Test all enhanced recommendation features working together"""
    with app.app_context():
        print("🔍 COMPREHENSIVE RECOMMENDATION SYSTEM TEST")
        print("=" * 80)
        
        # Test Case 1: DSA Visualizer with Java/JVM Technologies
        print("\n🎯 TEST CASE 1: DSA Visualizer + Java Ecosystem")
        print("-" * 50)
        
        request = UnifiedRecommendationRequest(
            user_id=1,
            title='DSA visualiser',
            description='Need Java-based data structure visualization tools with bytecode instrumentation capabilities using Byte Buddy and AST manipulation for JVM runtime analysis',
            technologies='java,instrumentation,byte buddy,ast,jvm,data structure,algorithm,visualization',
            user_interests='java,jvm,bytecode,visualization,dsa,compiler,instrumentation',
            max_recommendations=15,
            engine_preference='intelligent',  # Use the UNIFIED ENSEMBLE
            diversity_weight=0.3,
            quality_threshold=5,  # Lower threshold to see more results
            include_global_content=True
        )
        
        print(f"📝 Request: {request.title}")
        print(f"🔧 Technologies: {request.technologies}")
        print(f"📖 Description: {request.description[:100]}...")
        print(f"🎯 Engine: {request.engine_preference}")
        
        # Initialize orchestrator
        orchestrator = UnifiedRecommendationOrchestrator()
        print(f"✅ Orchestrator initialized with {len(orchestrator.engines)} engines")
        
        # STEP 1: Test Content Retrieval
        print("\n🔍 STEP 1: Content Retrieval & Initial Filtering")
        content_list = orchestrator.data_layer.get_candidate_content(request.user_id, request)
        print(f"📊 Raw content from database: {len(content_list)} items")
        
        # STEP 2: Test Intelligent Filtering
        print("\n🔍 STEP 2: Intelligent Content Filtering")
        filtered_content = orchestrator._filter_content_by_relevance(content_list, request)
        print(f"📊 After intelligent filtering: {len(filtered_content)} items")
        
        # Show top filtered items with relevance scores
        print("\n📋 TOP 10 FILTERED ITEMS (by relevance score):")
        for i, content in enumerate(filtered_content[:10]):
            title = content.get('title', 'No title')[:70]
            score = content.get('relevance_score', 0)
            techs = content.get('technologies', [])
            if isinstance(techs, list):
                tech_str = ', '.join(techs[:5])  # Show first 5 technologies
            else:
                tech_str = str(techs)[:50]
            print(f"   {i+1:2d}. Score: {score:.3f} | {title}")
            print(f"       Tech: {tech_str}")
        
        # STEP 3: Test Engine Execution with Detailed Scoring
        print("\n🔍 STEP 3: Engine Execution & Detailed Scoring Analysis")
        try:
            results = orchestrator._execute_engine_strategy(request, filtered_content)
            print(f"📊 Final engine results: {len(results)} recommendations")
            
            if results:
                print("\n🏆 TOP 10 FINAL RECOMMENDATIONS (with detailed analysis):")
                print("=" * 80)
                
                for i, result in enumerate(results[:10]):
                    print(f"\n{i+1:2d}. 📊 SCORE: {result.score:.3f} | 🎯 CONFIDENCE: {result.confidence:.2f}")
                    print(f"    📝 TITLE: {result.title}")
                    print(f"    🔧 TECH: {result.technologies}")
                    print(f"    🧠 REASON: {result.reason}")
                    print(f"    🏷️  TYPE: {result.content_type} | 📈 QUALITY: {result.quality_score}")
                    print(f"    ⚙️  ENGINE: {result.engine_used}")
                    
                    # Show key concepts if available
                    if hasattr(result, 'key_concepts') and result.key_concepts:
                        concepts = result.key_concepts[:3]  # Show first 3 concepts
                        print(f"    💡 KEY CONCEPTS: {', '.join(concepts)}")
                    
                    print("-" * 80)
                
                # STEP 4: Analyze Specific Expected Results
                print("\n🔍 STEP 4: Analyzing Expected High-Priority Items")
                print("-" * 50)
                
                # Check if Byte Buddy is in top results
                byte_buddy_found = False
                dsa_content_found = False
                java_content_found = False
                
                for i, result in enumerate(results):
                    title_lower = result.title.lower()
                    
                    if 'byte buddy' in title_lower:
                        byte_buddy_found = True
                        print(f"✅ BYTE BUDDY found at position {i+1} with score {result.score:.3f}")
                    
                    if any(keyword in title_lower for keyword in ['dsa', 'data structure', 'algorithm', 'visualizer', 'visualiser']):
                        dsa_content_found = True
                        print(f"✅ DSA CONTENT found at position {i+1}: {result.title[:60]}... (score: {result.score:.3f})")
                    
                    tech_str = ' '.join(result.technologies).lower() if isinstance(result.technologies, list) else str(result.technologies).lower()
                    if 'java' in title_lower or 'java' in tech_str:
                        java_content_found = True
                        if i < 5:  # Only report if in top 5
                            print(f"✅ JAVA CONTENT in top 5 at position {i+1}: {result.title[:60]}... (score: {result.score:.3f})")
                
                # STEP 5: Technology Relationship Analysis
                print(f"\n🔍 STEP 5: Technology Relationship Analysis")
                print("-" * 50)
                
                # Analyze how well the system understood technology relationships
                java_ecosystem_count = 0
                dsa_related_count = 0
                
                for result in results[:10]:  # Check top 10
                    tech_str = ' '.join(result.technologies).lower() if isinstance(result.technologies, list) else str(result.technologies).lower()
                    title_lower = result.title.lower()
                    
                    # Count Java ecosystem items
                    if any(keyword in tech_str or keyword in title_lower for keyword in ['java', 'jvm', 'bytecode', 'instrumentation', 'ast']):
                        java_ecosystem_count += 1
                    
                    # Count DSA related items
                    if any(keyword in tech_str or keyword in title_lower for keyword in ['dsa', 'data structure', 'algorithm', 'visualizer', 'sorting', 'tree', 'graph']):
                        dsa_related_count += 1
                
                print(f"📊 Java ecosystem items in top 10: {java_ecosystem_count}/10")
                print(f"📊 DSA related items in top 10: {dsa_related_count}/10")
                
                # STEP 6: Final Assessment
                print(f"\n🏁 FINAL ASSESSMENT")
                print("=" * 50)
                
                score_assessment = "✅ EXCELLENT" if results[0].score > 0.7 else "✅ GOOD" if results[0].score > 0.5 else "⚠️ NEEDS IMPROVEMENT"
                print(f"Top score: {results[0].score:.3f} - {score_assessment}")
                
                relevance_assessment = "✅ EXCELLENT" if byte_buddy_found and dsa_content_found else "⚠️ PARTIAL"
                print(f"Expected content found: {relevance_assessment}")
                
                diversity_assessment = "✅ GOOD" if java_ecosystem_count >= 5 and dsa_related_count >= 3 else "⚠️ LIMITED"
                print(f"Technology diversity: {diversity_assessment}")
                
                print(f"\n🎯 RECOMMENDATION QUALITY: ", end="")
                if score_assessment == "✅ EXCELLENT" and relevance_assessment == "✅ EXCELLENT":
                    print("🏆 OUTSTANDING - All systems working perfectly!")
                elif "✅" in score_assessment and "✅" in relevance_assessment:
                    print("✅ VERY GOOD - System is working well!")
                else:
                    print("⚠️ NEEDS OPTIMIZATION - Some improvements needed")
                
            else:
                print("❌ No recommendations returned!")
                
        except Exception as e:
            print(f"❌ Engine execution failed: {e}")
            import traceback
            traceback.print_exc()
        
        # STEP 7: Test Additional Scenarios
        print(f"\n🔍 STEP 7: Testing Additional Scenarios")
        print("-" * 50)
        
        # Test Case 2: More specific DSA request
        print("\n🎯 TEST CASE 2: Specific DSA Algorithm Request")
        
        specific_request = UnifiedRecommendationRequest(
            user_id=1,
            title='Binary tree visualization in Java',
            description='Need interactive binary tree and graph algorithm visualizations with Java implementation examples',
            technologies='java,data structure,tree,graph,algorithm,visualization',
            user_interests='java,algorithms,data structures,visualization',
            max_recommendations=5,
            engine_preference='intelligent',
            diversity_weight=0.2,
            quality_threshold=6,
            include_global_content=True
        )
        
        try:
            specific_results = orchestrator._execute_engine_strategy(
                specific_request, 
                orchestrator._filter_content_by_relevance(
                    orchestrator.data_layer.get_candidate_content(specific_request.user_id, specific_request),
                    specific_request
                )
            )
            
            print(f"📊 Specific DSA results: {len(specific_results)} recommendations")
            if specific_results:
                print("🏆 TOP 3 SPECIFIC DSA RECOMMENDATIONS:")
                for i, result in enumerate(specific_results[:3]):
                    print(f"   {i+1}. Score: {result.score:.3f} | {result.title[:60]}...")
                    print(f"      Reason: {result.reason[:80]}...")
        
        except Exception as e:
            print(f"❌ Specific test failed: {e}")
        
        print(f"\n✅ COMPREHENSIVE TEST COMPLETED!")
        print("=" * 80)

if __name__ == "__main__":
    comprehensive_recommendation_test()
