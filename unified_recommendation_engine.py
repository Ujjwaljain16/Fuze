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

# Import enhanced analysis modules
try:
    from enhanced_content_analysis import enhanced_content_analyzer
    from enhanced_diversity_engine import enhanced_diversity_engine
    from enhanced_context_extraction import enhanced_context_extractor
    ENHANCED_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Enhanced modules not available: {e}")
    ENHANCED_MODULES_AVAILABLE = False

class UnifiedRecommendationEngine:
    """
    Unified, intelligent recommendation engine that extracts everything from user input
    and provides optimal matches from saved content database.
    """
    
    def __init__(self):
        # Initialize embedding model for semantic similarity
        import torch
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Fix meta tensor issue by using to_empty() instead of to()
        if hasattr(torch, 'meta') and torch.meta.is_available():
            # Use to_empty() for meta tensors
            self.embedding_model = self.embedding_model.to_empty(device='cpu')
        else:
            # Fallback to CPU
            self.embedding_model = self.embedding_model.to('cpu')
        
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
                'keywords': ['java', 'jvm', 'spring', 'maven', 'gradle', 'bytecode', 'asm', 'byte buddy', 'jakarta', 'jdk', 'jre', 'javac', 'jar', 'war', 'ear', 'servlet', 'jsp', 'ejb', 'jpa', 'hibernate', 'junit', 'mockito', 'lombok', 'guava', 'apache commons', 'log4j', 'slf4j', 'tomcat', 'jetty', 'wildfly', 'glassfish', 'weblogic', 'websphere'],
                'weight': 1.0
            },
            'javascript': {
                'keywords': ['javascript', 'js', 'es6', 'es7', 'es8', 'es9', 'es10', 'node', 'nodejs', 'node.js', 'typescript', 'ts', 'ecmascript', 'vanilla js'],
                'weight': 1.0
            },
            'python': {
                'keywords': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy', 'scipy', 'scikit-learn', 'matplotlib', 'seaborn', 'plotly', 'jupyter', 'pip', 'conda', 'virtualenv', 'venv', 'pyenv', 'poetry', 'pytest', 'unittest', 'pylint', 'black', 'flake8'],
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
        Extract comprehensive context from user input using enhanced analysis
        """
        # Create cache key for this input
        cache_key = f"context_extraction:{hash(f'{title}{description}{technologies}{user_interests}')}"
        
        # Check cache first
        try:
            from redis_utils import redis_cache
            cached_context = redis_cache.get_cache(cache_key)
            if cached_context:
                print(f"✅ Using cached context for: {title[:50]}...")
                return cached_context
        except Exception as e:
            print(f"Cache check failed: {e}")
        
        # If not in cache, extract context
        try:
            if ENHANCED_MODULES_AVAILABLE:
                # Use enhanced context extraction
                extracted_context = enhanced_context_extractor.extract_context(
                    title=title,
                    description=description,
                    technologies=technologies,
                    user_interests=user_interests
                )
                
                # Convert ExtractedContext object to dictionary format
                context_result = {
                    'title': title,
                    'description': description,
                    'technologies': self._extract_technologies(f"{title} {description} {technologies} {user_interests}"),
                    'content_type': extracted_context.content_type,
                    'difficulty': extracted_context.difficulty,
                    'intent': extracted_context.intent,
                    'key_concepts': extracted_context.key_concepts,
                    'requirements': extracted_context.implicit_requirements,
                    'complexity_score': extracted_context.complexity,
                    'full_text': f"{title} {description} {technologies} {user_interests}".lower(),
                    'keywords': self._extract_keywords(f"{title} {description} {technologies} {user_interests}"),
                    'primary_technologies': extracted_context.primary_technologies,
                    'secondary_technologies': extracted_context.secondary_technologies,
                    'core_domains': extracted_context.core_domains,
                    'learning_objectives': extracted_context.learning_objectives,
                    'content_types_needed': extracted_context.content_types_needed,
                    'ambiguous_terms_resolved': extracted_context.ambiguous_terms_resolved,
                    'confidence_score': extracted_context.confidence_score,
                    'analysis_metadata': extracted_context.analysis_metadata
                }
            else:
                # Fallback to basic extraction
                context_result = self._extract_context_fallback(title, description, technologies, user_interests)
            
            # Cache the result for 1 hour
            try:
                from redis_utils import redis_cache
                redis_cache.set_cache(cache_key, context_result, 3600)
                print(f"✅ Cached context for: {title[:50]}...")
            except Exception as e:
                print(f"Context caching failed: {e}")
            
            return context_result
            
        except Exception as e:
            print(f"Context extraction failed: {e}")
            return self._extract_context_fallback(title, description, technologies, user_interests)

    def _extract_context_fallback(self, title: str, description: str = "", technologies: str = "", user_interests: str = "") -> Dict:
        """Fallback context extraction method"""
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

    def _extract_technologies(self, text: str) -> List[Dict]:
        """Extract technologies using advanced spaCy-based detection"""
        try:
            # Import and use advanced technology detector
            from advanced_tech_detection import advanced_tech_detector
            tech_results = advanced_tech_detector.extract_technologies(text)
            
            # Convert the advanced detector results to the format expected by the unified engine
            # The advanced detector returns List[Dict] with 'category', 'keyword', 'confidence', 'weight'
            # We need to return the same format for consistency
            return tech_results
            
        except ImportError:
            # Fallback to original method if advanced detector is not available
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
                            'weight': pattern['weight'],
                            'confidence': 0.8  # Default confidence for fallback
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
        """Calculate technology match score with improved accuracy for React Native, UPI, mobile development"""
        # Extract technology categories from both bookmark and context
        bookmark_techs = []
        if 'technologies' in bookmark_analysis:
            for tech in bookmark_analysis['technologies']:
                if isinstance(tech, dict) and 'category' in tech:
                    bookmark_techs.append(tech['category'])
                elif isinstance(tech, str):
                    bookmark_techs.append(tech)
        
        context_techs = []
        if 'technologies' in context:
            for tech in context['technologies']:
                if isinstance(tech, dict) and 'category' in tech:
                    context_techs.append(tech['category'])
                elif isinstance(tech, str):
                    context_techs.append(tech)
        
        # Also check primary_technologies from context
        if 'primary_technologies' in context:
            context_techs.extend(context['primary_technologies'])
        
        # Get text content for keyword matching
        bookmark_text = f"{bookmark_analysis.get('title', '')} {bookmark_analysis.get('content', '')}".lower()
        context_text = context.get('full_text', '').lower()
        
        # React Native specific technologies
        react_native_keywords = {
            'react native', 'react-native', 'expo', 'react native cli', 'metro bundler',
            'react navigation', 'react-navigation', 'react native elements',
            'react native paper', 'react native vector icons', 'react native maps',
            'react native firebase', 'react native async storage', 'react native permissions'
        }
        
        # UPI specific keywords
        upi_keywords = {
            'upi', 'unified payments interface', 'upi integration', 'upi payment',
            'upi sdk', 'upi deep linking', 'upi intent', 'upi merchant',
            'upi payment gateway', 'upi transaction', 'upi qr code', 'setu'
        }
        
        # Mobile development keywords
        mobile_keywords = {
            'mobile app', 'mobile development', 'ios', 'android', 'cross platform',
            'native app', 'hybrid app', 'mobile ui', 'mobile ux', 'mobile testing',
            'app store', 'google play', 'mobile deployment', 'mobile performance'
        }
        
        # Check for specific technology matches
        bookmark_react_native = any(keyword in bookmark_text for keyword in react_native_keywords)
        context_react_native = any(keyword in context_text for keyword in react_native_keywords)
        
        bookmark_upi = any(keyword in bookmark_text for keyword in upi_keywords)
        context_upi = any(keyword in context_text for keyword in upi_keywords)
        
        bookmark_mobile = any(keyword in bookmark_text for keyword in mobile_keywords)
        context_mobile = any(keyword in context_text for keyword in mobile_keywords)
        
        if not context_techs:
            return 15  # Neutral if no context techs
        
        if not bookmark_techs:
            return 5   # Low score if no bookmark techs
        
        # Calculate overlap
        bookmark_set = set(bookmark_techs)
        context_set = set(context_techs)
        overlap = bookmark_set.intersection(context_set)
        
        # Calculate weighted scores for overlapping technologies
        overlap_scores = []
        for cat in overlap:
            # Find the technology objects for this category
            bookmark_tech = next((tech for tech in bookmark_analysis.get('technologies', []) 
                                if isinstance(tech, dict) and tech.get('category') == cat), None)
            context_tech = next((tech for tech in context.get('technologies', []) 
                               if isinstance(tech, dict) and tech.get('category') == cat), None)
            
            if bookmark_tech and context_tech:
                # Calculate confidence-weighted score
                confidence_score = (bookmark_tech.get('confidence', 0.5) + context_tech.get('confidence', 0.5)) / 2
                weight_score = (bookmark_tech.get('weight', 1.0) + context_tech.get('weight', 1.0)) / 2
                overlap_scores.append(confidence_score * weight_score)
            else:
                # Simple overlap
                overlap_scores.append(1.0)
        
        # Calculate total context weight
        total_context_weight = len(context_set)
        
        if total_context_weight == 0:
            return 15
        
        # Calculate final score with more granularity
        base_score = 0
        if overlap_scores:
            overlap_score = sum(overlap_scores)
            match_ratio = overlap_score / total_context_weight
            
            # Apply non-linear scaling for better differentiation
            if match_ratio >= 0.8:
                base_score = 25  # Perfect match
            elif match_ratio >= 0.6:
                base_score = 20  # Very good match
            elif match_ratio >= 0.4:
                base_score = 15  # Good match
            elif match_ratio >= 0.2:
                base_score = 10  # Moderate match
            else:
                base_score = 5   # Weak match
        else:
            base_score = 5  # No overlap
        
        # BOOST SCORE FOR SPECIFIC TECHNOLOGY MATCHES
        boost = 0
        
        # Perfect React Native match
        if bookmark_react_native and context_react_native:
            boost += 10
        
        # Perfect UPI match
        if bookmark_upi and context_upi:
            boost += 10
        
        # Perfect mobile development match
        if bookmark_mobile and context_mobile:
            boost += 8
        
        # Partial matches (one side has the technology)
        if (bookmark_react_native or bookmark_upi or bookmark_mobile) and (context_react_native or context_upi or context_mobile):
            boost += 5
        
        return min(30, base_score + boost)  # Cap at 30 points

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
        """Calculate difficulty alignment with improved logic"""
        bookmark_diff = bookmark_analysis['difficulty']
        context_diff = context['difficulty']
        
        # Perfect match
        if bookmark_diff == context_diff:
            return 15
        
        # Handle unknown difficulties
        if bookmark_diff == 'unknown' or context_diff == 'unknown':
            return 10
        
        # Define difficulty hierarchy
        difficulty_levels = {
            'beginner': 1,
            'intermediate': 2,
            'advanced': 3
        }
        
        bookmark_level = difficulty_levels.get(bookmark_diff, 2)
        context_level = difficulty_levels.get(context_diff, 2)
        
        # Calculate level difference
        level_diff = abs(bookmark_level - context_level)
        
        if level_diff == 0:
            return 15  # Same level
        elif level_diff == 1:
            # Adjacent levels - moderate penalty
            if context_level > bookmark_level:
                # Context is harder than bookmark - slight penalty
                return 12
            else:
                # Context is easier than bookmark - more penalty for advanced projects
                return 8
        else:
            # Two levels apart - significant penalty
            return 3

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
        """Generate personalized, actionable recommendation reason with improved specificity"""
        
        # Get specific technology matches
        bookmark_techs = []
        if 'technologies' in bookmark_analysis:
            for tech in bookmark_analysis['technologies']:
                if isinstance(tech, dict) and 'category' in tech:
                    bookmark_techs.append(tech['category'])
                elif isinstance(tech, str):
                    bookmark_techs.append(tech)
        
        context_techs = []
        if 'technologies' in context:
            for tech in context['technologies']:
                if isinstance(tech, dict) and 'category' in tech:
                    context_techs.append(tech['category'])
                elif isinstance(tech, str):
                    context_techs.append(tech)
        if 'primary_technologies' in context:
            context_techs.extend(context['primary_technologies'])
        
        tech_matches = set(bookmark_techs).intersection(set(context_techs))
        
        # Build specific reason components
        reason_parts = []
        
        # Technology match explanation
        if tech_matches:
            tech_str = ", ".join(list(tech_matches)[:3])  # Limit to top 3
            reason_parts.append(f"Directly covers {tech_str} technologies")
        elif scores['tech_match'] > 15:
            reason_parts.append("Relevant technology overlap")
        elif scores['tech_match'] < 10:
            reason_parts.append("Limited technology relevance")
        
        # Difficulty explanation
        if bookmark_analysis['difficulty'] == context['difficulty']:
            reason_parts.append("Perfect difficulty match for your skill level")
        elif scores['difficulty_alignment'] > 10:
            reason_parts.append("Appropriate difficulty level")
        elif scores['difficulty_alignment'] < 8:
            reason_parts.append("May be too basic for your advanced project")
        
        # Content type explanation
        content_type = bookmark_analysis['content_type']
        if content_type == 'tutorial' and context['intent'] == 'learning':
            reason_parts.append("Structured learning approach")
        elif content_type == 'example' and context['intent'] == 'implementation':
            reason_parts.append("Practical implementation examples")
        elif content_type == 'documentation':
            reason_parts.append("Comprehensive technical reference")
        
        # Intent alignment
        if bookmark_analysis['intent'] == context['intent']:
            reason_parts.append("Matches your learning intent")
        
        # Semantic relevance
        if scores['semantic_similarity'] > 15:
            reason_parts.append("High semantic relevance to your project")
        elif scores['semantic_similarity'] > 10:
            reason_parts.append("Moderate semantic relevance")
        
        # Overall assessment
        if total_score > 70:
            reason_parts.append("Highly recommended for your project")
        elif total_score > 50:
            reason_parts.append("Worth considering for your project")
        else:
            reason_parts.append("May provide some useful insights")
        
        # Combine all parts
        if reason_parts:
            return ". ".join(reason_parts) + "."
        else:
            return "Provides relevant content for your project needs."

    def _get_skill_level_note(self, context: Dict, bookmark_analysis: Dict) -> str:
        """Get personalized skill level note"""
        context_diff = context.get('difficulty', 'intermediate')
        bookmark_diff = bookmark_analysis.get('difficulty', 'intermediate')
        
        if context_diff == 'beginner' and bookmark_diff == 'beginner':
            return "Perfect for beginners with step-by-step guidance."
        elif context_diff == 'beginner' and bookmark_diff == 'intermediate':
            return "Good for beginners looking to advance their skills."
        elif context_diff == 'advanced' and bookmark_diff == 'advanced':
            return "Excellent for advanced developers seeking deep insights."
        elif context_diff == 'advanced' and bookmark_diff == 'intermediate':
            return "Suitable for advanced developers wanting practical implementation."
        elif context_diff == 'intermediate' and bookmark_diff == 'intermediate':
            return "Well-suited for intermediate developers."
        else:
            return "Appropriate for your current skill level."

    def _get_technology_explanation(self, bookmark_analysis: Dict, context: Dict, scores: Dict) -> str:
        """Get specific technology match explanation"""
        if scores.get('tech_match', 0) < 15:
            return ""
        
        bookmark_techs = bookmark_analysis.get('technologies', [])
        context_techs = context.get('technologies', [])
        
        if not context_techs:
            return ""
        
        # Extract categories for overlap checking
        bookmark_categories = [tech['category'] for tech in bookmark_techs if isinstance(tech, dict) and 'category' in tech]
        context_categories = [tech['category'] for tech in context_techs if isinstance(tech, dict) and 'category' in tech]
        
        # Find overlapping technologies
        overlap = set(bookmark_categories).intersection(set(context_categories))
        
        if overlap:
            tech_list = ", ".join(sorted(overlap))
            if len(overlap) == 1:
                return f"Directly covers {tech_list} technology that you're working with."
            else:
                return f"Comprehensive coverage of {tech_list} technologies relevant to your project."
        else:
            # Check for related technologies - pass the full technology dictionaries
            related_techs = self._find_related_technologies(bookmark_techs, context_techs)
            if related_techs:
                return f"Features {', '.join(related_techs)} which complement your technology stack."
        
        return ""

    def _get_intent_explanation(self, context: Dict, bookmark_analysis: Dict) -> str:
        """Get intent-based explanation"""
        context_intent = context.get('intent', 'general')
        bookmark_type = bookmark_analysis.get('content_type', 'general')
        
        intent_mapping = {
            'learning': {
                'tutorial': "Provides structured learning path for",
                'documentation': "Offers comprehensive reference for",
                'example': "Demonstrates practical examples of",
                'best_practice': "Teaches best practices for",
                'general': "Helps you learn about"
            },
            'implementation': {
                'tutorial': "Guides you through implementing",
                'documentation': "Provides implementation details for",
                'example': "Shows how to implement",
                'best_practice': "Demonstrates proper implementation of",
                'general': "Helps you implement"
            },
            'troubleshooting': {
                'tutorial': "Walks through solving issues with",
                'documentation': "Contains troubleshooting guides for",
                'example': "Shows solutions for common problems with",
                'best_practice': "Prevents issues by teaching best practices for",
                'general': "Helps you troubleshoot"
            },
            'optimization': {
                'tutorial': "Teaches optimization techniques for",
                'documentation': "Provides optimization guidelines for",
                'example': "Demonstrates optimized approaches to",
                'best_practice': "Shows performance best practices for",
                'general': "Helps you optimize"
            }
        }
        
        intent_explanations = intent_mapping.get(context_intent, {})
        explanation = intent_explanations.get(bookmark_type, intent_explanations.get('general', ''))
        
        if explanation:
            project_title = context.get('title', 'your project')
            return f"{explanation} {project_title}."
        
        return ""

    def _get_content_type_benefit(self, bookmark_analysis: Dict, context: Dict) -> str:
        """Get content type specific benefits"""
        content_type = bookmark_analysis.get('content_type', 'general')
        
        benefits = {
            'tutorial': "Includes step-by-step instructions and explanations.",
            'documentation': "Provides comprehensive technical reference and API details.",
            'example': "Offers practical code examples and real-world scenarios.",
            'troubleshooting': "Focuses on problem-solving and debugging techniques.",
            'best_practice': "Teaches industry standards and proven patterns.",
            'project': "Shows complete project implementation from start to finish."
        }
        
        return benefits.get(content_type, "")

    def _get_difficulty_note(self, bookmark_analysis: Dict, context: Dict) -> str:
        """Get difficulty alignment explanation"""
        bookmark_diff = bookmark_analysis.get('difficulty', 'intermediate')
        context_diff = context.get('difficulty', 'intermediate')
        
        if bookmark_diff == context_diff:
            return f"Difficulty level ({bookmark_diff}) matches your project requirements."
        elif bookmark_diff == 'beginner' and context_diff in ['intermediate', 'advanced']:
            return "Provides foundational knowledge that builds up to your project complexity."
        elif bookmark_diff == 'advanced' and context_diff in ['beginner', 'intermediate']:
            return "Offers advanced insights that will help you grow beyond current requirements."
        else:
            return ""

    def _get_learning_objective_note(self, bookmark_analysis: Dict, context: Dict) -> str:
        """Get learning objective alignment note"""
        bookmark_objectives = bookmark_analysis.get('learning_objectives', [])
        context_objectives = context.get('learning_objectives', [])
        
        if not bookmark_objectives or not context_objectives:
            return ""
        
        # Find overlapping learning objectives
        overlap = set(bookmark_objectives).intersection(set(context_objectives))
        
        if overlap:
            objectives = ", ".join(list(overlap)[:2])  # Limit to 2 for readability
            return f"Specifically addresses your learning goals: {objectives}."
        
        return ""

    def _get_relevance_strength(self, total_score: float) -> str:
        """Get relevance strength indicator"""
        if total_score >= 85:
            return "This is a highly relevant resource for your needs."
        elif total_score >= 70:
            return "This resource is very relevant to your project."
        elif total_score >= 50:
            return "This content is relevant and worth considering."
        else:
            return "This may be useful as supplementary material."

    def _find_related_technologies(self, bookmark_techs: List[Dict], context_techs: List[Dict]) -> List[str]:
        """Find related technologies between bookmark and context with improved Java ecosystem support"""
        related = []
        
        # Extract technology categories from both lists
        bookmark_categories = [tech['category'] for tech in bookmark_techs if isinstance(tech, dict) and 'category' in tech]
        context_categories = [tech['category'] for tech in context_techs if isinstance(tech, dict) and 'category' in tech]
        
        # Technology relationships for better matching
        tech_relationships = {
            'java': ['jvm', 'spring', 'maven', 'gradle', 'jakarta', 'hibernate', 'jpa'],
            'javascript': ['typescript', 'node', 'react', 'vue', 'angular', 'express'],
            'python': ['django', 'flask', 'fastapi', 'pandas', 'numpy', 'scipy'],
            'react': ['javascript', 'typescript', 'redux', 'react native'],
            'dsa': ['algorithm', 'data structure', 'computer science'],
            'database': ['sql', 'nosql', 'mongodb', 'postgresql', 'redis'],
            'ai_ml': ['machine learning', 'deep learning', 'neural networks', 'tensorflow', 'pytorch'],
            'authentication': ['oauth', 'jwt', 'security', 'authorization'],
            'frontend': ['react', 'vue', 'angular', 'javascript', 'typescript', 'html', 'css'],
            'backend': ['java', 'python', 'node', 'express', 'django', 'flask'],
            'mobile': ['react native', 'flutter', 'ios', 'android', 'swift', 'kotlin'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'microservices'],
            'devops': ['docker', 'kubernetes', 'ci/cd', 'jenkins', 'gitlab', 'github actions'],
            'testing': ['jest', 'cypress', 'selenium', 'junit', 'pytest', 'tdd', 'bdd'],
            'performance': ['optimization', 'caching', 'redis', 'cdn', 'load balancing'],
            'security': ['authentication', 'authorization', 'encryption', 'oauth', 'jwt', 'https'],
            'api': ['rest', 'graphql', 'microservices', 'express', 'django', 'fastapi'],
            'data': ['database', 'sql', 'nosql', 'analytics', 'big data', 'data science'],
            'web': ['frontend', 'backend', 'fullstack', 'html', 'css', 'javascript'],
            'tool': ['git', 'docker', 'kubernetes', 'jenkins', 'vscode', 'intellij']
        }
        
        # Find direct matches
        for bookmark_cat in bookmark_categories:
            if bookmark_cat in context_categories:
                related.append(bookmark_cat)
        
        # Find related technologies
        for bookmark_cat in bookmark_categories:
            if bookmark_cat in tech_relationships:
                for related_tech in tech_relationships[bookmark_cat]:
                    if related_tech in context_categories:
                        related.append(related_tech)
        
        # Find reverse relationships
        for context_cat in context_categories:
            if context_cat in tech_relationships:
                for related_tech in tech_relationships[context_cat]:
                    if related_tech in bookmark_categories:
                        related.append(related_tech)
        
        # Remove duplicates and limit results
        return list(set(related))[:3]

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
            
            # BOOST USER'S OWN CONTENT
            if bookmark.get('is_user_content', False):
                score_data['total_score'] *= 1.5  # 50% boost for user's own content
                score_data['confidence'] = min(1.0, score_data['confidence'] * 1.2)
            
            # Format for frontend compatibility
            formatted_bookmark = {
                **bookmark,
                'score': score_data['total_score'],  # Frontend expects 'score'
                'match_score': score_data['total_score'],  # Alternative field name
                'reason': score_data['reason'],  # Frontend expects 'reason'
                'confidence': score_data['confidence'],  # Frontend expects 'confidence'
                'technologies': [tech['category'] for tech in score_data['bookmark_analysis']['technologies']],  # Add technologies
                'analysis': {  # Frontend expects 'analysis' object
                    'algorithm_used': 'UnifiedRecommendationEngine',
                    'text_similarity': score_data['scores'].get('semantic_similarity', 0),
                    'interest_similarity': score_data['scores'].get('content_relevance', 0),
                    'tech_match': score_data['scores'].get('tech_match', 0),
                    'difficulty_alignment': score_data['scores'].get('difficulty_alignment', 0),
                    'intent_alignment': score_data['scores'].get('intent_alignment', 0),
                    'total_score': score_data['total_score']
                },
                'score_data': score_data  # Keep original data for internal use
            }
            
            scored_bookmarks.append(formatted_bookmark)
        
        # Sort by total score (descending)
        scored_bookmarks.sort(key=lambda x: x['score'], reverse=True)
        
        # Apply technology-based boosting for better relevance
        context_primary_techs = []
        if 'technologies' in context:
            context_primary_techs = [tech['category'] if isinstance(tech, dict) else tech 
                                   for tech in context['technologies']]
        
        # Apply boosting and penalties
        for bookmark in scored_bookmarks:
            bookmark_techs = bookmark.get('technologies', [])
            
            # Boost for technology overlap
            tech_overlap = False
            if context_primary_techs and bookmark_techs:
                overlap = set(context_primary_techs).intersection(set(bookmark_techs))
                if overlap:
                    tech_overlap = True
                    # Boost based on overlap strength
                    overlap_ratio = len(overlap) / len(context_primary_techs)
                    bookmark['score'] *= (1 + overlap_ratio * 0.3)  # Up to 30% boost
                    bookmark['match_score'] *= (1 + overlap_ratio * 0.3)
            
            # Apply penalty for major technology mismatches
            if context_primary_techs:
                # Check for major language mismatches
                major_languages = {'java', 'javascript', 'python', 'c++', 'c#', 'go', 'rust'}
                context_languages = set(context_primary_techs).intersection(major_languages)
                bookmark_languages = set(bookmark_techs).intersection(major_languages)
                
                if context_languages and bookmark_languages and not context_languages.intersection(bookmark_languages):
                    # Major language mismatch - apply significant penalty
                    bookmark['score'] *= 0.4  # Stronger penalty
                    bookmark['match_score'] *= 0.4
                
                # Apply penalty for no technology overlap at all
                if not tech_overlap and context_primary_techs:
                    bookmark['score'] *= 0.7  # Penalty for no tech overlap
                    bookmark['match_score'] *= 0.7
        
        # Re-sort after boosting
        scored_bookmarks.sort(key=lambda x: x['score'], reverse=True)
        
        # Apply stricter quality filter - only show high-quality recommendations
        relevant_bookmarks = [
            b for b in scored_bookmarks 
            if b['score'] >= 35  # Increased from 25 to 35 for stricter filtering
        ]
        
        # If we don't have enough high-quality recommendations, include some medium quality
        if len(relevant_bookmarks) < 3:
            medium_quality = [
                b for b in scored_bookmarks 
                if b['score'] >= 25 and b not in relevant_bookmarks
            ]
            relevant_bookmarks.extend(medium_quality[:2])  # Add max 2 medium quality
        
        # Return top recommendations
        return relevant_bookmarks[:max_recommendations]

    def get_diverse_recommendations(self, bookmarks: List[Dict], context: Dict, max_recommendations: int = 10) -> List[Dict]:
        """
        Get truly diverse recommendations using enhanced diversity engine
        """
        try:
            # Use enhanced diversity engine for better diversity
            from enhanced_diversity_engine import enhanced_diversity_engine
            
            # Get base recommendations first
            base_recommendations = self.get_recommendations(bookmarks, context, max_recommendations * 3)
            
            if not base_recommendations:
                return []
            
            # Convert to format expected by diversity engine
            candidates = []
            for rec in base_recommendations:
                bookmark_data = {
                    'id': rec.get('id'),
                    'title': rec.get('title', ''),
                    'notes': rec.get('notes', ''),
                    'extracted_text': rec.get('extracted_text', ''),
                    'technology_tags': rec.get('technology_tags', []),
                    'content_type': rec.get('score_data', {}).get('bookmark_analysis', {}).get('content_type', 'general'),
                    'difficulty': rec.get('score_data', {}).get('bookmark_analysis', {}).get('difficulty', 'intermediate'),
                    'score': rec.get('score_data', {}).get('total_score', 0.0)
                }
                candidates.append(bookmark_data)
            
            # Get diverse recommendations using enhanced engine
            diverse_recommendations = enhanced_diversity_engine.get_diverse_recommendations(
                candidates, context, max_recommendations
            )
            
            # Convert back to original format and add diversity metadata
            result = []
            for diverse_rec in diverse_recommendations:
                # Find original recommendation
                original_rec = next((rec for rec in base_recommendations if rec.get('id') == diverse_rec.get('id')), None)
                if original_rec:
                    # Add diversity metadata
                    original_rec['diversity_metadata'] = diverse_rec.get('diversity_metadata', {})
                    result.append(original_rec)
            
            return result
            
        except Exception as e:
            # Fallback to basic diversity
            logger.warning(f"Error in enhanced diversity selection: {e}, falling back to basic diversity")
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