#!/usr/bin/env python3
"""
Enhanced Context Extraction Engine
Implements Gemini-powered analysis for comprehensive context extraction
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import Counter

logger = logging.getLogger(__name__)

class ContextComplexity(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

@dataclass
class ExtractedContext:
    """Structured context extraction result"""
    primary_technologies: List[str]
    secondary_technologies: List[str]
    core_domains: List[str]
    learning_objectives: List[str]
    complexity: float
    content_types_needed: List[str]
    implicit_requirements: List[str]
    ambiguous_terms_resolved: Dict[str, str]
    confidence_score: float
    analysis_metadata: Dict[str, Any]
    # Add fields that match unified engine expectations
    content_type: str = "general"
    difficulty: str = "intermediate"
    intent: str = "general"
    key_concepts: List[str] = None
    
    def __post_init__(self):
        if self.key_concepts is None:
            self.key_concepts = []

class EnhancedContextExtractor:
    """
    Enhanced context extractor using Gemini-powered analysis:
    - Handles ambiguous terms and implicit requirements
    - Analyzes complex descriptions
    - Provides structured context extraction
    - Includes confidence scoring and metadata
    """
    
    def __init__(self):
        # Initialize Gemini analyzer
        try:
            from gemini_utils import GeminiAnalyzer
            self.gemini_analyzer = GeminiAnalyzer()
            self.gemini_available = True
            logger.info("Gemini analyzer initialized for enhanced context extraction")
        except Exception as e:
            self.gemini_analyzer = None
            self.gemini_available = False
            logger.warning(f"Gemini not available, falling back to rule-based extraction: {e}")
        
        # Technology mapping for ambiguous terms
        self.technology_mappings = {
            'js': 'javascript',
            'ts': 'typescript',
            'react': 'react',
            'vue': 'vue.js',
            'angular': 'angular',
            'node': 'node.js',
            'express': 'express.js',
            'mongo': 'mongodb',
            'postgres': 'postgresql',
            'sql': 'sql',
            'nosql': 'nosql',
            'aws': 'amazon web services',
            'azure': 'microsoft azure',
            'gcp': 'google cloud platform',
            'docker': 'docker',
            'k8s': 'kubernetes',
            'k8': 'kubernetes',
            'kubectl': 'kubernetes',
            'git': 'git',
            'ci/cd': 'continuous integration',
            'cicd': 'continuous integration',
            'api': 'api development',
            'rest': 'rest api',
            'graphql': 'graphql',
            'microservices': 'microservices',
            'monolith': 'monolithic architecture',
            'spa': 'single page application',
            'pwa': 'progressive web app',
            'ssr': 'server side rendering',
            'csr': 'client side rendering',
            'ssg': 'static site generation',
            'jwt': 'json web tokens',
            'oauth': 'oauth',
            'auth': 'authentication',
            'authn': 'authentication',
            'authz': 'authorization',
            'db': 'database',
            'orm': 'object relational mapping',
            'mvc': 'model view controller',
            'mvvm': 'model view viewmodel',
            'redux': 'redux',
            'mobx': 'mobx',
            'zustand': 'zustand',
            'recoil': 'recoil',
            'context': 'react context',
            'hooks': 'react hooks',
            'functional': 'functional programming',
            'oop': 'object oriented programming',
            'fp': 'functional programming',
            'tdd': 'test driven development',
            'bdd': 'behavior driven development',
            'unit': 'unit testing',
            'integration': 'integration testing',
            'e2e': 'end to end testing',
            'jest': 'jest',
            'cypress': 'cypress',
            'selenium': 'selenium',
            'webpack': 'webpack',
            'vite': 'vite',
            'babel': 'babel',
            'eslint': 'eslint',
            'prettier': 'prettier',
            'typescript': 'typescript',
            'flow': 'flow',
            'scss': 'sass',
            'less': 'less',
            'stylus': 'stylus',
            'tailwind': 'tailwind css',
            'bootstrap': 'bootstrap',
            'material': 'material ui',
            'antd': 'ant design',
            'chakra': 'chakra ui',
            'styled': 'styled components',
            'emotion': 'emotion',
            'framer': 'framer motion',
            'gsap': 'gsap',
            'three': 'three.js',
            'webgl': 'webgl',
            'canvas': 'html5 canvas',
            'svg': 'svg',
            'd3': 'd3.js',
            'chart': 'chart.js',
            'recharts': 'recharts',
            'plotly': 'plotly',
            'tensorflow': 'tensorflow',
            'pytorch': 'pytorch',
            'keras': 'keras',
            'scikit': 'scikit learn',
            'pandas': 'pandas',
            'numpy': 'numpy',
            'matplotlib': 'matplotlib',
            'seaborn': 'seaborn',
            'jupyter': 'jupyter',
            'colab': 'google colab',
            'kaggle': 'kaggle',
            'huggingface': 'hugging face',
            'transformers': 'transformers',
            'spacy': 'spacy',
            'nltk': 'nltk',
            'gensim': 'gensim',
            'word2vec': 'word2vec',
            'bert': 'bert',
            'gpt': 'gpt',
            'llm': 'large language models',
            'nlp': 'natural language processing',
            'cv': 'computer vision',
            'opencv': 'opencv',
            'pillow': 'pillow',
            'scipy': 'scipy',
            'sympy': 'sympy',
            'statsmodels': 'statsmodels',
            'plotly': 'plotly',
            'bokeh': 'bokeh',
            'dash': 'dash',
            'streamlit': 'streamlit',
            'gradio': 'gradio',
            'fastapi': 'fastapi',
            'flask': 'flask',
            'django': 'django',
            'rails': 'ruby on rails',
            'spring': 'spring boot',
            'laravel': 'laravel',
            'asp': 'asp.net',
            'dotnet': '.net',
            'java': 'java',
            'kotlin': 'kotlin',
            'scala': 'scala',
            'go': 'golang',
            'rust': 'rust',
            'c++': 'c++',
            'c#': 'c#',
            'php': 'php',
            'python': 'python',
            'ruby': 'ruby',
            'swift': 'swift',
            'objective-c': 'objective-c',
            'react native': 'react native',
            'flutter': 'flutter',
            'xamarin': 'xamarin',
            'ionic': 'ionic',
            'cordova': 'cordova',
            'electron': 'electron',
            'tauri': 'tauri',
            'nw': 'nw.js',
            'deno': 'deno',
            'bun': 'bun',
            'pnpm': 'pnpm',
            'yarn': 'yarn',
            'npm': 'npm',
            'pip': 'pip',
            'conda': 'conda',
            'poetry': 'poetry',
            'cargo': 'cargo',
            'maven': 'maven',
            'gradle': 'gradle',
            'composer': 'composer',
            'gem': 'gem',
            'homebrew': 'homebrew',
            'chocolatey': 'chocolatey',
            'scoop': 'scoop',
            'apt': 'apt',
            'yum': 'yum',
            'pacman': 'pacman',
            'brew': 'homebrew',
            'snap': 'snap',
            'flatpak': 'flatpak',
            'docker': 'docker',
            'podman': 'podman',
            'lxc': 'lxc',
            'lxd': 'lxd',
            'vagrant': 'vagrant',
            'terraform': 'terraform',
            'ansible': 'ansible',
            'puppet': 'puppet',
            'chef': 'chef',
            'salt': 'salt',
            'jenkins': 'jenkins',
            'gitlab': 'gitlab',
            'github': 'github',
            'bitbucket': 'bitbucket',
            'azure devops': 'azure devops',
            'circleci': 'circleci',
            'travis': 'travis ci',
            'appveyor': 'appveyor',
            'teamcity': 'teamcity',
            'bamboo': 'bamboo',
            'go': 'golang',
            'rust': 'rust',
            'elixir': 'elixir',
            'erlang': 'erlang',
            'haskell': 'haskell',
            'clojure': 'clojure',
            'f#': 'f#',
            'ocaml': 'ocaml',
            'racket': 'racket',
            'scheme': 'scheme',
            'lisp': 'lisp',
            'prolog': 'prolog',
            'coq': 'coq',
            'agda': 'agda',
            'idris': 'idris',
            'lean': 'lean',
            'isabelle': 'isabelle',
            'hol': 'hol',
            'acl2': 'acl2',
            'twelf': 'twelf',
            'metamath': 'metamath',
            'mizar': 'mizar',
            'coq': 'coq',
            'agda': 'agda',
            'idris': 'idris',
            'lean': 'lean',
            'isabelle': 'isabelle',
            'hol': 'hol',
            'acl2': 'acl2',
            'twelf': 'twelf',
            'metamath': 'metamath',
            'mizar': 'mizar'
        }
        
        # Domain mappings for implicit requirements
        self.domain_mappings = {
            'web': ['frontend', 'backend', 'fullstack', 'web development'],
            'mobile': ['ios', 'android', 'mobile development', 'app development'],
            'desktop': ['desktop application', 'gui', 'native app'],
            'data': ['data science', 'machine learning', 'ai', 'analytics'],
            'cloud': ['cloud computing', 'devops', 'infrastructure'],
            'security': ['cybersecurity', 'authentication', 'authorization', 'encryption'],
            'performance': ['optimization', 'scalability', 'monitoring'],
            'testing': ['quality assurance', 'testing', 'tdd', 'bdd'],
            'ui/ux': ['user interface', 'user experience', 'design'],
            'api': ['api development', 'microservices', 'integration'],
            'database': ['data modeling', 'database design', 'orm'],
            'networking': ['network programming', 'protocols', 'communication']
        }
        
        # Content type mappings
        self.content_type_mappings = {
            'tutorial': ['guide', 'walkthrough', 'step by step', 'how to'],
            'documentation': ['reference', 'api docs', 'manual', 'specification'],
            'example': ['demo', 'sample', 'code example', 'implementation'],
            'troubleshooting': ['debug', 'fix', 'error', 'problem solving'],
            'best_practice': ['pattern', 'architecture', 'design principle'],
            'article': ['blog post', 'discussion', 'analysis', 'overview'],
            'project': ['build', 'create', 'develop', 'application']
        }

    def extract_context(self, title: str, description: str = "", 
                       technologies: List[str] = None, 
                       user_interests: List[str] = None) -> ExtractedContext:
        """
        Enhanced context extraction using Gemini-powered analysis
        """
        try:
            # Normalize inputs
            technologies = technologies or []
            user_interests = user_interests or []
            
            if self.gemini_available:
                return self._extract_context_with_gemini(title, description, technologies, user_interests)
            else:
                return self._extract_context_rule_based(title, description, technologies, user_interests)
                
        except Exception as e:
            logger.error(f"Error in enhanced context extraction: {e}")
            return self._get_fallback_context(title, description, technologies, user_interests)

    def _extract_context_with_gemini(self, title: str, description: str, 
                                    technologies: List[str], user_interests: List[str]) -> ExtractedContext:
        """Extract context using Gemini analysis"""
        try:
            # Get Gemini analysis using the correct method for single context
            response = self.gemini_analyzer.analyze_user_context(
                title=title,
                description=description,
                technologies=', '.join(technologies) if technologies else '',
                user_interests=', '.join(user_interests) if user_interests else ''
            )
            
            # Parse Gemini response (response is already a dict)
            parsed_result = self._parse_gemini_user_context_response(response)
            
            # Enhance with rule-based analysis
            enhanced_result = self._enhance_with_rule_based_analysis(
                parsed_result, title, description, technologies, user_interests
            )
            
            return enhanced_result
            
        except Exception as e:
            logger.warning(f"Gemini analysis failed, falling back to rule-based: {e}")
            return self._extract_context_rule_based(title, description, technologies, user_interests)



    def _parse_gemini_response(self, response: str) -> Dict[str, Any]:
        """Parse Gemini response and extract structured data"""
        try:
            # Clean response and extract JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                
                # Validate and normalize parsed data
                return self._validate_and_normalize_parsed_data(parsed)
            else:
                raise ValueError("No JSON found in Gemini response")
                
        except Exception as e:
            logger.warning(f"Error parsing Gemini response: {e}")
            return self._get_empty_parsed_data()

    def _parse_gemini_user_context_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gemini user context response and extract structured data"""
        try:
            # Convert user context format to our expected format
            parsed = {
                'primary_technologies': response.get('technologies', []),
                'secondary_technologies': [],
                'core_domains': response.get('focus_areas', []),
                'learning_objectives': response.get('learning_needs', []),
                'complexity': self._convert_difficulty_to_complexity(response.get('difficulty_preference', 'intermediate')),
                'content_types_needed': response.get('preferred_content_types', ['tutorial']),
                'implicit_requirements': response.get('technical_requirements', []),
                'ambiguous_terms_resolved': {},
                'confidence_score': 0.8,  # Default confidence for user context
                'analysis_notes': response.get('project_summary', '')
            }
            
            return self._validate_and_normalize_parsed_data(parsed)
                
        except Exception as e:
            logger.warning(f"Error parsing Gemini user context response: {e}")
            return self._get_empty_parsed_data()

    def _parse_gemini_dict_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gemini dictionary response and extract structured data"""
        try:
            # The response is already a dictionary, extract the first item if it's a batch response
            if 'items' in response and response['items']:
                # Take the first item from batch response
                first_item = response['items'][0]
                
                # Convert batch format to our expected format
                parsed = {
                    'primary_technologies': first_item.get('technologies', []),
                    'secondary_technologies': [],
                    'core_domains': first_item.get('key_concepts', []),
                    'learning_objectives': first_item.get('learning_objectives', []),
                    'complexity': self._convert_difficulty_to_complexity(first_item.get('difficulty', 'intermediate')),
                    'content_types_needed': [first_item.get('content_type', 'general')],
                    'implicit_requirements': [],
                    'ambiguous_terms_resolved': {},
                    'confidence_score': first_item.get('relevance_score', 50) / 100.0,
                    'analysis_notes': first_item.get('summary', '')
                }
                
                return self._validate_and_normalize_parsed_data(parsed)
            else:
                # Direct response format
                return self._validate_and_normalize_parsed_data(response)
                
        except Exception as e:
            logger.warning(f"Error parsing Gemini dict response: {e}")
            return self._get_empty_parsed_data()

    def _convert_difficulty_to_complexity(self, difficulty: str) -> float:
        """Convert difficulty string to complexity float"""
        difficulty_map = {
            'beginner': 0.3,
            'intermediate': 0.6,
            'advanced': 0.9
        }
        return difficulty_map.get(difficulty.lower(), 0.5)

    def _validate_and_normalize_parsed_data(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize parsed data from Gemini"""
        normalized = {
            'primary_technologies': self._normalize_list(parsed.get('primary_technologies', [])),
            'secondary_technologies': self._normalize_list(parsed.get('secondary_technologies', [])),
            'core_domains': self._normalize_list(parsed.get('core_domains', [])),
            'learning_objectives': self._normalize_list(parsed.get('learning_objectives', [])),
            'complexity': self._normalize_float(parsed.get('complexity', 0.5)),
            'content_types_needed': self._normalize_list(parsed.get('content_types_needed', [])),
            'implicit_requirements': self._normalize_list(parsed.get('implicit_requirements', [])),
            'ambiguous_terms_resolved': self._normalize_dict(parsed.get('ambiguous_terms_resolved', {})),
            'confidence_score': self._normalize_float(parsed.get('confidence_score', 0.5)),
            'analysis_notes': str(parsed.get('analysis_notes', ''))
        }
        
        return normalized

    def _enhance_with_rule_based_analysis(self, parsed_result: Dict[str, Any], 
                                         title: str, description: str, 
                                         technologies: List[str], 
                                         user_interests: List[str]) -> ExtractedContext:
        """Enhance Gemini results with rule-based analysis"""
        
        # Use advanced tech detector for proper technology extraction
        try:
            from advanced_tech_detection import advanced_tech_detector
            full_text = f"{title} {description} {' '.join(technologies) if technologies else ''}"
            detected_techs = advanced_tech_detector.extract_technologies(full_text)
            
            # Extract technology categories from the detected technologies
            tech_categories = [tech['category'] for tech in detected_techs if isinstance(tech, dict) and 'category' in tech]
            
            # Resolve ambiguous terms
            resolved_technologies = self._resolve_ambiguous_terms(technologies)
            
            # Combine detected technologies with resolved ones
            all_technologies = list(set(tech_categories + resolved_technologies))
            
        except Exception as e:
            logger.warning(f"Advanced tech detection failed, using fallback: {e}")
            # Fallback to original method
            resolved_technologies = self._resolve_ambiguous_terms(technologies)
            all_technologies = resolved_technologies
        
        # Extract implicit requirements
        implicit_reqs = self._extract_implicit_requirements(title, description, all_technologies)
        
        # Determine content types needed
        content_types = self._determine_content_types_needed(title, description, all_technologies)
        
        # Calculate complexity
        complexity = self._calculate_complexity(title, description, all_technologies)
        
        # Merge with Gemini results
        final_result = {
            'primary_technologies': list(set(parsed_result['primary_technologies'] + all_technologies)),
            'secondary_technologies': parsed_result['secondary_technologies'],
            'core_domains': list(set(parsed_result['core_domains'] + self._extract_core_domains(title, description))),
            'learning_objectives': list(set(parsed_result['learning_objectives'] + self._extract_learning_objectives(title, description, user_interests))),
            'complexity': (parsed_result['complexity'] + complexity) / 2,  # Average of both
            'content_types_needed': list(set(parsed_result['content_types_needed'] + content_types)),
            'implicit_requirements': list(set(parsed_result['implicit_requirements'] + implicit_reqs)),
            'ambiguous_terms_resolved': {**parsed_result['ambiguous_terms_resolved'], **self._resolve_ambiguous_terms_dict(technologies)},
            'confidence_score': min(1.0, parsed_result['confidence_score'] + 0.1),  # Boost confidence
            'analysis_metadata': {
                'gemini_analysis': True,
                'rule_based_enhancement': True,
                'total_technologies': len(all_technologies),
                'analysis_methods': ['gemini', 'rule_based', 'advanced_tech_detection']
            },
            # Add unified engine compatible fields
            'content_type': self._determine_content_type(title, description),
            'difficulty': self._determine_difficulty(title, description),
            'intent': self._determine_intent(title, description),
            'key_concepts': all_technologies  # Use the properly extracted technologies instead of broken method
        }
        
        return ExtractedContext(**final_result)

    def _extract_context_rule_based(self, title: str, description: str, 
                                   technologies: List[str], user_interests: List[str]) -> ExtractedContext:
        """Extract context using rule-based analysis"""
        
        # Use advanced tech detector for proper technology extraction
        try:
            from advanced_tech_detection import advanced_tech_detector
            full_text = f"{title} {description} {' '.join(technologies) if technologies else ''}"
            detected_techs = advanced_tech_detector.extract_technologies(full_text)
            
            # Extract technology categories from the detected technologies
            tech_categories = [tech['category'] for tech in detected_techs if isinstance(tech, dict) and 'category' in tech]
            
            # Resolve ambiguous terms
            resolved_technologies = self._resolve_ambiguous_terms(technologies)
            
            # Combine detected technologies with resolved ones
            all_technologies = list(set(tech_categories + resolved_technologies))
            
        except Exception as e:
            logger.warning(f"Advanced tech detection failed, using fallback: {e}")
            # Fallback to original method
            resolved_technologies = self._resolve_ambiguous_terms(technologies)
            all_technologies = resolved_technologies
        
        # Extract primary and secondary technologies
        primary_techs = self._extract_primary_technologies(title, description, all_technologies)
        secondary_techs = self._extract_secondary_technologies(title, description, all_technologies)
        
        # Extract core domains
        core_domains = self._extract_core_domains(title, description)
        
        # Extract learning objectives
        learning_objectives = self._extract_learning_objectives(title, description, user_interests)
        
        # Calculate complexity
        complexity = self._calculate_complexity(title, description, all_technologies)
        
        # Determine content types needed
        content_types = self._determine_content_types_needed(title, description, all_technologies)
        
        # Extract implicit requirements
        implicit_reqs = self._extract_implicit_requirements(title, description, all_technologies)
        
        # Resolve ambiguous terms
        ambiguous_resolved = self._resolve_ambiguous_terms_dict(technologies)
        
        # Calculate confidence score
        confidence = self._calculate_confidence_score(title, description, technologies)
        
        return ExtractedContext(
            primary_technologies=primary_techs,
            secondary_technologies=secondary_techs,
            core_domains=core_domains,
            learning_objectives=learning_objectives,
            complexity=complexity,
            content_types_needed=content_types,
            implicit_requirements=implicit_reqs,
            ambiguous_terms_resolved=ambiguous_resolved,
            confidence_score=confidence,
            analysis_metadata={
                'gemini_analysis': False,
                'rule_based_enhancement': True,
                'total_technologies': len(all_technologies),
                'analysis_methods': ['rule_based', 'advanced_tech_detection']
            },
            # Add unified engine compatible fields
            content_type=self._determine_content_type(title, description),
            difficulty=self._determine_difficulty(title, description),
            intent=self._determine_intent(title, description),
            key_concepts=all_technologies  # Use the properly extracted technologies instead of broken method
        )

    def _resolve_ambiguous_terms(self, technologies: List[str]) -> List[str]:
        """Resolve ambiguous technology terms"""
        resolved = []
        for tech in technologies:
            tech_lower = tech.lower().strip()
            resolved_tech = self.technology_mappings.get(tech_lower, tech)
            resolved.append(resolved_tech)
        return resolved

    def _resolve_ambiguous_terms_dict(self, technologies: List[str]) -> Dict[str, str]:
        """Resolve ambiguous terms and return mapping dictionary"""
        resolved_dict = {}
        for tech in technologies:
            tech_lower = tech.lower().strip()
            if tech_lower in self.technology_mappings:
                resolved_dict[tech] = self.technology_mappings[tech_lower]
        return resolved_dict

    def _extract_primary_technologies(self, title: str, description: str, 
                                     technologies: List[str]) -> List[str]:
        """Extract primary technologies from context"""
        text = f"{title} {description}".lower()
        primary_techs = []
        
        # Check for explicit technologies
        for tech in technologies:
            if tech.lower() in text:
                primary_techs.append(tech)
        
        # Extract from text using patterns
        tech_patterns = [
            r'\b(react|vue|angular|node\.?js|express|django|flask|spring|laravel)\b',
            r'\b(javascript|typescript|python|java|kotlin|swift|go|rust)\b',
            r'\b(mongodb|postgresql|mysql|redis|elasticsearch)\b',
            r'\b(docker|kubernetes|aws|azure|gcp)\b'
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, text)
            primary_techs.extend(matches)
        
        return list(set(primary_techs))

    def _extract_secondary_technologies(self, title: str, description: str, 
                                      technologies: List[str]) -> List[str]:
        """Extract secondary/supporting technologies"""
        text = f"{title} {description}".lower()
        secondary_techs = []
        
        # Supporting technologies patterns
        supporting_patterns = [
            r'\b(jest|cypress|selenium|webpack|vite|babel)\b',
            r'\b(eslint|prettier|git|github|gitlab)\b',
            r'\b(tailwind|bootstrap|material|antd|chakra)\b',
            r'\b(jwt|oauth|bcrypt|passport)\b'
        ]
        
        for pattern in supporting_patterns:
            matches = re.findall(pattern, text)
            secondary_techs.extend(matches)
        
        return list(set(secondary_techs))

    def _extract_core_domains(self, title: str, description: str) -> List[str]:
        """Extract core domains from context"""
        text = f"{title} {description}".lower()
        domains = []
        
        # Domain keywords
        domain_keywords = {
            'web': ['web', 'frontend', 'backend', 'fullstack', 'website'],
            'mobile': ['mobile', 'ios', 'android', 'app', 'application'],
            'data': ['data', 'machine learning', 'ai', 'analytics', 'ml'],
            'cloud': ['cloud', 'devops', 'infrastructure', 'deployment'],
            'security': ['security', 'authentication', 'authorization', 'encryption'],
            'performance': ['performance', 'optimization', 'scalability'],
            'testing': ['testing', 'quality', 'tdd', 'bdd', 'test'],
            'ui/ux': ['ui', 'ux', 'design', 'interface', 'user experience'],
            'api': ['api', 'rest', 'graphql', 'microservices'],
            'database': ['database', 'db', 'data modeling', 'orm'],
            'blockchain': ['blockchain', 'crypto', 'ethereum', 'bitcoin', 'smart contract', 'web3', 'solidity', 'defi', 'nft'],
            'web3': ['web3', 'ethereum', 'solidity', 'smart contract', 'blockchain', 'defi', 'nft', 'metamask']
        }
        
        for domain, keywords in domain_keywords.items():
            if any(keyword in text for keyword in keywords):
                domains.append(domain)
        
        return domains

    def _extract_learning_objectives(self, title: str, description: str, 
                                   user_interests: List[str]) -> List[str]:
        """Extract learning objectives from context"""
        objectives = []
        text = f"{title} {description}".lower()
        
        # Common learning objectives
        if 'learn' in text or 'tutorial' in text:
            objectives.append('Learn new technologies')
        
        if 'build' in text or 'create' in text:
            objectives.append('Build practical project')
        
        if 'deploy' in text or 'production' in text:
            objectives.append('Deploy to production')
        
        if 'test' in text or 'testing' in text:
            objectives.append('Implement testing')
        
        if 'api' in text or 'backend' in text:
            objectives.append('Develop backend APIs')
        
        if 'frontend' in text or 'ui' in text:
            objectives.append('Create user interface')
        
        # Add user-specific objectives based on interests
        for interest in user_interests:
            if interest.lower() in text:
                objectives.append(f'Apply {interest} knowledge')
        
        return objectives

    def _calculate_complexity(self, title: str, description: str, 
                            technologies: List[str]) -> float:
        """Calculate project complexity score"""
        complexity = 0.5  # Base complexity
        
        text = f"{title} {description}".lower()
        
        # Technology complexity factors
        advanced_techs = ['kubernetes', 'microservices', 'machine learning', 'ai', 'blockchain']
        for tech in advanced_techs:
            if tech in text or any(tech in t.lower() for t in technologies):
                complexity += 0.2
        
        # Project scope factors
        if 'fullstack' in text or 'full-stack' in text:
            complexity += 0.15
        
        if 'production' in text or 'deploy' in text:
            complexity += 0.1
        
        if 'testing' in text or 'tdd' in text:
            complexity += 0.05
        
        # Scale factors
        if 'scalable' in text or 'performance' in text:
            complexity += 0.1
        
        if 'real-time' in text or 'websocket' in text:
            complexity += 0.1
        
        return min(1.0, complexity)

    def _determine_content_types_needed(self, title: str, description: str, 
                                      technologies: List[str]) -> List[str]:
        """Determine what content types would be most helpful"""
        content_types = []
        text = f"{title} {description}".lower()
        
        # Always include tutorial for learning
        content_types.append('tutorial')
        
        # Add based on context
        if 'api' in text or 'backend' in text:
            content_types.append('documentation')
        
        if 'error' in text or 'debug' in text:
            content_types.append('troubleshooting')
        
        if 'best practice' in text or 'pattern' in text:
            content_types.append('best_practice')
        
        if 'example' in text or 'demo' in text:
            content_types.append('example')
        
        if 'build' in text or 'create' in text:
            content_types.append('project')
        
        return list(set(content_types))

    def _extract_implicit_requirements(self, title: str, description: str, 
                                     technologies: List[str]) -> List[str]:
        """Extract implicit requirements not explicitly stated"""
        requirements = []
        text = f"{title} {description}".lower()
        
        # Common implicit requirements
        if any(tech in text for tech in ['react', 'vue', 'angular']):
            requirements.append('JavaScript/TypeScript knowledge')
        
        if 'database' in text or any(tech in text for tech in ['mongodb', 'postgresql', 'mysql']):
            requirements.append('Database design understanding')
        
        if 'api' in text or 'backend' in text:
            requirements.append('HTTP and REST knowledge')
        
        if 'deploy' in text or 'production' in text:
            requirements.append('Deployment and hosting knowledge')
        
        if 'testing' in text:
            requirements.append('Testing framework knowledge')
        
        if 'git' in text or 'version control' in text:
            requirements.append('Version control with Git')
        
        return requirements

    def _calculate_confidence_score(self, title: str, description: str, 
                                  technologies: List[str]) -> float:
        """Calculate confidence score for the analysis"""
        confidence = 0.5  # Base confidence
        
        # More information = higher confidence
        if len(title) > 10:
            confidence += 0.1
        
        if len(description) > 50:
            confidence += 0.1
        
        if technologies:
            confidence += 0.1
        
        # Specific technologies mentioned
        if any(tech in title.lower() or tech in description.lower() 
               for tech in ['react', 'node', 'python', 'java']):
            confidence += 0.1
        
        # Clear project type
        if any(keyword in title.lower() for keyword in ['app', 'website', 'api', 'project']):
            confidence += 0.1
        
        return min(1.0, confidence)

    def _get_fallback_context(self, title: str, description: str, 
                            technologies: List[str], user_interests: List[str]) -> ExtractedContext:
        """Get fallback context when all analysis fails"""
        return ExtractedContext(
            primary_technologies=technologies or [],
            secondary_technologies=[],
            core_domains=['general'],
            learning_objectives=['Learn new skills'],
            complexity=0.5,
            content_types_needed=['tutorial'],
            implicit_requirements=[],
            ambiguous_terms_resolved={},
            confidence_score=0.3,
            analysis_metadata={
                'gemini_analysis': False,
                'rule_based_enhancement': False,
                'total_technologies': len(technologies or []),
                'analysis_methods': ['fallback']
            }
        )

    def _get_empty_parsed_data(self) -> Dict[str, Any]:
        """Get empty parsed data structure"""
        return {
            'primary_technologies': [],
            'secondary_technologies': [],
            'core_domains': [],
            'learning_objectives': [],
            'complexity': 0.5,
            'content_types_needed': [],
            'implicit_requirements': [],
            'ambiguous_terms_resolved': {},
            'confidence_score': 0.3,
            'analysis_notes': 'Analysis failed'
        }

    def _normalize_list(self, data: Any) -> List[str]:
        """Normalize list data"""
        if isinstance(data, list):
            return [str(item).strip() for item in data if item]
        return []

    def _normalize_dict(self, data: Any) -> Dict[str, str]:
        """Normalize dictionary data"""
        if isinstance(data, dict):
            return {str(k).strip(): str(v).strip() for k, v in data.items() if k and v}
        return {}

    def _normalize_float(self, data: Any) -> float:
        """Normalize float data"""
        try:
            value = float(data)
            return max(0.0, min(1.0, value))
        except (ValueError, TypeError):
            return 0.5

    def _determine_content_type(self, title: str, description: str) -> str:
        """Determine content type for unified engine compatibility"""
        text = f"{title} {description}".lower()
        
        # Check content type patterns
        if any(keyword in text for keyword in ['tutorial', 'guide', 'how to', 'learn']):
            return 'tutorial'
        elif any(keyword in text for keyword in ['documentation', 'api', 'reference']):
            return 'documentation'
        elif any(keyword in text for keyword in ['example', 'demo', 'sample']):
            return 'example'
        elif any(keyword in text for keyword in ['error', 'fix', 'debug', 'troubleshoot']):
            return 'troubleshooting'
        elif any(keyword in text for keyword in ['best practice', 'pattern', 'architecture']):
            return 'best_practice'
        elif any(keyword in text for keyword in ['build', 'create', 'develop', 'project']):
            return 'project'
        else:
            return 'general'

    def _determine_difficulty(self, title: str, description: str) -> str:
        """Determine difficulty for unified engine compatibility"""
        text = f"{title} {description}".lower()
        
        if any(keyword in text for keyword in ['beginner', 'basic', 'intro', 'simple']):
            return 'beginner'
        elif any(keyword in text for keyword in ['advanced', 'expert', 'complex', 'master']):
            return 'advanced'
        else:
            return 'intermediate'

    def _determine_intent(self, title: str, description: str) -> str:
        """Determine intent for unified engine compatibility"""
        text = f"{title} {description}".lower()
        
        if any(keyword in text for keyword in ['learn', 'understand', 'study']):
            return 'learning'
        elif any(keyword in text for keyword in ['build', 'create', 'develop', 'implement']):
            return 'implementation'
        elif any(keyword in text for keyword in ['debug', 'fix', 'error', 'troubleshoot']):
            return 'troubleshooting'
        elif any(keyword in text for keyword in ['optimize', 'improve', 'performance']):
            return 'optimization'
        else:
            return 'general'

    def _extract_key_concepts_enhanced(self, text: str) -> List[str]:
        """Extract key concepts for unified engine compatibility"""
        try:
            # Use spaCy for better concept extraction if available
            if hasattr(self, 'spacy_available') and self.spacy_available:
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
                # Fallback to simple keyword extraction - FIXED VERSION
                # Split text into words properly, handling punctuation and special characters
                import re
                
                # Clean the text first - remove extra whitespace and normalize
                text = re.sub(r'\s+', ' ', text.lower().strip())
                
                # Split into words, handling punctuation properly
                words = re.findall(r'[a-zA-Z0-9]+(?:\-[a-zA-Z0-9]+)*', text)
                
                # Filter out stop words and short words
                stop_words = {
                    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                    'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                    'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
                    'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
                    'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
                }
                
                # Filter words: must be longer than 2 characters and not in stop words
                key_words = [word for word in words if len(word) > 2 and word not in stop_words]
                
                # Count occurrences and return most common
                word_counts = Counter(key_words)
                return [word for word, count in word_counts.most_common(10)]
                
        except Exception as e:
            logger.warning(f"Error in enhanced key concept extraction: {e}")
            # Return empty list as fallback
            return []

# Global instance
enhanced_context_extractor = EnhancedContextExtractor() 