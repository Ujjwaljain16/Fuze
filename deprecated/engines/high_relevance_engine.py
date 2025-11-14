#!/usr/bin/env python3
"""
High Relevance Recommendation Engine
Focuses on giving the BEST recommendations based on user's actual input:
- Project description
- Technologies
- Tasks/Todos
- Specific requirements
"""

import numpy as np
import re
import logging
from typing import List, Dict, Optional, Any, Tuple
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

class HighRelevanceEngine:
    """
    High Relevance Engine that prioritizes:
    - Exact technology matches
    - Project description relevance
    - Task-specific content
    - User's actual input (not generic)
    - Quality and recency
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
        
        # Technology patterns for exact matching
        self.tech_patterns = {
            'frontend': ['react', 'vue', 'angular', 'javascript', 'typescript', 'html', 'css', 'sass', 'tailwind', 'bootstrap'],
            'backend': ['node.js', 'python', 'django', 'flask', 'fastapi', 'java', 'spring', 'c#', '.net', 'php', 'laravel'],
            'database': ['mysql', 'postgresql', 'mongodb', 'redis', 'sqlite', 'oracle', 'sql server'],
            'mobile': ['react native', 'flutter', 'ios', 'android', 'swift', 'kotlin'],
            'devops': ['docker', 'kubernetes', 'aws', 'azure', 'gcp', 'ci/cd', 'jenkins', 'gitlab'],
            'ai_ml': ['tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy', 'machine learning', 'ai'],
            'blockchain': ['ethereum', 'bitcoin', 'solidity', 'web3', 'blockchain', 'smart contract'],
            'game': ['unity', 'unreal', 'game development', 'opengl', 'directx']
        }
        
        # Content quality indicators
        self.quality_indicators = {
            'comprehensive': ['complete', 'full', 'comprehensive', 'detailed', 'thorough', 'step-by-step'],
            'practical': ['hands-on', 'practical', 'real-world', 'production-ready', 'tutorial'],
            'up_to_date': ['latest', 'modern', 'current', '2024', '2023', 'new'],
            'well_structured': ['guide', 'course', 'tutorial', 'documentation', 'reference']
        }
    
    def analyze_user_input(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user input to extract key requirements"""
        title = user_input.get('title', '')
        description = user_input.get('description', '')
        technologies = user_input.get('technologies', '')
        project_id = user_input.get('project_id')
        
        # Combine all text for analysis
        full_text = f"{title} {description} {technologies}".lower()
        
        # Extract exact technologies
        exact_techs = self._extract_exact_technologies(full_text)
        
        # Extract project requirements
        project_requirements = self._extract_project_requirements(full_text)
        
        # Determine content type needed
        content_type_needed = self._determine_content_type_needed(full_text)
        
        # Extract specific tasks/todos
        specific_tasks = self._extract_specific_tasks(full_text)
        
        # Determine urgency/priority
        urgency = self._determine_urgency(full_text)
        
        return {
            'exact_technologies': exact_techs,
            'project_requirements': project_requirements,
            'content_type_needed': content_type_needed,
            'specific_tasks': specific_tasks,
            'urgency': urgency,
            'full_context': full_text,
            'project_id': project_id
        }
    
    def _extract_exact_technologies(self, text: str) -> List[str]:
        """Extract exact technology matches"""
        exact_techs = []
        
        # Check each technology category
        for category, techs in self.tech_patterns.items():
            for tech in techs:
                # Use word boundaries for exact matching
                pattern = r'\b' + re.escape(tech) + r'\b'
                if re.search(pattern, text):
                    exact_techs.append(tech)
        
        # Also extract any other tech-like words
        tech_words = re.findall(r'\b[a-zA-Z]+(?:\.[a-zA-Z]+)*\b', text)
        for word in tech_words:
            if len(word) > 2 and word.lower() not in ['the', 'and', 'for', 'with', 'from', 'this', 'that']:
                exact_techs.append(word.lower())
        
        return list(set(exact_techs))
    
    def _extract_project_requirements(self, text: str) -> List[str]:
        """Extract specific project requirements"""
        requirements = []
        
        # Look for requirement patterns
        requirement_patterns = [
            r'need\s+(\w+(?:\s+\w+)*)',
            r'want\s+(\w+(?:\s+\w+)*)',
            r'build\s+(\w+(?:\s+\w+)*)',
            r'create\s+(\w+(?:\s+\w+)*)',
            r'develop\s+(\w+(?:\s+\w+)*)',
            r'implement\s+(\w+(?:\s+\w+)*)',
            r'add\s+(\w+(?:\s+\w+)*)',
            r'fix\s+(\w+(?:\s+\w+)*)',
            r'optimize\s+(\w+(?:\s+\w+)*)',
            r'deploy\s+(\w+(?:\s+\w+)*)'
        ]
        
        for pattern in requirement_patterns:
            matches = re.findall(pattern, text)
            requirements.extend(matches)
        
        return list(set(requirements))
    
    def _determine_content_type_needed(self, text: str) -> str:
        """Determine what type of content the user needs"""
        if any(word in text for word in ['tutorial', 'learn', 'guide', 'how to']):
            return 'tutorial'
        elif any(word in text for word in ['documentation', 'api', 'reference', 'docs']):
            return 'documentation'
        elif any(word in text for word in ['example', 'sample', 'demo', 'code']):
            return 'example'
        elif any(word in text for word in ['fix', 'error', 'bug', 'issue', 'problem']):
            return 'troubleshooting'
        elif any(word in text for word in ['best practice', 'pattern', 'architecture']):
            return 'best_practice'
        else:
            return 'general'
    
    def _extract_specific_tasks(self, text: str) -> List[str]:
        """Extract specific tasks or todos"""
        tasks = []
        
        # Look for task patterns
        task_patterns = [
            r'todo\s*:\s*(\w+(?:\s+\w+)*)',
            r'task\s*:\s*(\w+(?:\s+\w+)*)',
            r'need\s+to\s+(\w+(?:\s+\w+)*)',
            r'must\s+(\w+(?:\s+\w+)*)',
            r'should\s+(\w+(?:\s+\w+)*)'
        ]
        
        for pattern in task_patterns:
            matches = re.findall(pattern, text)
            tasks.extend(matches)
        
        return list(set(tasks))
    
    def _determine_urgency(self, text: str) -> str:
        """Determine urgency level"""
        if any(word in text for word in ['urgent', 'asap', 'quick', 'fast', 'immediate']):
            return 'high'
        elif any(word in text for word in ['soon', 'today', 'this week']):
            return 'medium'
        else:
            return 'low'
    
    def calculate_high_relevance_score(self, content: Dict[str, Any], user_analysis: Dict[str, Any]) -> Dict[str, float]:
        """Calculate high relevance score based on user's actual input"""
        scores = {}
        
        # 1. Exact Technology Match (35% weight) - Most important
        scores['exact_tech_match'] = self._calculate_exact_tech_match(
            content, user_analysis['exact_technologies']
        )
        
        # 2. Project Requirements Match (25% weight)
        scores['requirements_match'] = self._calculate_requirements_match(
            content, user_analysis['project_requirements']
        )
        
        # 3. Content Type Match (20% weight)
        scores['content_type_match'] = self._calculate_content_type_match(
            content, user_analysis['content_type_needed']
        )
        
        # 4. Task-Specific Relevance (15% weight)
        scores['task_relevance'] = self._calculate_task_relevance(
            content, user_analysis['specific_tasks']
        )
        
        # 5. Quality and Recency (5% weight)
        scores['quality_recency'] = self._calculate_quality_recency(content)
        
        return scores
    
    def _calculate_exact_tech_match(self, content: Dict[str, Any], user_techs: List[str]) -> float:
        """Calculate exact technology match score"""
        if not user_techs:
            return 0.5  # Neutral if no techs specified
        
        content_text = f"{content.get('title', '')} {content.get('extracted_text', '')}".lower()
        content_techs = content.get('technologies', [])
        
        # Convert content_techs to list if it's a string
        if isinstance(content_techs, str):
            content_techs = [tech.strip() for tech in content_techs.split(',') if tech.strip()]
        
        # Count exact matches with stricter matching
        exact_matches = 0
        for user_tech in user_techs:
            user_tech_lower = user_tech.lower()
            
            # Check in content text with word boundaries
            pattern = r'\b' + re.escape(user_tech_lower) + r'\b'
            if re.search(pattern, content_text):
                exact_matches += 1
            # Check in content technologies with exact match
            elif any(user_tech_lower == tech.lower() for tech in content_techs):
                exact_matches += 1
            # Check for partial matches in content technologies (for variations like "python" vs "python3")
            elif any(user_tech_lower in tech.lower() or tech.lower() in user_tech_lower for tech in content_techs):
                exact_matches += 0.5  # Partial match gets half credit
        
        return min(1.0, exact_matches / len(user_techs))
    
    def _calculate_requirements_match(self, content: Dict[str, Any], requirements: List[str]) -> float:
        """Calculate how well content matches project requirements"""
        if not requirements:
            return 0.5
        
        content_text = f"{content.get('title', '')} {content.get('extracted_text', '')}".lower()
        
        # Count requirement matches
        matches = 0
        for requirement in requirements:
            if requirement.lower() in content_text:
                matches += 1
        
        return min(1.0, matches / len(requirements))
    
    def _calculate_content_type_match(self, content: Dict[str, Any], needed_type: str) -> float:
        """Calculate if content type matches what user needs"""
        content_text = f"{content.get('title', '')} {content.get('extracted_text', '')}".lower()
        
        # Define keywords for each content type
        type_keywords = {
            'tutorial': ['tutorial', 'guide', 'learn', 'how to', 'step by step', 'course'],
            'documentation': ['documentation', 'api', 'reference', 'docs', 'manual'],
            'example': ['example', 'sample', 'demo', 'code', 'implementation'],
            'troubleshooting': ['fix', 'error', 'bug', 'issue', 'problem', 'solution', 'debug'],
            'best_practice': ['best practice', 'pattern', 'architecture', 'design', 'optimization']
        }
        
        keywords = type_keywords.get(needed_type, [])
        if not keywords:
            return 0.5
        
        # Count keyword matches
        matches = sum(1 for keyword in keywords if keyword in content_text)
        return min(1.0, matches / len(keywords))
    
    def _calculate_task_relevance(self, content: Dict[str, Any], tasks: List[str]) -> float:
        """Calculate relevance to specific tasks"""
        if not tasks:
            return 0.5
        
        content_text = f"{content.get('title', '')} {content.get('extracted_text', '')}".lower()
        
        # Count task matches
        matches = 0
        for task in tasks:
            if task.lower() in content_text:
                matches += 1
        
        return min(1.0, matches / len(tasks))
    
    def _calculate_quality_recency(self, content: Dict[str, Any]) -> float:
        """Calculate quality and recency score"""
        score = 0.5  # Base score
        
        # Quality score boost
        quality_score = content.get('quality_score', 5) / 10.0
        score += quality_score * 0.3
        
        # Recency boost (if available)
        created_at = content.get('created_at') or content.get('saved_at')
        if created_at:
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    created_at = None
            
            if created_at:
                days_old = (datetime.now() - created_at).days
                if days_old < 30:  # Less than 30 days old
                    score += 0.2
                elif days_old < 90:  # Less than 3 months old
                    score += 0.1
        
        return min(1.0, score)
    
    def get_high_relevance_recommendations(self, bookmarks: List[Dict], user_input: Dict[str, Any], max_recommendations: int = 10) -> List[Dict]:
        """Get highly relevant recommendations based on user's actual input"""
        # Analyze user input
        user_analysis = self.analyze_user_input(user_input)
        
        # Score each bookmark
        scored_bookmarks = []
        for bookmark in bookmarks:
            scores = self.calculate_high_relevance_score(bookmark, user_analysis)
            
            # STRICT FILTERING: Only include content with reasonable technology relevance
            if user_analysis['exact_technologies']:
                # If user specified technologies, require at least 30% tech match
                if scores['exact_tech_match'] < 0.3:
                    continue  # Skip content with low tech relevance
            else:
                # If no specific technologies, require at least 20% overall relevance
                total_relevance = (
                    scores['exact_tech_match'] * 0.35 +
                    scores['requirements_match'] * 0.25 +
                    scores['content_type_match'] * 0.20 +
                    scores['task_relevance'] * 0.15 +
                    scores['quality_recency'] * 0.05
                )
                if total_relevance < 0.2:
                    continue  # Skip low relevance content
            
            # Calculate weighted total score
            total_score = (
                scores['exact_tech_match'] * 0.35 +
                scores['requirements_match'] * 0.25 +
                scores['content_type_match'] * 0.20 +
                scores['task_relevance'] * 0.15 +
                scores['quality_recency'] * 0.05
            ) * 100  # Convert to percentage
            
            # Add bonus for exact matches
            if scores['exact_tech_match'] > 0.8:
                total_score += 20  # Bonus for high tech match
            
            if scores['requirements_match'] > 0.7:
                total_score += 15  # Bonus for high requirements match
            
            # ADDITIONAL FILTER: Only include content with reasonable overall score
            if total_score < 25:  # Minimum 25% overall relevance
                continue
            
            scored_bookmark = {
                **bookmark,
                'relevance_scores': scores,
                'total_score': total_score,
                'reason': self._generate_high_relevance_reason(bookmark, scores, user_analysis)
            }
            scored_bookmarks.append(scored_bookmark)
        
        # Sort by total score and return top recommendations
        scored_bookmarks.sort(key=lambda x: x['total_score'], reverse=True)
        
        return scored_bookmarks[:max_recommendations]
    
    def _generate_high_relevance_reason(self, bookmark: Dict[str, Any], scores: Dict[str, float], user_analysis: Dict[str, Any]) -> str:
        """Generate reason focused on high relevance to user's input"""
        reasons = []
        
        # Technology match reason
        if scores['exact_tech_match'] > 0.8:
            techs = ', '.join(user_analysis['exact_technologies'][:3])
            reasons.append(f"Perfect match for {techs}")
        elif scores['exact_tech_match'] > 0.5:
            reasons.append("Matches your technology stack")
        
        # Requirements match reason
        if scores['requirements_match'] > 0.7:
            requirements = ', '.join(user_analysis['project_requirements'][:2])
            reasons.append(f"Directly addresses: {requirements}")
        
        # Content type reason
        if scores['content_type_match'] > 0.6:
            content_type = user_analysis['content_type_needed'].replace('_', ' ').title()
            reasons.append(f"Provides {content_type} content")
        
        # Task relevance reason
        if scores['task_relevance'] > 0.6:
            reasons.append("Relevant to your specific tasks")
        
        # Quality reason
        if scores['quality_recency'] > 0.7:
            reasons.append("High-quality, up-to-date content")
        
        # Fallback reason
        if not reasons:
            if scores['exact_tech_match'] > 0.3:
                reasons.append("Relevant to your project")
            else:
                reasons.append("Quality content for your needs")
        
        return ' • '.join(reasons)

# Global instance
high_relevance_engine = HighRelevanceEngine() 