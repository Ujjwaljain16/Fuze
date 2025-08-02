import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple, Optional
import re
from datetime import datetime
from collections import Counter

class SmartTaskRecommendationEngine:
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Technology and concept keywords for precise matching
        self.tech_concepts = {
            'react_native': ['react native', 'rn', 'expo', 'metro', 'react navigation', 'native modules'],
            'javascript': ['javascript', 'js', 'es6', 'es7', 'async', 'promise', 'callback'],
            'python': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy', 'requests'],
            'mobile': ['mobile', 'ios', 'android', 'app', 'application', 'native', 'hybrid'],
            'web': ['web', 'html', 'css', 'frontend', 'backend', 'api', 'rest', 'graphql'],
            'database': ['database', 'sql', 'nosql', 'mongodb', 'postgresql', 'mysql', 'redis'],
            'ai_ml': ['ai', 'machine learning', 'ml', 'tensorflow', 'pytorch', 'neural', 'model'],
            'devops': ['devops', 'docker', 'kubernetes', 'ci/cd', 'deployment', 'aws', 'cloud'],
            'blockchain': ['blockchain', 'crypto', 'ethereum', 'bitcoin', 'smart contract', 'web3'],
            'payment': ['payment', 'stripe', 'paypal', 'upi', 'sms', 'gateway', 'transaction'],
            'expense': ['expense', 'tracking', 'budget', 'finance', 'money', 'cost', 'spending'],
            'ocr': ['ocr', 'text recognition', 'image processing', 'scan', 'extract text'],
            'sms': ['sms', 'message', 'text', 'notification', 'alert', 'inbox'],
            'authentication': ['auth', 'login', 'signup', 'jwt', 'oauth', 'password', 'security']
        }
    
    def extract_task_context(self, task_title: str, task_description: str, project_context: Dict) -> Dict:
        """Extract precise context from current task"""
        full_context = f"{task_title} {task_description} {project_context.get('title', '')} {project_context.get('description', '')} {project_context.get('technologies', '')}"
        
        # Extract technologies and concepts
        detected_techs = []
        for tech_category, keywords in self.tech_concepts.items():
            for keyword in keywords:
                if keyword.lower() in full_context.lower():
                    detected_techs.append(tech_category)
                    break
        
        # Extract task type
        task_type = self._classify_task_type(task_title, task_description)
        
        # Extract complexity level
        complexity = self._extract_complexity(task_title, task_description)
        
        # Extract specific requirements
        requirements = self._extract_requirements(task_title, task_description)
        
        return {
            'technologies': list(set(detected_techs)),
            'task_type': task_type,
            'complexity': complexity,
            'requirements': requirements,
            'context_text': full_context,
            'keywords': self._extract_keywords(full_context)
        }
    
    def _classify_task_type(self, title: str, description: str) -> str:
        """Classify what type of task this is"""
        text = f"{title} {description}".lower()
        
        if any(word in text for word in ['implement', 'build', 'create', 'develop', 'code']):
            return 'implementation'
        elif any(word in text for word in ['debug', 'fix', 'error', 'issue', 'problem']):
            return 'debugging'
        elif any(word in text for word in ['learn', 'understand', 'study', 'research']):
            return 'learning'
        elif any(word in text for word in ['optimize', 'improve', 'performance', 'refactor']):
            return 'optimization'
        elif any(word in text for word in ['test', 'validate', 'verify']):
            return 'testing'
        else:
            return 'general'
    
    def _extract_complexity(self, title: str, description: str) -> str:
        """Extract task complexity"""
        text = f"{title} {description}".lower()
        
        if any(word in text for word in ['simple', 'basic', 'easy', 'quick', 'minor']):
            return 'simple'
        elif any(word in text for word in ['complex', 'advanced', 'difficult', 'challenging', 'major']):
            return 'complex'
        else:
            return 'medium'
    
    def _extract_requirements(self, title: str, description: str) -> List[str]:
        """Extract specific requirements from task"""
        text = f"{title} {description}".lower()
        requirements = []
        
        # Look for specific requirements
        if 'sms' in text or 'message' in text:
            requirements.append('sms_processing')
        if 'payment' in text or 'upi' in text or 'transaction' in text:
            requirements.append('payment_integration')
        if 'ocr' in text or 'text recognition' in text:
            requirements.append('ocr_processing')
        if 'auth' in text or 'login' in text:
            requirements.append('authentication')
        if 'api' in text or 'endpoint' in text:
            requirements.append('api_integration')
        if 'database' in text or 'db' in text:
            requirements.append('database')
        if 'ui' in text or 'interface' in text:
            requirements.append('ui_development')
        
        return requirements
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text"""
        # Remove common words and extract technical terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can'}
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]
        
        # Return most frequent keywords
        return [word for word, _ in Counter(keywords).most_common(10)]
    
    def calculate_precision_score(self, bookmark: Dict, task_context: Dict) -> Dict:
        """Calculate precision score for bookmark relevance to current task"""
        
        # Extract bookmark analysis
        bookmark_analysis = self._analyze_bookmark(bookmark)
        
        # Factor 1: Technology Match (0-40 points) - MOST IMPORTANT
        tech_score = self._calculate_tech_precision(bookmark_analysis, task_context)
        
        # Factor 2: Task Type Alignment (0-25 points)
        task_type_score = self._calculate_task_type_alignment(bookmark_analysis, task_context)
        
        # Factor 3: Requirements Match (0-20 points)
        requirements_score = self._calculate_requirements_match(bookmark_analysis, task_context)
        
        # Factor 4: Semantic Similarity (0-15 points)
        semantic_score = self._calculate_semantic_similarity(bookmark, task_context)
        
        # Calculate total precision score
        total_score = tech_score + task_type_score + requirements_score + semantic_score
        
        # Determine if this is a high-precision match
        is_high_precision = total_score >= 70  # Only show if 70%+ match
        
        return {
            'total_score': total_score,
            'tech_score': tech_score,
            'task_type_score': task_type_score,
            'requirements_score': requirements_score,
            'semantic_score': semantic_score,
            'is_high_precision': is_high_precision,
            'bookmark_analysis': bookmark_analysis,
            'task_context': task_context,
            'reason': self._generate_precision_reason(bookmark_analysis, task_context, total_score)
        }
    
    def _analyze_bookmark(self, bookmark: Dict) -> Dict:
        """Analyze bookmark content for precise matching"""
        full_text = f"{bookmark['title']} {bookmark.get('notes', '')} {bookmark.get('extracted_text', '')}"
        
        # Extract technologies
        detected_techs = []
        for tech_category, keywords in self.tech_concepts.items():
            for keyword in keywords:
                if keyword.lower() in full_text.lower():
                    detected_techs.append(tech_category)
                    break
        
        # Extract content type
        content_type = self._classify_content_type(bookmark['title'], bookmark.get('notes', ''))
        
        # Extract complexity
        complexity = self._extract_complexity(bookmark['title'], bookmark.get('notes', ''))
        
        # Extract requirements
        requirements = self._extract_requirements(bookmark['title'], bookmark.get('notes', ''))
        
        return {
            'technologies': list(set(detected_techs)),
            'content_type': content_type,
            'complexity': complexity,
            'requirements': requirements,
            'keywords': self._extract_keywords(full_text)
        }
    
    def _classify_content_type(self, title: str, content: str) -> str:
        """Classify content type for task alignment"""
        text = f"{title} {content}".lower()
        
        if any(word in text for word in ['tutorial', 'guide', 'how to', 'step by step']):
            return 'tutorial'
        elif any(word in text for word in ['documentation', 'api', 'reference']):
            return 'documentation'
        elif any(word in text for word in ['example', 'demo', 'sample', 'code']):
            return 'example'
        elif any(word in text for word in ['error', 'fix', 'debug', 'issue']):
            return 'troubleshooting'
        elif any(word in text for word in ['best practice', 'pattern', 'architecture']):
            return 'best_practice'
        else:
            return 'general'
    
    def _calculate_tech_precision(self, bookmark_analysis: Dict, task_context: Dict) -> float:
        """Calculate technology precision score (0-40 points)"""
        bookmark_techs = set(bookmark_analysis['technologies'])
        task_techs = set(task_context['technologies'])
        
        if not task_techs:
            return 20  # Neutral if no task techs specified
        
        if not bookmark_techs:
            return 0   # No techs in bookmark = not relevant
        
        # Calculate overlap
        overlap = len(bookmark_techs.intersection(task_techs))
        total_task_techs = len(task_techs)
        
        if total_task_techs == 0:
            return 20
        
        # Precision score: exact matches get full points
        precision_ratio = overlap / total_task_techs
        
        # Bonus for exact matches
        if overlap == total_task_techs and len(bookmark_techs) == len(task_techs):
            return 40  # Perfect match
        elif overlap >= total_task_techs * 0.8:
            return 35  # Very high match
        else:
            return min(30, precision_ratio * 30)
    
    def _calculate_task_type_alignment(self, bookmark_analysis: Dict, task_context: Dict) -> float:
        """Calculate task type alignment (0-25 points)"""
        bookmark_type = bookmark_analysis['content_type']
        task_type = task_context['task_type']
        
        # Perfect alignment
        if task_type == 'implementation' and bookmark_type in ['tutorial', 'example']:
            return 25
        elif task_type == 'debugging' and bookmark_type == 'troubleshooting':
            return 25
        elif task_type == 'learning' and bookmark_type in ['tutorial', 'documentation']:
            return 25
        elif task_type == 'optimization' and bookmark_type == 'best_practice':
            return 25
        
        # Good alignment
        elif bookmark_type in ['tutorial', 'example', 'documentation']:
            return 15
        else:
            return 5
    
    def _calculate_requirements_match(self, bookmark_analysis: Dict, task_context: Dict) -> float:
        """Calculate requirements match (0-20 points)"""
        bookmark_reqs = set(bookmark_analysis['requirements'])
        task_reqs = set(task_context['requirements'])
        
        if not task_reqs:
            return 10  # Neutral if no specific requirements
        
        if not bookmark_reqs:
            return 0   # No requirements in bookmark
        
        # Calculate overlap
        overlap = len(bookmark_reqs.intersection(task_reqs))
        total_task_reqs = len(task_reqs)
        
        if total_task_reqs == 0:
            return 10
        
        # Requirements are critical - exact matches get full points
        if overlap == total_task_reqs:
            return 20  # Perfect requirements match
        elif overlap >= total_task_reqs * 0.7:
            return 15  # Good requirements match
        else:
            return min(10, overlap * 10)
    
    def _calculate_semantic_similarity(self, bookmark: Dict, task_context: Dict) -> float:
        """Calculate semantic similarity (0-15 points)"""
        try:
            bookmark_text = f"{bookmark['title']} {bookmark.get('notes', '')}"
            task_text = task_context['context_text']
            
            bookmark_emb = self.embedding_model.encode([bookmark_text])[0]
            task_emb = self.embedding_model.encode([task_text])[0]
            
            similarity = np.dot(bookmark_emb, task_emb) / (np.linalg.norm(bookmark_emb) * np.linalg.norm(task_emb))
            
            # Convert to 0-15 scale
            return min(15, similarity * 15)
        except:
            return 5  # Neutral score if embedding fails
    
    def _generate_precision_reason(self, bookmark_analysis: Dict, task_context: Dict, total_score: float) -> str:
        """Generate precise reason for recommendation"""
        reasons = []
        
        # Technology match
        tech_match = set(bookmark_analysis['technologies']).intersection(set(task_context['technologies']))
        if tech_match:
            reasons.append(f"Matches {', '.join(tech_match)} technologies")
        
        # Task type alignment
        if bookmark_analysis['content_type'] in ['tutorial', 'example'] and task_context['task_type'] == 'implementation':
            reasons.append("Perfect for implementation")
        elif bookmark_analysis['content_type'] == 'troubleshooting' and task_context['task_type'] == 'debugging':
            reasons.append("Perfect for debugging")
        
        # Requirements match
        req_match = set(bookmark_analysis['requirements']).intersection(set(task_context['requirements']))
        if req_match:
            reasons.append(f"Addresses {', '.join(req_match)} requirements")
        
        # Precision level
        if total_score >= 80:
            reasons.append("High precision match")
        elif total_score >= 70:
            reasons.append("Good precision match")
        else:
            reasons.append("Moderate relevance")
        
        return " | ".join(reasons) if reasons else "Recommended based on content analysis"
    
    def get_precision_recommendations(self, bookmarks: List[Dict], task_context: Dict, max_recommendations: int = 3) -> List[Dict]:
        """Get only high-precision recommendations"""
        
        # Calculate precision scores for all bookmarks
        scored_bookmarks = []
        for bookmark in bookmarks:
            score_data = self.calculate_precision_score(bookmark, task_context)
            scored_bookmarks.append({
                **bookmark,
                'score_data': score_data
            })
        
        # Filter for high precision only (70%+ match)
        high_precision = [
            b for b in scored_bookmarks 
            if b['score_data']['is_high_precision']
        ]
        
        # Sort by total score (descending)
        high_precision.sort(key=lambda x: x['score_data']['total_score'], reverse=True)
        
        # Return only top recommendations
        return high_precision[:max_recommendations] 