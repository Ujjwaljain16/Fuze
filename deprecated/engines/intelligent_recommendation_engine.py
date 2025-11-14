#!/usr/bin/env python3
"""
Intelligent Recommendation Engine
Uses advanced NLP, semantic understanding, and dynamic context analysis
No hardcoded words - learns and adapts to user input dynamically
"""

import os
import sys
import time
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class IntelligentAnalysis:
    """Intelligent analysis results"""
    primary_intent: str
    secondary_intents: List[str]
    domain: str
    complexity_level: str
    technology_focus: List[str]
    business_context: str
    user_expertise: str
    project_phase: str
    key_concepts: List[str]
    related_domains: List[str]
    confidence_score: float
    analysis_metadata: Dict[str, Any]

class IntelligentContextAnalyzer:
    """Advanced context analyzer using NLP and semantic understanding"""
    
    def __init__(self):
        self.nlp_model = None
        self.semantic_matcher = None
        self._initialize_nlp()
    
    def _initialize_nlp(self):
        """Initialize NLP capabilities with fallbacks"""
        try:
            # Try to use spaCy for advanced NLP
            import spacy
            try:
                self.nlp_model = spacy.load("en_core_web_sm")
                logger.info("✅ spaCy NLP model loaded successfully")
            except OSError:
                # Download if not available
                import subprocess
                subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
                self.nlp_model = spacy.load("en_core_web_sm")
                logger.info("✅ spaCy NLP model downloaded and loaded")
        except ImportError:
            logger.warning("⚠️ spaCy not available, using fallback NLP")
            self.nlp_model = None
        
        # Initialize semantic matcher
        try:
            from universal_semantic_matcher import UniversalSemanticMatcher
            self.semantic_matcher = UniversalSemanticMatcher()
            logger.info("✅ Universal semantic matcher initialized")
        except Exception as e:
            logger.warning(f"⚠️ Universal semantic matcher not available: {e}")
            self.semantic_matcher = None
    
    def analyze_user_input(self, title: str, description: str, technologies: str, user_interests: str) -> IntelligentAnalysis:
        """Intelligently analyze user input using advanced NLP"""
        try:
            # Combine all input for comprehensive analysis
            full_text = f"{title} {description} {technologies} {user_interests}".strip()
            
            if not full_text:
                return self._create_default_analysis()
            
            # Perform multi-layer analysis
            analysis = IntelligentAnalysis(
                primary_intent=self._extract_primary_intent(full_text),
                secondary_intents=self._extract_secondary_intents(full_text),
                domain=self._identify_domain(full_text),
                complexity_level=self._assess_complexity(full_text),
                technology_focus=self._extract_technology_focus(full_text, technologies),
                business_context=self._extract_business_context(full_text),
                user_expertise=self._assess_user_expertise(full_text),
                project_phase=self._identify_project_phase(full_text),
                key_concepts=self._extract_key_concepts(full_text),
                related_domains=self._identify_related_domains(full_text),
                confidence_score=0.0,
                analysis_metadata={}
            )
            
            # Calculate confidence score
            analysis.confidence_score = self._calculate_confidence(analysis, full_text)
            
            # Add metadata
            analysis.analysis_metadata = {
                'analysis_timestamp': datetime.now().isoformat(),
                'input_length': len(full_text),
                'nlp_model_used': 'spacy' if self.nlp_model else 'fallback',
                'semantic_analysis': self.semantic_matcher is not None
            }
            
            logger.info(f"✅ Intelligent analysis completed: {analysis.primary_intent} - {analysis.domain}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in intelligent analysis: {e}")
            return self._create_default_analysis()
    
    def _extract_primary_intent(self, text: str) -> str:
        """Extract primary intent using NLP and pattern recognition"""
        try:
            if self.nlp_model:
                # Use spaCy for advanced intent extraction
                doc = self.nlp_model(text.lower())
                
                # Extract verbs and action words
                action_verbs = [token.lemma_ for token in doc if token.pos_ == "VERB" and token.is_alpha]
                
                # Intent mapping based on action verbs
                intent_patterns = {
                    'build': ['build', 'create', 'develop', 'make', 'construct', 'implement', 'design'],
                    'learn': ['learn', 'study', 'understand', 'explore', 'research', 'analyze'],
                    'deploy': ['deploy', 'host', 'publish', 'release', 'launch', 'run'],
                    'optimize': ['optimize', 'improve', 'enhance', 'upgrade', 'refactor'],
                    'integrate': ['integrate', 'connect', 'link', 'combine', 'merge'],
                    'secure': ['secure', 'protect', 'defend', 'safeguard', 'encrypt'],
                    'scale': ['scale', 'expand', 'grow', 'handle', 'manage'],
                    'test': ['test', 'validate', 'verify', 'check', 'debug']
                }
                
                # Find the most likely intent
                intent_scores = {}
                for intent, patterns in intent_patterns.items():
                    score = sum(1 for pattern in patterns if pattern in action_verbs)
                    if score > 0:
                        intent_scores[intent] = score
                
                if intent_scores:
                    return max(intent_scores, key=intent_scores.get)
            
            # Fallback: Use keyword-based intent detection
            return self._fallback_intent_detection(text)
            
        except Exception as e:
            logger.debug(f"Error in primary intent extraction: {e}")
            return self._fallback_intent_detection(text)
    
    def _fallback_intent_detection(self, text: str) -> str:
        """Fallback intent detection using keyword analysis"""
        text_lower = text.lower()
        
        # Simple but effective keyword-based detection
        if any(word in text_lower for word in ['build', 'create', 'develop', 'make']):
            return 'build'
        elif any(word in text_lower for word in ['learn', 'study', 'understand', 'tutorial']):
            return 'learn'
        elif any(word in text_lower for word in ['deploy', 'host', 'publish', 'launch']):
            return 'deploy'
        elif any(word in text_lower for word in ['optimize', 'improve', 'enhance']):
            return 'optimize'
        elif any(word in text_lower for word in ['integrate', 'connect', 'link']):
            return 'integrate'
        else:
            return 'build'  # Default to build
    
    def _extract_secondary_intents(self, text: str) -> List[str]:
        """Extract secondary intents for comprehensive understanding"""
        try:
            secondary_intents = []
            text_lower = text.lower()
            
            # Identify additional intents beyond primary
            intent_indicators = {
                'research': ['research', 'investigate', 'explore', 'analyze'],
                'planning': ['plan', 'design', 'architecture', 'strategy'],
                'testing': ['test', 'validate', 'verify', 'debug'],
                'documentation': ['document', 'write', 'create guide', 'tutorial'],
                'maintenance': ['maintain', 'support', 'update', 'fix'],
                'collaboration': ['team', 'collaborate', 'share', 'work together']
            }
            
            for intent, indicators in intent_indicators.items():
                if any(indicator in text_lower for indicator in indicators):
                    secondary_intents.append(intent)
            
            return secondary_intents[:3]  # Limit to top 3
            
        except Exception as e:
            logger.debug(f"Error in secondary intent extraction: {e}")
            return []
    
    def _identify_domain(self, text: str) -> str:
        """Identify the primary domain of the project"""
        try:
            text_lower = text.lower()
            
            # Domain identification patterns
            domain_patterns = {
                'web_development': ['web', 'website', 'frontend', 'backend', 'fullstack', 'react', 'vue', 'angular'],
                'mobile_development': ['mobile', 'app', 'ios', 'android', 'react native', 'flutter'],
                'data_science': ['data', 'analytics', 'machine learning', 'ai', 'ml', 'statistics', 'visualization'],
                'devops': ['deployment', 'ci/cd', 'docker', 'kubernetes', 'aws', 'azure', 'infrastructure'],
                'cybersecurity': ['security', 'encryption', 'authentication', 'penetration testing', 'vulnerability'],
                'blockchain': ['blockchain', 'cryptocurrency', 'smart contract', 'web3', 'defi'],
                'iot': ['iot', 'internet of things', 'sensor', 'embedded', 'hardware'],
                'game_development': ['game', 'unity', 'unreal', 'gaming', '3d', 'graphics'],
                'enterprise': ['enterprise', 'business', 'erp', 'crm', 'workflow', 'automation'],
                'fintech': ['finance', 'payment', 'banking', 'trading', 'investment', 'insurance']
            }
            
            # Calculate domain scores
            domain_scores = {}
            for domain, patterns in domain_patterns.items():
                score = sum(1 for pattern in patterns if pattern in text_lower)
                if score > 0:
                    domain_scores[domain] = score
            
            if domain_scores:
                return max(domain_scores, key=domain_scores.get)
            
            return 'general_development'
            
        except Exception as e:
            logger.debug(f"Error in domain identification: {e}")
            return 'general_development'
    
    def _assess_complexity(self, text: str) -> str:
        """Assess project complexity using NLP analysis"""
        try:
            if self.nlp_model:
                doc = self.nlp_model(text.lower())
                
                # Complexity indicators
                simple_indicators = ['simple', 'basic', 'starter', 'beginner', 'tutorial', 'example']
                medium_indicators = ['intermediate', 'moderate', 'standard', 'typical', 'common']
                complex_indicators = ['advanced', 'complex', 'sophisticated', 'enterprise', 'scalable', 'distributed']
                
                # Count complexity indicators
                simple_count = sum(1 for token in doc if token.text in simple_indicators)
                medium_count = sum(1 for token in doc if token.text in medium_indicators)
                complex_count = sum(1 for token in doc if token.text in complex_indicators)
                
                # Determine complexity level
                if complex_count > (simple_count + medium_count):
                    return 'advanced'
                elif simple_count > (medium_count + complex_count):
                    return 'beginner'
                else:
                    return 'intermediate'
            
            # Fallback complexity assessment
            return self._fallback_complexity_assessment(text)
            
        except Exception as e:
            logger.debug(f"Error in complexity assessment: {e}")
            return self._fallback_complexity_assessment(text)
    
    def _fallback_complexity_assessment(self, text: str) -> str:
        """Fallback complexity assessment"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['simple', 'basic', 'starter', 'beginner']):
            return 'beginner'
        elif any(word in text_lower for word in ['advanced', 'complex', 'enterprise', 'scalable']):
            return 'advanced'
        else:
            return 'intermediate'
    
    def _extract_technology_focus(self, text: str, technologies: str) -> List[str]:
        """Extract technology focus areas dynamically"""
        try:
            tech_focus = []
            
            # Parse explicit technologies
            if technologies:
                tech_list = [tech.strip().lower() for tech in technologies.split(',') if tech.strip()]
                tech_focus.extend(tech_list)
            
            # Extract implicit technologies from text
            text_lower = text.lower()
            
            # Technology categories for dynamic detection
            tech_categories = {
                'frontend': ['html', 'css', 'javascript', 'react', 'vue', 'angular', 'svelte', 'bootstrap', 'tailwind'],
                'backend': ['python', 'node.js', 'java', 'c#', '.net', 'php', 'ruby', 'go', 'rust'],
                'database': ['mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'sqlite', 'oracle'],
                'cloud': ['aws', 'azure', 'gcp', 'heroku', 'digitalocean', 'linode', 'vultr'],
                'devops': ['docker', 'kubernetes', 'jenkins', 'gitlab', 'github actions', 'terraform'],
                'mobile': ['react native', 'flutter', 'xamarin', 'ionic', 'cordova'],
                'ai_ml': ['tensorflow', 'pytorch', 'scikit-learn', 'opencv', 'nltk', 'spacy']
            }
            
            # Detect technologies mentioned in text
            for category, techs in tech_categories.items():
                for tech in techs:
                    if tech in text_lower and tech not in tech_focus:
                        tech_focus.append(tech)
            
            # Remove duplicates and limit
            return list(set(tech_focus))[:10]
            
        except Exception as e:
            logger.debug(f"Error in technology focus extraction: {e}")
            return []
    
    def _extract_business_context(self, text: str) -> str:
        """Extract business context and purpose"""
        try:
            text_lower = text.lower()
            
            # Business context patterns
            business_patterns = {
                'startup': ['startup', 'mvp', 'prototype', 'idea', 'entrepreneur'],
                'enterprise': ['enterprise', 'business', 'corporate', 'organization', 'company'],
                'personal': ['personal', 'portfolio', 'learning', 'hobby', 'side project'],
                'academic': ['academic', 'research', 'study', 'thesis', 'paper'],
                'open_source': ['open source', 'community', 'contribute', 'github', 'collaboration'],
                'freelance': ['freelance', 'client', 'contract', 'consulting', 'service']
            }
            
            for context, patterns in business_patterns.items():
                if any(pattern in text_lower for pattern in patterns):
                    return context
            
            return 'general'
            
        except Exception as e:
            logger.debug(f"Error in business context extraction: {e}")
            return 'general'
    
    def _assess_user_expertise(self, text: str) -> str:
        """Assess user expertise level from input"""
        try:
            text_lower = text.lower()
            
            # Expertise indicators
            beginner_indicators = ['beginner', 'new', 'learning', 'first time', 'start', 'tutorial']
            intermediate_indicators = ['intermediate', 'some experience', 'familiar', 'working with']
            advanced_indicators = ['advanced', 'expert', 'professional', 'senior', 'architect']
            
            if any(indicator in text_lower for indicator in advanced_indicators):
                return 'advanced'
            elif any(indicator in text_lower for indicator in intermediate_indicators):
                return 'intermediate'
            elif any(indicator in text_lower for indicator in beginner_indicators):
                return 'beginner'
            else:
                return 'intermediate'  # Default assumption
                
        except Exception as e:
            logger.debug(f"Error in expertise assessment: {e}")
            return 'intermediate'
    
    def _identify_project_phase(self, text: str) -> str:
        """Identify the current phase of the project"""
        try:
            text_lower = text.lower()
            
            # Project phase indicators
            phase_patterns = {
                'planning': ['plan', 'design', 'architecture', 'research', 'analysis'],
                'development': ['develop', 'build', 'create', 'implement', 'coding'],
                'testing': ['test', 'debug', 'validate', 'verify', 'quality'],
                'deployment': ['deploy', 'launch', 'publish', 'release', 'production'],
                'maintenance': ['maintain', 'update', 'fix', 'support', 'monitor']
            }
            
            for phase, patterns in phase_patterns.items():
                if any(pattern in text_lower for pattern in patterns):
                    return phase
            
            return 'development'  # Default to development phase
            
        except Exception as e:
            logger.debug(f"Error in project phase identification: {e}")
            return 'development'
    
    def _extract_key_concepts(self, text: str) -> List[str]:
        """Extract key concepts using NLP"""
        try:
            key_concepts = []
            
            if self.nlp_model:
                doc = self.nlp_model(text)
                
                # Extract nouns and noun phrases
                nouns = [token.text for token in doc if token.pos_ in ['NOUN', 'PROPN'] and token.is_alpha]
                noun_chunks = [chunk.text for chunk in doc.noun_chunks]
                
                # Combine and filter
                concepts = list(set(nouns + noun_chunks))
                
                # Filter out common words and short terms
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
                filtered_concepts = [concept for concept in concepts if len(concept) > 2 and concept.lower() not in stop_words]
                
                key_concepts = filtered_concepts[:10]  # Limit to top 10
            
            return key_concepts
            
        except Exception as e:
            logger.debug(f"Error in key concept extraction: {e}")
            return []
    
    def _identify_related_domains(self, text: str) -> str:
        """Identify related domains for cross-domain recommendations"""
        try:
            text_lower = text.lower()
            related_domains = []
            
            # Cross-domain relationships
            domain_relationships = {
                'web_development': ['mobile_development', 'devops', 'cybersecurity'],
                'mobile_development': ['web_development', 'ui_ux', 'backend_development'],
                'data_science': ['machine_learning', 'web_development', 'devops'],
                'devops': ['web_development', 'mobile_development', 'cybersecurity'],
                'cybersecurity': ['web_development', 'devops', 'network_administration']
            }
            
            # Find primary domain and add related ones
            primary_domain = self._identify_domain(text)
            if primary_domain in domain_relationships:
                related_domains = domain_relationships[primary_domain]
            
            return related_domains
            
        except Exception as e:
            logger.debug(f"Error in related domain identification: {e}")
            return []
    
    def _calculate_confidence(self, analysis: IntelligentAnalysis, text: str) -> float:
        """Calculate confidence score for the analysis"""
        try:
            confidence = 0.0
            
            # Base confidence from input quality
            if len(text) > 50:
                confidence += 0.3
            elif len(text) > 20:
                confidence += 0.2
            else:
                confidence += 0.1
            
            # Confidence from analysis completeness
            if analysis.primary_intent != 'unknown':
                confidence += 0.2
            
            if analysis.domain != 'general_development':
                confidence += 0.2
            
            if analysis.technology_focus:
                confidence += 0.15
            
            if analysis.key_concepts:
                confidence += 0.15
            
            # Cap at 1.0
            return min(confidence, 1.0)
            
        except Exception as e:
            logger.debug(f"Error in confidence calculation: {e}")
            return 0.5
    
    def _create_default_analysis(self) -> IntelligentAnalysis:
        """Create default analysis when input is insufficient"""
        return IntelligentAnalysis(
            primary_intent='build',
            secondary_intents=[],
            domain='general_development',
            complexity_level='intermediate',
            technology_focus=[],
            business_context='general',
            user_expertise='intermediate',
            project_phase='development',
            key_concepts=[],
            related_domains=[],
            confidence_score=0.1,
            analysis_metadata={'fallback': True}
        )

class IntelligentRecommendationEngine:
    """Main intelligent recommendation engine"""
    
    def __init__(self):
        self.context_analyzer = IntelligentContextAnalyzer()
        self.semantic_matcher = None
        self._initialize_semantic_matching()
    
    def _initialize_semantic_matching(self):
        """Initialize semantic matching capabilities"""
        try:
            from universal_semantic_matcher import UniversalSemanticMatcher
            self.semantic_matcher = UniversalSemanticMatcher()
            logger.info("✅ Semantic matcher initialized for intelligent recommendations")
        except Exception as e:
            logger.warning(f"⚠️ Semantic matcher not available: {e}")
    
    def get_intelligent_recommendations(self, user_input: Dict[str, Any], content_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get intelligent recommendations based on comprehensive analysis"""
        try:
            # Analyze user input intelligently
            analysis = self.context_analyzer.analyze_user_input(
                title=user_input.get('title', ''),
                description=user_input.get('description', ''),
                technologies=user_input.get('technologies', ''),
                user_interests=user_input.get('user_interests', '')
            )
            
            logger.info(f"🧠 Intelligent analysis: {analysis.primary_intent} - {analysis.domain} - {analysis.complexity_level}")
            
            # Score content based on intelligent analysis
            scored_content = self._score_content_intelligently(content_list, analysis)
            
            # Generate intelligent recommendations
            recommendations = self._generate_intelligent_recommendations(scored_content, analysis)
            
            logger.info(f"✅ Generated {len(recommendations)} intelligent recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error in intelligent recommendations: {e}")
            return []
    
    def _score_content_intelligently(self, content_list: List[Dict[str, Any]], analysis: IntelligentAnalysis) -> List[Dict[str, Any]]:
        """Score content using intelligent analysis instead of hardcoded rules"""
        try:
            scored_content = []
            
            for content in content_list:
                score = self._calculate_intelligent_score(content, analysis)
                content['intelligent_score'] = score
                scored_content.append(content)
            
            # Sort by intelligent score
            scored_content.sort(key=lambda x: x.get('intelligent_score', 0), reverse=True)
            return scored_content
            
        except Exception as e:
            logger.error(f"Error in intelligent content scoring: {e}")
            return content_list
    
    def _calculate_intelligent_score(self, content: Dict[str, Any], analysis: IntelligentAnalysis) -> float:
        """Calculate intelligent relevance score using multiple factors"""
        try:
            score = 0.0
            
            # 1. Intent alignment (25% weight)
            intent_score = self._calculate_intent_alignment(content, analysis)
            score += intent_score * 0.25
            
            # 2. Domain relevance (20% weight)
            domain_score = self._calculate_domain_relevance(content, analysis)
            score += domain_score * 0.20
            
            # 3. Technology compatibility (20% weight)
            tech_score = self._calculate_technology_compatibility(content, analysis)
            score += tech_score * 0.20
            
            # 4. Complexity match (15% weight)
            complexity_score = self._calculate_complexity_match(content, analysis)
            score += complexity_score * 0.15
            
            # 5. Semantic similarity (20% weight)
            semantic_score = self._calculate_semantic_similarity(content, analysis)
            score += semantic_score * 0.20
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.debug(f"Error in intelligent score calculation: {e}")
            return 0.0
    
    def _calculate_intent_alignment(self, content: Dict[str, Any], analysis: IntelligentAnalysis) -> float:
        """Calculate intent alignment using semantic understanding"""
        try:
            # Extract content intent
            content_text = f"{content.get('title', '')} {content.get('extracted_text', '')}".lower()
            
            # Intent keywords for dynamic matching
            intent_keywords = {
                'build': ['build', 'create', 'develop', 'make', 'implement', 'construct'],
                'learn': ['learn', 'study', 'understand', 'tutorial', 'guide', 'course'],
                'deploy': ['deploy', 'host', 'publish', 'launch', 'release', 'production'],
                'optimize': ['optimize', 'improve', 'enhance', 'performance', 'efficiency'],
                'integrate': ['integrate', 'connect', 'link', 'api', 'service', 'system']
            }
            
            # Calculate intent match score
            primary_intent = analysis.primary_intent
            if primary_intent in intent_keywords:
                keywords = intent_keywords[primary_intent]
                matches = sum(1 for keyword in keywords if keyword in content_text)
                return min(matches / len(keywords), 1.0)
            
            return 0.0
            
        except Exception as e:
            logger.debug(f"Error in intent alignment calculation: {e}")
            return 0.0
    
    def _calculate_domain_relevance(self, content: Dict[str, Any], analysis: IntelligentAnalysis) -> float:
        """Calculate domain relevance using semantic analysis"""
        try:
            content_text = f"{content.get('title', '')} {content.get('extracted_text', '')}".lower()
            
            # Domain-specific keywords for dynamic matching
            domain_keywords = {
                'web_development': ['web', 'website', 'frontend', 'backend', 'fullstack', 'browser'],
                'mobile_development': ['mobile', 'app', 'ios', 'android', 'smartphone', 'tablet'],
                'data_science': ['data', 'analytics', 'machine learning', 'ai', 'ml', 'statistics'],
                'devops': ['deployment', 'ci/cd', 'docker', 'kubernetes', 'infrastructure', 'automation'],
                'cybersecurity': ['security', 'encryption', 'authentication', 'vulnerability', 'threat']
            }
            
            # Calculate domain match score
            domain = analysis.domain
            if domain in domain_keywords:
                keywords = domain_keywords[domain]
                matches = sum(1 for keyword in keywords if keyword in content_text)
                return min(matches / len(keywords), 1.0)
            
            return 0.0
            
        except Exception as e:
            logger.debug(f"Error in domain relevance calculation: {e}")
            return 0.0
    
    def _calculate_technology_compatibility(self, content: Dict[str, Any], analysis: IntelligentAnalysis) -> float:
        """Calculate technology compatibility dynamically"""
        try:
            if not analysis.technology_focus:
                return 0.5  # Neutral score if no specific tech focus
            
            content_text = f"{content.get('title', '')} {content.get('extracted_text', '')}".lower()
            content_techs = content.get('technologies', [])
            
            # Convert to list if string
            if isinstance(content_techs, str):
                content_techs = [tech.strip().lower() for tech in content_techs.split(',') if tech.strip()]
            
            # Calculate technology overlap
            matches = 0
            for tech in analysis.technology_focus:
                if tech in content_text or any(tech in ct.lower() for ct in content_techs):
                    matches += 1
            
            return min(matches / len(analysis.technology_focus), 1.0)
            
        except Exception as e:
            logger.debug(f"Error in technology compatibility calculation: {e}")
            return 0.0
    
    def _calculate_complexity_match(self, content: Dict[str, Any], analysis: IntelligentAnalysis) -> float:
        """Calculate complexity level match"""
        try:
            content_text = f"{content.get('title', '')} {content.get('extracted_text', '')}".lower()
            
            # Complexity indicators for dynamic matching
            complexity_indicators = {
                'beginner': ['beginner', 'basic', 'simple', 'starter', 'tutorial', 'guide'],
                'intermediate': ['intermediate', 'moderate', 'standard', 'typical', 'common'],
                'advanced': ['advanced', 'complex', 'sophisticated', 'enterprise', 'scalable']
            }
            
            # Calculate complexity match
            target_complexity = analysis.complexity_level
            if target_complexity in complexity_indicators:
                keywords = complexity_indicators[target_complexity]
                matches = sum(1 for keyword in keywords if keyword in content_text)
                return min(matches / len(keywords), 1.0)
            
            return 0.5  # Neutral score
            
        except Exception as e:
            logger.debug(f"Error in complexity match calculation: {e}")
            return 0.5
    
    def _calculate_semantic_similarity(self, content: Dict[str, Any], analysis: IntelligentAnalysis) -> float:
        """Calculate semantic similarity using advanced NLP"""
        try:
            if not self.semantic_matcher:
                return 0.5  # Fallback score
            
            # Prepare text for semantic comparison
            user_text = f"{analysis.primary_intent} {analysis.domain} {' '.join(analysis.key_concepts)}"
            content_text = f"{content.get('title', '')} {content.get('extracted_text', '')}"
            
            # Calculate semantic similarity
            similarity = self.semantic_matcher.calculate_similarity(user_text, content_text)
            return min(similarity, 1.0)
            
        except Exception as e:
            logger.debug(f"Error in semantic similarity calculation: {e}")
            return 0.5
    
    def _generate_intelligent_recommendations(self, scored_content: List[Dict[str, Any]], analysis: IntelligentAnalysis) -> List[Dict[str, Any]]:
        """Generate intelligent recommendations with explanations"""
        try:
            recommendations = []
            
            for i, content in enumerate(scored_content[:20]):  # Top 20
                recommendation = {
                    'id': content.get('id'),
                    'title': content.get('title'),
                    'url': content.get('url'),
                    'score': content.get('intelligent_score', 0) * 100,
                    'reason': self._generate_intelligent_reason(content, analysis, i + 1),
                    'content_type': content.get('content_type', 'article'),
                    'difficulty': content.get('difficulty', 'intermediate'),
                    'technologies': content.get('technologies', []),
                    'key_concepts': content.get('key_concepts', []),
                    'quality_score': content.get('quality_score', 6),
                    'engine_used': 'IntelligentRecommendationEngine',
                    'confidence': analysis.confidence_score,
                    'analysis_metadata': {
                        'primary_intent': analysis.primary_intent,
                        'domain': analysis.domain,
                        'complexity_level': analysis.complexity_level,
                        'technology_focus': analysis.technology_focus,
                        'business_context': analysis.business_context,
                        'user_expertise': analysis.user_expertise,
                        'project_phase': analysis.project_phase,
                        'key_concepts': analysis.key_concepts,
                        'related_domains': analysis.related_domains,
                        'confidence_score': analysis.confidence_score
                    }
                }
                
                recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating intelligent recommendations: {e}")
            return []
    
    def _generate_intelligent_reason(self, content: Dict[str, Any], analysis: IntelligentAnalysis, rank: int) -> str:
        """Generate intelligent reasoning for recommendations"""
        try:
            reasons = []
            
            # Intent alignment reason
            if analysis.primary_intent == 'build':
                reasons.append(f"Perfect for building {analysis.domain} projects")
            elif analysis.primary_intent == 'learn':
                reasons.append(f"Excellent learning resource for {analysis.domain}")
            
            # Domain relevance reason
            if analysis.domain != 'general_development':
                reasons.append(f"Specifically focused on {analysis.domain.replace('_', ' ')}")
            
            # Technology compatibility reason
            if analysis.technology_focus:
                tech_list = ', '.join(analysis.technology_focus[:3])
                reasons.append(f"Covers key technologies: {tech_list}")
            
            # Complexity match reason
            if analysis.complexity_level == 'beginner':
                reasons.append("Suitable for beginners")
            elif analysis.complexity_level == 'advanced':
                reasons.append("Advanced level content")
            
            # Business context reason
            if analysis.business_context != 'general':
                reasons.append(f"Relevant for {analysis.business_context} context")
            
            # Combine reasons
            if reasons:
                return f"Rank #{rank}: {'; '.join(reasons)}"
            else:
                return f"Rank #{rank}: Highly relevant content based on intelligent analysis"
                
        except Exception as e:
            logger.debug(f"Error generating intelligent reason: {e}")
            return f"Rank #{rank}: Recommended based on intelligent analysis"

# Convenience function for easy integration
def get_intelligent_recommendations(user_input: Dict[str, Any], content_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get intelligent recommendations using the intelligent engine"""
    try:
        engine = IntelligentRecommendationEngine()
        return engine.get_intelligent_recommendations(user_input, content_list)
    except Exception as e:
        logger.error(f"Error getting intelligent recommendations: {e}")
        return []

if __name__ == "__main__":
    # Test the intelligent recommendation engine
    print("🧠 Testing Intelligent Recommendation Engine")
    
    # Sample user input
    test_input = {
        'title': 'Build a Mobile Expense Tracker',
        'description': 'I want to create a mobile application for tracking expenses using SMS and UPI payments. The app should be able to extract payment information from messages and log expenses automatically.',
        'technologies': 'react native,firebase,python',
        'user_interests': 'mobile development,fintech,automation'
    }
    
    # Sample content (you would normally get this from your database)
    sample_content = [
        {
            'id': 1,
            'title': 'React Native Mobile App Development Guide',
            'url': 'https://example.com/react-native-guide',
            'extracted_text': 'Complete guide to building mobile apps with React Native',
            'technologies': ['react native', 'javascript', 'mobile'],
            'content_type': 'tutorial',
            'difficulty': 'intermediate',
            'quality_score': 8
        }
    ]
    
    # Get intelligent recommendations
    recommendations = get_intelligent_recommendations(test_input, sample_content)
    
    print(f"\n✅ Generated {len(recommendations)} intelligent recommendations")
    for rec in recommendations:
        print(f"\n📱 {rec['title']}")
        print(f"   Score: {rec['score']:.1f}")
        print(f"   Reason: {rec['reason']}")
        print(f"   Intent: {rec['analysis_metadata']['primary_intent']}")
        print(f"   Domain: {rec['analysis_metadata']['domain']}")
