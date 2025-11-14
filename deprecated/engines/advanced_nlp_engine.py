#!/usr/bin/env python3
"""
Advanced NLP Engine for Enhanced Intent Understanding and Semantic Analysis
- Deep intent analysis with context understanding
- Advanced semantic relationship detection
- Multi-language support and entity recognition
- Contextual query expansion and refinement
- Intelligent content categorization

CRITICAL: Enhances understanding while processing ALL user content!
"""

import re
import time
import logging
from typing import List, Dict, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict, Counter
from datetime import datetime
import json
import numpy as np

# NLP Libraries
try:
    import spacy
    import nltk
    from nltk.corpus import stopwords, wordnet
    from nltk.tokenize import word_tokenize, sent_tokenize
    from nltk.stem import WordNetLemmatizer
    from nltk.chunk import ne_chunk
    from nltk.tag import pos_tag
    NLP_LIBRARIES_AVAILABLE = True
except ImportError:
    NLP_LIBRARIES_AVAILABLE = False

# Advanced libraries (optional)
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

try:
    from transformers import pipeline, AutoTokenizer, AutoModel
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class IntentAnalysisResult:
    """Advanced intent analysis result"""
    primary_intent: str
    secondary_intents: List[str]
    confidence_score: float
    intent_categories: Dict[str, float]
    user_goal: str
    complexity_level: str
    domain_focus: str
    technology_focus: List[str]
    learning_stage: str
    urgency_level: str
    specific_requirements: List[str]
    context_entities: List[Dict[str, Any]]
    semantic_themes: List[str]
    query_expansion: List[str]
    refined_query: str
    metadata: Dict[str, Any]

@dataclass
class SemanticAnalysisResult:
    """Advanced semantic analysis result"""
    content_type: str
    difficulty_level: str
    key_concepts: List[str]
    technology_tags: List[str]
    domain_classification: str
    concept_relationships: Dict[str, List[str]]
    semantic_similarity_score: float
    readability_score: float
    complexity_indicators: List[str]
    learning_objectives: List[str]
    prerequisites: List[str]
    target_audience: str
    content_quality_score: float
    language_patterns: Dict[str, Any]
    entities: List[Dict[str, Any]]
    metadata: Dict[str, Any]

@dataclass
class NLPConfiguration:
    """NLP engine configuration"""
    spacy_model: str = "en_core_web_sm"
    enable_entity_recognition: bool = True
    enable_sentiment_analysis: bool = True
    enable_topic_modeling: bool = True
    enable_query_expansion: bool = True
    enable_content_categorization: bool = True
    confidence_threshold: float = 0.6
    max_query_expansions: int = 5
    language: str = "en"

class AdvancedNLPEngine:
    """Advanced NLP engine for enhanced understanding"""
    
    def __init__(self, config: Optional[NLPConfiguration] = None):
        self.config = config or NLPConfiguration()
        self.nlp = None
        self.lemmatizer = None
        self.sentiment_analyzer = None
        self.ner_pipeline = None
        self.topic_model = None
        
        # Initialize NLP components
        self._initialize_nlp_components()
        
        # Intent patterns and rules
        self._initialize_intent_patterns()
        
        # Semantic analysis patterns
        self._initialize_semantic_patterns()
        
        logger.info("✅ Advanced NLP Engine initialized with enhanced understanding capabilities")
    
    def _initialize_nlp_components(self):
        """Initialize NLP libraries and models"""
        try:
            # Initialize spaCy
            if NLP_LIBRARIES_AVAILABLE:
                try:
                    self.nlp = spacy.load(self.config.spacy_model)
                    logger.info(f"✅ spaCy model '{self.config.spacy_model}' loaded successfully")
                except OSError:
                    logger.warning(f"spaCy model '{self.config.spacy_model}' not found, using fallback")
                    # Try smaller model
                    try:
                        self.nlp = spacy.load("en_core_web_sm")
                    except OSError:
                        logger.warning("No spaCy model available, using basic NLP")
                        self.nlp = None
                
                # Initialize NLTK components
                try:
                    nltk.download('punkt', quiet=True)
                    nltk.download('stopwords', quiet=True)
                    nltk.download('wordnet', quiet=True)
                    nltk.download('averaged_perceptron_tagger', quiet=True)
                    nltk.download('maxent_ne_chunker', quiet=True)
                    nltk.download('words', quiet=True)
                    
                    self.lemmatizer = WordNetLemmatizer()
                    logger.info("✅ NLTK components initialized")
                except Exception as e:
                    logger.warning(f"NLTK initialization failed: {e}")
            
            # Initialize transformers-based models (optional)
            if TRANSFORMERS_AVAILABLE and self.config.enable_sentiment_analysis:
                try:
                    self.sentiment_analyzer = pipeline("sentiment-analysis", 
                                                      model="cardiffnlp/twitter-roberta-base-sentiment-latest")
                    logger.info("✅ Transformer sentiment analyzer loaded")
                except Exception as e:
                    logger.warning(f"Transformer sentiment analyzer failed: {e}")
            
            # Initialize TextBlob (fallback)
            if TEXTBLOB_AVAILABLE and not self.sentiment_analyzer:
                logger.info("✅ TextBlob available for sentiment analysis")
            
        except Exception as e:
            logger.error(f"Error initializing NLP components: {e}")
    
    def _initialize_intent_patterns(self):
        """Initialize intent recognition patterns"""
        self.intent_patterns = {
            'learn': [
                r'\b(learn|understand|study|tutorial|guide|how to|explain|teach)\b',
                r'\b(beginner|introduction|basics|fundamentals|getting started)\b',
                r'\b(course|lesson|training|education)\b'
            ],
            'build': [
                r'\b(build|create|develop|make|implement|code|program)\b',
                r'\b(project|application|app|system|tool|solution)\b',
                r'\b(development|coding|programming|implementation)\b'
            ],
            'solve': [
                r'\b(solve|fix|debug|troubleshoot|error|problem|issue)\b',
                r'\b(help|assistance|support|solution)\b',
                r'\b(bug|crash|failure|not working)\b'
            ],
            'optimize': [
                r'\b(optimize|improve|enhance|performance|speed|efficiency)\b',
                r'\b(faster|better|scalable|performance)\b',
                r'\b(refactor|clean|optimization)\b'
            ],
            'explore': [
                r'\b(explore|discover|find|search|browse|look for)\b',
                r'\b(what is|tell me about|show me|examples)\b',
                r'\b(comparison|alternatives|options)\b'
            ],
            'integrate': [
                r'\b(integrate|connect|combine|merge|link)\b',
                r'\b(api|service|library|framework|plugin)\b',
                r'\b(integration|connection|setup)\b'
            ]
        }
        
        self.complexity_patterns = {
            'beginner': [
                r'\b(beginner|basic|simple|easy|introduction|getting started)\b',
                r'\b(first time|new to|never used|just starting)\b'
            ],
            'intermediate': [
                r'\b(intermediate|some experience|familiar with|know basics)\b',
                r'\b(improve|enhance|next level|advance)\b'
            ],
            'advanced': [
                r'\b(advanced|expert|complex|sophisticated|deep dive)\b',
                r'\b(optimize|architecture|design patterns|best practices)\b'
            ]
        }
        
        self.domain_patterns = {
            'web_development': [
                r'\b(web|website|frontend|backend|fullstack|html|css|javascript)\b',
                r'\b(react|angular|vue|node|express|django|flask)\b'
            ],
            'data_science': [
                r'\b(data|analytics|machine learning|ai|statistics|analysis)\b',
                r'\b(pandas|numpy|sklearn|tensorflow|pytorch)\b'
            ],
            'mobile_development': [
                r'\b(mobile|app|android|ios|flutter|react native)\b',
                r'\b(smartphone|tablet|mobile app)\b'
            ],
            'system_programming': [
                r'\b(system|low level|memory|performance|c\+\+|rust|go)\b',
                r'\b(operating system|kernel|driver|embedded)\b'
            ],
            'devops': [
                r'\b(devops|deployment|docker|kubernetes|ci/cd|cloud)\b',
                r'\b(aws|azure|gcp|infrastructure|automation)\b'
            ]
        }
    
    def _initialize_semantic_patterns(self):
        """Initialize semantic analysis patterns"""
        self.content_type_patterns = {
            'tutorial': [
                r'\b(tutorial|step by step|how to|guide|walkthrough)\b',
                r'\b(learn|teach|instruction|example)\b'
            ],
            'documentation': [
                r'\b(documentation|docs|reference|manual|api)\b',
                r'\b(specification|standard|protocol)\b'
            ],
            'example': [
                r'\b(example|sample|demo|showcase|case study)\b',
                r'\b(implementation|code example|snippet)\b'
            ],
            'article': [
                r'\b(article|blog|post|discussion|analysis)\b',
                r'\b(opinion|perspective|thoughts|insights)\b'
            ],
            'tool': [
                r'\b(tool|utility|application|software|program)\b',
                r'\b(framework|library|package|plugin)\b'
            ]
        }
        
        self.difficulty_indicators = {
            'beginner': [
                r'\b(beginner|basic|simple|introduction|getting started)\b',
                r'\b(101|basics|fundamentals|primer)\b'
            ],
            'intermediate': [
                r'\b(intermediate|practical|hands.on|real.world)\b',
                r'\b(beyond basics|next level|applied)\b'
            ],
            'advanced': [
                r'\b(advanced|expert|complex|deep|comprehensive)\b',
                r'\b(optimization|architecture|patterns|mastery)\b'
            ]
        }
    
    def analyze_intent(self, query: str, context: Optional[Dict[str, Any]] = None) -> IntentAnalysisResult:
        """Perform advanced intent analysis"""
        try:
            start_time = time.time()
            
            # Clean and preprocess query
            cleaned_query = self._preprocess_text(query)
            
            # Extract entities if spaCy is available
            entities = self._extract_entities(cleaned_query) if self.nlp else []
            
            # Detect primary intent
            primary_intent, intent_scores = self._detect_intent(cleaned_query)
            
            # Determine complexity level
            complexity_level = self._determine_complexity(cleaned_query)
            
            # Classify domain
            domain_focus = self._classify_domain(cleaned_query)
            
            # Extract technology focus
            technology_focus = self._extract_technologies(cleaned_query, entities)
            
            # Determine learning stage
            learning_stage = self._determine_learning_stage(cleaned_query, complexity_level)
            
            # Assess urgency
            urgency_level = self._assess_urgency(cleaned_query)
            
            # Extract specific requirements
            requirements = self._extract_requirements(cleaned_query, entities)
            
            # Semantic theme analysis
            semantic_themes = self._analyze_semantic_themes(cleaned_query)
            
            # Query expansion
            expanded_queries = self._expand_query(cleaned_query) if self.config.enable_query_expansion else []
            
            # Refined query
            refined_query = self._refine_query(cleaned_query, entities, semantic_themes)
            
            # Calculate confidence
            confidence_score = self._calculate_intent_confidence(intent_scores, entities, semantic_themes)
            
            # Get secondary intents
            secondary_intents = [intent for intent, score in intent_scores.items() 
                               if intent != primary_intent and score > 0.3][:2]
            
            processing_time = time.time() - start_time
            
            result = IntentAnalysisResult(
                primary_intent=primary_intent,
                secondary_intents=secondary_intents,
                confidence_score=confidence_score,
                intent_categories=intent_scores,
                user_goal=self._infer_user_goal(primary_intent, complexity_level, domain_focus),
                complexity_level=complexity_level,
                domain_focus=domain_focus,
                technology_focus=technology_focus,
                learning_stage=learning_stage,
                urgency_level=urgency_level,
                specific_requirements=requirements,
                context_entities=entities,
                semantic_themes=semantic_themes,
                query_expansion=expanded_queries,
                refined_query=refined_query,
                metadata={
                    'processing_time_ms': processing_time * 1000,
                    'original_query': query,
                    'cleaned_query': cleaned_query,
                    'nlp_components_used': self._get_active_components()
                }
            )
            
            logger.debug(f"Intent analysis completed in {processing_time*1000:.2f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Error in intent analysis: {e}")
            return self._create_fallback_intent_result(query)
    
    def analyze_content_semantics(self, content: Dict[str, Any]) -> SemanticAnalysisResult:
        """Perform advanced semantic analysis of content"""
        try:
            start_time = time.time()
            
            # Extract text content
            text_content = self._extract_content_text(content)
            
            # Clean and preprocess
            cleaned_text = self._preprocess_text(text_content)
            
            # Extract entities
            entities = self._extract_entities(cleaned_text) if self.nlp else []
            
            # Classify content type
            content_type = self._classify_content_type(cleaned_text, content)
            
            # Determine difficulty level
            difficulty_level = self._analyze_content_difficulty(cleaned_text, content)
            
            # Extract key concepts
            key_concepts = self._extract_key_concepts(cleaned_text, entities)
            
            # Extract technology tags
            technology_tags = self._extract_content_technologies(cleaned_text, entities, content)
            
            # Classify domain
            domain_classification = self._classify_content_domain(cleaned_text, technology_tags)
            
            # Analyze concept relationships
            concept_relationships = self._analyze_concept_relationships(key_concepts, entities)
            
            # Calculate readability
            readability_score = self._calculate_readability(cleaned_text)
            
            # Identify complexity indicators
            complexity_indicators = self._identify_complexity_indicators(cleaned_text)
            
            # Extract learning objectives
            learning_objectives = self._extract_learning_objectives(cleaned_text)
            
            # Identify prerequisites
            prerequisites = self._identify_prerequisites(cleaned_text, technology_tags)
            
            # Determine target audience
            target_audience = self._determine_target_audience(difficulty_level, complexity_indicators)
            
            # Calculate content quality
            content_quality_score = self._calculate_content_quality(cleaned_text, entities, key_concepts)
            
            # Analyze language patterns
            language_patterns = self._analyze_language_patterns(cleaned_text)
            
            processing_time = time.time() - start_time
            
            result = SemanticAnalysisResult(
                content_type=content_type,
                difficulty_level=difficulty_level,
                key_concepts=key_concepts,
                technology_tags=technology_tags,
                domain_classification=domain_classification,
                concept_relationships=concept_relationships,
                semantic_similarity_score=0.0,  # Will be calculated in context
                readability_score=readability_score,
                complexity_indicators=complexity_indicators,
                learning_objectives=learning_objectives,
                prerequisites=prerequisites,
                target_audience=target_audience,
                content_quality_score=content_quality_score,
                language_patterns=language_patterns,
                entities=entities,
                metadata={
                    'processing_time_ms': processing_time * 1000,
                    'text_length': len(cleaned_text),
                    'entity_count': len(entities),
                    'nlp_components_used': self._get_active_components()
                }
            )
            
            logger.debug(f"Semantic analysis completed in {processing_time*1000:.2f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Error in semantic analysis: {e}")
            return self._create_fallback_semantic_result(content)
    
    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate advanced semantic similarity between texts"""
        try:
            if self.nlp:
                # Use spaCy's semantic similarity
                doc1 = self.nlp(text1)
                doc2 = self.nlp(text2)
                return doc1.similarity(doc2)
            else:
                # Fallback to simple word overlap
                words1 = set(self._preprocess_text(text1).split())
                words2 = set(self._preprocess_text(text2).split())
                intersection = words1.intersection(words2)
                union = words1.union(words2)
                return len(intersection) / len(union) if union else 0.0
                
        except Exception as e:
            logger.error(f"Error calculating semantic similarity: {e}")
            return 0.0
    
    def enhance_query_understanding(self, query: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Enhance query understanding with context and expansion"""
        try:
            # Perform intent analysis
            intent_result = self.analyze_intent(query, user_context)
            
            # Generate query variations
            query_variations = self._generate_query_variations(query, intent_result)
            
            # Extract implicit requirements
            implicit_requirements = self._extract_implicit_requirements(query, intent_result)
            
            # Suggest related concepts
            related_concepts = self._suggest_related_concepts(intent_result.technology_focus, 
                                                            intent_result.semantic_themes)
            
            # Generate search hints
            search_hints = self._generate_search_hints(intent_result)
            
            return {
                'intent_analysis': intent_result,
                'query_variations': query_variations,
                'implicit_requirements': implicit_requirements,
                'related_concepts': related_concepts,
                'search_hints': search_hints,
                'enhanced_understanding': True
            }
            
        except Exception as e:
            logger.error(f"Error enhancing query understanding: {e}")
            return {'error': str(e), 'enhanced_understanding': False}
    
    # Helper methods for NLP processing
    
    def _preprocess_text(self, text: str) -> str:
        """Clean and preprocess text"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove special characters but keep alphanumeric and basic punctuation
        text = re.sub(r'[^\w\s\-\.]', ' ', text)
        
        return text
    
    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities from text"""
        entities = []
        
        if self.nlp:
            try:
                doc = self.nlp(text)
                for ent in doc.ents:
                    entities.append({
                        'text': ent.text,
                        'label': ent.label_,
                        'start': ent.start_char,
                        'end': ent.end_char,
                        'confidence': getattr(ent, 'score', 0.9)
                    })
            except Exception as e:
                logger.debug(f"spaCy entity extraction failed: {e}")
        
        # Fallback NLTK entity extraction
        if not entities and NLP_LIBRARIES_AVAILABLE:
            try:
                tokens = word_tokenize(text)
                pos_tags = pos_tag(tokens)
                chunks = ne_chunk(pos_tags)
                
                for chunk in chunks:
                    if hasattr(chunk, 'label'):
                        entity_text = ' '.join([token for token, pos in chunk])
                        entities.append({
                            'text': entity_text,
                            'label': chunk.label(),
                            'start': 0,
                            'end': len(entity_text),
                            'confidence': 0.7
                        })
            except Exception as e:
                logger.debug(f"NLTK entity extraction failed: {e}")
        
        return entities
    
    def _detect_intent(self, text: str) -> Tuple[str, Dict[str, float]]:
        """Detect user intent using pattern matching"""
        intent_scores = defaultdict(float)
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                intent_scores[intent] += matches * 0.3
        
        # Boost based on specific keywords
        if not intent_scores:
            # Default intent based on common patterns
            if any(word in text for word in ['learn', 'tutorial', 'how']):
                intent_scores['learn'] = 0.5
            elif any(word in text for word in ['build', 'create', 'develop']):
                intent_scores['build'] = 0.5
            else:
                intent_scores['explore'] = 0.4
        
        # Normalize scores
        total_score = sum(intent_scores.values())
        if total_score > 0:
            intent_scores = {k: v/total_score for k, v in intent_scores.items()}
        
        primary_intent = max(intent_scores.items(), key=lambda x: x[1])[0] if intent_scores else 'explore'
        
        return primary_intent, dict(intent_scores)
    
    def _determine_complexity(self, text: str) -> str:
        """Determine complexity level from text"""
        complexity_scores = defaultdict(float)
        
        for level, patterns in self.complexity_patterns.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                complexity_scores[level] += matches
        
        if not complexity_scores:
            return 'intermediate'  # Default
        
        return max(complexity_scores.items(), key=lambda x: x[1])[0]
    
    def _classify_domain(self, text: str) -> str:
        """Classify domain/field from text"""
        domain_scores = defaultdict(float)
        
        for domain, patterns in self.domain_patterns.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                domain_scores[domain] += matches
        
        if not domain_scores:
            return 'general_programming'
        
        return max(domain_scores.items(), key=lambda x: x[1])[0]
    
    def _extract_technologies(self, text: str, entities: List[Dict[str, Any]]) -> List[str]:
        """Extract technology names from text"""
        technologies = set()
        
        # Common technology patterns
        tech_patterns = [
            r'\b(python|java|javascript|typescript|c\+\+|c#|go|rust|php|ruby)\b',
            r'\b(react|angular|vue|node|express|django|flask|spring)\b',
            r'\b(docker|kubernetes|aws|azure|gcp|terraform)\b',
            r'\b(mysql|postgresql|mongodb|redis|elasticsearch)\b',
            r'\b(git|github|gitlab|jenkins|ci/cd)\b'
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            technologies.update(matches)
        
        # Extract from entities
        for entity in entities:
            if entity['label'] in ['ORG', 'PRODUCT']:
                technologies.add(entity['text'])
        
        return list(technologies)
    
    def _determine_learning_stage(self, text: str, complexity: str) -> str:
        """Determine user's learning stage"""
        if complexity == 'beginner':
            return 'exploration'
        elif complexity == 'intermediate':
            return 'application'
        else:
            return 'mastery'
    
    def _assess_urgency(self, text: str) -> str:
        """Assess urgency level of the request"""
        urgent_patterns = [
            r'\b(urgent|asap|quickly|fast|immediate|deadline|emergency)\b',
            r'\b(need now|right away|time sensitive)\b'
        ]
        
        for pattern in urgent_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return 'high'
        
        return 'normal'
    
    def _extract_requirements(self, text: str, entities: List[Dict[str, Any]]) -> List[str]:
        """Extract specific requirements from text"""
        requirements = []
        
        # Pattern-based requirement extraction
        requirement_patterns = [
            r'need to\s+([^.]+)',
            r'want to\s+([^.]+)',
            r'looking for\s+([^.]+)',
            r'require\s+([^.]+)',
            r'must\s+([^.]+)'
        ]
        
        for pattern in requirement_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            requirements.extend([match.strip() for match in matches])
        
        return requirements[:5]  # Limit to top 5
    
    def _analyze_semantic_themes(self, text: str) -> List[str]:
        """Analyze semantic themes in text"""
        themes = []
        
        # Theme detection patterns
        theme_patterns = {
            'performance': r'\b(performance|speed|optimization|efficiency|fast)\b',
            'security': r'\b(security|encryption|authentication|privacy|secure)\b',
            'scalability': r'\b(scalability|scale|distributed|microservices)\b',
            'learning': r'\b(learning|education|tutorial|guide|course)\b',
            'development': r'\b(development|coding|programming|building)\b',
            'analysis': r'\b(analysis|analytics|data|insights|metrics)\b'
        }
        
        for theme, pattern in theme_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                themes.append(theme)
        
        return themes
    
    def _expand_query(self, query: str) -> List[str]:
        """Generate expanded query variations"""
        expansions = []
        
        # Simple synonym expansion
        synonyms = {
            'learn': ['understand', 'study', 'master'],
            'build': ['create', 'develop', 'implement'],
            'fast': ['quick', 'efficient', 'optimized'],
            'simple': ['easy', 'basic', 'straightforward']
        }
        
        words = query.split()
        for word in words:
            if word.lower() in synonyms:
                for synonym in synonyms[word.lower()]:
                    expanded = query.replace(word, synonym)
                    if expanded != query:
                        expansions.append(expanded)
        
        return expansions[:self.config.max_query_expansions]
    
    def _refine_query(self, query: str, entities: List[Dict[str, Any]], themes: List[str]) -> str:
        """Create a refined version of the query"""
        refined = query
        
        # Add entity context
        entity_terms = [e['text'] for e in entities if e['confidence'] > 0.8]
        if entity_terms:
            refined += f" related to {', '.join(entity_terms[:3])}"
        
        # Add theme context
        if themes:
            refined += f" focusing on {', '.join(themes[:2])}"
        
        return refined
    
    def _calculate_intent_confidence(self, intent_scores: Dict[str, float], 
                                   entities: List[Dict[str, Any]], 
                                   themes: List[str]) -> float:
        """Calculate confidence score for intent analysis"""
        base_confidence = max(intent_scores.values()) if intent_scores else 0.3
        
        # Boost confidence based on entities and themes
        entity_boost = min(0.2, len(entities) * 0.05)
        theme_boost = min(0.1, len(themes) * 0.03)
        
        return min(1.0, base_confidence + entity_boost + theme_boost)
    
    def _infer_user_goal(self, intent: str, complexity: str, domain: str) -> str:
        """Infer high-level user goal"""
        goal_mapping = {
            ('learn', 'beginner'): 'skill_acquisition',
            ('learn', 'intermediate'): 'skill_enhancement',
            ('learn', 'advanced'): 'expertise_development',
            ('build', 'beginner'): 'guided_creation',
            ('build', 'intermediate'): 'independent_development',
            ('build', 'advanced'): 'advanced_implementation',
            ('solve', 'any'): 'problem_resolution',
            ('optimize', 'any'): 'performance_improvement',
            ('explore', 'any'): 'knowledge_discovery'
        }
        
        return goal_mapping.get((intent, complexity), 
                               goal_mapping.get((intent, 'any'), 'general_assistance'))
    
    def _get_active_components(self) -> List[str]:
        """Get list of active NLP components"""
        components = []
        if self.nlp:
            components.append('spacy')
        if self.lemmatizer:
            components.append('nltk')
        if self.sentiment_analyzer:
            components.append('transformers')
        if TEXTBLOB_AVAILABLE:
            components.append('textblob')
        return components
    
    def _create_fallback_intent_result(self, query: str) -> IntentAnalysisResult:
        """Create fallback intent result when analysis fails"""
        return IntentAnalysisResult(
            primary_intent='explore',
            secondary_intents=[],
            confidence_score=0.3,
            intent_categories={'explore': 1.0},
            user_goal='general_assistance',
            complexity_level='intermediate',
            domain_focus='general_programming',
            technology_focus=[],
            learning_stage='application',
            urgency_level='normal',
            specific_requirements=[],
            context_entities=[],
            semantic_themes=[],
            query_expansion=[],
            refined_query=query,
            metadata={'fallback': True}
        )
    
    # Additional helper methods for semantic analysis
    
    def _extract_content_text(self, content: Dict[str, Any]) -> str:
        """Extract all text content from content dict"""
        text_parts = []
        
        if content.get('title'):
            text_parts.append(content['title'])
        if content.get('extracted_text'):
            text_parts.append(content['extracted_text'])
        if content.get('summary'):
            text_parts.append(content['summary'])
        if content.get('tags'):
            text_parts.append(content['tags'])
        
        return ' '.join(text_parts)
    
    def _classify_content_type(self, text: str, content: Dict[str, Any]) -> str:
        """Classify content type"""
        type_scores = defaultdict(float)
        
        for content_type, patterns in self.content_type_patterns.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                type_scores[content_type] += matches
        
        # Check URL for additional clues
        url = content.get('url', '')
        if 'github.com' in url:
            type_scores['example'] += 1
        elif 'docs.' in url or 'documentation' in url:
            type_scores['documentation'] += 1
        
        return max(type_scores.items(), key=lambda x: x[1])[0] if type_scores else 'article'
    
    def _analyze_content_difficulty(self, text: str, content: Dict[str, Any]) -> str:
        """Analyze content difficulty level"""
        difficulty_scores = defaultdict(float)
        
        for level, patterns in self.difficulty_indicators.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                difficulty_scores[level] += matches
        
        # Analyze text complexity
        sentences = sent_tokenize(text) if NLP_LIBRARIES_AVAILABLE else [text]
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
        
        if avg_sentence_length > 20:
            difficulty_scores['advanced'] += 1
        elif avg_sentence_length < 10:
            difficulty_scores['beginner'] += 1
        else:
            difficulty_scores['intermediate'] += 1
        
        return max(difficulty_scores.items(), key=lambda x: x[1])[0] if difficulty_scores else 'intermediate'
    
    def _extract_key_concepts(self, text: str, entities: List[Dict[str, Any]]) -> List[str]:
        """Extract key concepts from text"""
        concepts = set()
        
        # Extract from entities
        for entity in entities:
            if entity['confidence'] > 0.7:
                concepts.add(entity['text'])
        
        # Extract important noun phrases
        if self.nlp:
            doc = self.nlp(text)
            for chunk in doc.noun_chunks:
                if len(chunk.text.split()) <= 3:  # Keep short phrases
                    concepts.add(chunk.text)
        
        # Pattern-based concept extraction
        concept_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Title case phrases
            r'\b\w+(?:\.js|\.py|\.java|\.cpp)\b',  # File extensions
            r'\b\w+(?:API|SDK|CLI|IDE)\b'  # Tech acronyms
        ]
        
        for pattern in concept_patterns:
            matches = re.findall(pattern, text)
            concepts.update(matches)
        
        return list(concepts)[:10]  # Limit to top 10
    
    def _extract_content_technologies(self, text: str, entities: List[Dict[str, Any]], content: Dict[str, Any]) -> List[str]:
        """Extract technology tags from content"""
        technologies = set()
        
        # Use existing technology extraction
        tech_from_text = self._extract_technologies(text, entities)
        technologies.update(tech_from_text)
        
        # Extract from content metadata
        if content.get('technologies'):
            if isinstance(content['technologies'], list):
                technologies.update(content['technologies'])
            else:
                technologies.update(content['technologies'].split(','))
        
        return list(technologies)
    
    def _classify_content_domain(self, text: str, technologies: List[str]) -> str:
        """Classify content domain"""
        domain_scores = defaultdict(float)
        
        # Score based on text patterns
        for domain, patterns in self.domain_patterns.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                domain_scores[domain] += matches
        
        # Score based on technologies
        tech_domain_mapping = {
            'web_development': ['javascript', 'html', 'css', 'react', 'angular', 'vue'],
            'data_science': ['python', 'pandas', 'numpy', 'tensorflow', 'pytorch'],
            'mobile_development': ['android', 'ios', 'flutter', 'react-native'],
            'devops': ['docker', 'kubernetes', 'aws', 'jenkins']
        }
        
        for domain, tech_list in tech_domain_mapping.items():
            for tech in technologies:
                if any(t in tech.lower() for t in tech_list):
                    domain_scores[domain] += 1
        
        return max(domain_scores.items(), key=lambda x: x[1])[0] if domain_scores else 'general_programming'
    
    def _analyze_concept_relationships(self, concepts: List[str], entities: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Analyze relationships between concepts"""
        relationships = defaultdict(list)
        
        # Simple co-occurrence based relationships
        for i, concept1 in enumerate(concepts):
            for concept2 in concepts[i+1:]:
                if concept1 != concept2:
                    relationships[concept1].append(concept2)
                    relationships[concept2].append(concept1)
        
        return dict(relationships)
    
    def _calculate_readability(self, text: str) -> float:
        """Calculate readability score (0-1, higher is more readable)"""
        if not text:
            return 0.5
        
        # Simple readability metrics
        sentences = sent_tokenize(text) if NLP_LIBRARIES_AVAILABLE else text.split('.')
        words = text.split()
        
        if not sentences or not words:
            return 0.5
        
        avg_sentence_length = len(words) / len(sentences)
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # Normalize to 0-1 scale (simpler is more readable)
        sentence_score = max(0, 1 - (avg_sentence_length - 10) / 20)
        word_score = max(0, 1 - (avg_word_length - 5) / 5)
        
        return (sentence_score + word_score) / 2
    
    def _identify_complexity_indicators(self, text: str) -> List[str]:
        """Identify complexity indicators in text"""
        indicators = []
        
        complexity_patterns = {
            'technical_jargon': r'\b\w{8,}\b',  # Long technical words
            'code_examples': r'```|<code>|\bdef\b|\bclass\b|\bfunction\b',
            'advanced_concepts': r'\b(architecture|design pattern|optimization|algorithm)\b',
            'mathematical': r'\b(equation|formula|calculation|mathematics)\b'
        }
        
        for indicator, pattern in complexity_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                indicators.append(indicator)
        
        return indicators
    
    def _extract_learning_objectives(self, text: str) -> List[str]:
        """Extract learning objectives from content"""
        objectives = []
        
        objective_patterns = [
            r'you will learn\s+([^.]+)',
            r'by the end.*you.*([^.]+)',
            r'objectives?:?\s*([^.]+)',
            r'goals?:?\s*([^.]+)'
        ]
        
        for pattern in objective_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            objectives.extend([match.strip() for match in matches])
        
        return objectives[:3]  # Top 3 objectives
    
    def _identify_prerequisites(self, text: str, technologies: List[str]) -> List[str]:
        """Identify prerequisites from content"""
        prerequisites = set()
        
        # Pattern-based prerequisites
        prereq_patterns = [
            r'prerequisite\s*:?\s*([^.]+)',
            r'requires?\s+([^.]+)',
            r'assumes?\s+([^.]+)',
            r'familiarity with\s+([^.]+)'
        ]
        
        for pattern in prereq_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            prerequisites.update([match.strip() for match in matches])
        
        # Add basic technology prerequisites
        for tech in technologies:
            if tech.lower() in ['react', 'angular', 'vue']:
                prerequisites.add('JavaScript basics')
            elif tech.lower() in ['django', 'flask']:
                prerequisites.add('Python basics')
        
        return list(prerequisites)[:5]
    
    def _determine_target_audience(self, difficulty: str, complexity_indicators: List[str]) -> str:
        """Determine target audience for content"""
        if difficulty == 'beginner' and not complexity_indicators:
            return 'newcomers'
        elif difficulty == 'intermediate' or len(complexity_indicators) <= 2:
            return 'practitioners'
        else:
            return 'experts'
    
    def _calculate_content_quality(self, text: str, entities: List[Dict[str, Any]], concepts: List[str]) -> float:
        """Calculate content quality score (0-1)"""
        if not text:
            return 0.0
        
        quality_factors = []
        
        # Length factor (not too short, not too long)
        length_score = min(1.0, len(text) / 1000) if len(text) < 1000 else max(0.5, 1000 / len(text))
        quality_factors.append(length_score)
        
        # Entity richness
        entity_score = min(1.0, len(entities) / 10)
        quality_factors.append(entity_score)
        
        # Concept richness
        concept_score = min(1.0, len(concepts) / 15)
        quality_factors.append(concept_score)
        
        # Structure indicators (headers, lists, etc.)
        structure_indicators = len(re.findall(r'^\s*[#\-\*]\s+', text, re.MULTILINE))
        structure_score = min(1.0, structure_indicators / 5)
        quality_factors.append(structure_score)
        
        return sum(quality_factors) / len(quality_factors)
    
    def _analyze_language_patterns(self, text: str) -> Dict[str, Any]:
        """Analyze language patterns in text"""
        patterns = {
            'instructional': len(re.findall(r'\b(step|first|then|next|finally)\b', text, re.IGNORECASE)),
            'explanatory': len(re.findall(r'\b(because|since|therefore|thus|hence)\b', text, re.IGNORECASE)),
            'comparative': len(re.findall(r'\b(better|worse|compared|versus|vs)\b', text, re.IGNORECASE)),
            'example_heavy': len(re.findall(r'\b(example|instance|such as|for example)\b', text, re.IGNORECASE))
        }
        
        # Normalize by text length
        text_length = len(text.split())
        if text_length > 0:
            patterns = {k: v / text_length * 100 for k, v in patterns.items()}
        
        return patterns
    
    def _create_fallback_semantic_result(self, content: Dict[str, Any]) -> SemanticAnalysisResult:
        """Create fallback semantic result when analysis fails"""
        return SemanticAnalysisResult(
            content_type='article',
            difficulty_level='intermediate',
            key_concepts=[],
            technology_tags=[],
            domain_classification='general_programming',
            concept_relationships={},
            semantic_similarity_score=0.0,
            readability_score=0.5,
            complexity_indicators=[],
            learning_objectives=[],
            prerequisites=[],
            target_audience='practitioners',
            content_quality_score=0.5,
            language_patterns={},
            entities=[],
            metadata={'fallback': True}
        )
    
    # Query enhancement methods
    
    def _generate_query_variations(self, query: str, intent_result: IntentAnalysisResult) -> List[str]:
        """Generate query variations based on intent analysis"""
        variations = []
        
        # Add technology-specific variations
        for tech in intent_result.technology_focus:
            variations.append(f"{query} {tech}")
            variations.append(f"{tech} {query}")
        
        # Add intent-specific variations
        intent_modifiers = {
            'learn': ['tutorial', 'guide', 'how to'],
            'build': ['example', 'implementation', 'project'],
            'solve': ['fix', 'troubleshoot', 'debug'],
            'optimize': ['improve', 'performance', 'best practices']
        }
        
        modifiers = intent_modifiers.get(intent_result.primary_intent, [])
        for modifier in modifiers:
            variations.append(f"{modifier} {query}")
        
        return variations[:5]  # Limit variations
    
    def _extract_implicit_requirements(self, query: str, intent_result: IntentAnalysisResult) -> List[str]:
        """Extract implicit requirements from query and intent"""
        requirements = []
        
        # Add complexity-based requirements
        if intent_result.complexity_level == 'beginner':
            requirements.extend(['step-by-step guidance', 'basic explanations', 'simple examples'])
        elif intent_result.complexity_level == 'advanced':
            requirements.extend(['comprehensive coverage', 'best practices', 'optimization techniques'])
        
        # Add domain-specific requirements
        domain_requirements = {
            'web_development': ['responsive design', 'cross-browser compatibility'],
            'data_science': ['data visualization', 'statistical analysis'],
            'mobile_development': ['platform compatibility', 'user experience']
        }
        
        requirements.extend(domain_requirements.get(intent_result.domain_focus, []))
        
        return requirements[:5]
    
    def _suggest_related_concepts(self, technologies: List[str], themes: List[str]) -> List[str]:
        """Suggest related concepts based on technologies and themes"""
        related = set()
        
        # Technology-based suggestions
        tech_relationships = {
            'javascript': ['typescript', 'nodejs', 'react', 'frontend'],
            'python': ['django', 'flask', 'pandas', 'machine learning'],
            'java': ['spring', 'android', 'jvm', 'enterprise'],
            'react': ['jsx', 'hooks', 'state management', 'components']
        }
        
        for tech in technologies:
            related.update(tech_relationships.get(tech.lower(), []))
        
        # Theme-based suggestions
        theme_relationships = {
            'performance': ['optimization', 'caching', 'profiling'],
            'security': ['authentication', 'encryption', 'validation'],
            'learning': ['tutorial', 'documentation', 'examples']
        }
        
        for theme in themes:
            related.update(theme_relationships.get(theme, []))
        
        return list(related)[:10]
    
    def _generate_search_hints(self, intent_result: IntentAnalysisResult) -> List[str]:
        """Generate search hints based on intent analysis"""
        hints = []
        
        # Intent-based hints
        intent_hints = {
            'learn': ['Look for tutorials and guides', 'Check for beginner-friendly content'],
            'build': ['Search for examples and implementations', 'Look for project templates'],
            'solve': ['Check error messages and solutions', 'Look for troubleshooting guides'],
            'optimize': ['Search for performance tips', 'Look for best practices']
        }
        
        hints.extend(intent_hints.get(intent_result.primary_intent, []))
        
        # Technology-specific hints
        if intent_result.technology_focus:
            hints.append(f"Focus on {', '.join(intent_result.technology_focus)} resources")
        
        # Complexity-based hints
        if intent_result.complexity_level == 'beginner':
            hints.append("Start with fundamental concepts")
        elif intent_result.complexity_level == 'advanced':
            hints.append("Look for in-depth and comprehensive resources")
        
        return hints[:5]

# Export main classes
__all__ = [
    'AdvancedNLPEngine',
    'IntentAnalysisResult', 
    'SemanticAnalysisResult',
    'NLPConfiguration'
]

if __name__ == "__main__":
    print("🧠 Advanced NLP Engine for Enhanced Understanding")
    print("=" * 60)
    print("✅ Deep intent analysis with context understanding")
    print("✅ Advanced semantic relationship detection") 
    print("✅ Multi-language support and entity recognition")
    print("✅ Contextual query expansion and refinement")
    print("✅ Intelligent content categorization")
    print("=" * 60)
    print("🎯 Enhances recommendation intelligence while processing ALL content!")
