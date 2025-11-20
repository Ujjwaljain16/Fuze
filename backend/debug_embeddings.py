#!/usr/bin/env python3
"""
Debug embedding generation
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def debug_embeddings():
    """Debug embedding generation"""
    try:
        from utils.embedding_utils import get_embedding_model
        import numpy as np

        print("🔍 DEBUGGING EMBEDDING SYSTEM")
        print("=" * 50)

        # Check if model can be loaded
        print("Loading embedding model...")
        model = get_embedding_model()
        print(f"Model loaded: {model is not None}")

        if model is None:
            print("❌ Embedding model is None - this is the problem!")
            return

        # Test embedding generation
        test_text = "Learn Go backend development"
        print(f"Testing embedding generation for: '{test_text}'")

        try:
            embedding = model.encode([test_text])[0]
            print(f"✅ Embedding generated successfully")
            print(f"   Type: {type(embedding)}")
            print(f"   Shape: {embedding.shape if hasattr(embedding, 'shape') else 'No shape'}")
            print(f"   First 5 values: {embedding[:5] if len(embedding) > 5 else embedding}")

            # Test numpy operations
            embedding_array = np.array(embedding)
            norm = np.linalg.norm(embedding_array)
            print(f"✅ Numpy operations work - norm: {norm}")

        except Exception as e:
            print(f"❌ Embedding generation failed: {e}")
            import traceback
            traceback.print_exc()

        # Test with UnifiedDataLayer
        print("\nTesting UnifiedDataLayer...")
        try:
            from ml.unified_recommendation_orchestrator import UnifiedDataLayer
            data_layer = UnifiedDataLayer()

            embedding2 = data_layer.generate_embedding(test_text)
            print(f"✅ DataLayer embedding generated: {embedding2 is not None}")
            if embedding2 is not None:
                print(f"   Shape: {embedding2.shape}")
                print(f"   Type: {type(embedding2)}")

        except Exception as e:
            print(f"❌ DataLayer embedding failed: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_embeddings()

