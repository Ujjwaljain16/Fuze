#!/usr/bin/env python3
"""
Intent Analysis Engine for Enhanced Recommendations
Uses LLM to understand user intent, project requirements, and learning needs
"""

import os
import sys
import time
import logging
import json
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
    specific_needs: List[str]
    technology_preferences: List[str]
    content_type_preferences: List[str]  # tutorial, documentation, example, etc.
    skill_gaps: List[str]
    project_requirements: Dict[str, Any]
    learning_path: Dict[str, Any]
    confidence_score: float

@dataclass
class IntentAnalysisResult:
    """Complete intent analysis result"""
    user_intent: UserIntent
    enhanced_context: Dict[str, Any]
    recommendation_filters: Dict[str, Any]
    priority_weights: Dict[str, float]
    analysis_metadata: Dict[str, Any]

class IntentAnalysisEngine:
    """Advanced intent analysis using LLM and rule-based fallbacks"""
    
    def __init__(self):
        self.gemini_analyzer = None
        self.available = False
        self._init_gemini()
        
        # Rule-based fallback patterns
        self.learning_stage_patterns = {
            'beginner': [
                r'\b(learn|start|begin|first|new|basics|fundamentals|intro|getting started)\b',
                r'\b(tutorial|guide|step by step|how to)\b',
                r'\b(basic|simple|easy|beginner-friendly)\b'
            ],
            'intermediate': [
                r'\b(improve|enhance|build|develop|create|implement)\b',
                r'\b(project|application|app|website|api)\b',
                r'\b(intermediate|moderate|some experience)\b'
            ],
            'advanced': [
                r'\b(optimize|scale|production|enterprise|advanced|expert)\b',
                r'\b(architecture|design patterns|best practices|performance)\b',
                r'\b(senior|expert|professional|complex)\b'
            ]
        }
        
        self.project_type_patterns = {
            'web_app': [r'\b(web|website|frontend|react|vue|angular|html|css|javascript)\b'],
            'mobile_app': [r'\b(mobile|ios|android|react native|flutter|swift|kotlin)\b'],
            'api': [r'\b(api|backend|server|rest|graphql|microservices)\b'],
            'data_science': [r'\b(data|ml|ai|machine learning|analytics|python|pandas|numpy)\b'],
            'devops': [r'\b(devops|deployment|docker|kubernetes|ci/cd|aws|azure)\b'],
            'database': [r'\b(database|sql|nosql|mongodb|postgresql|mysql)\b']
        }
        
        self.urgency_patterns = {
            'high': [r'\b(urgent|asap|quick|fast|immediate|deadline|due)\b'],
            'medium': [r'\b(soon|next|planning|preparing)\b'],
            'low': [r'\b(learning|exploring|researching|someday)\b']
        }
    
    def _init_gemini(self):
        """Initialize Gemini analyzer with fallback"""
        try:
            from gemini_utils import GeminiAnalyzer
            self.gemini_analyzer = GeminiAnalyzer()
            self.available = True
            logger.info("Gemini analyzer initialized for intent analysis")
        except Exception as e:
            logger.warning(f"Gemini not available for intent analysis: {e}")
            self.gemini_analyzer = None
            self.available = False
    
    def analyze_user_intent(self, 
                          title: str = "",
                          description: str = "",
                          technologies: str = "",
                          user_interests: str = "",
                          project_id: Optional[int] = None) -> IntentAnalysisResult:
        """
        Analyze user intent using LLM with rule-based fallback
        """
        start_time = time.time()
        
        try:
            # Combine all user input
            full_input = f"{title} {description} {technologies} {user_interests}".strip()
            
            if not full_input:
                return self._get_default_intent()
            
            # Try LLM analysis first
            if self.available and self.gemini_analyzer:
                try:
                    llm_result = self._analyze_with_llm(full_input, project_id)
                    if llm_result and llm_result.confidence_score > 0.7:
                        logger.info(f"LLM intent analysis successful (confidence: {llm_result.confidence_score})")
                        return llm_result
                except Exception as e:
                    logger.warning(f"LLM analysis failed: {e}")
            
            # Fallback to rule-based analysis
            logger.info("Using rule-based intent analysis")
            return self._analyze_with_rules(full_input, project_id)
            
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            return self._get_default_intent()
    
    def _analyze_with_llm(self, user_input: str, project_id: Optional[int] = None) -> IntentAnalysisResult:
        """Analyze user intent using Gemini LLM"""
        try:
            # Create comprehensive analysis prompt
            prompt = self._create_intent_analysis_prompt(user_input, project_id)
            
            # Get LLM response
            response = self.gemini_analyzer.analyze_text(prompt)
            
            if not response:
                return None
            
            # Parse LLM response
            parsed_intent = self._parse_llm_intent_response(response)
            
            if not parsed_intent:
                return None
            
            # Create enhanced context and filters
            enhanced_context = self._create_enhanced_context(parsed_intent)
            recommendation_filters = self._create_recommendation_filters(parsed_intent)
            priority_weights = self._calculate_priority_weights(parsed_intent)
            
            return IntentAnalysisResult(
                user_intent=parsed_intent,
                enhanced_context=enhanced_context,
                recommendation_filters=recommendation_filters,
                priority_weights=priority_weights,
                analysis_metadata={
                    'analysis_method': 'llm',
                    'analysis_time': time.time(),
                    'input_length': len(user_input)
                }
            )
            
        except Exception as e:
            logger.error(f"LLM intent analysis error: {e}")
            return None
    
    def _create_intent_analysis_prompt(self, user_input: str, project_id: Optional[int] = None) -> str:
        """Create comprehensive prompt for intent analysis"""
        
        # Get project context if available
        project_context = ""
        if project_id:
            try:
                from models import Project
                project = Project.query.filter_by(id=project_id).first()
                if project:
                    project_context = f"""
Project Context:
- Title: {project.title}
- Description: {project.description or 'N/A'}
- Technologies: {project.technologies or 'N/A'}
- Created: {project.created_at}
"""
            except Exception as e:
                logger.warning(f"Could not load project context: {e}")
        
        prompt = f"""
Analyze the user's intent and requirements from their input. Provide a detailed analysis in JSON format.

User Input: "{user_input}"

{project_context}

Please analyze and return a JSON object with the following structure:

{{
    "primary_goal": "string - main objective (e.g., 'build a web app', 'learn React', 'debug an issue')",
    "learning_stage": "string - beginner, intermediate, or advanced",
    "project_type": "string - web_app, mobile_app, api, data_science, devops, database, or other",
    "urgency_level": "string - low, medium, or high",
    "specific_needs": ["array of specific requirements or pain points"],
    "technology_preferences": ["array of preferred or mentioned technologies"],
    "content_type_preferences": ["array of preferred content types - tutorial, documentation, example, guide, reference"],
    "skill_gaps": ["array of skills the user needs to develop"],
    "project_requirements": {{
        "complexity": "string - simple, moderate, or complex",
        "scope": "string - small, medium, or large",
        "timeline": "string - short-term, medium-term, or long-term",
        "constraints": ["array of any constraints or limitations"]
    }},
    "learning_path": {{
        "prerequisites": ["array of skills needed before this"],
        "next_steps": ["array of skills to learn after this"],
        "resources_needed": ["array of types of resources needed"]
    }},
    "confidence_score": "float between 0 and 1"
}}

Focus on understanding:
1. What is the user trying to accomplish?
2. What is their current skill level?
3. What specific technologies or concepts do they need help with?
4. What type of content would be most helpful?
5. What is the urgency and scope of their needs?

Return only the JSON object, no additional text.
"""
        
        return prompt
    
    def _parse_llm_intent_response(self, response: str) -> Optional[UserIntent]:
        """Parse LLM response into UserIntent object"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return None
            
            json_str = json_match.group()
            data = json.loads(json_str)
            
            # Validate and create UserIntent
            return UserIntent(
                primary_goal=data.get('primary_goal', 'Learn and improve skills'),
                learning_stage=data.get('learning_stage', 'intermediate'),
                project_type=data.get('project_type', 'web_app'),
                urgency_level=data.get('urgency_level', 'medium'),
                specific_needs=data.get('specific_needs', []),
                technology_preferences=data.get('technology_preferences', []),
                content_type_preferences=data.get('content_type_preferences', []),
                skill_gaps=data.get('skill_gaps', []),
                project_requirements=data.get('project_requirements', {}),
                learning_path=data.get('learning_path', {}),
                confidence_score=float(data.get('confidence_score', 0.5))
            )
            
        except Exception as e:
            logger.error(f"Failed to parse LLM intent response: {e}")
            return None
    
    def _analyze_with_rules(self, user_input: str, project_id: Optional[int] = None) -> IntentAnalysisResult:
        """Analyze user intent using rule-based patterns"""
        
        input_lower = user_input.lower()
        
        # Determine learning stage
        learning_stage = self._determine_learning_stage(input_lower)
        
        # Determine project type
        project_type = self._determine_project_type(input_lower)
        
        # Determine urgency
        urgency_level = self._determine_urgency_level(input_lower)
        
        # Extract technologies
        technology_preferences = self._extract_technologies(input_lower)
        
        # Extract specific needs
        specific_needs = self._extract_specific_needs(input_lower)
        
        # Determine content preferences
        content_type_preferences = self._determine_content_preferences(input_lower)
        
        # Create UserIntent
        user_intent = UserIntent(
            primary_goal=self._extract_primary_goal(input_lower),
            learning_stage=learning_stage,
            project_type=project_type,
            urgency_level=urgency_level,
            specific_needs=specific_needs,
            technology_preferences=technology_preferences,
            content_type_preferences=content_type_preferences,
            skill_gaps=self._identify_skill_gaps(input_lower, learning_stage),
            project_requirements=self._analyze_project_requirements(input_lower),
            learning_path=self._create_learning_path(learning_stage, project_type),
            confidence_score=0.6  # Lower confidence for rule-based analysis
        )
        
        # Create enhanced context and filters
        enhanced_context = self._create_enhanced_context(user_intent)
        recommendation_filters = self._create_recommendation_filters(user_intent)
        priority_weights = self._calculate_priority_weights(user_intent)
        
        return IntentAnalysisResult(
            user_intent=user_intent,
            enhanced_context=enhanced_context,
            recommendation_filters=recommendation_filters,
            priority_weights=priority_weights,
            analysis_metadata={
                'analysis_method': 'rule_based',
                'analysis_time': time.time(),
                'input_length': len(user_input)
            }
        )
    
    def _determine_learning_stage(self, text: str) -> str:
        """Determine learning stage using pattern matching"""
        scores = {'beginner': 0, 'intermediate': 0, 'advanced': 0}
        
        for stage, patterns in self.learning_stage_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    scores[stage] += 1
        
        # Return stage with highest score, default to intermediate
        return max(scores, key=scores.get) if max(scores.values()) > 0 else 'intermediate'
    
    def _determine_project_type(self, text: str) -> str:
        """Determine project type using pattern matching"""
        scores = {ptype: 0 for ptype in self.project_type_patterns.keys()}
        
        for ptype, patterns in self.project_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    scores[ptype] += 1
        
        # Return type with highest score, default to web_app
        return max(scores, key=scores.get) if max(scores.values()) > 0 else 'web_app'
    
    def _determine_urgency_level(self, text: str) -> str:
        """Determine urgency level using pattern matching"""
        scores = {'low': 0, 'medium': 0, 'high': 0}
        
        for level, patterns in self.urgency_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    scores[level] += 1
        
        # Return level with highest score, default to medium
        return max(scores, key=scores.get) if max(scores.values()) > 0 else 'medium'
    
    def _extract_technologies(self, text: str) -> List[str]:
        """Extract technology mentions from text"""
        # Common technology patterns
        tech_patterns = [
            r'\b(react|vue|angular|svelte)\b',
            r'\b(node\.js|express|fastapi|django|flask)\b',
            r'\b(python|javascript|typescript|java|c#|go|rust)\b',
            r'\b(mongodb|postgresql|mysql|redis|elasticsearch)\b',
            r'\b(docker|kubernetes|aws|azure|gcp)\b',
            r'\b(tensorflow|pytorch|scikit-learn|pandas|numpy)\b'
        ]
        
        technologies = []
        for pattern in tech_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            technologies.extend(matches)
        
        return list(set(technologies))
    
    def _extract_specific_needs(self, text: str) -> List[str]:
        """Extract specific needs and requirements"""
        needs = []
        
        # Common need patterns
        need_patterns = [
            r'\b(debug|fix|error|issue|problem)\b',
            r'\b(optimize|performance|speed|efficiency)\b',
            r'\b(security|authentication|authorization)\b',
            r'\b(testing|unit tests|integration tests)\b',
            r'\b(deployment|ci/cd|pipeline)\b',
            r'\b(design|architecture|patterns)\b'
        ]
        
        for pattern in need_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                needs.append(re.search(pattern, text, re.IGNORECASE).group())
        
        return needs
    
    def _determine_content_preferences(self, text: str) -> List[str]:
        """Determine preferred content types"""
        preferences = []
        
        if re.search(r'\b(tutorial|guide|step by step|how to)\b', text, re.IGNORECASE):
            preferences.append('tutorial')
        
        if re.search(r'\b(documentation|reference|api docs)\b', text, re.IGNORECASE):
            preferences.append('documentation')
        
        if re.search(r'\b(example|sample|demo|code)\b', text, re.IGNORECASE):
            preferences.append('example')
        
        if re.search(r'\b(best practices|patterns|architecture)\b', text, re.IGNORECASE):
            preferences.append('best_practices')
        
        # Default preferences if none detected
        if not preferences:
            preferences = ['tutorial', 'documentation']
        
        return preferences
    
    def _extract_primary_goal(self, text: str) -> str:
        """Extract primary goal from text"""
        if re.search(r'\b(build|create|develop|make)\b', text, re.IGNORECASE):
            return "Build a project"
        elif re.search(r'\b(learn|study|understand)\b', text, re.IGNORECASE):
            return "Learn new skills"
        elif re.search(r'\b(fix|debug|solve|resolve)\b', text, re.IGNORECASE):
            return "Solve a problem"
        elif re.search(r'\b(optimize|improve|enhance)\b', text, re.IGNORECASE):
            return "Improve existing work"
        else:
            return "Learn and improve skills"
    
    def _identify_skill_gaps(self, text: str, learning_stage: str) -> List[str]:
        """Identify potential skill gaps based on text and learning stage"""
        gaps = []
        
        if learning_stage == 'beginner':
            gaps.extend(['fundamentals', 'basic concepts', 'getting started'])
        elif learning_stage == 'intermediate':
            gaps.extend(['advanced concepts', 'best practices', 'real-world applications'])
        elif learning_stage == 'advanced':
            gaps.extend(['optimization', 'architecture', 'scaling'])
        
        # Add specific gaps based on text content
        if re.search(r'\b(performance|speed)\b', text, re.IGNORECASE):
            gaps.append('performance optimization')
        
        if re.search(r'\b(security)\b', text, re.IGNORECASE):
            gaps.append('security best practices')
        
        return gaps
    
    def _analyze_project_requirements(self, text: str) -> Dict[str, Any]:
        """Analyze project requirements"""
        complexity = 'moderate'
        if re.search(r'\b(simple|basic|easy)\b', text, re.IGNORECASE):
            complexity = 'simple'
        elif re.search(r'\b(complex|advanced|sophisticated)\b', text, re.IGNORECASE):
            complexity = 'complex'
        
        scope = 'medium'
        if re.search(r'\b(small|mini|simple)\b', text, re.IGNORECASE):
            scope = 'small'
        elif re.search(r'\b(large|enterprise|comprehensive)\b', text, re.IGNORECASE):
            scope = 'large'
        
        return {
            'complexity': complexity,
            'scope': scope,
            'timeline': 'medium-term',
            'constraints': []
        }
    
    def _create_learning_path(self, learning_stage: str, project_type: str) -> Dict[str, Any]:
        """Create learning path based on stage and project type"""
        return {
            'prerequisites': [],
            'next_steps': [],
            'resources_needed': ['tutorials', 'documentation']
        }
    
    def _create_enhanced_context(self, user_intent: UserIntent) -> Dict[str, Any]:
        """Create enhanced context for recommendations"""
        return {
            'learning_stage': user_intent.learning_stage,
            'project_type': user_intent.project_type,
            'urgency_level': user_intent.urgency_level,
            'technology_stack': user_intent.technology_preferences,
            'content_preferences': user_intent.content_type_preferences,
            'skill_gaps': user_intent.skill_gaps,
            'project_requirements': user_intent.project_requirements,
            'learning_path': user_intent.learning_path,
            'confidence_score': user_intent.confidence_score
        }
    
    def _create_recommendation_filters(self, user_intent: UserIntent) -> Dict[str, Any]:
        """Create filters for recommendation engine"""
        return {
            'min_difficulty': self._get_min_difficulty(user_intent.learning_stage),
            'max_difficulty': self._get_max_difficulty(user_intent.learning_stage),
            'preferred_technologies': user_intent.technology_preferences,
            'content_types': user_intent.content_type_preferences,
            'exclude_content_types': self._get_excluded_content_types(user_intent),
            'urgency_boost': user_intent.urgency_level == 'high'
        }
    
    def _calculate_priority_weights(self, user_intent: UserIntent) -> Dict[str, float]:
        """Calculate priority weights for different recommendation factors"""
        weights = {
            'technology_match': 0.3,
            'content_type_match': 0.2,
            'difficulty_match': 0.2,
            'relevance': 0.15,
            'quality': 0.15
        }
        
        # Adjust weights based on user intent
        if user_intent.urgency_level == 'high':
            weights['relevance'] += 0.1
            weights['quality'] -= 0.1
        
        if user_intent.learning_stage == 'beginner':
            weights['difficulty_match'] += 0.1
            weights['technology_match'] -= 0.1
        
        return weights
    
    def _get_min_difficulty(self, learning_stage: str) -> str:
        """Get minimum difficulty for learning stage"""
        if learning_stage == 'beginner':
            return 'beginner'
        elif learning_stage == 'intermediate':
            return 'beginner'
        else:
            return 'intermediate'
    
    def _get_max_difficulty(self, learning_stage: str) -> str:
        """Get maximum difficulty for learning stage"""
        if learning_stage == 'beginner':
            return 'intermediate'
        elif learning_stage == 'intermediate':
            return 'advanced'
        else:
            return 'advanced'
    
    def _get_excluded_content_types(self, user_intent: UserIntent) -> List[str]:
        """Get content types to exclude based on user intent"""
        excluded = []
        
        if user_intent.learning_stage == 'beginner':
            excluded.extend(['advanced_patterns', 'enterprise_architecture'])
        
        if user_intent.urgency_level == 'high':
            excluded.extend(['long_tutorials', 'comprehensive_guides'])
        
        return excluded
    
    def _get_default_intent(self) -> IntentAnalysisResult:
        """Get default intent when analysis fails"""
        default_intent = UserIntent(
            primary_goal="Learn and improve skills",
            learning_stage="intermediate",
            project_type="web_app",
            urgency_level="medium",
            specific_needs=[],
            technology_preferences=[],
            content_type_preferences=["tutorial", "documentation"],
            skill_gaps=[],
            project_requirements={},
            learning_path={},
            confidence_score=0.3
        )
        
        return IntentAnalysisResult(
            user_intent=default_intent,
            enhanced_context=self._create_enhanced_context(default_intent),
            recommendation_filters=self._create_recommendation_filters(default_intent),
            priority_weights=self._calculate_priority_weights(default_intent),
            analysis_metadata={
                'analysis_method': 'default',
                'analysis_time': time.time(),
                'error': 'Analysis failed, using default intent'
            }
        )

# Global instance
_intent_analyzer = None

def get_intent_analyzer() -> IntentAnalysisEngine:
    """Get global intent analyzer instance"""
    global _intent_analyzer
    if _intent_analyzer is None:
        _intent_analyzer = IntentAnalysisEngine()
    return _intent_analyzer

def analyze_user_intent(title: str = "", description: str = "", technologies: str = "", 
                       user_interests: str = "", project_id: Optional[int] = None) -> IntentAnalysisResult:
    """Convenience function to analyze user intent"""
    analyzer = get_intent_analyzer()
    return analyzer.analyze_user_intent(title, description, technologies, user_interests, project_id) 