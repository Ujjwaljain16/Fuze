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
        Calculate comprehensive recommendation score with intent-aware enhancements
        """
        try:
            # Get intent analysis if available
            intent_analysis = context.get('intent_analysis', {})
            scoring_weights = intent_analysis.get('scoring_weights', {})
            
            # Initialize scores
            scores = {}
            
            # 1. Semantic Similarity (20% weight)
            semantic_score = self._calculate_semantic_similarity(bookmark, context)
            scores['semantic_similarity'] = semantic_score
            
            # 2. Technology Match (25% weight - enhanced with intent)
            tech_match_score = self._calculate_enhanced_tech_match(bookmark, context, intent_analysis)
            scores['tech_match'] = tech_match_score
            
            # 3. Content Relevance (20% weight - enhanced with intent)
            content_relevance_score = self._calculate_enhanced_content_relevance(bookmark, context, intent_analysis)
            scores['content_relevance'] = content_relevance_score
            
            # 4. Difficulty Alignment (15% weight - enhanced with intent)
            difficulty_score = self._calculate_enhanced_difficulty_alignment(bookmark, context, intent_analysis)
            scores['difficulty_alignment'] = difficulty_score
            
            # 5. Intent Alignment (20% weight - new intent-aware scoring)
            intent_score = self._calculate_intent_alignment(bookmark, context, intent_analysis)
            scores['intent_alignment'] = intent_score
            
            # Calculate weighted total score
            weights = {
                'semantic_similarity': 0.20,
                'tech_match': scoring_weights.get('technology_match', 0.25),
                'content_relevance': scoring_weights.get('content_type_match', 0.20),
                'difficulty_alignment': scoring_weights.get('difficulty_alignment', 0.15),
                'intent_alignment': scoring_weights.get('learning_stage_alignment', 0.20)
            }
            
            # Normalize weights to sum to 1.0
            total_weight = sum(weights.values())
            normalized_weights = {k: v / total_weight for k, v in weights.items()}
            
            total_score = sum(scores[k] * normalized_weights[k] for k in scores.keys())
            
            # Apply urgency boost if available
            if intent_analysis.get('urgency_level') == 'high':
                urgency_boost = scoring_weights.get('urgency_boost', 0.1)
                total_score *= (1 + urgency_boost)
            
            # Calculate confidence
            confidence = self._calculate_confidence(scores, total_score)
            
            # Generate reason
            reason = self._generate_enhanced_reason(bookmark, context, scores, intent_analysis)
            
            return {
                'scores': scores,
                'total_score': min(100, total_score * 100),  # Scale to 0-100
                'confidence': confidence,
                'reason': reason,
                'bookmark_analysis': self._analyze_bookmark(bookmark),
                'intent_alignment': intent_score
            }
            
        except Exception as e:
            print(f"Error calculating recommendation score: {e}")
            return {
                'scores': {'error': 0},
                'total_score': 0,
                'confidence': 0,
                'reason': 'Error calculating score',
                'bookmark_analysis': {},
                'intent_alignment': 0
            }
    
    def _calculate_enhanced_tech_match(self, bookmark: Dict, context: Dict, intent_analysis: Dict) -> float:
        """Calculate enhanced technology match with intent awareness"""
        try:
            # Get technologies from both bookmark and context
            bookmark_techs = bookmark.get('technologies', [])
            context_techs = context.get('technologies', [])
            
            if not context_techs or not bookmark_techs:
                return 0.5
            
            # Convert to sets for comparison
            if isinstance(bookmark_techs, str):
                bookmark_techs = [tech.strip().lower() for tech in bookmark_techs.split(',') if tech.strip()]
            if isinstance(context_techs, str):
                context_techs = [tech.strip().lower() for tech in context_techs.split(',') if tech.strip()]
            
            # Calculate exact matches
            exact_matches = set(bookmark_techs).intersection(set(context_techs))
            
            # Calculate partial matches (for technology variations)
            partial_matches = 0
            for context_tech in context_techs:
                for bookmark_tech in bookmark_techs:
                    if (context_tech in bookmark_tech or bookmark_tech in context_tech) and context_tech != bookmark_tech:
                        partial_matches += 0.5
            
            # Calculate technology overlap score
            if context_techs:
                exact_score = len(exact_matches) / len(context_techs)
                partial_score = min(partial_matches / len(context_techs), 0.3)  # Cap partial matches
                tech_score = exact_score + partial_score
            else:
                tech_score = 0.5
            
            # Apply intent-based boosting
            if intent_analysis:
                primary_goal = intent_analysis.get('primary_goal', '')
                if primary_goal in ['build', 'implement', 'optimize']:
                    # Boost for implementation-focused intents
                    tech_score *= 1.2
                elif primary_goal == 'learn':
                    # Boost for learning-focused intents
                    tech_score *= 1.1
            
            return min(1.0, tech_score)
            
        except Exception as e:
            print(f"Error in enhanced tech match: {e}")
            return 0.5
    
    def _calculate_enhanced_content_relevance(self, bookmark: Dict, context: Dict, intent_analysis: Dict) -> float:
        """Calculate enhanced content relevance with intent awareness"""
        try:
            # Get content type from bookmark analysis
            bookmark_analysis = self._analyze_bookmark(bookmark)
            bookmark_content_type = bookmark_analysis.get('content_type', 'general')
            
            # Determine needed content type based on intent
            needed_content_type = self._determine_needed_content_type(intent_analysis)
            
            # Calculate content type match
            if needed_content_type == bookmark_content_type:
                content_type_score = 1.0
            elif needed_content_type in ['general', 'mixed'] or bookmark_content_type in ['general', 'mixed']:
                content_type_score = 0.7
            else:
                content_type_score = 0.3
            
            # Apply intent-based adjustments
            if intent_analysis:
                time_constraint = intent_analysis.get('time_constraint', '')
                if time_constraint == 'quick_tutorial' and bookmark_content_type == 'tutorial':
                    content_type_score *= 1.2
                elif time_constraint == 'deep_dive' and bookmark_content_type in ['documentation', 'course']:
                    content_type_score *= 1.2
                elif time_constraint == 'reference' and bookmark_content_type == 'documentation':
                    content_type_score *= 1.2
            
            return min(1.0, content_type_score)
            
        except Exception as e:
            print(f"Error in enhanced content relevance: {e}")
            return 0.5
    
    def _calculate_enhanced_difficulty_alignment(self, bookmark: Dict, context: Dict, intent_analysis: Dict) -> float:
        """Calculate enhanced difficulty alignment with intent awareness"""
        try:
            # Get difficulty levels
            bookmark_analysis = self._analyze_bookmark(bookmark)
            bookmark_difficulty = bookmark_analysis.get('difficulty', 'intermediate')
            user_learning_stage = intent_analysis.get('learning_stage', 'intermediate') if intent_analysis else 'intermediate'
            
            # Calculate difficulty alignment
            difficulty_mapping = {
                'beginner': 1,
                'intermediate': 2,
                'advanced': 3
            }
            
            bookmark_level = difficulty_mapping.get(bookmark_difficulty, 2)
            user_level = difficulty_mapping.get(user_learning_stage, 2)
            
            # Perfect alignment
            if bookmark_level == user_level:
                difficulty_score = 1.0
            # Slightly off (adjacent levels)
            elif abs(bookmark_level - user_level) == 1:
                difficulty_score = 0.8
            # Far off (skip one level)
            elif abs(bookmark_level - user_level) == 2:
                difficulty_score = 0.4
            else:
                difficulty_score = 0.2
            
            # Apply intent-based adjustments
            if intent_analysis:
                primary_goal = intent_analysis.get('primary_goal', '')
                if primary_goal == 'learn':
                    # For learning, prefer slightly challenging content
                    if bookmark_level == user_level + 1:
                        difficulty_score *= 1.1
                    elif bookmark_level == user_level - 1:
                        difficulty_score *= 0.9
            
            return min(1.0, difficulty_score)
            
        except Exception as e:
            print(f"Error in enhanced difficulty alignment: {e}")
            return 0.5
    
    def _calculate_intent_alignment(self, bookmark: Dict, context: Dict, intent_analysis: Dict) -> float:
        """Calculate intent alignment score - new intent-aware scoring"""
        try:
            if not intent_analysis:
                return 0.5
            
            intent_score = 0.0
            factors = 0
            
            # 1. Project type alignment
            if intent_analysis.get('project_type'):
                bookmark_analysis = self._analyze_bookmark(bookmark)
                bookmark_content = f"{bookmark.get('title', '')} {bookmark.get('extracted_text', '')}".lower()
                
                project_type = intent_analysis['project_type']
                if project_type in ['web_app', 'mobile_app', 'api', 'data_science']:
                    # Check if content mentions relevant project types
                    if any(tech in bookmark_content for tech in [project_type, 'web', 'mobile', 'api', 'data']):
                        intent_score += 1.0
                    else:
                        intent_score += 0.3
                factors += 1
            
            # 2. Learning stage alignment
            if intent_analysis.get('learning_stage'):
                bookmark_analysis = self._analyze_bookmark(bookmark)
                bookmark_difficulty = bookmark_analysis.get('difficulty', 'intermediate')
                
                if intent_analysis['learning_stage'] == bookmark_difficulty:
                    intent_score += 1.0
                elif abs(self._difficulty_to_number(intent_analysis['learning_stage']) - 
                        self._difficulty_to_number(bookmark_difficulty)) == 1:
                    intent_score += 0.7
                else:
                    intent_score += 0.3
                factors += 1
            
            # 3. Focus areas alignment
            if intent_analysis.get('focus_areas'):
                bookmark_content = f"{bookmark.get('title', '')} {bookmark.get('extracted_text', '')}".lower()
                focus_areas = intent_analysis['focus_areas']
                
                focus_matches = sum(1 for area in focus_areas if area.lower() in bookmark_content)
                if focus_areas:
                    intent_score += (focus_matches / len(focus_areas))
                factors += 1
            
            # 4. Time constraint alignment
            if intent_analysis.get('time_constraint'):
                bookmark_analysis = self._analyze_bookmark(bookmark)
                bookmark_content_type = bookmark_analysis.get('content_type', 'general')
                
                time_constraint = intent_analysis['time_constraint']
                if time_constraint == 'quick_tutorial' and bookmark_content_type == 'tutorial':
                    intent_score += 1.0
                elif time_constraint == 'deep_dive' and bookmark_content_type in ['documentation', 'course']:
                    intent_score += 1.0
                elif time_constraint == 'reference' and bookmark_content_type == 'documentation':
                    intent_score += 1.0
                else:
                    intent_score += 0.5
                factors += 1
            
            # Return average score
            return intent_score / factors if factors > 0 else 0.5
            
        except Exception as e:
            print(f"Error in intent alignment: {e}")
            return 0.5
    
    def _difficulty_to_number(self, difficulty: str) -> int:
        """Convert difficulty string to number for comparison"""
        difficulty_mapping = {
            'beginner': 1,
            'intermediate': 2,
            'advanced': 3
        }
        return difficulty_mapping.get(difficulty, 2)
    
    def _determine_needed_content_type(self, intent_analysis: Dict) -> str:
        """Determine needed content type based on intent analysis"""
        if not intent_analysis:
            return 'general'
        
        time_constraint = intent_analysis.get('time_constraint', '')
        primary_goal = intent_analysis.get('primary_goal', '')
        
        if time_constraint == 'quick_tutorial':
            return 'tutorial'
        elif time_constraint == 'deep_dive':
            return 'documentation'
        elif time_constraint == 'reference':
            return 'documentation'
        elif primary_goal == 'learn':
            return 'tutorial'
        elif primary_goal == 'build':
            return 'example'
        else:
            return 'general'

    def _calculate_semantic_similarity(self, bookmark: Dict, context: Dict) -> float:
        """Calculate semantic similarity using embeddings"""
        try:
            bookmark_text = f"{bookmark.get('title', '')} {bookmark.get('notes', '')} {bookmark.get('extracted_text', '')}"
            context_text = context.get('full_text', '').lower()
            
            bookmark_emb = self.embedding_model.encode([bookmark_text])[0]
            context_emb = self.embedding_model.encode([context_text])[0]
            
            similarity = np.dot(bookmark_emb, context_emb) / (np.linalg.norm(bookmark_emb) * np.linalg.norm(context_emb))
            
            # Convert to 0-20 scale
            return min(20, similarity * 20)
        except:
            return 10  # Neutral score if embedding fails

    def _generate_enhanced_reason(self, bookmark: Dict, context: Dict, scores: Dict, intent_analysis: Dict) -> str:
        """Generate enhanced reason with intent awareness"""
        try:
            reasons = []
            
            # Technology match explanation
            tech_score = scores.get('tech_match', 0)
            if tech_score > 0.7:
                tech_explanation = self._get_tech_explanation(bookmark, context)
                if tech_explanation:
                    reasons.append(tech_explanation)
            
            # Intent-based explanation
            if intent_analysis:
                intent_explanation = self._get_intent_explanation(context, self._analyze_bookmark(bookmark))
                if intent_explanation:
                    reasons.append(intent_explanation)
            
            # Content type benefit
            content_type_benefit = self._get_content_type_benefit(self._analyze_bookmark(bookmark), context)
            if content_type_benefit:
                reasons.append(content_type_benefit)
            
            # Difficulty alignment note
            difficulty_note = self._get_difficulty_note(self._analyze_bookmark(bookmark), context)
            if difficulty_note:
                reasons.append(difficulty_note)
            
            # Learning objective note
            learning_note = self._get_learning_objective_note(self._analyze_bookmark(bookmark), context)
            if learning_note:
                reasons.append(learning_note)
            
            # Relevance strength
            total_score = sum(scores.values()) / len(scores) if scores else 0
            relevance_strength = self._get_relevance_strength(total_score)
            if relevance_strength:
                reasons.append(relevance_strength)
            
            # Combine reasons
            if reasons:
                return " ".join(reasons)
            else:
                return "This content is relevant to your project."
                
        except Exception as e:
            print(f"Error generating enhanced reason: {e}")
            return "This content matches your project requirements."
    
    def _get_intent_explanation(self, context: Dict, bookmark_analysis: Dict) -> str:
        """Get intent-based explanation with enhanced context"""
        try:
            intent_analysis = context.get('intent_analysis', {})
            if not intent_analysis:
                return ""
            
            primary_goal = intent_analysis.get('primary_goal', '')
            project_type = intent_analysis.get('project_type', '')
            learning_stage = intent_analysis.get('learning_stage', '')
            
            bookmark_type = bookmark_analysis.get('content_type', 'general')
            
            # Enhanced intent mapping
            intent_mapping = {
                'learn': {
                    'tutorial': f"Provides structured learning path for {project_type or 'your project'}",
                    'documentation': f"Offers comprehensive reference for {project_type or 'your project'}",
                    'example': f"Demonstrates practical examples of {project_type or 'your project'}",
                    'best_practice': f"Teaches best practices for {project_type or 'your project'}",
                    'general': f"Helps you learn about {project_type or 'your project'}"
                },
                'build': {
                    'tutorial': f"Guides you through building {project_type or 'your project'}",
                    'documentation': f"Provides implementation details for {project_type or 'your project'}",
                    'example': f"Shows how to build {project_type or 'your project'}",
                    'best_practice': f"Demonstrates proper implementation of {project_type or 'your project'}",
                    'general': f"Helps you build {project_type or 'your project'}"
                },
                'optimize': {
                    'tutorial': f"Teaches optimization techniques for {project_type or 'your project'}",
                    'documentation': f"Provides optimization guidelines for {project_type or 'your project'}",
                    'example': f"Demonstrates optimized approaches to {project_type or 'your project'}",
                    'best_practice': f"Shows performance best practices for {project_type or 'your project'}",
                    'general': f"Helps you optimize {project_type or 'your project'}"
                }
            }
            
            intent_explanations = intent_mapping.get(primary_goal, {})
            explanation = intent_explanations.get(bookmark_type, intent_explanations.get('general', ''))
            
            if explanation:
                # Add learning stage context
                if learning_stage and learning_stage != 'intermediate':
                    explanation += f" (suitable for {learning_stage} level)"
                
                return explanation
            
            return ""
            
        except Exception as e:
            print(f"Error in intent explanation: {e}")
            return ""
    
    def _get_learning_objective_note(self, bookmark_analysis: Dict, context: Dict) -> str:
        """Get learning objective alignment note with intent awareness"""
        try:
            intent_analysis = context.get('intent_analysis', {})
            if not intent_analysis:
                return ""
            
            bookmark_objectives = bookmark_analysis.get('learning_objectives', [])
            focus_areas = intent_analysis.get('focus_areas', [])
            
            if not bookmark_objectives or not focus_areas:
                return ""
            
            # Find overlapping focus areas
            overlap = set(bookmark_objectives).intersection(set(focus_areas))
            
            if overlap:
                objectives = ", ".join(list(overlap)[:2])  # Limit to 2 for readability
                return f"Specifically addresses your learning goals: {objectives}."
            
            return ""
            
        except Exception as e:
            print(f"Error in learning objective note: {e}")
            return ""

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
        """Get difficulty alignment explanation with intent awareness"""
        try:
            intent_analysis = context.get('intent_analysis', {})
            bookmark_diff = bookmark_analysis.get('difficulty', 'intermediate')
            context_diff = context.get('difficulty', 'intermediate')
            
            # Use intent analysis if available
            if intent_analysis:
                user_level = intent_analysis.get('learning_stage', context_diff)
                if bookmark_diff == user_level:
                    return f"Difficulty level ({bookmark_diff}) matches your skill level."
                elif bookmark_diff == 'beginner' and user_level in ['intermediate', 'advanced']:
                    return "Provides foundational knowledge that builds up to your project complexity."
                elif bookmark_diff == 'advanced' and user_level in ['beginner', 'intermediate']:
                    return "Offers advanced insights that will help you grow beyond current requirements."
                else:
                    return f"Appropriate difficulty level ({bookmark_diff}) for your needs."
            else:
                # Fallback to context-based difficulty
                if bookmark_diff == context_diff:
                    return f"Difficulty level ({bookmark_diff}) matches your project requirements."
                elif bookmark_diff == 'beginner' and context_diff in ['intermediate', 'advanced']:
                    return "Provides foundational knowledge that builds up to your project complexity."
                elif bookmark_diff == 'advanced' and context_diff in ['beginner', 'intermediate']:
                    return "Offers advanced insights that will help you grow beyond current requirements."
                else:
                    return ""
            
        except Exception as e:
            print(f"Error in difficulty note: {e}")
            return ""
    
    def _get_content_type_benefit(self, bookmark_analysis: Dict, context: Dict) -> str:
        """Get content type specific benefits with intent awareness"""
        try:
            content_type = bookmark_analysis.get('content_type', 'general')
            intent_analysis = context.get('intent_analysis', {})
            
            benefits = {
                'tutorial': "Includes step-by-step instructions and explanations.",
                'documentation': "Provides comprehensive technical reference and API details.",
                'example': "Offers practical code examples and real-world scenarios.",
                'troubleshooting': "Focuses on problem-solving and debugging techniques.",
                'best_practice': "Teaches industry standards and proven patterns.",
                'project': "Shows complete project implementation from start to finish."
            }
            
            base_benefit = benefits.get(content_type, "")
            
            # Add intent-specific context
            if intent_analysis:
                primary_goal = intent_analysis.get('primary_goal', '')
                time_constraint = intent_analysis.get('time_constraint', '')
                
                if primary_goal == 'learn' and time_constraint == 'quick_tutorial':
                    base_benefit += " Perfect for quick learning."
                elif primary_goal == 'build' and content_type == 'example':
                    base_benefit += " Ideal for implementation reference."
                elif primary_goal == 'optimize' and content_type == 'best_practice':
                    base_benefit += " Essential for performance optimization."
            
            return base_benefit
            
        except Exception as e:
            print(f"Error in content type benefit: {e}")
            return ""
    
    def _get_relevance_strength(self, total_score: float) -> str:
        """Get relevance strength indicator with intent awareness"""
        try:
            if total_score >= 0.85:
                return "This is a highly relevant resource for your needs."
            elif total_score >= 0.70:
                return "This resource is very relevant to your project."
            elif total_score >= 0.50:
                return "This content is relevant and worth considering."
            else:
                return "This may be useful as supplementary material."
                
        except Exception as e:
            print(f"Error in relevance strength: {e}")
            return "This content matches your project requirements."

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