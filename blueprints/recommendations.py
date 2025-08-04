from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import text
import time
import os
from redis_utils import redis_cache
from models import User, Project, SavedContent, Feedback, Task, ContentAnalysis
from app import db
from gemini_utils import GeminiAnalyzer
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import json
import logging
from rate_limit_handler import GeminiRateLimiter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/api/recommendations')

# Initialize models
try:
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    gemini_analyzer = GeminiAnalyzer()
    rate_limiter = GeminiRateLimiter()
    logger.info("Models initialized successfully")
except Exception as e:
    logger.error(f"Error initializing models: {e}")
    embedding_model = None
    gemini_analyzer = None
    rate_limiter = None

class SmartRecommendationEngine:
    def __init__(self):
        self.embedding_model = embedding_model
        self.gemini_analyzer = gemini_analyzer
        self.cache_duration = 3600  # 1 hour
        
    def get_recommendations(self, user_id, user_input=None, use_cache=True):
        """Get smart recommendations based on user profile and input"""
        start_time = time.time()
        
        # Check cache first
        if use_cache:
            cache_key = f"smart_recommendations:{user_id}:{hash(str(user_input))}"
            cached_result = redis_cache.get_cache(cache_key)
            if cached_result is not None:
                cached_result['cached'] = True
                cached_result['computation_time_ms'] = 0
                return cached_result
        
        # Get user profile
        user_profile = self._get_user_profile(user_id)
        if not user_profile:
            return {'recommendations': [], 'error': 'User profile not found'}
        
        # Get user's saved content for analysis
        user_content = self._get_user_content(user_id)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(user_profile, user_content, user_input)
        
        computation_time = (time.time() - start_time) * 1000
        
        result = {
            'recommendations': recommendations,
            'cached': False,
            'computation_time_ms': computation_time,
            'total_candidates': len(user_content)
        }
        
        # Cache the result
        if use_cache:
            redis_cache.set_cache(cache_key, result, self.cache_duration)
        
        return result
    
    def _get_user_profile(self, user_id):
        """Get user's learning profile and preferences"""
        try:
            user = User.query.get(user_id)
            if not user:
                return None
            
            # Get user's saved content for profile analysis
            saved_content = SavedContent.query.filter_by(user_id=user_id).all()
            
            # Analyze user's interests based on saved content using cached analysis
            interests = []
            technologies = []
            
            for content in saved_content:
                # Use cached analysis instead of making fresh API calls
                cached_analysis = self._get_cached_analysis(content.id)
                if cached_analysis:
                    if 'technology_tags' in cached_analysis:
                        technologies.extend(cached_analysis['technology_tags'])
                    if 'key_concepts' in cached_analysis:
                        interests.extend(cached_analysis['key_concepts'])
                else:
                    # Fallback to basic extraction from tags/notes
                    if content.tags:
                        technologies.extend([tag.strip() for tag in content.tags.split(',')])
                    if content.notes:
                        interests.append(content.notes[:50])  # First 50 chars as concept
            
            return {
                'user_id': user_id,
                'interests': list(set(interests)),
                'technologies': list(set(technologies)),
                'total_saved': len(saved_content)
            }
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None
    
    def _get_user_content(self, user_id):
        """Get user's saved content"""
        try:
            return SavedContent.query.filter_by(user_id=user_id).all()
        except Exception as e:
            logger.error(f"Error getting user content: {e}")
            return []
    
    def _generate_recommendations(self, user_profile, user_content, user_input):
        """Generate recommendations based on profile and content"""
        recommendations = []
        
        try:
            # Get all available content (excluding user's own)
            all_content = SavedContent.query.filter(
                SavedContent.user_id != user_profile['user_id'],
                SavedContent.quality_score >= 7
            ).limit(50).all()
            
            for content in all_content:
                score = self._calculate_relevance_score(content, user_profile, user_input)
                
                if score > 0.3:  # Minimum relevance threshold
                    recommendations.append({
                        'id': content.id,
                        'title': content.title,
                        'content': content.extracted_text[:500],
                        'similarity_score': score,
                        'quality_score': content.quality_score,
                        'user_id': content.user_id,
                        'reason': self._generate_reason(content, user_profile)
                    })
            
            # Sort by score and take top 10
            recommendations.sort(key=lambda x: x['similarity_score'], reverse=True)
            return recommendations[:10]
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []
    
    def _calculate_relevance_score(self, content, user_profile, user_input):
        """Calculate relevance score for content"""
        try:
            score = 0.0
            
            # Base score from quality
            score += content.quality_score / 10.0
            
            # Technology match using cached analysis
            cached_analysis = self._get_cached_analysis(content.id)
            if cached_analysis:
                # Use cached analysis for technology matching
                content_techs = set(cached_analysis.get('technology_tags', []))
                user_techs = set(user_profile.get('technologies', []))
                
                if content_techs and user_techs:
                    overlap = len(content_techs.intersection(user_techs))
                    score += (overlap / len(user_techs)) * 0.3
                
                # Input-based scoring with cached analysis
                if user_input and user_input.get('technologies'):
                    input_techs = set(user_input['technologies'].split(','))
                    if content_techs and input_techs:
                        overlap = len(content_techs.intersection(input_techs))
                        score += (overlap / len(input_techs)) * 0.4
            else:
                # Fallback to basic scoring without analysis
                score += 0.1  # Small bonus for content without analysis
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating relevance score: {e}")
            return 0.0
    
    def _generate_reason(self, content, user_profile):
        """Generate reason for recommendation"""
        try:
            # Use cached analysis if available
            cached_analysis = self._get_cached_analysis(content.id)
            if cached_analysis and 'summary' in cached_analysis:
                return cached_analysis['summary']
            
            # Fallback reason
            return f"High-quality content matching your interests"
            
        except Exception as e:
            logger.error(f"Error generating reason: {e}")
            return "Recommended based on your profile"
    
    def _get_cached_analysis(self, content_id):
        """Get cached analysis for a content item"""
        try:
            # Try Redis first
            cache_key = f"content_analysis:{content_id}"
            cached_result = redis_cache.get_cache(cache_key)
            
            if cached_result:
                return cached_result
            
            # Try database
            analysis = ContentAnalysis.query.filter_by(content_id=content_id).first()
            if analysis:
                # Cache in Redis for future use
                redis_cache.set_cache(cache_key, analysis.analysis_data, ttl=86400)
                return analysis.analysis_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached analysis for content {content_id}: {e}")
            return None

class SmartTaskRecommendationEngine:
    def __init__(self):
        self.embedding_model = embedding_model
        self.gemini_analyzer = gemini_analyzer
        self.cache_duration = 1800  # 30 minutes
        
    def get_task_recommendations(self, user_id, task_id, use_cache=True):
        """Get recommendations for a specific task"""
        start_time = time.time()
        
        # Check cache first
        if use_cache:
            cache_key = f"task_recommendations:{user_id}:{task_id}"
            cached_result = redis_cache.get_cache(cache_key)
            if cached_result is not None:
                cached_result['cached'] = True
                cached_result['computation_time_ms'] = 0
                return cached_result
        
        try:
            # Get task details
            task = Task.query.get(task_id)
            if not task:
                return {'recommendations': [], 'error': 'Task not found'}
            
            # Get user's saved content
            user_content = SavedContent.query.filter_by(user_id=user_id).all()
            
            # Generate task-specific recommendations
            recommendations = self._generate_task_recommendations(task, user_content)
            
            computation_time = (time.time() - start_time) * 1000
            
            result = {
                'recommendations': recommendations,
                'task_id': task_id,
                'task_title': task.title,
                'cached': False,
                'computation_time_ms': computation_time
            }
            
            # Cache the result
            if use_cache:
                redis_cache.set_cache(cache_key, result, self.cache_duration)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting task recommendations: {e}")
            return {'recommendations': [], 'error': str(e)}
    
    def _generate_task_recommendations(self, task, user_content):
        """Generate recommendations for a specific task"""
        recommendations = []
        
        try:
            # Get all available content
            all_content = SavedContent.query.filter(
                SavedContent.quality_score >= 7
            ).limit(50).all()
            
            for content in all_content:
                score = self._calculate_task_relevance(content, task)
                
                if score > 0.3:
                    recommendations.append({
                        'id': content.id,
                        'title': content.title,
                        'content': content.extracted_text[:500],
                        'similarity_score': score,
                        'quality_score': content.quality_score,
                        'user_id': content.user_id,
                        'reason': f"Relevant to task: {task.title}"
                    })
            
            # Sort by score and take top 10
            recommendations.sort(key=lambda x: x['similarity_score'], reverse=True)
            return recommendations[:10]
            
        except Exception as e:
            logger.error(f"Error generating task recommendations: {e}")
            return []
    
    def _calculate_task_relevance(self, content, task):
        """Calculate relevance score for task"""
        try:
            score = 0.0
            
            # Base score from quality
            score += content.quality_score / 10.0
            
            # Task-content similarity analysis using cached analysis
            content_analysis = self._get_cached_analysis(content.id)
            if content_analysis:
                # Compare technologies
                content_techs = set(content_analysis.get('technology_tags', []))
                task_techs = set(task.tags.split(',') if task.tags else [])
                
                if content_techs and task_techs:
                    overlap = len(content_techs.intersection(task_techs))
                    score += (overlap / len(task_techs)) * 0.4
                
                # Compare key concepts
                content_concepts = set(content_analysis.get('key_concepts', []))
                task_concepts = set([task.title.lower(), task.description.lower()] if task.description else [task.title.lower()])
                
                if content_concepts and task_concepts:
                    overlap = len(content_concepts.intersection(task_concepts))
                    score += (overlap / len(task_concepts)) * 0.3
            else:
                # Fallback to basic scoring without analysis
                score += 0.1
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating task relevance: {e}")
            return 0.0
    
    def _get_cached_analysis(self, content_id):
        """Get cached analysis for a content item"""
        try:
            # Try Redis first
            cache_key = f"content_analysis:{content_id}"
            cached_result = redis_cache.get_cache(cache_key)
            
            if cached_result:
                return cached_result
            
            # Try database
            analysis = ContentAnalysis.query.filter_by(content_id=content_id).first()
            if analysis:
                # Cache in Redis for future use
                redis_cache.set_cache(cache_key, analysis.analysis_data, ttl=86400)
                return analysis.analysis_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached analysis for content {content_id}: {e}")
            return None

class UnifiedRecommendationEngine:
    def __init__(self):
        self.smart_engine = SmartRecommendationEngine()
        self.task_engine = SmartTaskRecommendationEngine()
        self.cache_duration = 3600
        
    def get_unified_recommendations(self, user_id, user_input=None, use_cache=True):
        """Get unified recommendations combining multiple approaches"""
        start_time = time.time()
        
        # Check cache first
        if use_cache:
            cache_key = f"unified_recommendations:{user_id}:{hash(str(user_input))}"
            cached_result = redis_cache.get_cache(cache_key)
            if cached_result is not None:
                cached_result['cached'] = True
                cached_result['computation_time_ms'] = 0
                return cached_result
        
        try:
            # Get recommendations from different engines
            smart_recs = self.smart_engine.get_recommendations(user_id, user_input, use_cache=False)
            general_recs = self._get_general_recommendations(user_id, use_cache=False)
            
            # Combine and deduplicate
            all_recommendations = []
            seen_ids = set()
            
            # Add smart recommendations first
            for rec in smart_recs.get('recommendations', []):
                if rec['id'] not in seen_ids:
                    all_recommendations.append(rec)
                    seen_ids.add(rec['id'])
            
            # Add general recommendations
            for rec in general_recs.get('recommendations', []):
                if rec['id'] not in seen_ids:
                    all_recommendations.append(rec)
                    seen_ids.add(rec['id'])
            
            # Sort by score and take top 10
            all_recommendations.sort(key=lambda x: x['similarity_score'], reverse=True)
            final_recommendations = all_recommendations[:10]
            
            computation_time = (time.time() - start_time) * 1000
            
            result = {
                'recommendations': final_recommendations,
                'cached': False,
                'computation_time_ms': computation_time,
                'total_candidates': len(all_recommendations)
            }
            
            # Cache the result
            if use_cache:
                redis_cache.set_cache(cache_key, result, self.cache_duration)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting unified recommendations: {e}")
            return {'recommendations': [], 'error': str(e)}
    
    def get_unified_project_recommendations(self, user_id, project_id, use_cache=True):
        """Get unified recommendations for a specific project"""
        start_time = time.time()
        
        # Check cache first
        if use_cache:
            cache_key = f"unified_project_recommendations:{user_id}:{project_id}"
            cached_result = redis_cache.get_cache(cache_key)
            if cached_result is not None:
                cached_result['cached'] = True
                cached_result['computation_time_ms'] = 0
                return cached_result
        
        try:
            # Get project details
            project = Project.query.get(project_id)
            if not project:
                return {'recommendations': [], 'error': 'Project not found'}
            
            # Get project-specific recommendations
            recommendations = self._get_project_recommendations(project, user_id)
            
            computation_time = (time.time() - start_time) * 1000
            
            result = {
                'recommendations': recommendations,
                'project_id': project_id,
                'project_title': project.title,
                'cached': False,
                'computation_time_ms': computation_time
            }
            
            # Cache the result
            if use_cache:
                redis_cache.set_cache(cache_key, result, self.cache_duration)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting unified project recommendations: {e}")
            return {'recommendations': [], 'error': str(e)}
    
    def _get_general_recommendations(self, user_id, use_cache=True):
        """Get general recommendations based on quality and diversity"""
        try:
            # Get high-quality content with diversity
            all_content = db.session.execute(text("""
                WITH content_categories AS (
                    SELECT 
                        id,
                        extracted_text,
                        quality_score,
                        user_id,
                        CASE 
                            WHEN LOWER(title) LIKE '%tutorial%' OR LOWER(title) LIKE '%guide%' OR LOWER(title) LIKE '%learn%' THEN 'tutorials'
                            WHEN LOWER(title) LIKE '%docs%' OR LOWER(title) LIKE '%documentation%' OR LOWER(title) LIKE '%api%' THEN 'documentation'
                            WHEN LOWER(title) LIKE '%project%' OR LOWER(title) LIKE '%github%' OR LOWER(title) LIKE '%repo%' THEN 'projects'
                            WHEN LOWER(title) LIKE '%leetcode%' THEN 'leetcode'
                            WHEN LOWER(title) LIKE '%interview%' OR LOWER(title) LIKE '%question%' THEN 'interviews'
                            ELSE 'other'
                        END as category
                    FROM saved_content 
                    WHERE quality_score >= 7
                    AND title NOT LIKE '%Test Bookmark%'
                    AND title NOT LIKE '%test bookmark%'
                ),
                ranked_content AS (
                    SELECT 
                        *,
                        ROW_NUMBER() OVER (PARTITION BY category ORDER BY quality_score DESC, RANDOM()) as rank_in_category
                    FROM content_categories
                )
                SELECT id, extracted_text, quality_score, user_id
                FROM ranked_content 
                WHERE rank_in_category <= 2
                ORDER BY RANDOM()
                LIMIT 15
            """), {'user_id': user_id}).fetchall()
            
            recommendations = []
            for content in all_content:
                # Get the actual title from the database
                content_obj = SavedContent.query.get(content[0])
                title = content_obj.title if content_obj else "No title available"
                
                recommendations.append({
                    'id': content[0],
                    'title': title,
                    'content': content[1],
                    'similarity_score': content[2] / 10.0,
                    'quality_score': content[2],
                    'user_id': content[3],
                    'reason': 'High-quality content from your saved bookmarks'
                })
            
            return {
                'recommendations': recommendations[:10],
                'cached': False,
                'computation_time_ms': 0,
                'total_candidates': len(all_content)
            }
            
        except Exception as e:
            logger.error(f"Error getting general recommendations: {e}")
            return {'recommendations': []}
    
    def _get_project_recommendations(self, project, user_id):
        """Get recommendations for a specific project"""
        try:
            # Extract project technologies and interests from project description
            project_techs = []
            project_interests = []
            
            # Extract technologies from project description and tags
            project_text = f"{project.title} {project.description or ''} {project.technologies or ''}"
            project_text = project_text.lower()
            
            # Enhanced technology keywords with better matching
            tech_keywords = {
                'java': ['java', 'jvm', 'spring', 'maven', 'gradle', 'bytecode', 'asm', 'byte buddy', 'javac', 'jdk', 'jre'],
                'javascript': ['javascript', 'js', 'es6', 'es7', 'node', 'nodejs', 'node.js', 'react', 'reactjs', 'react.js', 'vue', 'vuejs', 'angular', 'ecmascript'],
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
            
            # Extract technologies from project text using enhanced matching
            for tech_category, tech_list in tech_keywords.items():
                for tech in tech_list:
                    if tech in project_text:
                        project_techs.append(tech_category)
                        break  # Only add each category once
            
            # Enhanced domain interests
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
            
            for domain_category, domain_list in domain_keywords.items():
                for domain in domain_list:
                    if domain in project_text:
                        project_interests.append(domain_category)
                        break  # Only add each category once
            
            # Debug logging
            logger.info(f"Project: {project.title}")
            logger.info(f"Project technologies: {project_techs}")
            logger.info(f"Project interests: {project_interests}")
            
            # Get content with relevance scoring
            all_content = SavedContent.query.filter(
                SavedContent.quality_score >= 7,
                SavedContent.title.notlike('%Test Bookmark%'),
                SavedContent.title.notlike('%test bookmark%')
            ).limit(100).all()  # Increased limit for better selection
            
            scored_content = []
            for content in all_content:
                score = self._calculate_project_relevance(content, project_techs, project_interests, project)
                if score > 0.1:  # Lowered threshold to get more candidates
                    scored_content.append((content, score))
            
            # Sort by score and take top recommendations
            scored_content.sort(key=lambda x: x[1], reverse=True)
            
            recommendations = []
            for content, score in scored_content[:10]:
                recommendations.append({
                    'id': content.id,
                    'title': content.title,
                    'content': content.extracted_text[:500] if content.extracted_text else '',
                    'similarity_score': score,
                    'quality_score': content.quality_score,
                    'user_id': content.user_id,
                    'reason': self._generate_project_reason(content, project, score)
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting project recommendations: {e}")
            return []
    
    def _calculate_project_relevance(self, content, project_techs, project_interests, project):
        """Calculate relevance score for content based on project requirements"""
        try:
            score = 0.0
            
            # Base score from quality (reduced weight)
            score += (content.quality_score / 10.0) * 0.2
            
            # Get cached analysis for content
            cached_analysis = self._get_cached_analysis(content.id)
            
            if cached_analysis:
                # Technology matching with cached analysis
                content_techs = set(cached_analysis.get('technology_tags', []))
                if content_techs and project_techs:
                    overlap = len(content_techs.intersection(set(project_techs)))
                    if overlap > 0:
                        score += (overlap / len(project_techs)) * 0.4
                
                # Concept matching with cached analysis
                content_concepts = set(cached_analysis.get('key_concepts', []))
                if content_concepts and project_interests:
                    overlap = len(content_concepts.intersection(set(project_interests)))
                    if overlap > 0:
                        score += (overlap / len(project_interests)) * 0.3
            else:
                # Enhanced fallback: better text matching
                content_text = f"{content.title} {content.notes or ''} {content.tags or ''} {content.extracted_text or ''}".lower()
                
                # Technology matching with enhanced keywords
                tech_match_count = 0
                for tech in project_techs:
                    # Check for exact matches and variations
                    if tech in content_text:
                        tech_match_count += 1
                    elif tech == 'java' and ('jvm' in content_text or 'bytecode' in content_text):
                        tech_match_count += 1
                    elif tech == 'dsa' and ('data structure' in content_text or 'algorithm' in content_text):
                        tech_match_count += 1
                    elif tech == 'instrumentation' and ('byte buddy' in content_text or 'asm' in content_text):
                        tech_match_count += 1
                
                if tech_match_count > 0:
                    score += (tech_match_count / len(project_techs)) * 0.3
                
                # Domain matching
                domain_match_count = 0
                for domain in project_interests:
                    if domain in content_text:
                        domain_match_count += 1
                
                if domain_match_count > 0:
                    score += (domain_match_count / len(project_interests)) * 0.2
            
            # Title relevance bonus (increased weight)
            content_title_lower = content.title.lower()
            project_title_lower = project.title.lower()
            
            # Check for exact matches or strong relevance
            project_words = project_title_lower.split()
            title_matches = sum(1 for word in project_words if word in content_title_lower)
            if title_matches > 0:
                score += (title_matches / len(project_words)) * 0.3
            
            # Check for domain-specific keywords in title
            domain_keywords = ['tutorial', 'guide', 'documentation', 'example', 'implementation', 'visualization']
            if any(keyword in content_title_lower for keyword in domain_keywords):
                score += 0.1
            
            # Special bonus for DSA-related content
            if 'dsa' in project_techs or 'data structures' in project_interests:
                dsa_keywords = ['data structure', 'algorithm', 'dsa', 'sorting', 'searching', 'tree', 'graph', 'visualization']
                if any(keyword in content_title_lower for keyword in dsa_keywords):
                    score += 0.2
            
            # Special bonus for Java-related content
            if 'java' in project_techs:
                java_keywords = ['java', 'jvm', 'bytecode', 'byte buddy', 'instrumentation']
                if any(keyword in content_title_lower for keyword in java_keywords):
                    score += 0.2
            
            # Penalty for JavaScript content when project is Java-specific
            if 'java' in project_techs and ('javascript' in content_title_lower or 'js ' in content_title_lower or 'node' in content_title_lower):
                score -= 0.3  # Significant penalty for wrong language
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating project relevance: {e}")
            return 0.0
    
    def _generate_project_reason(self, content, project, score):
        """Generate reason for project recommendation"""
        try:
            # Use cached analysis if available
            cached_analysis = self._get_cached_analysis(content.id)
            if cached_analysis and 'summary' in cached_analysis:
                return f"Relevant to {project.title}: {cached_analysis['summary']}"
            
            # Generate specific reason based on content analysis
            content_title_lower = content.title.lower()
            project_title_lower = project.title.lower()
            
            # Check for specific technology matches
            if 'java' in content_title_lower or 'jvm' in content_title_lower:
                return f"Java-related content for {project.title} development"
            elif 'javascript' in content_title_lower or 'js ' in content_title_lower:
                return f"JavaScript content (different from Java) - may not be relevant for {project.title}"
            elif 'data structure' in content_title_lower or 'algorithm' in content_title_lower:
                return f"DSA content relevant to {project.title} visualization"
            elif 'bytecode' in content_title_lower or 'instrumentation' in content_title_lower:
                return f"Bytecode/instrumentation content for {project.title} implementation"
            elif 'visualization' in content_title_lower or 'visual' in content_title_lower:
                return f"Visualization content perfect for {project.title}"
            elif 'tutorial' in content_title_lower or 'guide' in content_title_lower:
                return f"Tutorial content to help with {project.title} development"
            elif 'documentation' in content_title_lower or 'docs' in content_title_lower:
                return f"Documentation useful for {project.title} implementation"
            
            # Check for project title matches
            project_words = project_title_lower.split()
            title_matches = [word for word in project_words if word in content_title_lower]
            if title_matches:
                return f"Content directly related to {', '.join(title_matches)} for {project.title}"
            
            # Fallback reason based on score
            if score > 0.7:
                return f"Highly relevant content for {project.title} requirements"
            elif score > 0.5:
                return f"Good match for {project.title} development"
            elif score > 0.3:
                return f"Useful content for {project.title} project"
            else:
                return f"Quality content that may help with {project.title}"
            
        except Exception as e:
            logger.error(f"Error generating project reason: {e}")
            return f"Recommended for {project.title}"
    
    def _get_cached_analysis(self, content_id):
        """Get cached analysis for a content item"""
        try:
            # Try Redis first
            cache_key = f"content_analysis:{content_id}"
            cached_result = redis_cache.get_cache(cache_key)
            
            if cached_result:
                return cached_result
            
            # Try database
            analysis = ContentAnalysis.query.filter_by(content_id=content_id).first()
            if analysis:
                # Cache in Redis for future use
                redis_cache.set_cache(cache_key, analysis.analysis_data, ttl=86400)
                return analysis.analysis_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached analysis for content {content_id}: {e}")
            return None

class GeminiEnhancedRecommendationEngine:
    def __init__(self):
        self.unified_engine = UnifiedRecommendationEngine()
        self.gemini_analyzer = gemini_analyzer
        self.rate_limiter = rate_limiter
        self.cache_duration = 1800  # 30 minutes
        self.max_recommendations = 10
        self.cache_hits = 0
        self.cache_misses = 0
        self.api_calls = 0
        self.batch_operations = 0
        self.gemini_available = gemini_analyzer is not None and rate_limiter is not None
        
    def get_gemini_enhanced_recommendations(self, user_id, user_input=None, use_cache=True):
        """Get Gemini-enhanced recommendations"""
        start_time = time.time()
        
        # Check cache first
        if use_cache:
            cache_key = f"gemini_enhanced_recommendations:{user_id}:{hash(str(user_input))}"
            cached_result = redis_cache.get_cache(cache_key)
            if cached_result is not None:
                cached_result['cached'] = True
                cached_result['computation_time_ms'] = 0
                return cached_result
        
        try:
            # Get base recommendations
            base_result = self.unified_engine.get_unified_recommendations(user_id, user_input, use_cache=False)
            recommendations = base_result.get('recommendations', [])
            
            # Enhance with Gemini analysis
            enhanced_recommendations = self._enhance_with_gemini(recommendations, user_input)
            
            computation_time = (time.time() - start_time) * 1000
            
            result = {
                'recommendations': enhanced_recommendations,
                'cached': False,
                'computation_time_ms': computation_time,
                'total_candidates': len(recommendations)
            }
            
            # Cache the result
            if use_cache:
                redis_cache.set_cache(cache_key, result, self.cache_duration)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting Gemini-enhanced recommendations: {e}")
            # Fallback to base recommendations
            return self.unified_engine.get_unified_recommendations(user_id, user_input, use_cache)
    
    def get_gemini_enhanced_project_recommendations(self, user_id, project_id, use_cache=True):
        """Get Gemini-enhanced project recommendations"""
        start_time = time.time()
        
        # Check cache first
        if use_cache:
            cache_key = f"gemini_enhanced_project_recommendations:{user_id}:{project_id}"
            cached_result = redis_cache.get_cache(cache_key)
            if cached_result is not None:
                cached_result['cached'] = True
                cached_result['computation_time_ms'] = 0
                return cached_result
        
        try:
            # Get base project recommendations
            base_result = self.unified_engine.get_unified_project_recommendations(user_id, project_id, use_cache=False)
            recommendations = base_result.get('recommendations', [])
            
            # Enhance with Gemini analysis
            enhanced_recommendations = self._enhance_with_gemini(recommendations, None, project_id)
            
            computation_time = (time.time() - start_time) * 1000
            
            result = {
                'recommendations': enhanced_recommendations,
                'project_id': project_id,
                'cached': False,
                'computation_time_ms': computation_time
            }
            
            # Cache the result
            if use_cache:
                redis_cache.set_cache(cache_key, result, self.cache_duration)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting Gemini-enhanced project recommendations: {e}")
            # Fallback to base project recommendations
            return self.unified_engine.get_unified_project_recommendations(user_id, project_id, use_cache)
    
    def _enhance_with_gemini(self, recommendations, user_input=None, project_id=None):
        """Enhance recommendations with Gemini analysis using cached results when possible"""
        if not self.gemini_available or not recommendations:
            return recommendations
        
        try:
            # Check rate limits
            if not self.rate_limiter.get_status().get('can_make_request', True):
                logger.warning("Gemini rate limit reached, using cached analysis")
                return self._enhance_with_cached_analysis(recommendations, user_input, project_id)
            
            # Take top candidates for enhancement (limit to avoid API costs)
            top_candidates = recommendations[:5]
            
            # Check for cached analysis first
            candidates_with_cache = []
            candidates_without_cache = []
            
            for candidate in top_candidates:
                cached_analysis = self._get_cached_analysis(candidate['id'])
                if cached_analysis:
                    candidates_with_cache.append((candidate, cached_analysis))
                else:
                    candidates_without_cache.append(candidate)
            
            # Use cached analysis for candidates that have it
            enhanced_from_cache = self._apply_cached_analysis(candidates_with_cache, user_input)
            
            # Use batch processing for candidates without cache
            enhanced_from_api = []
            if candidates_without_cache:
                enhanced_from_api = self._batch_gemini_enhancement(candidates_without_cache, user_input)
            
            # Combine all enhanced recommendations
            final_recommendations = enhanced_from_cache + enhanced_from_api + recommendations[5:]
            
            return final_recommendations[:self.max_recommendations]
            
        except Exception as e:
            logger.error(f"Error in batch Gemini enhancement: {e}")
            return self._enhance_with_cached_analysis(recommendations, user_input, project_id)
    
    def _batch_gemini_enhancement(self, candidates, user_input=None):
        """Process multiple candidates in a single Gemini API call"""
        if not candidates:
            return []
        
        try:
            # Create batch prompt
            batch_prompt = self._create_batch_prompt(candidates, user_input)
            
            # Make single API call for all candidates
            if self.rate_limiter.get_status().get('can_make_request', True):
                self.api_calls += 1
                self.batch_operations += 1
                
                batch_response = self.gemini_analyzer.analyze_batch_content(batch_prompt)
                
                if batch_response:
                    return self._extract_batch_insights(candidates, batch_response)
            
            return candidates
            
        except Exception as e:
            logger.error(f"Error in batch enhancement: {e}")
            return candidates
    
    def _get_cached_analysis(self, content_id):
        """Get cached analysis for a content item"""
        try:
            # Try Redis first
            cache_key = f"content_analysis:{content_id}"
            cached_result = redis_cache.get_cache(cache_key)
            
            if cached_result:
                return cached_result
            
            # Try database
            analysis = ContentAnalysis.query.filter_by(content_id=content_id).first()
            if analysis:
                # Cache in Redis for future use
                redis_cache.set_cache(cache_key, analysis.analysis_data, ttl=86400)
                return analysis.analysis_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached analysis for content {content_id}: {e}")
            return None
    
    def _enhance_with_cached_analysis(self, recommendations, user_input=None, project_id=None):
        """Enhance recommendations using only cached analysis"""
        if not recommendations:
            return recommendations
        
        enhanced_recommendations = []
        
        for candidate in recommendations[:5]:  # Limit to top 5
            cached_analysis = self._get_cached_analysis(candidate['id'])
            if cached_analysis:
                enhanced_candidate = candidate.copy()
                enhanced_candidate['reason'] = self._generate_reason_from_cache(cached_analysis, user_input)
                enhanced_candidate['cached_analysis'] = True
                enhanced_recommendations.append(enhanced_candidate)
            else:
                # Apply dynamic reason for candidates without cache
                enhanced_candidate = self._apply_dynamic_reason(candidate)
                enhanced_candidate['cached_analysis'] = False
                enhanced_recommendations.append(enhanced_candidate)
        
        # Add remaining recommendations with dynamic reasons
        for candidate in recommendations[5:]:
            enhanced_candidate = self._apply_dynamic_reason(candidate)
            enhanced_candidate['cached_analysis'] = False
            enhanced_recommendations.append(enhanced_candidate)
        
        return enhanced_recommendations
    
    def _apply_cached_analysis(self, candidates_with_cache, user_input=None):
        """Apply cached analysis to candidates"""
        enhanced_candidates = []
        
        for candidate, cached_analysis in candidates_with_cache:
            enhanced_candidate = candidate.copy()
            enhanced_candidate['reason'] = self._generate_reason_from_cache(cached_analysis, user_input)
            enhanced_candidate['cached_analysis'] = True
            enhanced_candidates.append(enhanced_candidate)
        
        return enhanced_candidates
    
    def _generate_reason_from_cache(self, cached_analysis, user_input=None):
        """Generate recommendation reason from cached analysis"""
        try:
            if not cached_analysis:
                return "Content analysis available"
            
            # Extract key information from cached analysis
            key_concepts = cached_analysis.get('key_concepts', [])
            content_type = cached_analysis.get('content_type', 'content')
            difficulty_level = cached_analysis.get('difficulty_level', 'intermediate')
            technology_tags = cached_analysis.get('technology_tags', [])
            
            # Build reason from cached data
            reason_parts = []
            
            if content_type and content_type != 'unknown':
                reason_parts.append(f"Excellent {content_type}")
            
            if difficulty_level and difficulty_level != 'unknown':
                reason_parts.append(f"({difficulty_level} level)")
            
            if technology_tags:
                if isinstance(technology_tags, list):
                    tech_str = ', '.join(technology_tags[:3])  # Limit to 3 technologies
                else:
                    tech_str = str(technology_tags)
                reason_parts.append(f"covers {tech_str}")
            
            if key_concepts:
                if isinstance(key_concepts, list):
                    concept_str = ', '.join(key_concepts[:2])  # Limit to 2 concepts
                else:
                    concept_str = str(key_concepts)
                reason_parts.append(f"focusing on {concept_str}")
            
            if user_input:
                reason_parts.append(f"relevant to your interest in {user_input}")
            
            if reason_parts:
                return ' '.join(reason_parts)
            else:
                return "Based on cached content analysis"
                
        except Exception as e:
            logger.error(f"Error generating reason from cache: {e}")
            return "Content analysis available"
    
    def _create_batch_prompt(self, candidates, user_input=None):
        """Create a batch prompt for multiple candidates"""
        prompt_parts = [
            "Analyze the following content items and provide insights for each in a structured JSON format.",
            "",
            "For each item, provide this exact JSON structure:",
            "{",
            '  "item_1": {',
            '    "key_benefit": "Brief, specific reason why this content is valuable",',
            '    "technologies": ["tech1", "tech2"],',
            '    "difficulty": "beginner|intermediate|advanced",',
            '    "relevance_score": 0.85',
            '  },',
            '  "item_2": {',
            '    "key_benefit": "Brief, specific reason why this content is valuable",',
            '    "technologies": ["tech1", "tech2"],',
            '    "difficulty": "beginner|intermediate|advanced",',
            '    "relevance_score": 0.75',
            '  }',
            "}",
            "",
            "Content items to analyze:"
        ]
        
        for i, candidate in enumerate(candidates, 1):
            content_preview = candidate.get('content', '')[:300]
            prompt_parts.append(f"Item {i}:")
            prompt_parts.append(f"Title: {candidate.get('title', 'N/A')}")
            prompt_parts.append(f"Content: {content_preview}")
            prompt_parts.append("")
        
        if user_input:
            prompt_parts.append(f"User context: {user_input}")
        
        prompt_parts.append("Provide ONLY the JSON response, no additional text.")
        
        return "\n".join(prompt_parts)
    
    def _extract_batch_insights(self, candidates, batch_response):
        """Extract insights from batch response and apply to candidates"""
        enhanced_candidates = []
        
        try:
            # Parse batch response
            if isinstance(batch_response, str):
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', batch_response, re.DOTALL)
                if json_match:
                    try:
                        batch_analysis = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse JSON from batch response, using fallback")
                        batch_analysis = {}
                else:
                    batch_analysis = {}
            else:
                batch_analysis = batch_response
            
            # Apply insights to each candidate
            for i, candidate in enumerate(candidates):
                enhanced_candidate = candidate.copy()
                
                # Get analysis for this candidate - try different key formats
                item_key = f"item_{i+1}"
                candidate_analysis = (
                    batch_analysis.get(item_key, {}) or 
                    batch_analysis.get(str(i+1), {}) or
                    batch_analysis.get(f"item{i+1}", {}) or
                    {}
                )
                
                if candidate_analysis:
                    # Update reason with Gemini insights
                    if candidate_analysis.get('key_benefit'):
                        enhanced_candidate['reason'] = candidate_analysis['key_benefit']
                    else:
                        # Generate dynamic reason as fallback
                        enhanced_candidate['reason'] = self._generate_dynamic_reason(candidate)
                    
                    # Add additional insights
                    if candidate_analysis.get('technologies'):
                        enhanced_candidate['technologies'] = candidate_analysis['technologies']
                    
                    if candidate_analysis.get('difficulty'):
                        enhanced_candidate['difficulty'] = candidate_analysis['difficulty']
                    
                    if candidate_analysis.get('relevance_score'):
                        enhanced_candidate['similarity_score'] = float(candidate_analysis['relevance_score'])
                else:
                    # Fallback to dynamic reason
                    enhanced_candidate['reason'] = self._generate_dynamic_reason(candidate)
                
                enhanced_candidates.append(enhanced_candidate)
            
            return enhanced_candidates
            
        except Exception as e:
            logger.error(f"Error extracting batch insights: {e}")
            # Fallback: apply dynamic reasons to all candidates
            return [self._apply_dynamic_reason(candidate) for candidate in candidates]
    
    def _generate_dynamic_reason(self, candidate):
        """Generate a dynamic reason based on content analysis"""
        try:
            title = candidate.get('title', '').lower()
            content = candidate.get('content', '').lower()
            
            # Extract technologies from title/content
            tech_keywords = ['python', 'javascript', 'java', 'react', 'node', 'sql', 'docker', 'aws', 'git', 'html', 'css', 'typescript', 'vue', 'angular', 'mongodb', 'postgresql', 'redis', 'kubernetes', 'terraform', 'jenkins', 'github', 'gitlab']
            found_techs = [tech for tech in tech_keywords if tech in title or tech in content]
            
            # Determine content type
            if any(word in title for word in ['tutorial', 'guide', 'learn', 'getting started']):
                content_type = 'tutorial'
            elif any(word in title for word in ['docs', 'documentation', 'api', 'reference']):
                content_type = 'documentation'
            elif any(word in title for word in ['project', 'github', 'repo', 'repository']):
                content_type = 'project'
            elif any(word in title for word in ['leetcode', 'interview', 'question', 'problem']):
                content_type = 'practice'
            elif any(word in title for word in ['best practice', 'pattern', 'architecture']):
                content_type = 'best practice'
            else:
                content_type = 'resource'
            
            # Build dynamic reason
            if found_techs:
                tech_part = f"Content about {', '.join(found_techs[:2])}"
            else:
                tech_part = "High-quality technical content"
            
            type_part = f" ({content_type})" if content_type != 'resource' else ""
            
            # Add quality indicator
            quality_score = candidate.get('quality_score', 7)
            if quality_score >= 9:
                quality_part = " - Excellent quality"
            elif quality_score >= 7:
                quality_part = " - High quality"
            else:
                quality_part = ""
            
            return f"{tech_part}{type_part}{quality_part}"
            
        except Exception as e:
            logger.error(f"Error generating dynamic reason: {e}")
            return "High-quality content from your saved bookmarks"
    
    def _apply_dynamic_reason(self, candidate):
        """Apply dynamic reason to a candidate"""
        enhanced_candidate = candidate.copy()
        enhanced_candidate['reason'] = self._generate_dynamic_reason(candidate)
        return enhanced_candidate

# Initialize engines
smart_engine = SmartRecommendationEngine()
task_engine = SmartTaskRecommendationEngine()
unified_engine = UnifiedRecommendationEngine()
gemini_enhanced_engine = GeminiEnhancedRecommendationEngine()

# Cache management functions
def get_cached_recommendations(cache_key):
    """Get cached recommendations"""
    return redis_cache.get_cache(cache_key)

def cache_recommendations(cache_key, data, ttl=3600):
    """Cache recommendations"""
    return redis_cache.set_cache(cache_key, data, ttl)

def invalidate_user_recommendations(user_id):
    """Invalidate all cached recommendations for a user"""
    try:
        # Get all keys for this user
        pattern = f"*:{user_id}:*"
        keys = redis_cache.redis_client.keys(pattern)
        
        if keys:
            redis_cache.redis_client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cached recommendations for user {user_id}")
        
        return True
    except Exception as e:
        logger.error(f"Error invalidating user recommendations: {e}")
        return False

# API Routes
@recommendations_bp.route('/general', methods=['GET'])
@jwt_required()
def get_general_recommendations():
    """Get general recommendations"""
    try:
        user_id = get_jwt_identity()
        user_input = request.args.to_dict()
        
        result = unified_engine.get_unified_recommendations(user_id, user_input)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in general recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/project/<int:project_id>', methods=['GET'])
@jwt_required()
def get_project_recommendations(project_id):
    """Get project-specific recommendations"""
    try:
        user_id = get_jwt_identity()
        
        result = unified_engine.get_unified_project_recommendations(user_id, project_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in project recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/task/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task_recommendations(task_id):
    """Get task-specific recommendations"""
    try:
        user_id = get_jwt_identity()
        
        result = task_engine.get_task_recommendations(user_id, task_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in task recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/unified', methods=['GET'])
@jwt_required()
def get_unified_recommendations():
    """Get unified recommendations"""
    try:
        user_id = get_jwt_identity()
        user_input = request.args.to_dict()
        
        result = unified_engine.get_unified_recommendations(user_id, user_input)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in unified recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/unified-project/<int:project_id>', methods=['GET'])
@jwt_required()
def get_unified_project_recommendations(project_id):
    """Get unified project recommendations"""
    try:
        user_id = get_jwt_identity()
        
        result = unified_engine.get_unified_project_recommendations(user_id, project_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in unified project recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/gemini-enhanced', methods=['POST'])
@jwt_required()
def get_gemini_enhanced_recommendations():
    """Get Gemini-enhanced recommendations"""
    try:
        user_id = get_jwt_identity()
        user_input = request.get_json() or {}
        
        result = gemini_enhanced_engine.get_gemini_enhanced_recommendations(user_id, user_input)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in Gemini-enhanced recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/gemini-enhanced-project/<int:project_id>', methods=['POST'])
@jwt_required()
def get_gemini_enhanced_project_recommendations(project_id):
    """Get Gemini-enhanced project recommendations"""
    try:
        user_id = get_jwt_identity()
        user_input = request.get_json() or {}
        
        result = gemini_enhanced_engine.get_gemini_enhanced_project_recommendations(user_id, project_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in Gemini-enhanced project recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/gemini-status', methods=['GET'])
@jwt_required()
def get_gemini_status():
    """Check if Gemini is available and working"""
    try:
        # Check if Gemini analyzer is available
        gemini_available = gemini_analyzer is not None and rate_limiter is not None
        
        status_info = {
            'gemini_available': False,
            'status': 'unavailable',
            'details': {
                'analyzer_initialized': gemini_analyzer is not None,
                'rate_limiter_initialized': rate_limiter is not None,
                'api_key_set': bool(os.environ.get('GEMINI_API_KEY')),
                'test_result': None,
                'error_message': None
            }
        }
        
        # Test Gemini with a simple call if available
        if gemini_available:
            try:
                # Simple test to see if Gemini is working
                test_response = gemini_analyzer.analyze_bookmark_content(
                    title="Test",
                    description="Test description",
                    content="Test content",
                    url=""
                )
                
                if test_response and isinstance(test_response, dict):
                    gemini_working = True
                    status_info['details']['test_result'] = 'success'
                    status_info['details']['test_response_keys'] = list(test_response.keys())
                else:
                    gemini_working = False
                    status_info['details']['test_result'] = 'invalid_response'
                    status_info['details']['error_message'] = 'Gemini returned invalid response format'
                    
            except Exception as e:
                logger.warning(f"Gemini test failed: {e}")
                gemini_working = False
                status_info['details']['test_result'] = 'error'
                status_info['details']['error_message'] = str(e)
        else:
            gemini_working = False
            status_info['details']['error_message'] = 'Gemini analyzer or rate limiter not initialized'
        
        # Update main status
        status_info['gemini_available'] = gemini_available and gemini_working
        status_info['status'] = 'working' if gemini_available and gemini_working else 'unavailable'
        
        return jsonify(status_info)
        
    except Exception as e:
        logger.error(f"Error checking Gemini status: {e}")
        return jsonify({
            'gemini_available': False,
            'status': 'error',
            'details': {
                'error_message': str(e)
            }
        }), 500

@recommendations_bp.route('/cache/clear', methods=['POST'])
@jwt_required()
def clear_recommendation_cache():
    """Clear recommendation cache for current user"""
    try:
        user_id = get_jwt_identity()
        
        success = invalidate_user_recommendations(user_id)
        
        if success:
            return jsonify({'message': 'Cache cleared successfully'})
        else:
            return jsonify({'error': 'Failed to clear cache'}), 500
            
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/analysis/stats', methods=['GET'])
@jwt_required()
def get_analysis_stats():
    """Get statistics about content analysis coverage"""
    try:
        from background_analysis_service import background_service
        
        stats = background_service.get_analysis_stats()
        
        return jsonify({
            'analysis_stats': stats,
            'message': 'Analysis statistics retrieved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error getting analysis stats: {e}")
        return jsonify({'error': 'Failed to get analysis stats'}), 500

@recommendations_bp.route('/analysis/analyze-content/<int:content_id>', methods=['POST'])
@jwt_required()
def analyze_content_immediately(content_id):
    """Analyze a specific content item immediately"""
    try:
        from background_analysis_service import background_service
        
        # Check if content exists and belongs to user
        user_id = get_jwt_identity()
        content = SavedContent.query.filter_by(id=content_id, user_id=user_id).first()
        
        if not content:
            return jsonify({'error': 'Content not found or access denied'}), 404
        
        # Analyze content immediately
        analysis_result = background_service.analyze_content_immediately(content_id)
        
        if analysis_result:
            return jsonify({
                'message': 'Content analyzed successfully',
                'analysis': analysis_result
            })
        else:
            return jsonify({'error': 'Failed to analyze content'}), 500
        
    except Exception as e:
        logger.error(f"Error analyzing content {content_id}: {e}")
        return jsonify({'error': 'Failed to analyze content'}), 500

@recommendations_bp.route('/analysis/start-background', methods=['POST'])
@jwt_required()
def start_background_analysis():
    """Start the background analysis service"""
    try:
        from background_analysis_service import start_background_service
        
        start_background_service()
        
        return jsonify({
            'message': 'Background analysis service started successfully'
        })
        
    except Exception as e:
        logger.error(f"Error starting background analysis: {e}")
        return jsonify({'error': 'Failed to start background analysis'}), 500

@recommendations_bp.route('/smart-recommendations', methods=['POST'])
@jwt_required()
def get_smart_recommendations():
    """Get AI-enhanced smart recommendations based on user context"""
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_title = data.get('project_title', '')
        project_description = data.get('project_description', '')
        technologies = data.get('technologies', '')
        learning_goals = data.get('learning_goals', '')
        limit = data.get('limit', 10)
        
        # Use the smart recommendation engine
        from smart_recommendation_engine import get_smart_recommendations
        
        project_info = {
            'title': project_title,
            'description': project_description,
            'technologies': technologies,
            'learning_goals': learning_goals
        }
        
        recommendations = get_smart_recommendations(user_id, project_info, limit)
        
        return jsonify({
            'recommendations': recommendations,
            'count': len(recommendations),
            'user_id': user_id,
            'analysis_used': True,
            'enhanced_features': [
                'learning_path_matching',
                'project_applicability',
                'skill_development_tracking',
                'ai_generated_reasoning'
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@recommendations_bp.route('/learning-path-recommendations', methods=['POST'])
@jwt_required()
def get_learning_path_recommendations():
    """Get recommendations for a specific learning path"""
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        target_skill = data.get('target_skill', '')
        current_level = data.get('current_level', 'beginner')
        limit = data.get('limit', 10)
        
        if not target_skill:
            return jsonify({'error': 'Target skill is required'}), 400
        
        # Create learning-focused project info
        project_info = {
            'title': f'Learning {target_skill}',
            'description': f'Master {target_skill} from {current_level} level',
            'technologies': target_skill,
            'learning_goals': target_skill
        }
        
        from smart_recommendation_engine import get_smart_recommendations
        recommendations = get_smart_recommendations(user_id, project_info, limit)
        
        # Filter for foundational content first
        foundational = [r for r in recommendations if r.get('learning_path_fit', 0) > 0.6]
        foundational.sort(key=lambda x: x.get('learning_path_fit', 0), reverse=True)
        
        return jsonify({
            'recommendations': foundational[:limit],
            'count': len(foundational[:limit]),
            'target_skill': target_skill,
            'current_level': current_level,
            'learning_path_focused': True
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@recommendations_bp.route('/project-recommendations', methods=['POST'])
@jwt_required()
def get_project_type_recommendations():
    """Get recommendations for a specific project type"""
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_type = data.get('project_type', 'general')
        technologies = data.get('technologies', '')
        complexity = data.get('complexity', 'moderate')
        limit = data.get('limit', 10)
        
        project_info = {
            'title': f'{project_type.title()} Project',
            'description': f'Building a {complexity} {project_type}',
            'technologies': technologies,
            'learning_goals': f'Implement {project_type} with {technologies}'
        }
        
        from smart_recommendation_engine import get_smart_recommendations
        recommendations = get_smart_recommendations(user_id, project_info, limit)
        
        # Filter for high project applicability
        project_focused = [r for r in recommendations if r.get('project_applicability', 0) > 0.6]
        project_focused.sort(key=lambda x: x.get('project_applicability', 0), reverse=True)
        
        return jsonify({
            'recommendations': project_focused[:limit],
            'count': len(project_focused[:limit]),
            'project_type': project_type,
            'complexity': complexity,
            'project_focused': True
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500