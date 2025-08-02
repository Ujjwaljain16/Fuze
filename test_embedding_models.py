#!/usr/bin/env python3
"""
Test different embedding models to find which one produces 4698 dimensions
"""

from sentence_transformers import SentenceTransformer
import numpy as np

def test_embedding_models():
    """Test different embedding models and their dimensions"""
    
    models_to_test = [
        'all-MiniLM-L6-v2',      # 384 dimensions
        'all-mpnet-base-v2',     # 768 dimensions
        'all-MiniLM-L12-v2',     # 384 dimensions
        'multi-qa-MiniLM-L6-v2', # 384 dimensions
        'paraphrase-MiniLM-L6-v2', # 384 dimensions
        'sentence-transformers/all-mpnet-base-v2', # 768 dimensions
        'sentence-transformers/all-MiniLM-L6-v2',  # 384 dimensions
    ]
    
    test_text = "This is a test sentence for embedding generation."
    
    print("🧪 Testing Embedding Models")
    print("=" * 50)
    
    for model_name in models_to_test:
        try:
            print(f"\n🔍 Testing: {model_name}")
            model = SentenceTransformer(model_name)
            embedding = model.encode([test_text])[0]
            
            if hasattr(embedding, 'tolist'):
                embedding_list = embedding.tolist()
            else:
                embedding_list = list(embedding)
            
            print(f"   📊 Dimensions: {len(embedding_list)}")
            print(f"   📊 First 5 values: {embedding_list[:5]}")
            
            if len(embedding_list) == 4698:
                print(f"   🎯 MATCH FOUND! This model produces 4698 dimensions!")
                return model_name
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}...")
    
    print(f"\n❌ No model found that produces exactly 4698 dimensions")
    print("The stored embeddings might be from a different model or have been processed differently")
    
    return None

if __name__ == "__main__":
    matching_model = test_embedding_models()
    if matching_model:
        print(f"\n✅ Use this model: {matching_model}")
    else:
        print(f"\n💡 Recommendation: Use 'all-MiniLM-L6-v2' (384 dimensions) and regenerate embeddings") 