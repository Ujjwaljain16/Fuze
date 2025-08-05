#!/usr/bin/env python3
"""
Enhanced Content Analysis Engine
Implements hybrid approach for content type, difficulty, and intent detection
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

class EnhancedContentAnalyzer:
    """
    Enhanced content analyzer using hybrid approach:
    - Rule-based pattern matching
    - Semantic analysis with spaCy
    - Structural analysis
    - Contextual cue detection
    """
    
    def __init__(self):
        # Enhanced content type patterns with contextual cues
        self.content_patterns = {
            'tutorial': {
                'keywords': ['tutorial', 'guide', 'how to', 'step by step', 'learn', 'getting started', 'walkthrough'],
                'contextual_cues': ['follow along', 'complete guide', 'beginner friendly', 'step 1', 'step 2'],
                'structural_indicators': ['numbered lists', 'screenshots', 'code examples'],
                'weight': 1.0
            },
            'documentation': {
                'keywords': ['documentation', 'api', 'reference', 'manual', 'specification', 'docs'],
                'contextual_cues': ['parameters', 'returns', 'examples', 'usage', 'installation'],
                'structural_indicators': ['code blocks', 'parameter tables', 'return types'],
                'weight': 0.9
            },
            'example': {
                'keywords': ['example', 'demo', 'sample', 'code', 'implementation', 'snippet'],
                'contextual_cues': ['working example', 'complete code', 'copy paste', 'run this'],
                'structural_indicators': ['code blocks', 'output examples', 'file structure'],
                'weight': 0.8
            },
            'troubleshooting': {
                'keywords': ['error', 'fix', 'debug', 'issue', 'problem', 'solution', 'troubleshoot', 'resolve'],
                'contextual_cues': ['common error', 'error message', 'debug steps', 'workaround'],
                'structural_indicators': ['error logs', 'before/after', 'debugging steps'],
                'weight': 0.8
            },
            'best_practice': {
                'keywords': ['best practice', 'pattern', 'architecture', 'design', 'principle', 'recommendation'],
                'contextual_cues': ['avoid this', 'do this instead', 'recommended approach', 'anti-pattern'],
                'structural_indicators': ['comparison tables', 'pros/cons', 'recommendations'],
                'weight': 0.9
            },
            'article': {
                'keywords': ['article', 'blog', 'post', 'discussion', 'analysis', 'overview'],
                'contextual_cues': ['in this article', 'we will discuss', 'analysis shows', 'conclusion'],
                'structural_indicators': ['paragraphs', 'headings', 'conclusions'],
                'weight': 0.7
            },
            'research': {
                'keywords': ['research', 'paper', 'study', 'analysis', 'investigation', 'findings'],
                'contextual_cues': ['research shows', 'study found', 'analysis reveals', 'conclusion'],
                'structural_indicators': ['abstract', 'methodology', 'results', 'conclusion'],
                'weight': 0.8
            },
            'project': {
                'keywords': ['project', 'build', 'create', 'develop', 'application', 'system'],
                'contextual_cues': ['project structure', 'build process', 'deployment', 'features'],
                'structural_indicators': ['project structure', 'file organization', 'setup instructions'],
                'weight': 0.8
            }
        }
        
        # Enhanced difficulty patterns with contextual analysis
        self.difficulty_patterns = {
            'beginner': {
                'keywords': ['beginner', 'basic', 'intro', 'getting started', 'simple', 'easy', 'first time'],
                'contextual_cues': ['no prior knowledge', 'assumes nothing', 'step by step', 'explained simply'],
                'complexity_indicators': ['short explanations', 'basic concepts', 'fundamentals'],
                'weight': 1.0
            },
            'intermediate': {
                'keywords': ['intermediate', 'medium', 'advanced beginner', 'moderate', 'some experience'],
                'contextual_cues': ['assumes basic knowledge', 'familiar with', 'previous experience'],
                'complexity_indicators': ['detailed explanations', 'concepts building', 'practical examples'],
                'weight': 1.0
            },
            'advanced': {
                'keywords': ['advanced', 'expert', 'complex', 'deep dive', 'master', 'professional', 'senior'],
                'contextual_cues': ['assumes expertise', 'deep understanding', 'complex scenarios', 'optimization'],
                'complexity_indicators': ['complex algorithms', 'advanced concepts', 'performance optimization'],
                'weight': 1.0
            }
        }
        
        # Enhanced troubleshooting difficulty patterns
        self.troubleshooting_difficulty_patterns = {
            'beginner': {
                'keywords': ['simple error', 'basic fix', 'common issue', 'easy solution'],
                'contextual_cues': ['simple mistake', 'basic problem', 'easy to fix'],
                'weight': 1.0
            },
            'intermediate': {
                'keywords': ['error handling', 'debug', 'fix issue', 'problem solving'],
                'contextual_cues': ['debugging', 'error resolution', 'problem solving'],
                'weight': 1.0
            },
            'advanced': {
                'keywords': ['memory leak', 'performance issue', 'complex error', 'production problem', 'race condition', 'deadlock'],
                'contextual_cues': ['complex debugging', 'performance optimization', 'production debugging', 'memory management'],
                'weight': 1.0
            }
        }
        
        # Enhanced intent patterns with contextual analysis
        self.intent_patterns = {
            'learning': {
                'keywords': ['learn', 'understand', 'study', 'education', 'course', 'knowledge'],
                'contextual_cues': ['learning objectives', 'what you will learn', 'educational content'],
                'structural_indicators': ['learning outcomes', 'prerequisites', 'curriculum'],
                'weight': 1.0
            },
            'implementation': {
                'keywords': ['implement', 'build', 'create', 'develop', 'code', 'make', 'construct'],
                'contextual_cues': ['implementation guide', 'build process', 'development steps'],
                'structural_indicators': ['code examples', 'implementation details', 'setup instructions'],
                'weight': 1.0
            },
            'troubleshooting': {
                'keywords': ['debug', 'fix', 'error', 'problem', 'issue', 'resolve', 'solve'],
                'contextual_cues': ['common issues', 'error resolution', 'problem solving'],
                'structural_indicators': ['error logs', 'debugging steps', 'solutions'],
                'weight': 1.0
            },
            'optimization': {
                'keywords': ['optimize', 'improve', 'performance', 'enhance', 'refactor', 'efficiency'],
                'contextual_cues': ['performance improvement', 'optimization techniques', 'better approach'],
                'structural_indicators': ['before/after comparisons', 'performance metrics', 'optimization tips'],
                'weight': 1.0
            },
            'research': {
                'keywords': ['research', 'explore', 'investigate', 'analyze', 'examine', 'study'],
                'contextual_cues': ['research findings', 'analysis results', 'investigation outcomes'],
                'structural_indicators': ['research methodology', 'data analysis', 'conclusions'],
                'weight': 1.0
            }
        }
        
        # Initialize spaCy for semantic analysis
        try:
            import spacy
            self.nlp = spacy.load("en_core_web_sm")
            self.spacy_available = True
            logger.info("spaCy model loaded successfully for semantic analysis")
        except Exception as e:
            self.nlp = None
            self.spacy_available = False
            logger.warning(f"spaCy not available, falling back to rule-based analysis: {e}")
    
    def analyze_content(self, title: str, description: str = "", extracted_text: str = "") -> Dict[str, Any]:
        """
        Comprehensive content analysis using hybrid approach
        """
        try:
            full_text = f"{title}. {description}. {extracted_text}".strip()
            
            # Rule 1: Explicit pattern matching
            content_type_rule1 = self._classify_content_type_rule_based(title, description, extracted_text)
            difficulty_rule1 = self._classify_difficulty_rule_based(title, description, extracted_text)
            intent_rule1 = self._classify_intent_rule_based(title, description, extracted_text)
            
            # Rule 2: Semantic analysis (if spaCy available)
            content_type_semantic = None
            difficulty_semantic = None
            intent_semantic = None
            
            if self.spacy_available:
                content_type_semantic = self._classify_content_type_semantic(full_text)
                difficulty_semantic = self._classify_difficulty_semantic(full_text)
                intent_semantic = self._classify_intent_semantic(full_text)
            
            # Rule 3: Structural analysis
            content_type_structural = self._classify_content_type_structural(full_text)
            difficulty_structural = self._classify_difficulty_structural(full_text)
            intent_structural = self._classify_intent_structural(full_text)
            
            # Combine results with confidence scores
            content_type, content_confidence = self._combine_classifications([
                (content_type_rule1, 0.4),
                (content_type_semantic, 0.3) if content_type_semantic else (None, 0),
                (content_type_structural, 0.3) if content_type_structural else (None, 0)
            ])
            
            difficulty, difficulty_confidence = self._combine_classifications([
                (difficulty_rule1, 0.4),
                (difficulty_semantic, 0.3) if difficulty_semantic else (None, 0),
                (difficulty_structural, 0.3) if difficulty_structural else (None, 0)
            ])
            
            intent, intent_confidence = self._combine_classifications([
                (intent_rule1, 0.4),
                (intent_semantic, 0.3) if intent_semantic else (None, 0),
                (intent_structural, 0.3) if intent_structural else (None, 0)
            ])
            
            # Extract additional insights
            key_concepts = self._extract_key_concepts_enhanced(full_text)
            complexity_score = self._calculate_complexity_score_enhanced(full_text)
            readability_score = self._calculate_readability_score(full_text)
            
            return {
                'content_type': content_type or 'general',
                'content_type_confidence': content_confidence,
                'difficulty': difficulty or 'intermediate',
                'difficulty_confidence': difficulty_confidence,
                'intent': intent or 'general',
                'intent_confidence': intent_confidence,
                'key_concepts': key_concepts,
                'complexity_score': complexity_score,
                'readability_score': readability_score,
                'analysis_methods': {
                    'rule_based': {
                        'content_type': content_type_rule1,
                        'difficulty': difficulty_rule1,
                        'intent': intent_rule1
                    },
                    'semantic': {
                        'content_type': content_type_semantic,
                        'difficulty': difficulty_semantic,
                        'intent': intent_semantic
                    } if self.spacy_available else None,
                    'structural': {
                        'content_type': content_type_structural,
                        'difficulty': difficulty_structural,
                        'intent': intent_structural
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced content analysis: {e}")
            return {
                'content_type': 'general',
                'content_type_confidence': 0.0,
                'difficulty': 'intermediate',
                'difficulty_confidence': 0.0,
                'intent': 'general',
                'intent_confidence': 0.0,
                'key_concepts': [],
                'complexity_score': 0.5,
                'readability_score': 0.5,
                'analysis_methods': {}
            }
    
    def _classify_content_type_rule_based(self, title: str, description: str, extracted_text: str) -> Optional[str]:
        """Rule-based content type classification"""
        text = f"{title} {description} {extracted_text}".lower()
        
        best_match = (None, 0.0)
        for content_type, pattern in self.content_patterns.items():
            # Check keywords
            keyword_score = self._calculate_pattern_match(text, pattern['keywords'])
            
            # Check contextual cues
            contextual_score = self._calculate_pattern_match(text, pattern.get('contextual_cues', []))
            
            # Combined score
            total_score = (keyword_score * 0.7) + (contextual_score * 0.3)
            
            if total_score > best_match[1]:
                best_match = (content_type, total_score)
        
        return best_match[0] if best_match[1] > 0.3 else None
    
    def _classify_content_type_semantic(self, text: str) -> Optional[str]:
        """Semantic content type classification using spaCy"""
        if not self.spacy_available:
            return None
        
        try:
            doc = self.nlp(text.lower())
            
            # Check for tutorial indicators
            tutorial_indicators = ['tutorial', 'learn', 'guide', 'step', 'follow']
            if any(token.text in tutorial_indicators for token in doc):
                return 'tutorial'
            
            # Check for documentation indicators
            doc_indicators = ['documentation', 'api', 'reference', 'parameter', 'return']
            if any(token.text in doc_indicators for token in doc):
                return 'documentation'
            
            # Check for troubleshooting indicators
            trouble_indicators = ['error', 'fix', 'debug', 'problem', 'issue', 'resolve']
            if any(token.text in trouble_indicators for token in doc):
                return 'troubleshooting'
            
            # Check for example indicators
            example_indicators = ['example', 'demo', 'sample', 'code', 'implementation']
            if any(token.text in example_indicators for token in doc):
                return 'example'
            
            # Check for best practice indicators
            practice_indicators = ['best practice', 'pattern', 'recommendation', 'avoid']
            if any(token.text in practice_indicators for token in doc):
                return 'best_practice'
            
            return None
            
        except Exception as e:
            logger.warning(f"Error in semantic content type classification: {e}")
            return None
    
    def _classify_content_type_structural(self, text: str) -> Optional[str]:
        """Structural content type classification"""
        # Check for documentation structure
        if re.search(r'#{2,}', text) and len(text) > 1000:
            return 'documentation'
        
        # Check for tutorial structure
        if re.search(r'\d+\.\s', text) and re.search(r'step|follow|learn', text.lower()):
            return 'tutorial'
        
        # Check for example structure
        if re.search(r'```[\w]*\n', text) and re.search(r'example|demo|sample', text.lower()):
            return 'example'
        
        # Check for troubleshooting structure
        if re.search(r'error|issue|problem', text.lower()) and re.search(r'solution|fix|resolve', text.lower()):
            return 'troubleshooting'
        
        # Check for article structure
        if len(text) > 2000 and re.search(r'conclusion|summary|in this article', text.lower()):
            return 'article'
        
        return None
    
    def _classify_difficulty_rule_based(self, title: str, description: str, extracted_text: str) -> Optional[str]:
        """Rule-based difficulty classification with enhanced troubleshooting detection"""
        text = f"{title} {description} {extracted_text}".lower()
        
        # Check if this is troubleshooting content
        is_troubleshooting = any(keyword in text for keyword in ['error', 'fix', 'debug', 'issue', 'problem', 'solution', 'troubleshoot', 'resolve'])
        
        if is_troubleshooting:
            # Use troubleshooting-specific difficulty patterns
            best_match = (None, 0.0)
            for difficulty, pattern in self.troubleshooting_difficulty_patterns.items():
                # Check keywords
                keyword_score = self._calculate_pattern_match(text, pattern['keywords'])
                
                # Check contextual cues
                contextual_score = self._calculate_pattern_match(text, pattern.get('contextual_cues', []))
                
                # Combined score
                total_score = (keyword_score * 0.7) + (contextual_score * 0.3)
                
                if total_score > best_match[1]:
                    best_match = (difficulty, total_score)
            
            # If no specific troubleshooting pattern matches, default to advanced for complex issues
            if best_match[1] > 0.3:
                return best_match[0]
            elif any(advanced_term in text for advanced_term in ['memory leak', 'performance', 'complex', 'production']):
                return 'advanced'
            else:
                return 'intermediate'  # Default for general troubleshooting
        
        # Use general difficulty patterns for non-troubleshooting content
        best_match = (None, 0.0)
        for difficulty, pattern in self.difficulty_patterns.items():
            # Check keywords
            keyword_score = self._calculate_pattern_match(text, pattern['keywords'])
            
            # Check contextual cues
            contextual_score = self._calculate_pattern_match(text, pattern.get('contextual_cues', []))
            
            # Combined score
            total_score = (keyword_score * 0.7) + (contextual_score * 0.3)
            
            if total_score > best_match[1]:
                best_match = (difficulty, total_score)
        
        return best_match[0] if best_match[1] > 0.3 else None
    
    def _classify_difficulty_semantic(self, text: str) -> Optional[str]:
        """Semantic difficulty classification using spaCy"""
        if not self.spacy_available:
            return None
        
        try:
            doc = self.nlp(text.lower())
            
            # Beginner indicators
            beginner_indicators = ['beginner', 'basic', 'simple', 'easy', 'first time', 'no experience']
            if any(token.text in beginner_indicators for token in doc):
                return 'beginner'
            
            # Advanced indicators (enhanced for better detection)
            advanced_indicators = [
                'advanced', 'expert', 'complex', 'deep dive', 'master', 'professional',
                'memory leak', 'performance optimization', 'debugging', 'troubleshooting',
                'error resolution', 'complex scenarios', 'production issues'
            ]
            if any(token.text in advanced_indicators for token in doc):
                return 'advanced'
            
            # Check for advanced troubleshooting patterns
            advanced_troubleshooting_patterns = [
                'memory leak', 'performance issue', 'complex error', 'production problem',
                'debugging', 'troubleshooting', 'error resolution', 'fix complex'
            ]
            if any(pattern in text.lower() for pattern in advanced_troubleshooting_patterns):
                return 'advanced'
            
            # Intermediate indicators
            intermediate_indicators = ['intermediate', 'moderate', 'some experience', 'familiar']
            if any(token.text in intermediate_indicators for token in doc):
                return 'intermediate'
            
            return None
            
        except Exception as e:
            logger.warning(f"Error in semantic difficulty classification: {e}")
            return None
    
    def _classify_difficulty_structural(self, text: str) -> Optional[str]:
        """Structural difficulty classification with enhanced troubleshooting detection"""
        # Check for beginner structure (lots of explanations, simple language)
        if len(text) > 2000 and text.count('explain') > 2:
            return 'beginner'
        
        # Check for advanced structure (technical terms, complex concepts)
        technical_terms = ['algorithm', 'complexity', 'optimization', 'architecture', 'framework']
        if sum(1 for term in technical_terms if term in text.lower()) > 3:
            return 'advanced'
        
        # Check for advanced troubleshooting structure
        advanced_troubleshooting_terms = [
            'memory leak', 'performance issue', 'race condition', 'deadlock', 
            'production problem', 'complex error', 'debugging', 'troubleshooting'
        ]
        if sum(1 for term in advanced_troubleshooting_terms if term in text.lower()) >= 2:
            return 'advanced'
        
        # Check for intermediate troubleshooting structure
        troubleshooting_terms = ['error', 'fix', 'debug', 'issue', 'problem', 'solution']
        if sum(1 for term in troubleshooting_terms if term in text.lower()) >= 2:
            return 'intermediate'
        
        return None
    
    def _classify_intent_rule_based(self, title: str, description: str, extracted_text: str) -> Optional[str]:
        """Rule-based intent classification"""
        text = f"{title} {description} {extracted_text}".lower()
        
        best_match = (None, 0.0)
        for intent, pattern in self.intent_patterns.items():
            # Check keywords
            keyword_score = self._calculate_pattern_match(text, pattern['keywords'])
            
            # Check contextual cues
            contextual_score = self._calculate_pattern_match(text, pattern.get('contextual_cues', []))
            
            # Combined score
            total_score = (keyword_score * 0.7) + (contextual_score * 0.3)
            
            if total_score > best_match[1]:
                best_match = (intent, total_score)
        
        return best_match[0] if best_match[1] > 0.3 else None
    
    def _classify_intent_semantic(self, text: str) -> Optional[str]:
        """Semantic intent classification using spaCy"""
        if not self.spacy_available:
            return None
        
        try:
            doc = self.nlp(text.lower())
            
            # Learning intent
            learning_indicators = ['learn', 'understand', 'study', 'education', 'knowledge']
            if any(token.text in learning_indicators for token in doc):
                return 'learning'
            
            # Implementation intent
            implementation_indicators = ['implement', 'build', 'create', 'develop', 'code']
            if any(token.text in implementation_indicators for token in doc):
                return 'implementation'
            
            # Troubleshooting intent
            troubleshooting_indicators = ['debug', 'fix', 'error', 'problem', 'resolve']
            if any(token.text in troubleshooting_indicators for token in doc):
                return 'troubleshooting'
            
            # Optimization intent
            optimization_indicators = ['optimize', 'improve', 'performance', 'enhance']
            if any(token.text in optimization_indicators for token in doc):
                return 'optimization'
            
            return None
            
        except Exception as e:
            logger.warning(f"Error in semantic intent classification: {e}")
            return None
    
    def _classify_intent_structural(self, text: str) -> Optional[str]:
        """Structural intent classification"""
        # Check for learning structure
        if re.search(r'learning objectives|what you will learn', text.lower()):
            return 'learning'
        
        # Check for implementation structure
        if re.search(r'implementation|build process|setup', text.lower()):
            return 'implementation'
        
        # Check for troubleshooting structure
        if re.search(r'error|problem.*solution|debug', text.lower()):
            return 'troubleshooting'
        
        return None
    
    def _combine_classifications(self, classifications: List[Tuple[Optional[str], float]]) -> Tuple[Optional[str], float]:
        """Combine multiple classification results with confidence scores"""
        valid_classifications = [(c, w) for c, w in classifications if c is not None]
        
        if not valid_classifications:
            return None, 0.0
        
        # Count occurrences of each classification
        class_counts = {}
        total_weight = 0
        
        for classification, weight in valid_classifications:
            if classification not in class_counts:
                class_counts[classification] = 0
            class_counts[classification] += weight
            total_weight += weight
        
        if total_weight == 0:
            return None, 0.0
        
        # Find most common classification
        best_classification = max(class_counts.items(), key=lambda x: x[1])
        confidence = best_classification[1] / total_weight
        
        return best_classification[0], confidence
    
    def _calculate_pattern_match(self, text: str, keywords: List[str]) -> float:
        """Calculate how well text matches a pattern"""
        if not keywords:
            return 0.0
        
        matches = sum(1 for keyword in keywords if keyword in text)
        return matches / len(keywords)
    
    def _extract_key_concepts_enhanced(self, text: str) -> List[str]:
        """Enhanced key concept extraction"""
        try:
            # Use spaCy for better concept extraction if available
            if self.spacy_available:
                doc = self.nlp(text)
                
                # Extract noun phrases and named entities
                concepts = []
                
                # Noun phrases
                for chunk in doc.noun_chunks:
                    if len(chunk.text) > 3 and chunk.text.lower() not in ['this', 'that', 'these', 'those']:
                        concepts.append(chunk.text.lower())
                
                # Named entities
                for ent in doc.ents:
                    if ent.label_ in ['ORG', 'PRODUCT', 'GPE', 'TECH']:
                        concepts.append(ent.text.lower())
                
                # Count and return most common
                concept_counts = Counter(concepts)
                return [concept for concept, count in concept_counts.most_common(10)]
            
            else:
                # Fallback to simple keyword extraction
                words = re.findall(r'\b\w+\b', text.lower())
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
                key_words = [word for word in words if len(word) > 3 and word not in stop_words]
                word_counts = Counter(key_words)
                return [word for word, count in word_counts.most_common(10)]
                
        except Exception as e:
            logger.warning(f"Error in enhanced key concept extraction: {e}")
            return []
    
    def _calculate_complexity_score_enhanced(self, text: str) -> float:
        """Enhanced complexity score calculation"""
        try:
            score = 0.5  # Base score
            
            # Factor 1: Technical terms density
            technical_terms = [
                'algorithm', 'complexity', 'optimization', 'architecture', 'framework', 
                'library', 'api', 'integration', 'deployment', 'configuration',
                'authentication', 'authorization', 'encryption', 'serialization',
                'asynchronous', 'concurrent', 'distributed', 'microservices'
            ]
            tech_count = sum(1 for term in technical_terms if term in text.lower())
            score += min(0.2, tech_count / 10)
            
            # Factor 2: Code complexity
            code_blocks = len(re.findall(r'```[\w]*\n.*?```', text, re.DOTALL))
            score += min(0.15, code_blocks / 5)
            
            # Factor 3: Length and structure
            if len(text) > 2000:
                score += 0.1
            if re.search(r'#{2,}', text):
                score += 0.05
            
            # Factor 4: Advanced concepts
            advanced_concepts = ['design pattern', 'dependency injection', 'inversion of control', 'SOLID']
            adv_count = sum(1 for concept in advanced_concepts if concept in text.lower())
            score += min(0.1, adv_count / 3)
            
            return min(1.0, score)
            
        except Exception as e:
            logger.warning(f"Error in enhanced complexity calculation: {e}")
            return 0.5
    
    def _calculate_readability_score(self, text: str) -> float:
        """Calculate readability score"""
        try:
            # Simple Flesch Reading Ease approximation
            sentences = len(re.findall(r'[.!?]+', text))
            words = len(re.findall(r'\b\w+\b', text))
            syllables = len(re.findall(r'[aeiouy]+', text.lower()))
            
            if sentences == 0 or words == 0:
                return 0.5
            
            # Flesch Reading Ease formula approximation
            flesch_score = 206.835 - (1.015 * (words / sentences)) - (84.6 * (syllables / words))
            
            # Normalize to 0-1 scale
            if flesch_score > 100:
                return 1.0
            elif flesch_score < 0:
                return 0.0
            else:
                return flesch_score / 100
                
        except Exception as e:
            logger.warning(f"Error in readability calculation: {e}")
            return 0.5

# Global instance
enhanced_content_analyzer = EnhancedContentAnalyzer() 