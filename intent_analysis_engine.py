#!/usr/bin/env python3
"""
Intent Analysis Engine for Enhanced Recommendations
Uses LLM to understand user intent, project requirements, and learning needs
With smart caching to avoid redundant analysis
"""

import os
import sys
import time
import logging
import json
import hashlib
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import re
from datetime import datetime, timedelta
from functools import lru_cache
import redis
import asyncio
import concurrent.futures

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db, Project, User
from gemini_utils import GeminiAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class UserIntent:
    """Analyzed user intent and requirements"""
    primary_goal: str
    learning_stage: str  # beginner, intermediate, advanced
    project_type: str  # web_app, mobile_app, api, data_science, etc.
    urgency_level: str  # low, medium, high
    specific_technologies: List[str]
    complexity_preference: str  # simple, moderate, complex
    time_constraint: str  # quick_tutorial, deep_dive, reference
    focus_areas: List[str]  # specific areas of interest
    context_hash: str  # hash of input for caching

class IntentAnalysisEngine:
    def __init__(self):
        self.gemini_client = GeminiAnalyzer()
        self.cache_duration = timedelta(hours=24)  # Cache for 24 hours
        
    def _generate_input_hash(self, user_input: str, project_id: Optional[int] = None) -> str:
        """Generate hash for input to enable caching"""
        input_string = f"{user_input}_{project_id}"
        return hashlib.md5(input_string.encode()).hexdigest()
    
    def _get_cached_analysis(self, context_hash: str, project_id: Optional[int] = None) -> Optional[Dict]:
        """Check if we have cached analysis for this input"""
        try:
            # Check if project has recent intent analysis
            if project_id:
                project = Project.query.get(project_id)
                if project and hasattr(project, 'intent_analysis'):
                    analysis_data = getattr(project, 'intent_analysis', None)
                    if analysis_data:
                        analysis = json.loads(analysis_data)
                        if analysis.get('context_hash') == context_hash:
                            # Check if cache is still valid
                            updated_at = datetime.fromisoformat(analysis.get('updated_at', '2000-01-01'))
                            if datetime.now() - updated_at < self.cache_duration:
                                logger.info(f"Using cached intent analysis for project {project_id}")
                                return analysis
            
            return None
        except Exception as e:
            logger.error(f"Error checking cached analysis: {e}")
            return None
    
    def _save_analysis_to_db(self, analysis: Dict, project_id: Optional[int] = None):
        """Save analysis results to database"""
        try:
            if project_id:
                project = Project.query.get(project_id)
                if project:
                    project.intent_analysis = json.dumps(analysis)
                    project.intent_analysis_updated = datetime.now()
                    db.session.commit()
                    logger.info(f"Saved intent analysis to project {project_id}")
        except Exception as e:
            logger.error(f"Error saving analysis to DB: {e}")
            db.session.rollback()
    
    def _extract_technologies(self, text: str) -> List[str]:
        """Extract technology mentions from text using regex patterns"""
        # Common technology patterns
        tech_patterns = [
            r'\b(python|javascript|js|react|vue|angular|node\.js|express|django|flask|fastapi)\b',
            r'\b(html|css|sql|mongodb|postgresql|mysql|redis|docker|kubernetes)\b',
            r'\b(aws|azure|gcp|firebase|heroku|netlify|vercel)\b',
            r'\b(machine learning|ml|ai|data science|analytics|visualization)\b',
            r'\b(mobile|ios|android|flutter|react native|swift|kotlin)\b',
            r'\b(api|rest|graphql|microservices|serverless|lambda)\b'
        ]
        
        technologies = set()
        for pattern in tech_patterns:
            matches = re.findall(pattern, text.lower())
            technologies.update(matches)
        
        return list(technologies)
    
    def _analyze_with_llm(self, user_input: str, project_context: Optional[Dict] = None) -> Dict:
        """Use LLM to analyze user intent"""
        try:
            # Build context for LLM
            project_info = ""
            if project_context:
                project_info = f"""
            PROJECT CONTEXT (CRITICAL - User wants to learn and develop THIS project):
            - Title: {project_context.get('title', 'N/A')}
            - Description: {project_context.get('description', 'N/A')}
            - Technologies: {project_context.get('technologies', 'N/A')}
            
            The user's intent is to LEARN and DEVELOP this specific project. Use this project context to understand:
            - What they need to learn (technologies, concepts, skills)
            - What they're building (project type, complexity)
            - What recommendations would help them build this project
            """
            
            context = f"""
            Analyze the following user input to understand their intent and requirements for recommendations.
            
            User Input: {user_input}
            {project_info}
            
            IMPORTANT: If project context is provided, the user's PRIMARY INTENT is to learn and develop that specific project.
            The recommendations should help them understand, build, and complete that project.
            
            Please analyze and return a JSON response with the following structure:
            {{
                "primary_goal": "main objective (e.g., learn, build, solve, optimize) - usually 'learn' or 'build' for projects",
                "learning_stage": "beginner/intermediate/advanced",
                "project_type": "web_app/mobile_app/api/data_science/automation/etc",
                "urgency_level": "low/medium/high",
                "complexity_preference": "simple/moderate/complex",
                "time_constraint": "quick_tutorial/deep_dive/reference",
                "focus_areas": ["area1", "area2", "area3"] - extract from project description,
                "confidence_score": 0.85
            }}
            
            Be specific and practical. Extract real intent from the input and project context.
            """
            
            result = self.gemini_client._make_gemini_request(context)
            
            if result:
                # Extract JSON from response
                analysis = self.gemini_client._extract_json_from_response(result)
                if analysis:
                    return analysis
            
            # Fallback to rule-based analysis
            return self._fallback_analysis(user_input)
                
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return self._fallback_analysis(user_input)
    
    def _fallback_analysis(self, user_input: str) -> Dict:
        """Rule-based fallback analysis when LLM fails"""
        input_lower = user_input.lower()
        
        # Determine learning stage
        if any(word in input_lower for word in ['beginner', 'start', 'learn', 'new', 'first']):
            learning_stage = 'beginner'
        elif any(word in input_lower for word in ['advanced', 'expert', 'complex', 'optimize']):
            learning_stage = 'advanced'
        else:
            learning_stage = 'intermediate'
        
        # Determine project type
        if any(word in input_lower for word in ['web', 'website', 'frontend', 'ui']):
            project_type = 'web_app'
        elif any(word in input_lower for word in ['mobile', 'app', 'ios', 'android']):
            project_type = 'mobile_app'
        elif any(word in input_lower for word in ['api', 'backend', 'server']):
            project_type = 'api'
        elif any(word in input_lower for word in ['data', 'ml', 'ai', 'analytics']):
            project_type = 'data_science'
        else:
            project_type = 'general'
        
        # Extract technologies
        technologies = self._extract_technologies(user_input)
        
        return {
            "primary_goal": "learn" if 'learn' in input_lower else "build",
            "learning_stage": learning_stage,
            "project_type": project_type,
            "urgency_level": "medium",
            "complexity_preference": "moderate",
            "time_constraint": "deep_dive",
            "focus_areas": technologies[:3],  # Top 3 technologies
            "confidence_score": 0.6
        }
    
    def analyze_intent(self, user_input: str, project_id: Optional[int] = None, force_analysis: bool = False) -> UserIntent:
        """
        Analyze user intent with smart caching
        
        Args:
            user_input: User's description, requirements, or query
            project_id: Optional project ID for context
            force_analysis: Force new analysis even if cached
            
        Returns:
            UserIntent object with analyzed information
        """
        try:
            # Generate hash for caching
            context_hash = self._generate_input_hash(user_input, project_id)
            
            # Check cache first (unless forced)
            if not force_analysis:
                cached = self._get_cached_analysis(context_hash, project_id)
                if cached:
                    return UserIntent(
                        primary_goal=cached['primary_goal'],
                        learning_stage=cached['learning_stage'],
                        project_type=cached['project_type'],
                        urgency_level=cached['urgency_level'],
                        specific_technologies=cached.get('specific_technologies', []),
                        complexity_preference=cached['complexity_preference'],
                        time_constraint=cached['time_constraint'],
                        focus_areas=cached.get('focus_areas', []),
                        context_hash=context_hash
                    )
            
            # Get project context if available
            project_context = None
            if project_id:
                project = Project.query.get(project_id)
                if project:
                    project_context = {
                        'title': project.title,
                        'description': project.description,
                        'technologies': project.technologies
                    }
            
            # Perform analysis
            logger.info(f"Performing intent analysis for input: {user_input[:100]}...")
            analysis_result = self._analyze_with_llm(user_input, project_context)
            
            # Extract technologies from input
            technologies = self._extract_technologies(user_input)
            
            # Create UserIntent object
            intent = UserIntent(
                primary_goal=analysis_result.get('primary_goal', 'learn'),
                learning_stage=analysis_result.get('learning_stage', 'intermediate'),
                project_type=analysis_result.get('project_type', 'general'),
                urgency_level=analysis_result.get('urgency_level', 'medium'),
                specific_technologies=technologies,
                complexity_preference=analysis_result.get('complexity_preference', 'moderate'),
                time_constraint=analysis_result.get('time_constraint', 'deep_dive'),
                focus_areas=analysis_result.get('focus_areas', []),
                context_hash=context_hash
            )
            
            # Save to database for caching
            analysis_data = {
                'primary_goal': intent.primary_goal,
                'learning_stage': intent.learning_stage,
                'project_type': intent.project_type,
                'urgency_level': intent.urgency_level,
                'specific_technologies': intent.specific_technologies,
                'complexity_preference': intent.complexity_preference,
                'time_constraint': intent.time_constraint,
                'focus_areas': intent.focus_areas,
                'context_hash': context_hash,
                'updated_at': datetime.now().isoformat(),
                'confidence_score': analysis_result.get('confidence_score', 0.7)
            }
            
            self._save_analysis_to_db(analysis_data, project_id)
            
            logger.info(f"Intent analysis completed: {intent.primary_goal} - {intent.project_type}")
            return intent
            
        except Exception as e:
            logger.error(f"Error in intent analysis: {e}")
            # Return default intent
            return UserIntent(
                primary_goal='learn',
                learning_stage='intermediate',
                project_type='general',
                urgency_level='medium',
                specific_technologies=[],
                complexity_preference='moderate',
                time_constraint='deep_dive',
                focus_areas=[],
                context_hash=''
            )

# Global instance
intent_engine = IntentAnalysisEngine()

def analyze_user_intent(user_input: str, project_id: Optional[int] = None, force_analysis: bool = False) -> UserIntent:
    """Convenience function to analyze user intent"""
    return intent_engine.analyze_intent(user_input, project_id, force_analysis)

# ============================================================================
# FALLBACK SYSTEM - Added for reliability when AI analysis fails
# ============================================================================

def get_fallback_intent(user_input: str, project_id: Optional[int] = None) -> UserIntent:
    """Get fallback intent when AI analysis fails"""
    try:
        # Extract basic information from input
        input_lower = user_input.lower()
        
        # Determine primary goal
        if any(word in input_lower for word in ['build', 'create', 'make', 'develop']):
            primary_goal = 'build'
        elif any(word in input_lower for word in ['learn', 'study', 'understand']):
            primary_goal = 'learn'
        elif any(word in input_lower for word in ['solve', 'fix', 'debug']):
            primary_goal = 'solve'
        else:
            primary_goal = 'learn'
        
        # Determine project type
        if any(word in input_lower for word in ['web', 'react', 'html', 'css']):
            project_type = 'web_app'
        elif any(word in input_lower for word in ['mobile', 'app', 'ios', 'android']):
            project_type = 'mobile_app'
        elif any(word in input_lower for word in ['api', 'backend', 'server']):
            project_type = 'api'
        elif any(word in input_lower for word in ['data', 'ml', 'ai', 'python']):
            project_type = 'data_science'
        else:
            project_type = 'general'
        
        # Extract technologies
        tech_keywords = ['python', 'javascript', 'react', 'node', 'django', 'flask', 'mongodb', 'postgresql']
        technologies = [tech for tech in tech_keywords if tech in input_lower]
        
        return UserIntent(
            primary_goal=primary_goal,
            learning_stage='intermediate',
            project_type=project_type,
            urgency_level='medium',
            specific_technologies=technologies,
            complexity_preference='moderate',
            time_constraint='deep_dive',
            focus_areas=[],
            context_hash='fallback'
        )
        
    except Exception as e:
        # Ultimate fallback
        return UserIntent(
            primary_goal='learn',
            learning_stage='intermediate',
            project_type='general',
            urgency_level='medium',
            specific_technologies=[],
            complexity_preference='moderate',
            time_constraint='deep_dive',
            focus_areas=[],
            context_hash='ultimate_fallback'
        )

# ============================================================================
# PERFORMANCE OPTIMIZATIONS - Added for better speed and caching
# ============================================================================

from functools import lru_cache
import redis

@lru_cache(maxsize=1000)
def get_cached_intent_analysis(input_hash: str) -> Optional[Dict]:
    """Get cached intent analysis with Redis fallback"""
    try:
        # Try Redis first
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        cached = redis_client.get(f"intent_analysis:{input_hash}")
        if cached:
            return json.loads(cached)
    except:
        pass
    
    # Fallback to database
    try:
        from models import Project
        project = Project.query.filter_by(intent_analysis_hash=input_hash).first()
        if project and project.intent_analysis:
            return json.loads(project.intent_analysis)
    except:
        pass
    
    return None

def analyze_multiple_intents(inputs: List[str]) -> List[UserIntent]:
    """Analyze multiple intents in batch for better performance"""
    results = []
    
    for user_input in inputs:
        try:
            intent = analyze_user_intent(user_input)
            results.append(intent)
        except Exception as e:
            # Use fallback for failed analysis
            fallback_intent = get_fallback_intent(user_input)
            results.append(fallback_intent)
    
    return results

import asyncio
import concurrent.futures

async def analyze_intent_async(user_input: str) -> UserIntent:
    """Analyze intent asynchronously"""
    loop = asyncio.get_event_loop()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(analyze_user_intent, user_input)
        try:
            intent = await loop.run_in_executor(None, future.result)
            return intent
        except Exception as e:
            return get_fallback_intent(user_input) 