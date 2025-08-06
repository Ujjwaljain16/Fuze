#!/usr/bin/env python3
"""
Project-Focused Recommendation Engine
Focuses on project description, learning objectives, and practical application
rather than just technology matching.
"""

import numpy as np
import re
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from collections import Counter
import hashlib

# Optional imports
try:
    from sentence_transformers import SentenceTransformer
    import torch
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)

class ProjectFocusedEngine:
    """
    Project-focused recommendation engine that prioritizes:
    - Project description analysis
    - Learning objectives alignment
    - Practical application value
    - Skill progression path
    - Real-world relevance
    """
    
    def __init__(self):
        # Initialize embedding model
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                if hasattr(torch, 'meta') and torch.meta.is_available():
                    self.embedding_model = self.embedding_model.to_empty(device='cpu')
                else:
                    self.embedding_model = self.embedding_model.to('cpu')
                self.embedding_available = True
            except Exception as e:
                logger.warning(f"Embedding model not available: {e}")
                self.embedding_available = False
        else:
            self.embedding_available = False
        
        # Project analysis patterns
        self.project_patterns = {
            'learning_objectives': [
                'learn', 'understand', 'master', 'build', 'create', 'develop',
                'implement', 'design', 'architect', 'optimize', 'deploy'
            ],
            'project_types': [
                'web app', 'mobile app', 'api', 'dashboard', 'e-commerce',
                'social media', 'blog', 'portfolio', 'game', 'tool', 'library'
            ],
            'complexity_indicators': [
                'beginner', 'intermediate', 'advanced', 'expert',
                'simple', 'complex', 'basic', 'advanced', 'professional'
            ],
            'practical_applications': [
                'real-world', 'production', 'commercial', 'enterprise',
                'startup', 'freelance', 'portfolio', 'side project'
            ]
        }
        
        # Content quality indicators
        self.quality_indicators = {
            'comprehensive': ['complete', 'full', 'comprehensive', 'detailed', 'thorough'],
            'practical': ['hands-on', 'practical', 'real-world', 'production-ready'],
            'up_to_date': ['latest', 'modern', 'current', '2024', '2023'],
            'well_structured': ['step-by-step', 'tutorial', 'guide', 'course']
        }
    
    def analyze_project_context(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze project context for learning objectives and requirements"""
        title = project_data.get('title', '')
        description = project_data.get('description', '')
        technologies = project_data.get('technologies', '')
        
        full_text = f"{title} {description} {technologies}".lower()
        
        # Extract learning objectives
        learning_objectives = self._extract_learning_objectives(full_text)
        
        # Determine project type
        project_type = self._determine_project_type(full_text)
        
        # Assess complexity level
        complexity = self._assess_complexity(full_text)
        
        # Extract practical requirements
        practical_requirements = self._extract_practical_requirements(full_text)
        
        # Determine target audience
        target_audience = self._determine_target_audience(complexity, project_type)
        
        return {
            'learning_objectives': learning_objectives,
            'project_type': project_type,
            'complexity': complexity,
            'practical_requirements': practical_requirements,
            'target_audience': target_audience,
            'project_context': full_text
        }
    
    def _extract_learning_objectives(self, text: str) -> List[str]:
        """Extract learning objectives from project description"""
        objectives = []
        
        # Look for learning-related patterns
        learning_patterns = [
            r'learn\s+(\w+(?:\s+\w+)*)',
            r'understand\s+(\w+(?:\s+\w+)*)',
            r'master\s+(\w+(?:\s+\w+)*)',
            r'build\s+(\w+(?:\s+\w+)*)',
            r'create\s+(\w+(?:\s+\w+)*)',
            r'develop\s+(\w+(?:\s+\w+)*)'
        ]
        
        for pattern in learning_patterns:
            matches = re.findall(pattern, text)
            objectives.extend(matches)
        
        return list(set(objectives))
    
    def _determine_project_type(self, text: str) -> str:
        """Determine the type of project being built"""
        project_types = {
            'web_application': ['web app', 'website', 'web application', 'frontend', 'backend'],
            'mobile_application': ['mobile app', 'ios', 'android', 'react native', 'flutter'],
            'api_service': ['api', 'rest api', 'graphql', 'microservice', 'backend service'],
            'data_analysis': ['data analysis', 'analytics', 'dashboard', 'visualization'],
            'e_commerce': ['e-commerce', 'online store', 'shopping', 'payment'],
            'social_platform': ['social media', 'social platform', 'community', 'chat'],
            'game': ['game', 'gaming', 'interactive'],
            'tool_utility': ['tool', 'utility', 'library', 'framework']
        }
        
        for project_type, keywords in project_types.items():
            if any(keyword in text for keyword in keywords):
                return project_type
        
        return 'general_development'
    
    def _assess_complexity(self, text: str) -> str:
        """Assess the complexity level of the project"""
        complexity_indicators = {
            'beginner': ['simple', 'basic', 'beginner', 'intro', 'first', 'starter'],
            'intermediate': ['intermediate', 'moderate', 'standard', 'typical'],
            'advanced': ['advanced', 'complex', 'expert', 'professional', 'enterprise']
        }
        
        for level, indicators in complexity_indicators.items():
            if any(indicator in text for indicator in indicators):
                return level
        
        return 'intermediate'  # Default
    
    def _extract_practical_requirements(self, text: str) -> List[str]:
        """Extract practical requirements and constraints"""
        requirements = []
        
        # Look for practical requirements
        practical_patterns = [
            r'production\s+ready',
            r'real\s+world',
            r'commercial',
            r'enterprise',
            r'startup',
            r'freelance',
            r'portfolio',
            r'side\s+project'
        ]
        
        for pattern in practical_patterns:
            if re.search(pattern, text):
                requirements.append(pattern.replace(r'\s+', ' '))
        
        return requirements
    
    def _determine_target_audience(self, complexity: str, project_type: str) -> str:
        """Determine the target audience based on complexity and project type"""
        if complexity == 'beginner':
            return 'students_and_beginners'
        elif complexity == 'advanced':
            return 'professionals_and_experts'
        elif project_type in ['e_commerce', 'enterprise']:
            return 'business_professionals'
        else:
            return 'developers_and_hobbyists'
    
    def calculate_project_alignment_score(self, content: Dict[str, Any], project_context: Dict[str, Any]) -> Dict[str, float]:
        """Calculate how well content aligns with project requirements"""
        scores = {}
        
        # 1. Learning Objective Alignment (40% weight)
        scores['learning_alignment'] = self._calculate_learning_alignment(
            content, project_context['learning_objectives']
        )
        
        # 2. Project Type Relevance (25% weight)
        scores['project_type_relevance'] = self._calculate_project_type_relevance(
            content, project_context['project_type']
        )
        
        # 3. Complexity Match (20% weight)
        scores['complexity_match'] = self._calculate_complexity_match(
            content, project_context['complexity']
        )
        
        # 4. Practical Application Value (15% weight)
        scores['practical_value'] = self._calculate_practical_value(
            content, project_context['practical_requirements']
        )
        
        return scores
    
    def _calculate_learning_alignment(self, content: Dict[str, Any], learning_objectives: List[str]) -> float:
        """Calculate how well content aligns with learning objectives"""
        if not learning_objectives:
            return 0.5  # Neutral score if no objectives specified
        
        content_text = f"{content.get('title', '')} {content.get('extracted_text', '')}".lower()
        
        # Count how many learning objectives are covered
        covered_objectives = 0
        for objective in learning_objectives:
            if objective.lower() in content_text:
                covered_objectives += 1
        
        return min(1.0, covered_objectives / len(learning_objectives))
    
    def _calculate_project_type_relevance(self, content: Dict[str, Any], project_type: str) -> float:
        """Calculate relevance to specific project type"""
        content_text = f"{content.get('title', '')} {content.get('extracted_text', '')}".lower()
        
        # Define keywords for each project type
        type_keywords = {
            'web_application': ['web', 'frontend', 'backend', 'html', 'css', 'javascript'],
            'mobile_application': ['mobile', 'ios', 'android', 'app', 'react native'],
            'api_service': ['api', 'rest', 'graphql', 'endpoint', 'service'],
            'data_analysis': ['data', 'analysis', 'analytics', 'dashboard', 'visualization'],
            'e_commerce': ['e-commerce', 'shopping', 'payment', 'store', 'cart'],
            'social_platform': ['social', 'community', 'chat', 'messaging', 'network'],
            'game': ['game', 'gaming', 'interactive', 'animation'],
            'tool_utility': ['tool', 'utility', 'library', 'framework', 'plugin']
        }
        
        keywords = type_keywords.get(project_type, [])
        if not keywords:
            return 0.5
        
        # Count keyword matches
        matches = sum(1 for keyword in keywords if keyword in content_text)
        return min(1.0, matches / len(keywords))
    
    def _calculate_complexity_match(self, content: Dict[str, Any], target_complexity: str) -> float:
        """Calculate if content complexity matches project complexity"""
        content_text = f"{content.get('title', '')} {content.get('extracted_text', '')}".lower()
        
        complexity_keywords = {
            'beginner': ['beginner', 'basic', 'simple', 'intro', 'starter', 'first'],
            'intermediate': ['intermediate', 'moderate', 'standard', 'typical'],
            'advanced': ['advanced', 'complex', 'expert', 'professional', 'enterprise']
        }
        
        target_keywords = complexity_keywords.get(target_complexity, [])
        content_complexity = 'intermediate'  # Default
        
        # Determine content complexity
        for level, keywords in complexity_keywords.items():
            if any(keyword in content_text for keyword in keywords):
                content_complexity = level
                break
        
        # Score based on complexity match
        if content_complexity == target_complexity:
            return 1.0
        elif (content_complexity == 'intermediate' and target_complexity in ['beginner', 'advanced']):
            return 0.7
        else:
            return 0.3
    
    def _calculate_practical_value(self, content: Dict[str, Any], practical_requirements: List[str]) -> float:
        """Calculate practical application value"""
        content_text = f"{content.get('title', '')} {content.get('extracted_text', '')}".lower()
        
        practical_indicators = [
            'real-world', 'production', 'commercial', 'enterprise',
            'startup', 'freelance', 'portfolio', 'practical', 'hands-on'
        ]
        
        # Count practical indicators
        matches = sum(1 for indicator in practical_indicators if indicator in content_text)
        return min(1.0, matches / len(practical_indicators))
    
    def get_project_focused_recommendations(self, bookmarks: List[Dict], project_data: Dict[str, Any], max_recommendations: int = 10) -> List[Dict]:
        """Get project-focused recommendations"""
        # Analyze project context
        project_context = self.analyze_project_context(project_data)
        
        # Score each bookmark
        scored_bookmarks = []
        for bookmark in bookmarks:
            scores = self.calculate_project_alignment_score(bookmark, project_context)
            
            # Calculate weighted total score
            total_score = (
                scores['learning_alignment'] * 0.4 +
                scores['project_type_relevance'] * 0.25 +
                scores['complexity_match'] * 0.2 +
                scores['practical_value'] * 0.15
            ) * 100  # Convert to percentage
            
            # Add quality score boost
            quality_score = bookmark.get('quality_score', 5) / 10.0
            total_score += quality_score * 10  # Add up to 10 points for quality
            
            scored_bookmark = {
                **bookmark,
                'project_alignment_scores': scores,
                'total_score': total_score,
                'reason': self._generate_project_focused_reason(bookmark, scores, project_context)
            }
            scored_bookmarks.append(scored_bookmark)
        
        # Sort by total score and return top recommendations
        scored_bookmarks.sort(key=lambda x: x['total_score'], reverse=True)
        
        return scored_bookmarks[:max_recommendations]
    
    def _generate_project_focused_reason(self, bookmark: Dict[str, Any], scores: Dict[str, float], project_context: Dict[str, Any]) -> str:
        """Generate reason focused on project alignment"""
        reasons = []
        
        # Learning alignment reason
        if scores['learning_alignment'] > 0.7:
            objectives = ', '.join(project_context['learning_objectives'][:2])
            reasons.append(f"Directly helps you learn {objectives}")
        
        # Project type reason
        if scores['project_type_relevance'] > 0.6:
            project_type = project_context['project_type'].replace('_', ' ').title()
            reasons.append(f"Perfect for {project_type} development")
        
        # Complexity reason
        if scores['complexity_match'] > 0.8:
            complexity = project_context['complexity'].title()
            reasons.append(f"Matches your {complexity} skill level")
        
        # Practical value reason
        if scores['practical_value'] > 0.6:
            reasons.append("Provides real-world practical value")
        
        # Fallback reason
        if not reasons:
            if scores['learning_alignment'] > 0.3:
                reasons.append("Relevant to your learning goals")
            else:
                reasons.append("Quality content for your project")
        
        return ' • '.join(reasons)

# Global instance
project_focused_engine = ProjectFocusedEngine() 