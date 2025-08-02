import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from collections import Counter
from difflib import SequenceMatcher
import json

class UnifiedRecommendationEngine:
    """
    Unified, intelligent recommendation engine that extracts everything from user input
    and provides optimal matches from saved content database.
    """
    
    def __init__(self):
        # Initialize embedding model for semantic similarity
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # TF-IDF for keyword-based similarity
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=2000,
            stop_words='english',
            ngram_range=(1, 3),
            min_df=1,
            max_df=0.95
        )
        
        # Dynamic technology detection patterns
        self.tech_patterns = {
            # Programming Languages
            'java': {
                'keywords': ['java', 'jvm', 'spring', 'maven', 'gradle', 'bytecode', 'asm', 'byte buddy', 'jakarta'],
                'weight': 1.0
            },
            'javascript': {
                'keywords': ['javascript', 'js', 'es6', 'es7', 'es8', 'es9', 'es10', 'node', 'nodejs', 'node.js', 'typescript', 'ts'],
                'weight': 1.0
            },
            'python': {
                'keywords': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy', 'scipy', 'scikit-learn', 'matplotlib'],
                'weight': 1.0
            },
            'react': {
                'keywords': ['react', 'reactjs', 'react.js', 'jsx', 'tsx', 'redux', 'context', 'hooks'],
                'weight': 0.9
            },
            'react_native': {
                'keywords': ['react native', 'rn', 'expo', 'metro', 'react navigation'],
                'weight': 0.9
            },
            
            # Domains
            'mobile': {
                'keywords': ['mobile', 'ios', 'android', 'app', 'application', 'native', 'hybrid', 'flutter', 'kotlin', 'swift'],
                'weight': 0.8
            },
            'web': {
                'keywords': ['web', 'html', 'css', 'frontend', 'backend', 'api', 'rest', 'graphql', 'http', 'https'],
                'weight': 0.8
            },
            'database': {
                'keywords': ['database', 'sql', 'nosql', 'mongodb', 'postgresql', 'mysql', 'redis', 'elasticsearch', 'cassandra'],
                'weight': 0.8
            },
            'ai_ml': {
                'keywords': ['ai', 'machine learning', 'ml', 'tensorflow', 'pytorch', 'neural', 'model', 'deep learning', 'nlp'],
                'weight': 0.9
            },
            'devops': {
                'keywords': ['devops', 'docker', 'kubernetes', 'ci/cd', 'deployment', 'aws', 'cloud', 'azure', 'gcp'],
                'weight': 0.7
            },
            'blockchain': {
                'keywords': ['blockchain', 'crypto', 'ethereum', 'bitcoin', 'smart contract', 'web3', 'solidity'],
                'weight': 0.8
            },
            'payment': {
                'keywords': ['payment', 'stripe', 'paypal', 'upi', 'gateway', 'transaction', 'billing'],
                'weight': 0.8
            },
            'authentication': {
                'keywords': ['auth', 'authentication', 'oauth', 'jwt', 'login', 'signup', 'password', 'security'],
                'weight': 0.7
            },
            
            # Specialized domains
            'dsa': {
                'keywords': ['data structure', 'algorithm', 'dsa', 'sorting', 'searching', 'tree', 'graph', 'dynamic programming'],
                'weight': 0.9
            },
            'instrumentation': {
                'keywords': ['instrumentation', 'byte buddy', 'asm', 'bytecode', 'profiling', 'monitoring'],
                'weight': 0.8
            },
            'testing': {
                'keywords': ['test', 'testing', 'unit test', 'integration test', 'jest', 'junit', 'pytest'],
                'weight': 0.6
            },
            'performance': {
                'keywords': ['performance', 'optimization', 'profiling', 'benchmark', 'speed', 'efficiency'],
                'weight': 0.7
            }
        }
        
        # Content type patterns
        self.content_patterns = {
            'tutorial': {
                'keywords': ['tutorial', 'guide', 'how to', 'step by step', 'learn', 'getting started'],
                'weight': 1.0
            },
            'documentation': {
                'keywords': ['documentation', 'api', 'reference', 'manual', 'specification'],
                'weight': 0.9
            },
            'example': {
                'keywords': ['example', 'demo', 'sample', 'code', 'implementation'],
                'weight': 0.8
            },
            'troubleshooting': {
                'keywords': ['error', 'fix', 'debug', 'issue', 'problem', 'solution', 'troubleshoot'],
                'weight': 0.8
            },
            'best_practice': {
                'keywords': ['best practice', 'pattern', 'architecture', 'design', 'principle'],
                'weight': 0.9
            }
        }
        
        # Difficulty patterns
        self.difficulty_patterns = {
            'beginner': {
                'keywords': ['beginner', 'basic', 'intro', 'getting started', 'simple', 'easy'],
                'weight': 1.0
            },
            'intermediate': {
                'keywords': ['intermediate', 'medium', 'advanced beginner', 'moderate'],
                'weight': 1.0
            },
            'advanced': {
                'keywords': ['advanced', 'expert', 'complex', 'deep dive', 'master', 'professional'],
                'weight': 1.0
            }
        }
        
        # Intent patterns
        self.intent_patterns = {
            'learning': {
                'keywords': ['learn', 'understand', 'study', 'education', 'course'],
                'weight': 1.0
            },
            'implementation': {
                'keywords': ['implement', 'build', 'create', 'develop', 'code', 'make'],
                'weight': 1.0
            },
            'troubleshooting': {
                'keywords': ['debug', 'fix', 'error', 'problem', 'issue', 'resolve'],
                'weight': 1.0
            },
            'optimization': {
                'keywords': ['optimize', 'improve', 'performance', 'enhance', 'refactor'],
                'weight': 1.0
            }
        }

    def extract_context_from_input(self, title: str, description: str = "", technologies: str = "", user_interests: str = "") -> Dict:
        """
        Extract comprehensive context from user input (project/task)
        """
        full_text = f"{title} {description} {technologies} {user_interests}".lower()
        
        # Extract technologies
        detected_techs = self._extract_technologies(full_text)
        
        # Extract content characteristics
        content_type = self._classify_content_type(title, description)
        difficulty = self._extract_difficulty(title, description)
        intent = self._extract_intent(title, description)
        
        # Extract key concepts and requirements
        key_concepts = self._extract_key_concepts(full_text)
        requirements = self._extract_requirements(full_text)
        
        # Calculate complexity score
        complexity_score = self._calculate_complexity_score(full_text)
        
        return {
            'title': title,
            'description': description,
            'technologies': detected_techs,
            'content_type': content_type,
            'difficulty': difficulty,
            'intent': intent,
            'key_concepts': key_concepts,
            'requirements': requirements,
            'complexity_score': complexity_score,
            'full_text': full_text,
            'keywords': self._extract_keywords(full_text)
        }

    def _extract_technologies(self, text: str) -> List[str]:
        """Extract technologies using word boundary matching"""
        detected_techs = []
        
        for tech_category, pattern in self.tech_patterns.items():
            keywords = pattern['keywords']
            # Sort by length (longest first) to avoid partial matches
            sorted_keywords = sorted(keywords, key=len, reverse=True)
            
            for keyword in sorted_keywords:
                # Use word boundaries to avoid partial matches
                if re.search(r'\b' + re.escape(keyword) + r'\b', text):
                    detected_techs.append({
                        'category': tech_category,
                        'keyword': keyword,
                        'weight': pattern['weight']
                    })
                    break  # Only add each category once
        
        return detected_techs

    def _classify_content_type(self, title: str, description: str) -> str:
        """Classify content type based on patterns"""
        text = f"{title} {description}".lower()
        
        best_match = ('general', 0.0)
        for content_type, pattern in self.content_patterns.items():
            score = self._calculate_pattern_match(text, pattern['keywords'])
            if score > best_match[1]:
                best_match = (content_type, score)
        
        return best_match[0] if best_match[1] > 0.3 else 'general'

    def _extract_difficulty(self, title: str, description: str) -> str:
        """Extract difficulty level"""
        text = f"{title} {description}".lower()
        
        best_match = ('unknown', 0.0)
        for difficulty, pattern in self.difficulty_patterns.items():
            score = self._calculate_pattern_match(text, pattern['keywords'])
            if score > best_match[1]:
                best_match = (difficulty, score)
        
        return best_match[0] if best_match[1] > 0.2 else 'unknown'

    def _extract_intent(self, title: str, description: str) -> str:
        """Extract intent/purpose"""
        text = f"{title} {description}".lower()
        
        best_match = ('general', 0.0)
        for intent, pattern in self.intent_patterns.items():
            score = self._calculate_pattern_match(text, pattern['keywords'])
            if score > best_match[1]:
                best_match = (intent, score)
        
        return best_match[0] if best_match[1] > 0.2 else 'general'

    def _extract_key_concepts(self, text: str) -> List[str]:
        """Extract key concepts using TF-IDF and frequency analysis"""
        # Simple keyword extraction for now
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common words and short words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
        
        key_words = [word for word in words if len(word) > 3 and word not in stop_words]
        
        # Return most frequent words
        word_counts = Counter(key_words)
        return [word for word, count in word_counts.most_common(10)]

    def _extract_requirements(self, text: str) -> List[str]:
        """Extract specific requirements"""
        requirements = []
        
        # Look for specific requirements based on context
        requirement_patterns = {
            'api_integration': ['api', 'endpoint', 'integration', 'connect'],
            'database': ['database', 'db', 'store', 'persist', 'save'],
            'authentication': ['auth', 'login', 'signup', 'user', 'password'],
            'payment': ['payment', 'pay', 'transaction', 'billing', 'money'],
            'mobile': ['mobile', 'app', 'ios', 'android'],
            'web': ['web', 'website', 'frontend', 'backend'],
            'performance': ['performance', 'speed', 'fast', 'optimize'],
            'security': ['security', 'secure', 'protect', 'encrypt'],
            'testing': ['test', 'testing', 'validate', 'verify'],
            'deployment': ['deploy', 'deployment', 'production', 'server']
        }
        
        for req_type, keywords in requirement_patterns.items():
            if any(keyword in text for keyword in keywords):
                requirements.append(req_type)
        
        return requirements

    def _calculate_complexity_score(self, text: str) -> float:
        """Calculate complexity score based on various factors"""
        score = 0.5  # Base score
        
        # Factor 1: Technical terms density
        tech_terms = len([word for word in text.split() if len(word) > 6])
        score += min(0.2, tech_terms / 20)
        
        # Factor 2: Length
        score += min(0.1, len(text) / 1000)
        
        # Factor 3: Technical keywords
        tech_keywords = ['algorithm', 'complexity', 'optimization', 'architecture', 'framework', 'library', 'api', 'integration']
        tech_count = sum(1 for keyword in tech_keywords if keyword in text)
        score += min(0.2, tech_count / 5)
        
        return min(1.0, score)

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords"""
        words = re.findall(r'\b\w+\b', text.lower())
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]
        return [word for word, _ in Counter(keywords).most_common(15)]

    def _calculate_pattern_match(self, text: str, keywords: List[str]) -> float:
        """Calculate how well text matches a pattern"""
        matches = sum(1 for keyword in keywords if keyword in text)
        return matches / len(keywords) if keywords else 0.0

    def calculate_recommendation_score(self, bookmark: Dict, context: Dict) -> Dict:
        """
        Calculate comprehensive recommendation score
        """
        # Extract bookmark analysis
        bookmark_text = f"{bookmark.get('title', '')} {bookmark.get('notes', '')} {bookmark.get('extracted_text', '')}"
        bookmark_analysis = self.extract_context_from_input(
            bookmark.get('title', ''),
            bookmark.get('notes', '') + ' ' + bookmark.get('extracted_text', '')
        )
        
        # Calculate various similarity scores
        scores = {}
        
        # 1. Technology Match (0-30 points)
        scores['tech_match'] = self._calculate_technology_match(bookmark_analysis, context)
        
        # 2. Content Type Relevance (0-20 points)
        scores['content_relevance'] = self._calculate_content_relevance(bookmark_analysis, context)
        
        # 3. Difficulty Alignment (0-15 points)
        scores['difficulty_alignment'] = self._calculate_difficulty_alignment(bookmark_analysis, context)
        
        # 4. Intent Alignment (0-15 points)
        scores['intent_alignment'] = self._calculate_intent_alignment(bookmark_analysis, context)
        
        # 5. Semantic Similarity (0-20 points)
        scores['semantic_similarity'] = self._calculate_semantic_similarity(bookmark_text, context['full_text'])
        
        # Calculate total score
        total_score = sum(scores.values())
        
        # Generate reason
        reason = self._generate_reason(bookmark_analysis, context, scores, total_score)
        
        return {
            'total_score': total_score,
            'scores': scores,
            'bookmark_analysis': bookmark_analysis,
            'context_analysis': context,
            'reason': reason,
            'confidence': self._calculate_confidence(scores, total_score)
        }

    def _calculate_technology_match(self, bookmark_analysis: Dict, context: Dict) -> float:
        """Calculate technology match score"""
        bookmark_techs = {tech['category'] for tech in bookmark_analysis['technologies']}
        context_techs = {tech['category'] for tech in context['technologies']}
        
        if not context_techs:
            return 15  # Neutral if no context techs
        
        if not bookmark_techs:
            return 5   # Low score if no bookmark techs
        
        # Calculate weighted overlap
        overlap = bookmark_techs.intersection(context_techs)
        overlap_weight = sum(
            next((tech['weight'] for tech in bookmark_analysis['technologies'] if tech['category'] == cat), 1.0)
            for cat in overlap
        )
        
        total_weight = sum(tech['weight'] for tech in context['technologies'])
        
        if total_weight == 0:
            return 15
        
        return min(30, (overlap_weight / total_weight) * 30)

    def _calculate_content_relevance(self, bookmark_analysis: Dict, context: Dict) -> float:
        """Calculate content type relevance"""
        bookmark_type = bookmark_analysis['content_type']
        context_type = context['content_type']
        
        # Perfect match
        if bookmark_type == context_type:
            return 20
        
        # Good matches
        good_matches = {
            ('tutorial', 'learning'): 18,
            ('example', 'implementation'): 18,
            ('documentation', 'implementation'): 16,
            ('troubleshooting', 'troubleshooting'): 18
        }
        
        for (bt, ct), score in good_matches.items():
            if bookmark_type == bt and context['intent'] == ct:
                return score
        
        # Default score
        return 10

    def _calculate_difficulty_alignment(self, bookmark_analysis: Dict, context: Dict) -> float:
        """Calculate difficulty alignment"""
        bookmark_diff = bookmark_analysis['difficulty']
        context_diff = context['difficulty']
        
        if bookmark_diff == context_diff:
            return 15
        elif bookmark_diff == 'unknown' or context_diff == 'unknown':
            return 10
        else:
            return 5

    def _calculate_intent_alignment(self, bookmark_analysis: Dict, context: Dict) -> float:
        """Calculate intent alignment"""
        bookmark_intent = bookmark_analysis['intent']
        context_intent = context['intent']
        
        if bookmark_intent == context_intent:
            return 15
        elif bookmark_intent == 'general' or context_intent == 'general':
            return 10
        else:
            return 5

    def _calculate_semantic_similarity(self, bookmark_text: str, context_text: str) -> float:
        """Calculate semantic similarity using embeddings"""
        try:
            bookmark_emb = self.embedding_model.encode([bookmark_text])[0]
            context_emb = self.embedding_model.encode([context_text])[0]
            
            similarity = np.dot(bookmark_emb, context_emb) / (np.linalg.norm(bookmark_emb) * np.linalg.norm(context_emb))
            
            # Convert to 0-20 scale
            return min(20, similarity * 20)
        except:
            return 10  # Neutral score if embedding fails

    def _generate_reason(self, bookmark_analysis: Dict, context: Dict, scores: Dict, total_score: float) -> str:
        """Generate human-readable reason for recommendation"""
        reasons = []
        
        # Technology match
        if scores['tech_match'] > 20:
            bookmark_techs = [tech['category'] for tech in bookmark_analysis['technologies']]
            context_techs = [tech['category'] for tech in context['technologies']]
            overlap = set(bookmark_techs).intersection(set(context_techs))
            if overlap:
                reasons.append(f"Matches {', '.join(overlap)} technologies")
        
        # Content type
        if scores['content_relevance'] > 15:
            reasons.append(f"Perfect {bookmark_analysis['content_type']} content")
        elif scores['content_relevance'] > 10:
            reasons.append(f"Good {bookmark_analysis['content_type']} content")
        
        # Intent alignment
        if scores['intent_alignment'] > 10:
            reasons.append(f"Perfect for {context['intent']}")
        
        # Overall score
        if total_score >= 80:
            reasons.append("Highly relevant")
        elif total_score >= 60:
            reasons.append("Very relevant")
        elif total_score >= 40:
            reasons.append("Moderately relevant")
        else:
            reasons.append("Somewhat relevant")
        
        return " | ".join(reasons) if reasons else "Recommended based on content analysis"

    def _calculate_confidence(self, scores: Dict, total_score: float) -> float:
        """Calculate confidence in the recommendation"""
        # Higher confidence if scores are balanced and high
        score_variance = np.var(list(scores.values()))
        avg_score = np.mean(list(scores.values()))
        
        confidence = min(1.0, (total_score / 100) * (1 - score_variance / 100))
        return confidence

    def get_recommendations(self, bookmarks: List[Dict], context: Dict, max_recommendations: int = 10) -> List[Dict]:
        """
        Get intelligent recommendations based on context
        """
        # Calculate scores for all bookmarks
        scored_bookmarks = []
        
        for bookmark in bookmarks:
            score_data = self.calculate_recommendation_score(bookmark, context)
            scored_bookmarks.append({
                **bookmark,
                'score_data': score_data
            })
        
        # Sort by total score (descending)
        scored_bookmarks.sort(key=lambda x: x['score_data']['total_score'], reverse=True)
        
        # Filter by minimum relevance (30 points = 30%)
        relevant_bookmarks = [
            b for b in scored_bookmarks 
            if b['score_data']['total_score'] >= 30
        ]
        
        # Return top recommendations
        return relevant_bookmarks[:max_recommendations]

    def get_diverse_recommendations(self, bookmarks: List[Dict], context: Dict, max_recommendations: int = 10) -> List[Dict]:
        """
        Get diverse recommendations (avoid too similar content)
        """
        recommendations = self.get_recommendations(bookmarks, context, max_recommendations * 2)
        
        # Simple diversity: avoid too many from same content type
        content_type_counts = {}
        diverse_recommendations = []
        
        for rec in recommendations:
            content_type = rec['score_data']['bookmark_analysis']['content_type']
            if content_type_counts.get(content_type, 0) < 3:  # Max 3 of same type
                diverse_recommendations.append(rec)
                content_type_counts[content_type] = content_type_counts.get(content_type, 0) + 1
            
            if len(diverse_recommendations) >= max_recommendations:
                break
        
        return diverse_recommendations 