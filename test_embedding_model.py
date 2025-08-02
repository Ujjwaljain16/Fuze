#!/usr/bin/env python3
"""
Test script to verify embedding model is working correctly
"""

import os
from dotenv import load_dotenv
from embedding_utils import get_embedding
import numpy as np

# Load environment variables
load_dotenv()

def test_embedding_model():
    """Test the embedding model directly"""
    
    print("🧪 Testing Embedding Model")
    print("=" * 50)
    
    # Test texts
    test_texts = [
        "Hello world",
        "React hooks and components",
        "Python machine learning",
        "JavaScript async programming",
        "Database design principles"
    ]
    
    print("1. Testing embedding generation...")
    
    for i, text in enumerate(test_texts, 1):
        print(f"\n   Test {i}: '{text}'")
        
        try:
            # Generate embedding
            embedding = get_embedding(text)
            
            # Check type and convert to list
            print(f"      Type: {type(embedding)}")
            
            if hasattr(embedding, 'shape'):
                print(f"      Shape: {embedding.shape}")
            
            if hasattr(embedding, 'tolist'):
                embedding_list = embedding.tolist()
            else:
                embedding_list = list(embedding)
            
            print(f"      Dimensions: {len(embedding_list)}")
            
            # Check if dimensions are correct (should be 384 for all-MiniLM-L6-v2)
            if len(embedding_list) == 384:
                print(f"      ✅ Correct dimensions (384)")
            else:
                print(f"      ❌ Wrong dimensions: {len(embedding_list)} (expected 384)")
            
            # Check if embedding values are reasonable
            embedding_array = np.array(embedding_list)
            print(f"      Min value: {embedding_array.min():.6f}")
            print(f"      Max value: {embedding_array.max():.6f}")
            print(f"      Mean value: {embedding_array.mean():.6f}")
            print(f"      Std dev: {embedding_array.std():.6f}")
            
        except Exception as e:
            print(f"      ❌ Error: {str(e)}")
    
    print(f"\n2. Testing model consistency...")
    
    # Test same text multiple times
    test_text = "Consistency test"
    embeddings = []
    
    for i in range(3):
        try:
            embedding = get_embedding(test_text)
            if hasattr(embedding, 'tolist'):
                embedding_list = embedding.tolist()
            else:
                embedding_list = list(embedding)
            embeddings.append(embedding_list)
            print(f"   Run {i+1}: {len(embedding_list)} dimensions")
        except Exception as e:
            print(f"   Run {i+1}: Error - {str(e)}")
    
    if len(embeddings) >= 2:
        # Check if embeddings are consistent
        embedding1 = np.array(embeddings[0])
        embedding2 = np.array(embeddings[1])
        
        if np.array_equal(embedding1, embedding2):
            print("   ✅ Embeddings are consistent (cached)")
        else:
            print("   ⚠️  Embeddings are different (not cached)")
    
    print(f"\n3. Testing Redis cache...")
    
    try:
        from redis_utils import redis_cache
        if redis_cache.connected:
            print("   ✅ Redis is connected")
            
            # Test cache functionality
            test_text = "Cache test"
            embedding1 = get_embedding(test_text)
            embedding2 = get_embedding(test_text)  # Should be cached
            
            if hasattr(embedding1, 'tolist'):
                emb1_list = embedding1.tolist()
                emb2_list = embedding2.tolist()
            else:
                emb1_list = list(embedding1)
                emb2_list = list(embedding2)
            
            if emb1_list == emb2_list:
                print("   ✅ Cache is working correctly")
            else:
                print("   ⚠️  Cache might not be working")
        else:
            print("   ⚠️  Redis is not connected")
    except Exception as e:
        print(f"   ❌ Error testing Redis: {str(e)}")

def main():
    """Main test function"""
    test_embedding_model()
    
    print(f"\n📊 Summary:")
    print(f"   The all-MiniLM-L6-v2 model should produce 384-dimensional embeddings.")
    print(f"   If you see different dimensions, there might be an issue with:")
    print(f"   1. The model installation")
    print(f"   2. The model configuration")
    print(f"   3. The embedding generation process")

if __name__ == "__main__":
    main() 