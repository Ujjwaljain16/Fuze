import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from typing import List, Dict, Tuple, Optional
import json
from datetime import datetime, timedelta

class SmartRecommendationEngine:
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        # Technology keywords for better matching
        self.tech_keywords = {
            'react_native': ['react native', 'react-native', 'rn', 'expo', 'metro', 'react navigation'],
            'javascript': ['javascript', 'js', 'es6', 'es7', 'node.js', 'nodejs'],
            'python': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy'],
            'mobile': ['mobile', 'ios', 'android', 'app', 'application', 'native'],
            'web': ['web', 'html', 'css', 'frontend', 'backend', 'api'],
            'database': ['database', 'sql', 'nosql', 'mongodb', 'postgresql', 'mysql'],
            'ai_ml': ['ai', 'machine learning', 'ml', 'tensorflow', 'pytorch', 'neural'],
            'devops': ['devops', 'docker', 'kubernetes', 'ci/cd', 'deployment'],
            'blockchain': ['blockchain', 'crypto', 'ethereum', 'bitcoin', 'smart contract']
        }
    
    def extract_content_summary(self, title: str, content: str, url: str) -> Dict:
        """Extract key information from content using AI and NLP"""
        full_text = f"{title} {content}".lower()
        
        # Extract technologies mentioned
        technologies = []
        for tech_category, keywords in self.tech_keywords.items():
            for keyword in keywords:
                if keyword in full_text:
                    technologies.append(tech_category)
                    break
        
        # Extract content type
        content_type = self._classify_content_type(title, content, url)
        
        # Extract difficulty level
        difficulty = self._extract_difficulty(title, content)
        
        # Extract intent/purpose
        intent = self._extract_intent(title, content)
        
        return {
            'technologies': list(set(technologies)),
            'content_type': content_type,
            'difficulty': difficulty,
            'intent': intent,
            'key_concepts': self._extract_key_concepts(title, content)
        }
    
    def _classify_content_type(self, title: str, content: str, url: str) -> str:
        """Classify the type of content"""
        text = f"{title} {content}".lower()
        
        if any(word in text for word in ['tutorial', 'guide', 'how to', 'step by step']):
            return 'tutorial'
        elif any(word in text for word in ['documentation', 'api', 'reference']):
            return 'documentation'
        elif any(word in text for word in ['example', 'demo', 'sample']):
            return 'example'
        elif any(word in text for word in ['article', 'blog', 'post']):
            return 'article'
        elif any(word in text for word in ['video', 'youtube', 'course']):
            return 'video'
        else:
            return 'general'
    
    def _extract_difficulty(self, title: str, content: str) -> str:
        """Extract difficulty level"""
        text = f"{title} {content}".lower()
        
        if any(word in text for word in ['beginner', 'basic', 'intro', 'getting started']):
            return 'beginner'
        elif any(word in text for word in ['advanced', 'expert', 'complex', 'deep dive']):
            return 'advanced'
        elif any(word in text for word in ['intermediate', 'medium']):
            return 'intermediate'
        else:
            return 'unknown'
    
    def _extract_intent(self, title: str, content: str) -> str:
        """Extract the intent/purpose of the content"""
        text = f"{title} {content}".lower()
        
        if any(word in text for word in ['learn', 'understand', 'concept']):
            return 'learning'
        elif any(word in text for word in ['build', 'create', 'develop', 'implement']):
            return 'implementation'
        elif any(word in text for word in ['debug', 'fix', 'error', 'problem']):
            return 'troubleshooting'
        elif any(word in text for word in ['optimize', 'performance', 'improve']):
            return 'optimization'
        else:
            return 'general'
    
    def _extract_key_concepts(self, title: str, content: str) -> List[str]:
        """Extract key concepts from content"""
        # Simple keyword extraction - can be enhanced with NLP
        text = f"{title} {content}".lower()
        words = re.findall(r'\b\w+\b', text)
        
        # Filter out common words and keep technical terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        key_words = [word for word in words if len(word) > 3 and word not in stop_words]
        
        # Return top 10 most frequent
        from collections import Counter
        return [word for word, _ in Counter(key_words).most_common(10)]
    
    def calculate_smart_score(self, bookmark: Dict, project_context: Dict) -> Dict:
        """Calculate comprehensive relevance score using multiple factors"""
        
        # Extract content analysis
        bookmark_analysis = self.extract_content_summary(
            bookmark['title'], 
            bookmark.get('notes', '') + ' ' + bookmark.get('extracted_text', ''),
            bookmark['url']
        )
        
        project_analysis = self.extract_content_summary(
            project_context['title'],
            project_context['description'] + ' ' + project_context['technologies'],
            ''
        )
        
        # Factor 1: Technology Match (0-30 points)
        tech_score = self._calculate_tech_match(bookmark_analysis, project_analysis)
        
        # Factor 2: Content Type Relevance (0-20 points)
        content_score = self._calculate_content_relevance(bookmark_analysis, project_analysis)
        
        # Factor 3: Difficulty Alignment (0-15 points)
        difficulty_score = self._calculate_difficulty_alignment(bookmark_analysis, project_analysis)
        
        # Factor 4: Intent Alignment (0-15 points)
        intent_score = self._calculate_intent_alignment(bookmark_analysis, project_analysis)
        
        # Factor 5: Semantic Similarity (0-20 points)
        semantic_score = self._calculate_semantic_similarity(bookmark, project_context)
        
        # Calculate total score
        total_score = tech_score + content_score + difficulty_score + intent_score + semantic_score
        
        return {
            'total_score': total_score,
            'tech_score': tech_score,
            'content_score': content_score,
            'difficulty_score': difficulty_score,
            'intent_score': intent_score,
            'semantic_score': semantic_score,
            'bookmark_analysis': bookmark_analysis,
            'project_analysis': project_analysis,
            'reason': self._generate_reason(bookmark_analysis, project_analysis, total_score)
        }
    
    def _calculate_tech_match(self, bookmark_analysis: Dict, project_analysis: Dict) -> float:
        """Calculate technology match score"""
        bookmark_techs = set(bookmark_analysis['technologies'])
        project_techs = set(project_analysis['technologies'])
        
        if not project_techs:
            return 15  # Neutral score if no project techs specified
        
        if not bookmark_techs:
            return 5   # Low score if no techs in bookmark
        
        # Calculate overlap
        overlap = len(bookmark_techs.intersection(project_techs))
        total = len(project_techs)
        
        if total == 0:
            return 15
        
        match_ratio = overlap / total
        
        # Score: 0-30 points
        return min(30, match_ratio * 30)
    
    def _calculate_content_relevance(self, bookmark_analysis: Dict, project_analysis: Dict) -> float:
        """Calculate content type relevance"""
        bookmark_type = bookmark_analysis['content_type']
        project_techs = project_analysis['technologies']
        
        # Prefer tutorials and examples for learning projects
        if 'react_native' in project_techs or 'mobile' in project_techs:
            if bookmark_type in ['tutorial', 'example']:
                return 20
            elif bookmark_type == 'documentation':
                return 15
            else:
                return 10
        
        # Prefer documentation for implementation
        if bookmark_type == 'documentation':
            return 20
        elif bookmark_type in ['tutorial', 'example']:
            return 15
        else:
            return 10
    
    def _calculate_difficulty_alignment(self, bookmark_analysis: Dict, project_analysis: Dict) -> float:
        """Calculate difficulty alignment"""
        bookmark_diff = bookmark_analysis['difficulty']
        project_diff = project_analysis['difficulty']
        
        if bookmark_diff == project_diff:
            return 15
        elif bookmark_diff == 'unknown' or project_diff == 'unknown':
            return 10
        else:
            return 5
    
    def _calculate_intent_alignment(self, bookmark_analysis: Dict, project_analysis: Dict) -> float:
        """Calculate intent alignment"""
        bookmark_intent = bookmark_analysis['intent']
        project_intent = project_analysis['intent']
        
        if bookmark_intent == project_intent:
            return 15
        elif bookmark_intent == 'general' or project_intent == 'general':
            return 10
        else:
            return 5
    
    def _calculate_semantic_similarity(self, bookmark: Dict, project_context: Dict) -> float:
        """Calculate semantic similarity using embeddings"""
        try:
            bookmark_text = f"{bookmark['title']} {bookmark.get('notes', '')}"
            project_text = f"{project_context['title']} {project_context['description']} {project_context['technologies']}"
            
            bookmark_emb = self.embedding_model.encode([bookmark_text])[0]
            project_emb = self.embedding_model.encode([project_text])[0]
            
            similarity = np.dot(bookmark_emb, project_emb) / (np.linalg.norm(bookmark_emb) * np.linalg.norm(project_emb))
            
            # Convert to 0-20 scale
            return min(20, similarity * 20)
        except:
            return 10  # Neutral score if embedding fails
    
    def _generate_reason(self, bookmark_analysis: Dict, project_analysis: Dict, total_score: float) -> str:
        """Generate human-readable reason for recommendation"""
        reasons = []
        
        if bookmark_analysis['technologies']:
            tech_match = set(bookmark_analysis['technologies']).intersection(set(project_analysis['technologies']))
            if tech_match:
                reasons.append(f"Matches your {', '.join(tech_match)} technologies")
        
        if bookmark_analysis['content_type'] in ['tutorial', 'example']:
            reasons.append(f"Provides {bookmark_analysis['content_type']} content")
        
        if total_score >= 70:
            reasons.append("Highly relevant to your project")
        elif total_score >= 50:
            reasons.append("Moderately relevant to your project")
        else:
            reasons.append("Somewhat related to your project")
        
        return " | ".join(reasons) if reasons else "Recommended based on content analysis"
    
    def get_smart_recommendations(self, bookmarks: List[Dict], project_context: Dict, max_recommendations: int = 5) -> List[Dict]:
        """Get smart recommendations using AI-powered analysis"""
        
        # Calculate scores for all bookmarks
        scored_bookmarks = []
        for bookmark in bookmarks:
            score_data = self.calculate_smart_score(bookmark, project_context)
            scored_bookmarks.append({
                **bookmark,
                'score_data': score_data
            })
        
        # Sort by total score (descending)
        scored_bookmarks.sort(key=lambda x: x['score_data']['total_score'], reverse=True)
        
        # Filter out very low quality recommendations (below 30 points)
        quality_recommendations = [
            b for b in scored_bookmarks 
            if b['score_data']['total_score'] >= 30
        ]
        
        # Return top recommendations
        return quality_recommendations[:max_recommendations] 