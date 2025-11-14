#!/usr/bin/env python3
"""
Debug why technology bonus is 0.000
"""

import sys
sys.path.append('.')

def debug_tech_bonus():
    """Debug technology bonus calculation"""
    
    print("🔍 DEBUGGING TECHNOLOGY BONUS CALCULATION")
    print("=" * 50)
    
    try:
        from app import app
        
        with app.app_context():
            from unified_recommendation_orchestrator import UnifiedRecommendationRequest, get_unified_orchestrator
            
            orchestrator = get_unified_orchestrator()
            
            # Simulate the exact request from the test
            request = UnifiedRecommendationRequest(
                user_id=1,
                title="DSA visualiser",
                description="Interactive data structure and algorithm visualization tools with Java/JVM bytecode manipulation",
                technologies="java instrumentation byte buddy AST JVM",
                max_recommendations=3
            )
            
            # Test sample content like from the results
            test_contents = [
                {
                    'id': 1,
                    'title': 'Think Data Structures.pdf - Free download books',
                    'technologies': ['java', 'wikipedia'],
                    'url': 'test'
                },
                {
                    'id': 2, 
                    'title': 'Python cheat sheet',
                    'technologies': ['python', 'numpy'],
                    'url': 'test'
                },
                {
                    'id': 3,
                    'title': 'Self upgrade IT prof',
                    'technologies': ['java', 'python', 'javascript', 'go', 'rust'],
                    'url': 'test'
                }
            ]
            
            print(f"🎯 Request Technologies: {request.technologies}")
            print(f"📋 Request Technologies Split: {[tech.strip().lower() for tech in request.technologies.split(',')]}")
            print()
            
            for i, content in enumerate(test_contents, 1):
                print(f"📖 Content {i}: {content['title']}")
                print(f"   Technologies: {content['technologies']}")
                
                # Test the tech bonus calculation
                tech_bonus = orchestrator._calculate_technology_alignment_bonus(content, request)
                title_bonus = orchestrator._calculate_title_query_alignment(content, request)
                keyword_bonus = orchestrator._calculate_keyword_amplification(content, request)
                
                print(f"   🔥 Tech Bonus: {tech_bonus:.3f}")
                print(f"   📰 Title Bonus: {title_bonus:.3f}")
                print(f"   🎯 Keyword Bonus: {keyword_bonus:.3f}")
                
                # Debug the exact calculation
                if hasattr(orchestrator, '_calculate_technology_alignment_bonus'):
                    request_techs = set(tech.strip().lower() for tech in request.technologies.split(',') if tech.strip())
                    content_techs = content.get('technologies', [])
                    
                    if isinstance(content_techs, list):
                        content_techs = set(tech.lower() for tech in content_techs)
                    
                    print(f"   🔍 Request techs: {request_techs}")
                    print(f"   🔍 Content techs: {content_techs}")
                    
                    exact_matches = request_techs.intersection(content_techs)
                    match_ratio = len(exact_matches) / len(request_techs) if request_techs else 0
                    
                    print(f"   🔍 Exact matches: {exact_matches}")
                    print(f"   🔍 Match ratio: {match_ratio:.3f}")
                    print(f"   🔍 Required for bonus: >= 0.3 (30%)")
                
                print()
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_tech_bonus()
