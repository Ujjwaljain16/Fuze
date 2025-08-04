#!/usr/bin/env python3
"""
Debug script to test project recommendation logic
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Project, SavedContent
from blueprints.recommendations import UnifiedRecommendationEngine

def debug_project_recommendations():
    """Debug the project recommendation logic"""
    print("🔍 DEBUGGING PROJECT RECOMMENDATIONS")
    print("=" * 50)
    
    # Create app context
    app = create_app()
    
    with app.app_context():
        # Get the DSA visualiser project
        project = Project.query.get(2)
        if not project:
            print("❌ Project not found")
            return
        
        print(f"📋 Project: {project.title}")
        print(f"📝 Description: {project.description}")
        print(f"🔧 Technologies: {project.technologies}")
        print()
        
        # Create engine
        engine = UnifiedRecommendationEngine()
        
        # Test project text extraction
        project_text = f"{project.title} {project.description or ''} {project.technologies or ''}"
        project_text = project_text.lower()
        print(f"🔍 Project text: {project_text}")
        print()
        
        # Test technology extraction
        tech_keywords = {
            'java': ['java', 'jvm', 'spring', 'maven', 'gradle', 'bytecode', 'asm', 'byte buddy'],
            'javascript': ['javascript', 'js', 'es6', 'es7', 'node', 'nodejs', 'node.js', 'react', 'reactjs', 'react.js', 'vue', 'vuejs', 'angular'],
            'python': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy', 'scipy'],
            'react': ['react', 'reactjs', 'react.js', 'react native', 'rn', 'jsx'],
            'react_native': ['react native', 'rn', 'expo', 'metro'],
            'mobile': ['mobile', 'ios', 'android', 'app', 'application', 'native', 'hybrid'],
            'web': ['web', 'html', 'css', 'frontend', 'backend', 'api', 'rest', 'graphql'],
            'database': ['database', 'sql', 'nosql', 'mongodb', 'postgresql', 'mysql', 'redis'],
            'ai_ml': ['ai', 'machine learning', 'ml', 'tensorflow', 'pytorch', 'neural', 'model'],
            'devops': ['devops', 'docker', 'kubernetes', 'ci/cd', 'deployment', 'aws', 'cloud'],
            'blockchain': ['blockchain', 'crypto', 'ethereum', 'bitcoin', 'smart contract', 'web3'],
            'payment': ['payment', 'stripe', 'paypal', 'upi', 'gateway', 'transaction'],
            'authentication': ['auth', 'authentication', 'oauth', 'jwt', 'login', 'signup'],
            'instrumentation': ['instrumentation', 'byte buddy', 'asm', 'bytecode', 'jvm'],
            'dsa': ['data structure', 'algorithm', 'dsa', 'sorting', 'searching', 'tree', 'graph']
        }
        
        project_techs = []
        for tech_category, tech_list in tech_keywords.items():
            for tech in tech_list:
                if tech in project_text:
                    project_techs.append(tech_category)
                    break
        
        print(f"🔧 Extracted technologies: {project_techs}")
        
        # Test domain extraction
        domain_keywords = {
            'web development': ['web development', 'frontend', 'backend', 'full stack'],
            'mobile development': ['mobile development', 'mobile app', 'ios', 'android'],
            'data science': ['data science', 'data analysis', 'statistics'],
            'machine learning': ['machine learning', 'ai', 'artificial intelligence', 'neural networks'],
            'backend development': ['backend development', 'server', 'api', 'database'],
            'frontend development': ['frontend development', 'ui', 'ux', 'user interface'],
            'data structures': ['data structures', 'algorithms', 'dsa', 'computer science'],
            'visualization': ['visualization', 'visual', 'chart', 'graph', 'plot'],
            'tutorial': ['tutorial', 'guide', 'learn', 'learning', 'course'],
            'documentation': ['documentation', 'docs', 'reference', 'manual'],
            'testing': ['testing', 'test', 'unit test', 'integration test'],
            'deployment': ['deployment', 'deploy', 'production', 'hosting'],
            'security': ['security', 'secure', 'authentication', 'authorization'],
            'performance': ['performance', 'optimization', 'speed', 'efficiency']
        }
        
        project_interests = []
        for domain_category, domain_list in domain_keywords.items():
            for domain in domain_list:
                if domain in project_text:
                    project_interests.append(domain_category)
                    break
        
        print(f"🎯 Extracted interests: {project_interests}")
        print()
        
        # Test scoring on a few content items
        print("🧮 TESTING SCORING LOGIC")
        print("-" * 30)
        
        # Get some content items
        content_items = SavedContent.query.filter(
            SavedContent.quality_score >= 7,
            SavedContent.title.notlike('%Test Bookmark%')
        ).limit(5).all()
        
        for i, content in enumerate(content_items, 1):
            print(f"\n📄 Content {i}: {content.title}")
            
            # Calculate score
            score = engine._calculate_project_relevance(content, project_techs, project_interests, project)
            print(f"   Score: {score:.3f}")
            
            # Generate reason
            reason = engine._generate_project_reason(content, project, score)
            print(f"   Reason: {reason}")
            
            # Check for DSA keywords in title
            title_lower = content.title.lower()
            dsa_keywords = ['data structure', 'algorithm', 'dsa', 'sorting', 'searching', 'tree', 'graph', 'visualization']
            found_keywords = [kw for kw in dsa_keywords if kw in title_lower]
            if found_keywords:
                print(f"   ✅ DSA keywords found: {found_keywords}")
            else:
                print(f"   ❌ No DSA keywords found")
        
        print("\n" + "=" * 50)
        print("DEBUG COMPLETED")

if __name__ == '__main__':
    debug_project_recommendations() 