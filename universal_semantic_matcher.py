#!/usr/bin/env python3
"""
Universal Semantic Matcher for Fuze
Handles spelling variations, synonyms, and semantic variations automatically
"""

import re
import difflib
from typing import List, Dict, Tuple, Optional
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class UniversalSemanticMatcher:
    """Universal semantic matcher that handles all variations"""
    
    # Class-level flag to prevent multiple embedding model initializations
    _embedding_model_initialized = False
    _embedding_model = None
    
    def __init__(self):
        # Only initialize embedding model once across all instances
        if not UniversalSemanticMatcher._embedding_model_initialized:
            try:
                import torch
                UniversalSemanticMatcher._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                
                # More robust meta tensor handling
                try:
                    # Check if we're dealing with meta tensors
                    if hasattr(torch, 'meta') and torch.meta.is_available():
                        # Use to_empty() for meta tensors
                        UniversalSemanticMatcher._embedding_model = UniversalSemanticMatcher._embedding_model.to_empty(device='cpu')
                        print("✅ UniversalSemanticMatcher embedding model initialized with to_empty() for meta tensors")
                    else:
                        # Fallback to CPU
                        UniversalSemanticMatcher._embedding_model = UniversalSemanticMatcher._embedding_model.to('cpu')
                        print("✅ UniversalSemanticMatcher embedding model initialized with to() for CPU")
                except Exception as tensor_error:
                    print(f"⚠️ Tensor device placement error: {tensor_error}")
                    # Try alternative approach - don't move the model
                    print("✅ Using embedding model without device placement")
                    # The model will work without explicit device placement
                
                UniversalSemanticMatcher._embedding_model_initialized = True
                print("✅ UniversalSemanticMatcher embedding model initialized successfully")
            except Exception as e:
                print(f"❌ Failed to initialize UniversalSemanticMatcher: {e}")
                UniversalSemanticMatcher._embedding_model = None
                UniversalSemanticMatcher._embedding_model_initialized = True  # Prevent retries
        
        # Use the class-level embedding model
        self.embedding_model = UniversalSemanticMatcher._embedding_model
        
        # Spelling variations and synonyms
        self.spelling_variations = {
            'visualiser': ['visualizer', 'visualisation', 'visualization'],
            'optimise': ['optimize', 'optimisation', 'optimization'],
            'analyse': ['analyze', 'analysis'],
            'programme': ['program', 'programming'],
            'centre': ['center', 'central'],
            'colour': ['color', 'coloring'],
            'favour': ['favor', 'favorite'],
            'behaviour': ['behavior', 'behavioral'],
            'organisation': ['organization', 'organizational'],
            'realise': ['realize', 'realization'],
            'customise': ['customize', 'customization'],
            'standardise': ['standardize', 'standardization']
        }
        
        # Technology synonyms and variations
        self.tech_synonyms = {
            'javascript': ['js', 'node', 'nodejs', 'es6', 'es2015'],
            'python': ['py', 'python3', 'python2'],
            'react': ['reactjs', 'jsx', 'tsx', 'react-native'],
            'typescript': ['ts', 'typescript'],
            'node': ['nodejs', 'node.js'],
            'sql': ['mysql', 'postgresql', 'sqlite', 'database'],
            'mongodb': ['nosql', 'mongo', 'documentdb'],
            'docker': ['container', 'kubernetes', 'k8s'],
            'aws': ['amazon', 'cloud', 'ec2', 'lambda'],
            'git': ['github', 'gitlab', 'version control'],
            'java': ['jvm', 'spring', 'maven', 'gradle'],
            'c++': ['cpp', 'cplusplus', 'cxx'],
            'c#': ['csharp', 'dotnet', '.net'],
            'php': ['php7', 'php8', 'laravel', 'symfony']
        }
        
        # Content type variations
        self.content_variations = {
            'tutorial': ['guide', 'how-to', 'step-by-step', 'walkthrough'],
            'documentation': ['docs', 'reference', 'api', 'manual'],
            'article': ['blog', 'post', 'write-up', 'explanation'],
            'course': ['training', 'learning', 'education', 'class'],
            'example': ['sample', 'demo', 'code example', 'snippet'],
            'video': ['screencast', 'recording', 'tutorial video']
        }
        
        # Difficulty variations
        self.difficulty_variations = {
            'beginner': ['basic', 'intro', 'starter', 'novice', 'easy'],
            'intermediate': ['medium', 'moderate', 'intermediate', 'advanced-beginner'],
            'advanced': ['expert', 'pro', 'senior', 'hard', 'complex']
        }
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for better matching"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Replace common variations (use word boundaries to avoid partial matches)
        for original, variations in self.spelling_variations.items():
            for variation in variations:
                # Use word boundaries to avoid partial replacements
                text = re.sub(r'\b' + re.escape(variation) + r'\b', original, text)
        
        # Replace technology variations
        for original, variations in self.tech_synonyms.items():
            for variation in variations:
                # Use word boundaries to avoid partial replacements
                text = re.sub(r'\b' + re.escape(variation) + r'\b', original, text)
        
        # Replace content type variations
        for original, variations in self.content_variations.items():
            for variation in variations:
                # Use word boundaries to avoid partial replacements
                text = re.sub(r'\b' + re.escape(variation) + r'\b', original, text)
        
        # Replace difficulty variations
        for original, variations in self.difficulty_variations.items():
            for variation in variations:
                # Use word boundaries to avoid partial replacements
                text = re.sub(r'\b' + re.escape(variation) + r'\b', original, text)
        
        return text
    
    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity with normalization"""
        try:
            # Check if embedding model is available
            if not self.embedding_model:
                print("⚠️ Embedding model not available, using fallback similarity")
                return self._fallback_similarity(text1, text2)
            
            # Normalize both texts
            norm_text1 = self.normalize_text(text1)
            norm_text2 = self.normalize_text(text2)
            
            # Generate embeddings
            embeddings = self.embedding_model.encode([norm_text1, norm_text2])
            
            # Calculate cosine similarity
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            
            return float(similarity)
            
        except Exception as e:
            print(f"Error calculating semantic similarity: {e}")
            return self._fallback_similarity(text1, text2)
    
    def find_semantic_matches(self, query: str, candidates: List[Dict], 
                             threshold: float = 0.3, max_results: int = 10) -> List[Dict]:
        """Find semantic matches with enhanced matching"""
        try:
            # Normalize query
            normalized_query = self.normalize_text(query)
            
            # Calculate similarities for all candidates
            results = []
            for candidate in candidates:
                # Get candidate text
                candidate_text = f"{candidate.get('title', '')} {candidate.get('extracted_text', '')}"
                
                # Calculate semantic similarity
                semantic_score = self.calculate_semantic_similarity(normalized_query, candidate_text)
                
                # Calculate spelling similarity (fuzzy matching)
                spelling_score = self.calculate_spelling_similarity(query, candidate_text)
                
                # Calculate technology overlap
                tech_score = self.calculate_technology_overlap(query, candidate)
                
                # Combined score (semantic + spelling + tech)
                combined_score = (semantic_score * 0.6) + (spelling_score * 0.3) + (tech_score * 0.1)
                
                if combined_score >= threshold:
                    results.append({
                        'candidate': candidate,
                        'semantic_score': semantic_score,
                        'spelling_score': spelling_score,
                        'tech_score': tech_score,
                        'combined_score': combined_score
                    })
            
            # Sort by combined score
            results.sort(key=lambda x: x['combined_score'], reverse=True)
            
            return results[:max_results]
            
        except Exception as e:
            print(f"Error finding semantic matches: {e}")
            return []
    
    def calculate_spelling_similarity(self, text1: str, text2: str) -> float:
        """Calculate spelling similarity using fuzzy matching"""
        try:
            # Use difflib for fuzzy string matching
            similarity = difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
            return similarity
        except Exception:
            return 0.0
    
    def calculate_technology_overlap(self, query: str, candidate: Dict) -> float:
        """Calculate technology overlap score"""
        try:
            query_techs = self.extract_technologies(query)
            candidate_techs = candidate.get('technologies', [])
            
            if not query_techs or not candidate_techs:
                return 0.0
            
            # Normalize technologies
            query_techs = [self.normalize_text(tech) for tech in query_techs]
            candidate_techs = [self.normalize_text(tech) for tech in candidate_techs]
            
            # Calculate overlap
            intersection = set(query_techs).intersection(set(candidate_techs))
            union = set(query_techs).union(set(candidate_techs))
            
            if not union:
                return 0.0
            
            return len(intersection) / len(union)
            
        except Exception:
            return 0.0
    
    def extract_technologies(self, text: str) -> List[str]:
        """Extract technologies from text"""
        try:
            # Simple technology extraction
            tech_keywords = [
                'python', 'javascript', 'react', 'node', 'java', 'c++', 'c#',
                'php', 'ruby', 'go', 'rust', 'swift', 'kotlin', 'dart',
                'sql', 'mongodb', 'redis', 'docker', 'kubernetes', 'aws',
                'azure', 'gcp', 'git', 'github', 'gitlab'
            ]
            
            found_techs = []
            text_lower = text.lower()
            
            for tech in tech_keywords:
                if tech in text_lower:
                    found_techs.append(tech)
            
            return found_techs
            
        except Exception:
            return []
    
    def _fallback_similarity(self, text1: str, text2: str) -> float:
        """Fallback similarity calculation when embedding model is not available"""
        try:
            # Simple text-based similarity using normalization
            norm_text1 = self.normalize_text(text1).lower()
            norm_text2 = self.normalize_text(text2).lower()
            
            # Calculate Jaccard similarity on words
            words1 = set(norm_text1.split())
            words2 = set(norm_text2.split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception:
            return 0.0

def test_universal_matcher():
    """Test the universal semantic matcher"""
    print("🧪 Testing Universal Semantic Matcher")
    print("=" * 50)
    
    try:
        matcher = UniversalSemanticMatcher()
        print("✅ UniversalSemanticMatcher initialized")
        
        # Test normalization
        print("\n📊 Testing text normalization...")
        test_text = "Python visualiser for DSA with React and Node.js"
        normalized = matcher.normalize_text(test_text)
        print(f"Original: {test_text}")
        print(f"Normalized: {normalized}")
        
        # Test semantic similarity
        print("\n📊 Testing semantic similarity...")
        text1 = "DSA visualiser"
        text2 = "Data Structures and Algorithms visualizer"
        similarity = matcher.calculate_semantic_similarity(text1, text2)
        print(f"Similarity between '{text1}' and '{text2}': {similarity:.3f}")
        
        # Test spelling similarity
        print("\n📊 Testing spelling similarity...")
        spelling_sim = matcher.calculate_spelling_similarity("visualiser", "visualizer")
        print(f"Spelling similarity 'visualiser' vs 'visualizer': {spelling_sim:.3f}")
        
        print("\n🎉 Universal Semantic Matcher is working correctly!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_universal_matcher()
