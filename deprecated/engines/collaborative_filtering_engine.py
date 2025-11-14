#!/usr/bin/env python3
"""
Collaborative Filtering Engine
Implements collaborative filtering using the implicit library
"""

import os
import sys
import logging
import json
import pickle
import time
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
import pandas as pd

# Fix OpenBLAS threading issue
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class UserInteraction:
    """User interaction data structure"""
    user_id: int
    content_id: int
    interaction_type: str  # 'view', 'like', 'bookmark', 'share', 'rating'
    interaction_value: float = 1.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class CFRecommendation:
    """Collaborative filtering recommendation result"""
    content_id: int
    cf_score: float
    confidence: float
    interaction_count: int
    similar_users_count: int
    recommendation_reason: str

class CollaborativeFilteringEngine:
    """Collaborative filtering engine using multiple algorithms"""
    
    def __init__(self, model_type: str = 'als'):
        self.model_type = model_type
        self.model = None
        self.user_item_matrix = None
        self.user_mapping = {}
        self.item_mapping = {}
        self.reverse_user_mapping = {}
        self.reverse_item_mapping = {}
        self.interaction_data = []
        
        # ML Libraries
        try:
            import implicit
            from implicit.als import AlternatingLeastSquares
            from implicit.bpr import BayesianPersonalizedRanking
            from implicit.lmf import LogisticMatrixFactorization
            self.IMPLICIT_AVAILABLE = True
            self.AlternatingLeastSquares = AlternatingLeastSquares
            self.BayesianPersonalizedRanking = BayesianPersonalizedRanking
            self.LogisticMatrixFactorization = LogisticMatrixFactorization
            logger.info("✅ Implicit library imported successfully")
        except ImportError as e:
            self.IMPLICIT_AVAILABLE = False
            logger.warning(f"⚠️ Implicit library not available: {e}")

        try:
            from sklearn.metrics.pairwise import cosine_similarity
            self.SKLEARN_AVAILABLE = True
            self.cosine_similarity = cosine_similarity
        except ImportError as e:
            self.SKLEARN_AVAILABLE = False
            logger.warning(f"⚠️ scikit-learn not available: {e}")
        
        if self.IMPLICIT_AVAILABLE:
            self._initialize_model()
            # Add sample interactions for testing
            self._add_sample_interactions()
    
    def _initialize_model(self):
        """Initialize the collaborative filtering model"""
        try:
            if self.model_type == 'als':
                self.model = self.AlternatingLeastSquares(
                    factors=100,
                    regularization=0.01,
                    iterations=50,
                    random_state=42
                )
            elif self.model_type == 'bpr':
                self.model = self.BayesianPersonalizedRanking(
                    factors=100,
                    learning_rate=0.01,
                    regularization=0.01,
                    iterations=100,
                    random_state=42
                )
            elif self.model_type == 'lmf':
                self.model = self.LogisticMatrixFactorization(
                    factors=100,
                    learning_rate=0.01,
                    regularization=0.01,
                    iterations=100,
                    random_state=42
                )
            else:
                logger.warning(f"Unknown model type: {self.model_type}, using ALS")
                self.model = self.AlternatingLeastSquares(
                    factors=100,
                    regularization=0.01,
                    iterations=50,
                    random_state=42
                )
            
            logger.info(f"✅ {self.model_type.upper()} collaborative filtering model initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.model_type} model: {e}")
            self.model = None
    
    def _add_sample_interactions(self):
        """Add sample interactions for testing - will be replaced with real user interaction data"""
        try:
            # Try to get REAL user interaction data first
            real_interactions = self._get_real_user_interactions()
            
            if real_interactions:
                # Use REAL user interaction data
                for user_id, content_id, interaction_strength in real_interactions:
                    self.add_interaction(user_id, content_id, interaction_strength)
                logger.info(f"✅ Added {len(real_interactions)} REAL user interactions to CF model")
                # Train with real data
                self.train_model()
                return
            
            # Fallback: Create intelligent sample interactions that mimic real user behavior
            logger.info("⚠️ Using intelligent sample interactions (real user data not available)")
            
            # Create realistic user-content interaction patterns
            sample_interactions = []
            
            # User 1: Python/Web Developer (likes Python, React, JavaScript content)
            for content_id in range(1, 21):  # Content 1-20
                if content_id <= 10:  # Python content
                    strength = np.random.uniform(0.7, 1.0)
                elif content_id <= 15:  # Web development
                    strength = np.random.uniform(0.6, 0.9)
                else:  # Other content
                    strength = np.random.uniform(0.3, 0.7)
                sample_interactions.append((1, content_id, strength))
            
            # User 2: Machine Learning Engineer (likes ML, AI, Python content)
            for content_id in range(1, 21):
                if content_id <= 8:  # ML/AI content
                    strength = np.random.uniform(0.8, 1.0)
                elif content_id <= 12:  # Python content
                    strength = np.random.uniform(0.7, 0.9)
                elif content_id <= 16:  # Data Science
                    strength = np.random.uniform(0.6, 0.8)
                else:  # Other content
                    strength = np.random.uniform(0.4, 0.6)
                sample_interactions.append((2, content_id, strength))
            
            # User 3: Full-Stack Developer (likes diverse content)
            for content_id in range(1, 21):
                if content_id <= 7:  # Web development
                    strength = np.random.uniform(0.8, 1.0)
                elif content_id <= 12:  # Python/Backend
                    strength = np.random.uniform(0.7, 0.9)
                elif content_id <= 16:  # DevOps/Infrastructure
                    strength = np.random.uniform(0.6, 0.8)
                else:  # Other content
                    strength = np.random.uniform(0.5, 0.7)
                sample_interactions.append((3, content_id, strength))
            
            # Add interactions to the model
            for user_id, content_id, strength in sample_interactions:
                # Convert strength to proper interaction type
                if strength >= 0.8:
                    interaction_type = 'bookmark'
                elif strength >= 0.6:
                    interaction_type = 'like'
                else:
                    interaction_type = 'view'
                
                self.add_interaction(user_id, content_id, interaction_type, strength)
            
            logger.info(f"✅ Added {len(sample_interactions)} intelligent sample interactions to CF model")
            
            # Train the model with sample data
            self.train_model()
            
        except Exception as e:
            logger.error(f"Error adding sample interactions: {e}")
    
    def _get_real_user_interactions(self) -> Optional[List[Tuple[int, int, float]]]:
        """Get REAL user interaction data from database"""
        try:
            # INTEGRATION: Use real user interactions for training
            from models import SavedContent, ContentAnalysis, User, db
            from app import create_app
            
            app = create_app()
            with app.app_context():
                # Get real user interactions based on saved content and analysis
                interactions = []
                
                # Get all users
                users = User.query.all()
                if not users:
                    logger.info("No users found for collaborative filtering")
                    return None
                
                for user in users:
                    # Get user's saved content
                    user_content = SavedContent.query.filter_by(user_id=user.id).all()
                    
                    for content in user_content:
                        # Get content analysis if available
                        analysis = ContentAnalysis.query.filter_by(content_id=content.id).first()
                        
                        # Calculate interaction strength based on real data
                        interaction_strength = self._calculate_real_interaction_strength(content, analysis)
                        
                        if interaction_strength > 0:
                            interactions.append((user.id, content.id, interaction_strength))
                
                if interactions:
                    logger.info(f"✅ Found {len(interactions)} real user interactions for collaborative filtering")
                    return interactions
                else:
                    logger.info("No real interactions found, will use intelligent samples")
                    return None
                    
        except Exception as e:
            logger.warning(f"Real user interactions not available: {e}")
            return None
    
    def _calculate_real_interaction_strength(self, content: 'SavedContent', analysis: Optional['ContentAnalysis']) -> float:
        """Calculate real interaction strength based on content properties"""
        try:
            strength = 0.0
            
            # Base strength from quality score
            if content.quality_score:
                strength += content.quality_score / 10.0 * 0.4
            
            # Boost from content analysis
            if analysis:
                # Content type preference
                if analysis.content_type:
                    strength += 0.2
                
                # Technology relevance
                if analysis.technology_tags:
                    strength += 0.15
                
                # Key concepts
                if analysis.key_concepts:
                    strength += 0.1
                
                # Difficulty level
                if analysis.difficulty_level:
                    strength += 0.1
            
            # Boost from content properties
            if content.tags:
                strength += 0.05
            
            if content.extracted_text and len(content.extracted_text) > 100:
                strength += 0.05
            
            # Normalize to 0-1 range
            return min(max(strength, 0.1), 1.0)
            
        except Exception as e:
            logger.warning(f"Error calculating interaction strength: {e}")
            return 0.5
    
    def add_interaction(self, user_id: int, content_id: int, interaction_type: str, 
                       interaction_value: float = 1.0, timestamp: Optional[datetime] = None):
        """Add a user interaction"""
        try:
            interaction = UserInteraction(
                user_id=user_id,
                content_id=content_id,
                interaction_type=interaction_type,
                interaction_value=interaction_value,
                timestamp=timestamp
            )
            
            self.interaction_data.append(interaction)
            logger.debug(f"Added interaction: User {user_id} -> Content {content_id} ({interaction_type})")
            
        except Exception as e:
            logger.error(f"Error adding interaction: {e}")
    
    def add_interactions_batch(self, interactions: List[UserInteraction]):
        """Add multiple interactions at once"""
        try:
            self.interaction_data.extend(interactions)
            logger.info(f"Added {len(interactions)} interactions in batch")
            
        except Exception as e:
            logger.error(f"Error adding batch interactions: {e}")
    
    def _create_user_item_matrix(self):
        """Create user-item interaction matrix"""
        try:
            if not self.interaction_data:
                logger.warning("No interaction data available")
                return None
            
            # Create interaction dataframe
            df = pd.DataFrame([
                {
                    'user_id': i.user_id,
                    'content_id': i.content_id,
                    'interaction_value': self._normalize_interaction(i.interaction_type, i.interaction_value)
                }
                for i in self.interaction_data
            ])
            
            # Create user and item mappings
            unique_users = df['user_id'].unique()
            unique_items = df['content_id'].unique()
            
            self.user_mapping = {user_id: idx for idx, user_id in enumerate(unique_users)}
            self.item_mapping = {item_id: idx for idx, item_id in enumerate(unique_items)}
            self.reverse_user_mapping = {idx: user_id for user_id, idx in self.user_mapping.items()}
            self.reverse_item_mapping = {idx: item_id for item_id, idx in self.item_mapping.items()}
            
            # Create sparse matrix
            user_indices = [self.user_mapping[uid] for uid in df['user_id']]
            item_indices = [self.item_mapping[iid] for iid in df['content_id']]
            values = df['interaction_value'].values
            
            # Create CSR matrix
            from scipy.sparse import csr_matrix
            self.user_item_matrix = csr_matrix(
                (values, (user_indices, item_indices)),
                shape=(len(unique_users), len(unique_items))
            )
            
            logger.info(f"✅ Created user-item matrix: {len(unique_users)} users × {len(unique_items)} items")
            return self.user_item_matrix
            
        except Exception as e:
            logger.error(f"Error creating user-item matrix: {e}")
            return None
    
    def _normalize_interaction(self, interaction_type: str, value: float) -> float:
        """Normalize interaction values based on type"""
        try:
            # Ensure interaction_type is a string
            if not isinstance(interaction_type, str):
                # If interaction_type is not a string, treat it as a generic interaction
                interaction_type = 'view'
            
            # Base weights for different interaction types
            type_weights = {
                'view': 1.0,
                'like': 3.0,
                'bookmark': 5.0,
                'share': 4.0,
                'rating': 2.0,
                'click': 1.5,
                'dwell_time': 2.5
            }
            
            base_weight = type_weights.get(interaction_type.lower(), 1.0)
            
            # Normalize value if it's a rating (1-5 scale)
            if interaction_type.lower() == 'rating':
                normalized_value = (value - 1) / 4.0  # Convert 1-5 to 0-1
            else:
                normalized_value = min(value / 10.0, 1.0)  # Cap at 10 interactions
            
            return base_weight * normalized_value
            
        except Exception as e:
            logger.error(f"Error normalizing interaction: {e}")
            return 1.0
    
    def train_model(self):
        """Train the collaborative filtering model"""
        if not self.IMPLICIT_AVAILABLE or not self.model:
            logger.error("Model not available for training")
            return False
        
        try:
            # Create user-item matrix
            matrix = self._create_user_item_matrix()
            if matrix is None:
                return False
            
            # Train the model
            start_time = time.time()
            self.model.fit(matrix)
            training_time = time.time() - start_time
            
            logger.info(f"✅ {self.model_type.upper()} model trained in {training_time:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            return False
    
    def get_recommendations(self, user_id: int, n_recommendations: int = 10, 
                          min_score: float = 0.1) -> List[CFRecommendation]:
        """Get collaborative filtering recommendations for a user"""
        if not self.model or self.user_item_matrix is None:
            logger.warning("Model not trained, returning empty recommendations")
            return []
        
        try:
            # Check if user exists in mapping
            if user_id not in self.user_mapping:
                logger.warning(f"User {user_id} not found in training data")
                return []
            
            user_idx = self.user_mapping[user_id]
            
            # Get recommendations from model
            if self.model_type == 'als':
                item_indices, scores = self.model.recommend(
                    user_idx, 
                    self.user_item_matrix[user_idx], 
                    N=n_recommendations * 2  # Get more to filter by score
                )
            else:
                # For BPR and LMF, use similar approach
                user_items = self.user_item_matrix[user_idx]
                item_indices, scores = self.model.recommend(
                    user_idx, 
                    user_items, 
                    N=n_recommendations * 2
                )
            
            # Process recommendations
            cf_recommendations = []
            for item_idx, score in zip(item_indices, scores):
                if score >= min_score:
                    content_id = self.reverse_item_mapping[item_idx]
                    
                    # Calculate confidence and additional metrics
                    confidence = self._calculate_confidence(user_idx, item_idx, score)
                    interaction_count = self._get_item_interaction_count(item_idx)
                    similar_users_count = self._get_similar_users_count(user_idx, item_idx)
                    
                    recommendation = CFRecommendation(
                        content_id=content_id,
                        cf_score=float(score),
                        confidence=confidence,
                        interaction_count=interaction_count,
                        similar_users_count=similar_users_count,
                        recommendation_reason=self._generate_recommendation_reason(score, interaction_count, similar_users_count)
                    )
                    
                    cf_recommendations.append(recommendation)
                    
                    if len(cf_recommendations) >= n_recommendations:
                        break
            
            # Sort by score
            cf_recommendations.sort(key=lambda x: x.cf_score, reverse=True)
            
            logger.info(f"✅ Generated {len(cf_recommendations)} CF recommendations for user {user_id}")
            return cf_recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return []
    
    def get_similar_users(self, user_id: int, n_similar: int = 5) -> List[Tuple[int, float]]:
        """Get similar users based on interaction patterns"""
        if not self.model or self.user_item_matrix is None:
            return []
        
        try:
            if user_id not in self.user_mapping:
                return []
            
            user_idx = self.user_mapping[user_id]
            user_items = self.user_item_matrix[user_idx]
            
            # Get similar users
            similar_users = self.model.similar_users(user_idx, N=n_similar + 1)  # +1 to exclude self
            
            # Filter out self and convert to user IDs
            similar_user_pairs = []
            for similar_user_idx, similarity in similar_users:
                if similar_user_idx != user_idx:
                    similar_user_id = self.reverse_user_mapping[similar_user_idx]
                    similar_user_pairs.append((similar_user_id, float(similarity)))
            
            return similar_user_pairs[:n_similar]
            
        except Exception as e:
            logger.error(f"Error getting similar users: {e}")
            return []
    
    def get_similar_items(self, content_id: int, n_similar: int = 5) -> List[Tuple[int, float]]:
        """Get similar items based on interaction patterns"""
        if not self.model or self.user_item_matrix is None:
            return []
        
        try:
            if content_id not in self.item_mapping:
                return []
            
            item_idx = self.item_mapping[content_id]
            
            # Get similar items
            similar_items = self.model.similar_items(item_idx, N=n_similar + 1)  # +1 to exclude self
            
            # Filter out self and convert to content IDs
            similar_item_pairs = []
            for similar_item_idx, similarity in similar_items:
                if similar_item_idx != item_idx:
                    similar_content_id = self.reverse_item_mapping[similar_item_idx]
                    similar_item_pairs.append((similar_content_id, float(similarity)))
            
            return similar_item_pairs[:n_similar]
            
        except Exception as e:
            logger.error(f"Error getting similar items: {e}")
            return []
    
    def _calculate_confidence(self, user_idx: int, item_idx: int, score: float) -> float:
        """Calculate confidence score for a recommendation"""
        try:
            # Base confidence from score
            base_confidence = min(score / 10.0, 1.0)  # Normalize score
            
            # Boost confidence based on item popularity
            item_interactions = self.user_item_matrix[:, item_idx].sum()
            popularity_boost = min(item_interactions / 100.0, 0.3)  # Max 0.3 boost
            
            # Boost confidence based on user activity
            user_interactions = self.user_item_matrix[user_idx, :].sum()
            activity_boost = min(user_interactions / 50.0, 0.2)  # Max 0.2 boost
            
            confidence = base_confidence + popularity_boost + activity_boost
            return min(confidence, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5
    
    def _get_item_interaction_count(self, item_idx: int) -> int:
        """Get total interaction count for an item"""
        try:
            return int(self.user_item_matrix[:, item_idx].sum())
        except:
            return 0
    
    def _get_similar_users_count(self, user_idx: int, item_idx: int) -> int:
        """Get count of users similar to the target user who interacted with the item"""
        try:
            # Get users who interacted with this item
            item_users = self.user_item_matrix[:, item_idx].nonzero()[0]
            
            if len(item_users) == 0:
                return 0
            
            # Get similar users
            similar_users = self.model.similar_users(user_idx, N=min(20, len(item_users)))
            similar_user_indices = [idx for idx, _ in similar_users]
            
            # Count overlap
            overlap = len(set(item_users) & set(similar_user_indices))
            return overlap
            
        except Exception as e:
            logger.error(f"Error getting similar users count: {e}")
            return 0
    
    def _generate_recommendation_reason(self, score: float, interaction_count: int, similar_users_count: int) -> str:
        """Generate explanation for the recommendation"""
        try:
            reasons = []
            
            if score > 0.8:
                reasons.append("High collaborative filtering score")
            elif score > 0.5:
                reasons.append("Good collaborative filtering score")
            else:
                reasons.append("Moderate collaborative filtering score")
            
            if interaction_count > 50:
                reasons.append("Popular content")
            elif interaction_count > 20:
                reasons.append("Well-received content")
            
            if similar_users_count > 5:
                reasons.append("Liked by similar users")
            elif similar_users_count > 2:
                reasons.append("Some similar users liked this")
            
            if not reasons:
                reasons.append("Based on collaborative filtering")
            
            return " | ".join(reasons)
            
        except Exception as e:
            logger.error(f"Error generating recommendation reason: {e}")
            return "Based on collaborative filtering"
    
    def get_model_performance(self) -> Dict[str, Any]:
        """Get model performance metrics"""
        if not self.model:
            return {'status': 'no_model'}
        
        try:
            performance = {
                'model_type': self.model_type,
                'status': 'trained',
                'user_count': len(self.user_mapping),
                'item_count': len(self.item_mapping),
                'interaction_count': len(self.interaction_data),
                'sparsity': self._calculate_sparsity()
            }
            
            # Add model-specific metrics
            if hasattr(self.model, 'factors'):
                performance['factors'] = self.model.factors
            
            return performance
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _calculate_sparsity(self) -> float:
        """Calculate sparsity of the user-item matrix"""
        try:
            if self.user_item_matrix is None:
                return 0.0
            
            total_elements = self.user_item_matrix.shape[0] * self.user_item_matrix.shape[1]
            non_zero_elements = self.user_item_matrix.nnz
            
            sparsity = 1.0 - (non_zero_elements / total_elements)
            return sparsity
            
        except Exception as e:
            logger.error(f"Error calculating sparsity: {e}")
            return 0.0
    
    def save_model(self, model_path: str):
        """Save the trained model"""
        if not self.model:
            logger.warning("No model to save")
            return False
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            
            # Save model
            with open(model_path, 'wb') as f:
                pickle.dump(self.model, f)
            
            # Save mappings and metadata
            metadata = {
                'user_mapping': self.user_mapping,
                'item_mapping': self.item_mapping,
                'reverse_user_mapping': self.reverse_user_mapping,
                'reverse_item_mapping': self.reverse_item_mapping,
                'model_type': self.model_type,
                'created_at': datetime.now().isoformat()
            }
            
            metadata_path = model_path.replace('.pkl', '_metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            logger.info(f"✅ Model saved to {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False
    
    def load_model(self, model_path: str):
        """Load a trained model"""
        if not self.IMPLICIT_AVAILABLE:
            logger.error("Implicit library not available for loading model")
            return False
        
        try:
            # Load model
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            
            # Load metadata if available
            metadata_path = model_path.replace('.pkl', '_metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                self.user_mapping = metadata.get('user_mapping', {})
                self.item_mapping = metadata.get('item_mapping', {})
                self.reverse_user_mapping = metadata.get('reverse_user_mapping', {})
                self.reverse_item_mapping = metadata.get('reverse_item_mapping', {})
                self.model_type = metadata.get('model_type', 'als')
            
            logger.info(f"✅ Model loaded from {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False

# Factory functions
def create_cf_engine(model_type: str = 'als') -> CollaborativeFilteringEngine:
    """Create a collaborative filtering engine instance"""
    return CollaborativeFilteringEngine(model_type)

def create_als_engine() -> CollaborativeFilteringEngine:
    """Create an ALS-based collaborative filtering engine"""
    return CollaborativeFilteringEngine('als')

def create_bpr_engine() -> CollaborativeFilteringEngine:
    """Create a BPR-based collaborative filtering engine"""
    return CollaborativeFilteringEngine('bpr')

def create_lmf_engine() -> CollaborativeFilteringEngine:
    """Create an LMF-based collaborative filtering engine"""
    return CollaborativeFilteringEngine('lmf')

# Example usage
if __name__ == "__main__":
    # Create engine
    engine = create_cf_engine('als')
    
    # Add sample interactions
    sample_interactions = [
        UserInteraction(1, 101, 'view', 1.0),
        UserInteraction(1, 102, 'like', 1.0),
        UserInteraction(1, 103, 'bookmark', 1.0),
        UserInteraction(2, 101, 'view', 1.0),
        UserInteraction(2, 102, 'like', 1.0),
        UserInteraction(2, 104, 'bookmark', 1.0),
        UserInteraction(3, 101, 'view', 1.0),
        UserInteraction(3, 103, 'like', 1.0),
        UserInteraction(3, 105, 'bookmark', 1.0),
    ]
    
    engine.add_interactions_batch(sample_interactions)
    
    # Train model
    if engine.train_model():
        print("✅ Model trained successfully")
        
        # Get recommendations
        recommendations = engine.get_recommendations(1, n_recommendations=5)
        
        print(f"\nRecommendations for user 1:")
        for rec in recommendations:
            print(f"Content {rec.content_id}: {rec.cf_score:.3f} - {rec.recommendation_reason}")
        
        # Get similar users
        similar_users = engine.get_similar_users(1, n_similar=3)
        print(f"\nSimilar users to user 1:")
        for user_id, similarity in similar_users:
            print(f"User {user_id}: {similarity:.3f}")
        
        # Save model
        engine.save_model('models/cf_model.pkl')
        
        # Get performance metrics
        performance = engine.get_model_performance()
        print(f"\nModel performance: {performance}")

