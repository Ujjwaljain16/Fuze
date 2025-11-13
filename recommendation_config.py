"""
Recommendation Engine Configuration
====================================
ALL configurable parameters for the recommendation system.
NO HARDCODED VALUES - everything is here!

This allows easy tuning without touching core engine logic.
"""

from typing import Dict, List
import os


class RecommendationConfig:
    """Central configuration for all recommendation settings"""
    
    # ============================================================================
    # SCORING WEIGHTS (0.0 - 1.0, must sum to 1.0 where applicable)
    # ============================================================================
    
    # FastSemanticEngine weights
    FAST_ENGINE_WEIGHTS = {
        'technology_overlap': float(os.getenv('FAST_TECH_WEIGHT', '0.5')),      # 50%
        'semantic_similarity': float(os.getenv('FAST_SEMANTIC_WEIGHT', '0.4')), # 40%
        'quality_score': float(os.getenv('FAST_QUALITY_WEIGHT', '0.1'))         # 10%
    }
    
    # ContextAwareEngine weights
    CONTEXT_ENGINE_WEIGHTS = {
        'technology': float(os.getenv('CONTEXT_TECH_WEIGHT', '0.35')),          # 35%
        'semantic': float(os.getenv('CONTEXT_SEMANTIC_WEIGHT', '0.25')),        # 25%
        'content_type': float(os.getenv('CONTEXT_CONTENT_TYPE_WEIGHT', '0.15')), # 15%
        'difficulty': float(os.getenv('CONTEXT_DIFFICULTY_WEIGHT', '0.10')),    # 10%
        'quality': float(os.getenv('CONTEXT_QUALITY_WEIGHT', '0.05')),          # 5%
        'intent_alignment': float(os.getenv('CONTEXT_INTENT_WEIGHT', '0.10'))   # 10%
    }
    
    # ============================================================================
    # SCORING THRESHOLDS
    # ============================================================================
    
    # Minimum scores for various criteria
    THRESHOLDS = {
        'min_quality_score': int(os.getenv('MIN_QUALITY_SCORE', '3')),          # 1-10 scale
        'high_similarity': float(os.getenv('HIGH_SIMILARITY', '0.8')),          # 0-1 scale
        'high_tech_overlap': float(os.getenv('HIGH_TECH_OVERLAP', '0.7')),      # 0-1 scale
        'high_quality': float(os.getenv('HIGH_QUALITY', '0.8')),                # 0-1 scale
        'medium_quality': float(os.getenv('MEDIUM_QUALITY', '0.6')),            # 0-1 scale
        'good_tech_match': float(os.getenv('GOOD_TECH_MATCH', '0.6')),          # 0-1 scale
        'good_semantic': float(os.getenv('GOOD_SEMANTIC', '0.7')),              # 0-1 scale
    }
    
    # ============================================================================
    # BOOST VALUES
    # ============================================================================
    
    BOOSTS = {
        'user_content': float(os.getenv('USER_CONTENT_BOOST', '0.1')),          # +10%
        'project_context': float(os.getenv('PROJECT_CONTEXT_BOOST', '0.02')),   # +2%
        'relevance_multiplier': float(os.getenv('RELEVANCE_MULTIPLIER', '0.15')), # 15% of relevance score
        'fast_engine_user_boost': float(os.getenv('FAST_USER_BOOST', '0.05'))   # +5% for fast engine
    }
    
    # ============================================================================
    # TECHNOLOGY RELATIONS (Dynamic - can be updated from DB/API)
    # ============================================================================
    
    TECHNOLOGY_RELATIONS = {
        'javascript': ['js', 'node', 'nodejs', 'react', 'vue', 'angular', 'typescript', 'ts'],
        'python': ['py', 'django', 'flask', 'fastapi', 'python3', 'pip'],
        'java': ['spring', 'maven', 'gradle', 'jvm', 'springboot'],
        'react': ['reactjs', 'jsx', 'tsx', 'react-native'],
        'typescript': ['ts', 'javascript', 'js'],
        'node': ['nodejs', 'javascript', 'npm', 'express'],
        'sql': ['mysql', 'postgresql', 'postgres', 'database', 'sqlite'],
        'mongodb': ['nosql', 'database', 'mongo'],
        'docker': ['container', 'kubernetes', 'k8s', 'containerization'],
        'aws': ['amazon', 'cloud', 'ec2', 's3', 'lambda'],
        'git': ['github', 'gitlab', 'version-control', 'bitbucket'],
        'frontend': ['html', 'css', 'javascript', 'ui', 'ux'],
        'backend': ['api', 'server', 'database', 'rest'],
        'react-native': ['react', 'mobile', 'ios', 'android'],
        'vue': ['vuejs', 'javascript', 'frontend'],
        'angular': ['angularjs', 'javascript', 'typescript'],
        'ruby': ['rails', 'ruby-on-rails', 'gem'],
        'php': ['laravel', 'symfony', 'wordpress'],
        'rust': ['cargo', 'rustc'],
        'go': ['golang', 'gofmt'],
        'kubernetes': ['k8s', 'docker', 'container', 'orchestration'],
        'redis': ['cache', 'nosql', 'in-memory'],
        'postgresql': ['postgres', 'sql', 'database'],
        'mysql': ['sql', 'database', 'mariadb'],
        'graphql': ['api', 'query-language'],
        'rest': ['api', 'http', 'restful'],
        'machine-learning': ['ml', 'ai', 'tensorflow', 'pytorch'],
        'tensorflow': ['ml', 'machine-learning', 'ai'],
        'pytorch': ['ml', 'machine-learning', 'ai'],
    }
    
    # ============================================================================
    # INTENT-BASED WEIGHTS (Dynamic based on user intent)
    # ============================================================================
    
    INTENT_WEIGHTS = {
        'tech_match': {
            'build': float(os.getenv('INTENT_BUILD_TECH', '0.40')),
            'implement': float(os.getenv('INTENT_IMPLEMENT_TECH', '0.40')),
            'optimize': float(os.getenv('INTENT_OPTIMIZE_TECH', '0.40')),
            'learn': float(os.getenv('INTENT_LEARN_TECH', '0.35')),
            'default': float(os.getenv('INTENT_DEFAULT_TECH', '0.30'))
        },
        'content_type': {
            'quick_tutorial': float(os.getenv('INTENT_QUICK_CONTENT', '0.25')),
            'deep_dive': float(os.getenv('INTENT_DEEP_CONTENT', '0.20')),
            'default': float(os.getenv('INTENT_DEFAULT_CONTENT', '0.15'))
        },
        'difficulty': {
            'learn': float(os.getenv('INTENT_LEARN_DIFFICULTY', '0.25')),
            'default': float(os.getenv('INTENT_DEFAULT_DIFFICULTY', '0.15'))
        },
        'urgency': {
            'high': float(os.getenv('INTENT_HIGH_URGENCY', '0.20')),
            'medium': float(os.getenv('INTENT_MEDIUM_URGENCY', '0.10')),
            'low': float(os.getenv('INTENT_LOW_URGENCY', '0.05'))
        }
    }
    
    # ============================================================================
    # DIFFICULTY MAPPING
    # ============================================================================
    
    DIFFICULTY_SCORES = {
        'beginner': 1,
        'intermediate': 2,
        'advanced': 3,
        'expert': 4
    }
    
    # ============================================================================
    # CONTENT TYPE PREFERENCES
    # ============================================================================
    
    CONTENT_TYPE_PREFERENCES = {
        'tutorial': {
            'learn': float(os.getenv('TUTORIAL_LEARN_PREF', '1.0')),
            'build': float(os.getenv('TUTORIAL_BUILD_PREF', '0.8')),
            'default': float(os.getenv('TUTORIAL_DEFAULT_PREF', '0.7'))
        },
        'documentation': {
            'build': float(os.getenv('DOCS_BUILD_PREF', '1.0')),
            'implement': float(os.getenv('DOCS_IMPLEMENT_PREF', '0.9')),
            'default': float(os.getenv('DOCS_DEFAULT_PREF', '0.6'))
        },
        'article': {
            'learn': float(os.getenv('ARTICLE_LEARN_PREF', '0.8')),
            'default': float(os.getenv('ARTICLE_DEFAULT_PREF', '0.7'))
        },
        'video': {
            'learn': float(os.getenv('VIDEO_LEARN_PREF', '0.9')),
            'default': float(os.getenv('VIDEO_DEFAULT_PREF', '0.7'))
        }
    }
    
    # ============================================================================
    # PERFORMANCE SETTINGS
    # ============================================================================
    
    PERFORMANCE = {
        'batch_size': int(os.getenv('EMBEDDING_BATCH_SIZE', '32')),
        'max_content_length': int(os.getenv('MAX_CONTENT_LENGTH', '1000')),
        'query_length': int(os.getenv('QUERY_LENGTH', '500')),
        'cache_duration': int(os.getenv('CACHE_DURATION', '3600')),  # seconds
        'max_db_retries': int(os.getenv('MAX_DB_RETRIES', '3')),
        'retry_delay': float(os.getenv('RETRY_DELAY', '0.5'))  # seconds
    }
    
    # ============================================================================
    # ML ENHANCEMENT SETTINGS
    # ============================================================================
    
    ML_SETTINGS = {
        'enable_ml_boost': os.getenv('ENABLE_ML_BOOST', 'true').lower() == 'true',
        'ml_boost_weight': float(os.getenv('ML_BOOST_WEIGHT', '0.15')),
        'tfidf_min_df': int(os.getenv('TFIDF_MIN_DF', '1')),
        'tfidf_max_df': float(os.getenv('TFIDF_MAX_DF', '0.85')),
        'tfidf_max_features': int(os.getenv('TFIDF_MAX_FEATURES', '5000'))
    }
    
    # ============================================================================
    # DEFAULT VALUES (Fallbacks)
    # ============================================================================
    
    DEFAULTS = {
        'content_type': 'article',
        'difficulty': 'intermediate',
        'quality_score': 6,
        'relevance_score': 0,
        'max_recommendations': 10,
        'diversity_weight': 0.3,
        'quality_threshold': 3
    }
    
    # ============================================================================
    # FEATURE FLAGS
    # ============================================================================
    
    FEATURES = {
        'use_intent_analysis': os.getenv('USE_INTENT_ANALYSIS', 'true').lower() == 'true',
        'use_universal_matcher': os.getenv('USE_UNIVERSAL_MATCHER', 'true').lower() == 'true',
        'use_ml_enhancement': os.getenv('USE_ML_ENHANCEMENT', 'true').lower() == 'true',
        'use_batch_embeddings': os.getenv('USE_BATCH_EMBEDDINGS', 'true').lower() == 'true',
        'use_gemini_reasoning': os.getenv('USE_GEMINI_REASONING', 'false').lower() == 'true',
        'enable_caching': os.getenv('ENABLE_CACHING', 'true').lower() == 'true',
        'enable_diversity': os.getenv('ENABLE_DIVERSITY', 'true').lower() == 'true'
    }
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    @classmethod
    def get_tech_relations(cls, tech: str) -> List[str]:
        """Get related technologies for a given technology"""
        tech = tech.lower().strip()
        return cls.TECHNOLOGY_RELATIONS.get(tech, [])
    
    @classmethod
    def add_tech_relation(cls, tech: str, related: List[str]):
        """Dynamically add a technology relation"""
        tech = tech.lower().strip()
        if tech in cls.TECHNOLOGY_RELATIONS:
            cls.TECHNOLOGY_RELATIONS[tech].extend(related)
            cls.TECHNOLOGY_RELATIONS[tech] = list(set(cls.TECHNOLOGY_RELATIONS[tech]))
        else:
            cls.TECHNOLOGY_RELATIONS[tech] = related
    
    @classmethod
    def get_difficulty_score(cls, difficulty: str) -> int:
        """Get numeric score for difficulty level"""
        return cls.DIFFICULTY_SCORES.get(difficulty.lower(), 2)
    
    @classmethod
    def get_content_type_preference(cls, content_type: str, intent_goal: str = 'default') -> float:
        """Get content type preference based on intent"""
        content_prefs = cls.CONTENT_TYPE_PREFERENCES.get(content_type, {})
        return content_prefs.get(intent_goal, content_prefs.get('default', 0.7))
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate that all weights sum correctly"""
        # Check FastEngine weights sum to 1.0
        fast_sum = sum(cls.FAST_ENGINE_WEIGHTS.values())
        if not (0.99 <= fast_sum <= 1.01):  # Allow small floating point error
            print(f"⚠️ Warning: FAST_ENGINE_WEIGHTS sum to {fast_sum}, should be 1.0")
            return False
        
        # Check ContextEngine weights sum to 1.0
        context_sum = sum(cls.CONTEXT_ENGINE_WEIGHTS.values())
        if not (0.99 <= context_sum <= 1.01):
            print(f"⚠️ Warning: CONTEXT_ENGINE_WEIGHTS sum to {context_sum}, should be 1.0")
            return False
        
        return True
    
    @classmethod
    def print_config(cls):
        """Print current configuration"""
        print("=" * 80)
        print("RECOMMENDATION ENGINE CONFIGURATION")
        print("=" * 80)
        print("\n📊 FAST ENGINE WEIGHTS:")
        for key, val in cls.FAST_ENGINE_WEIGHTS.items():
            print(f"   {key}: {val}")
        
        print("\n📊 CONTEXT ENGINE WEIGHTS:")
        for key, val in cls.CONTEXT_ENGINE_WEIGHTS.items():
            print(f"   {key}: {val}")
        
        print("\n🎯 THRESHOLDS:")
        for key, val in cls.THRESHOLDS.items():
            print(f"   {key}: {val}")
        
        print("\n⚡ BOOSTS:")
        for key, val in cls.BOOSTS.items():
            print(f"   {key}: {val}")
        
        print("\n🚀 PERFORMANCE:")
        for key, val in cls.PERFORMANCE.items():
            print(f"   {key}: {val}")
        
        print("\n🤖 ML SETTINGS:")
        for key, val in cls.ML_SETTINGS.items():
            print(f"   {key}: {val}")
        
        print("\n🎛️  FEATURES:")
        for key, val in cls.FEATURES.items():
            print(f"   {key}: {val}")
        
        print("\n✅ Configuration valid:", cls.validate_config())
        print("=" * 80)


# Initialize and validate on import
if __name__ == "__main__":
    RecommendationConfig.print_config()

