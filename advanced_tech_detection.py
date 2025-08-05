#!/usr/bin/env python3
"""
Advanced Technology Detection using spaCy for Contextual NER
"""

import spacy
import re
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class AdvancedTechnologyDetector:
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy model loaded successfully")
        except OSError:
            logger.error("spaCy model not found. Please install: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        # Technology patterns with context clues
        self.tech_patterns = {
            'java': {
                'keywords': ['java', 'jvm', 'spring', 'maven', 'gradle', 'bytecode', 'asm', 'byte buddy', 'jakarta'],
                'context_clues': ['programming', 'language', 'backend', 'enterprise', 'framework', 'application'],
                'weight': 1.0
            },
            'javascript': {
                'keywords': ['javascript', 'js', 'node', 'nodejs', 'node.js', 'typescript', 'ts', 'express', 'express.js'],
                'context_clues': ['frontend', 'web', 'browser', 'scripting', 'dynamic', 'server'],
                'weight': 1.0
            },
            'python': {
                'keywords': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy', 'scipy', 'matplotlib'],
                'context_clues': ['data science', 'machine learning', 'scripting', 'automation', 'backend'],
                'weight': 1.0
            },
            'react': {
                'keywords': ['react', 'reactjs', 'react.js', 'jsx', 'tsx', 'redux', 'react native'],
                'context_clues': ['frontend', 'ui', 'component', 'virtual dom', 'mobile'],
                'weight': 0.9
            },
            'ai_ml': {
                'keywords': ['ai', 'machine learning', 'ml', 'tensorflow', 'pytorch', 'neural', 'deep learning'],
                'context_clues': ['artificial intelligence', 'prediction', 'training', 'algorithm', 'model'],
                'weight': 0.9
            },
            'dsa': {
                'keywords': ['data structure', 'algorithm', 'dsa', 'sorting', 'searching', 'tree', 'graph', 'binary search'],
                'context_clues': ['computer science', 'problem solving', 'optimization', 'efficiency'],
                'weight': 0.9
            },
            'database': {
                'keywords': ['database', 'sql', 'nosql', 'mongodb', 'postgresql', 'mysql', 'redis', 'elasticsearch'],
                'context_clues': ['data storage', 'query', 'schema', 'index', 'caching'],
                'weight': 0.8
            },
            'authentication': {
                'keywords': ['auth', 'authentication', 'oauth', 'jwt', 'login', 'signup', 'password', 'security'],
                'context_clues': ['user verification', 'identity', 'access control', 'security'],
                'weight': 0.7
            }
        }
        
        # Multi-word patterns
        self.multi_word_patterns = {
            'machine learning': 'ai_ml',
            'deep learning': 'ai_ml',
            'artificial intelligence': 'ai_ml',
            'react native': 'react',
            'node.js': 'javascript',
            'express.js': 'javascript',
            'data structure': 'dsa',
            'data structures': 'dsa',
            'binary search': 'dsa',
            'sorting algorithm': 'dsa',
            'searching algorithm': 'dsa',
            'spring framework': 'java',
            'spring boot': 'java',
            'postgresql': 'database',
            'mongodb': 'database',
            'elasticsearch': 'database',
            'tensorflow': 'ai_ml',
            'pytorch': 'ai_ml',
            'natural language processing': 'ai_ml',
            'nlp': 'ai_ml',
            'type script': 'javascript',
            'typescript': 'javascript'
        }
    
    def extract_technologies(self, text: str) -> List[Dict]:
        if not self.nlp:
            return self._fallback_keyword_extraction(text)
        
        try:
            doc = self.nlp(text.lower())
            technologies = []
            
            # Multi-word patterns
            multi_word_techs = self._extract_multi_word_technologies(text)
            technologies.extend(multi_word_techs)
            
            # Context-aware matching
            context_techs = self._extract_context_aware_technologies(doc, text)
            technologies.extend(context_techs)
            
            return self._deduplicate_technologies(technologies)
            
        except Exception as e:
            logger.error(f"Error in advanced technology extraction: {e}")
            return self._fallback_keyword_extraction(text)
    
    def _extract_multi_word_technologies(self, text: str) -> List[Dict]:
        technologies = []
        for pattern, category in self.multi_word_patterns.items():
            if pattern.lower() in text.lower():
                technologies.append({
                    'category': category,
                    'keyword': pattern,
                    'weight': self.tech_patterns[category]['weight'],
                    'confidence': 0.9,
                    'method': 'multi_word_pattern'
                })
        return technologies
    
    def _extract_context_aware_technologies(self, doc, text: str) -> List[Dict]:
        technologies = []
        for category, pattern in self.tech_patterns.items():
            for keyword in pattern['keywords']:
                if keyword in text.lower():
                    context_score = self._calculate_context_score(doc, pattern['context_clues'])
                    # Lower threshold for better detection
                    if context_score > 0.1 or len(pattern['context_clues']) == 0:
                        technologies.append({
                            'category': category,
                            'keyword': keyword,
                            'weight': pattern['weight'],
                            'confidence': 0.6 + context_score * 0.3,
                            'method': 'context_aware'
                        })
        return technologies
    
    def _calculate_context_score(self, doc, context_clues: List[str]) -> float:
        if not context_clues:
            return 0.0
        text_tokens = [token.text.lower() for token in doc]
        matches = sum(1 for clue in context_clues if clue.lower() in text_tokens)
        return matches / len(context_clues)
    
    def _deduplicate_technologies(self, technologies: List[Dict]) -> List[Dict]:
        tech_dict = {}
        for tech in technologies:
            key = (tech['category'], tech['keyword'])
            if key in tech_dict:
                existing = tech_dict[key]
                existing['confidence'] = max(existing['confidence'], tech['confidence'])
            else:
                tech_dict[key] = tech.copy()
        return list(tech_dict.values())
    
    def _fallback_keyword_extraction(self, text: str) -> List[Dict]:
        technologies = []
        for category, pattern in self.tech_patterns.items():
            for keyword in pattern['keywords']:
                if re.search(r'\b' + re.escape(keyword) + r'\b', text.lower()):
                    technologies.append({
                        'category': category,
                        'keyword': keyword,
                        'weight': pattern['weight'],
                        'confidence': 0.5,
                        'method': 'fallback_keyword'
                    })
                    break
        return technologies

# Global instance
advanced_tech_detector = AdvancedTechnologyDetector() 