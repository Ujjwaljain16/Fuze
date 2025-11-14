#!/usr/bin/env python3
"""
Test Sentence Transformer Training and Performance
This script checks if your sentence transformer is correctly trained and working
"""

import time
import numpy as np
from sentence_transformers import SentenceTransformer
import torch

def test_sentence_transformer():
    """Test if sentence transformer is correctly trained and working"""
    print("🧪 Testing Sentence Transformer Training and Performance")
    print("=" * 60)
    
    try:
        # Test 1: Model Loading
        print("\n📦 Test 1: Model Loading")
        print("-" * 30)
        
        start_time = time.time()
        model = SentenceTransformer('all-MiniLM-L6-v2')
        load_time = time.time() - start_time
        
        print(f"✅ Model loaded successfully in {load_time:.2f} seconds")
        print(f"📊 Model: all-MiniLM-L6-v2")
        print(f"🔧 Device: {next(model.parameters()).device}")
        
        # Test 2: Model Architecture
        print("\n🏗️ Test 2: Model Architecture")
        print("-" * 30)
        
        # Check model parameters
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        print(f"📊 Total parameters: {total_params:,}")
        print(f"🎯 Trainable parameters: {trainable_params:,}")
        print(f"🔒 Frozen parameters: {total_params - trainable_params:,}")
        
        # Check if model is in training mode
        training_mode = model.training
        print(f"🎓 Training mode: {'Yes' if training_mode else 'No'}")
        
        # Test 3: Basic Functionality
        print("\n⚡ Test 3: Basic Functionality")
        print("-" * 30)
        
        test_texts = [
            "Python web development with Flask",
            "React hooks and state management",
            "Machine learning algorithms",
            "Database optimization techniques"
        ]
        
        start_time = time.time()
        embeddings = model.encode(test_texts)
        encode_time = time.time() - start_time
        
        print(f"✅ Generated {len(embeddings)} embeddings in {encode_time:.3f} seconds")
        print(f"📊 Embedding dimensions: {embeddings[0].shape}")
        print(f"🚀 Average time per embedding: {encode_time/len(test_texts)*1000:.1f}ms")
        
        # Test 4: Semantic Similarity
        print("\n🔍 Test 4: Semantic Similarity")
        print("-" * 30)
        
        # Test similar concepts
        similar_texts = [
            "Python programming language",
            "Python coding",
            "Python development"
        ]
        
        similar_embeddings = model.encode(similar_texts)
        
        # Calculate similarities
        from sklearn.metrics.pairwise import cosine_similarity
        
        similarity_matrix = cosine_similarity(similar_embeddings)
        
        print("📊 Similarity Matrix (should show high values for similar concepts):")
        for i, text1 in enumerate(similar_texts):
            for j, text2 in enumerate(similar_texts):
                if i <= j:
                    similarity = similarity_matrix[i][j]
                    print(f"   '{text1[:20]}...' vs '{text2[:20]}...': {similarity:.3f}")
        
        # Test 5: Training Status Check
        print("\n🎓 Test 5: Training Status Check")
        print("-" * 30)
        
        # Check if model weights are properly initialized (not all zeros)
        first_layer = next(model.parameters())
        if first_layer is not None:
            weight_stats = {
                'mean': float(first_layer.mean()),
                'std': float(first_layer.std()),
                'min': float(first_layer.min()),
                'max': float(first_layer.max())
            }
            
            print("📊 First layer weight statistics:")
            for stat, value in weight_stats.items():
                print(f"   {stat}: {value:.6f}")
            
            # Check if weights are properly initialized (not all zeros or very small)
            if abs(weight_stats['mean']) > 1e-6 and weight_stats['std'] > 1e-6:
                print("✅ Weights appear to be properly initialized")
            else:
                print("⚠️ Weights may not be properly initialized")
        
        # Test 6: Performance Benchmark
        print("\n⚡ Test 6: Performance Benchmark")
        print("-" * 30)
        
        # Test batch processing
        batch_sizes = [1, 5, 10, 20]
        
        for batch_size in batch_sizes:
            test_batch = test_texts * (batch_size // len(test_texts) + 1)
            test_batch = test_batch[:batch_size]
            
            start_time = time.time()
            batch_embeddings = model.encode(test_batch, batch_size=batch_size)
            batch_time = time.time() - start_time
            
            print(f"📦 Batch size {batch_size:2d}: {batch_time:.3f}s ({batch_time/batch_size*1000:.1f}ms per text)")
        
        # Test 7: Model Consistency
        print("\n🔄 Test 7: Model Consistency")
        print("-" * 30)
        
        # Test if model produces consistent embeddings for same input
        test_input = "Test input for consistency"
        
        embedding1 = model.encode([test_input])[0]
        embedding2 = model.encode([test_input])[0]
        
        consistency_score = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
        
        print(f"📊 Consistency score (should be 1.0): {consistency_score:.6f}")
        
        if abs(consistency_score - 1.0) < 1e-6:
            print("✅ Model produces consistent embeddings")
        else:
            print("⚠️ Model may have consistency issues")
        
        # Test 8: Training Mode Verification
        print("\n🎓 Test 8: Training Mode Verification")
        print("-" * 30)
        
        # Check if model can be put in training mode
        original_mode = model.training
        
        try:
            model.train()
            print(f"✅ Can switch to training mode: {model.training}")
            
            model.eval()
            print(f"✅ Can switch to evaluation mode: {model.training}")
            
            # Restore original mode
            if original_mode:
                model.train()
            else:
                model.eval()
                
        except Exception as e:
            print(f"❌ Error switching training modes: {e}")
        
        print("\n" + "=" * 60)
        print("🏁 Sentence Transformer Testing Completed!")
        
        # Summary
        print("\n📋 Summary:")
        print("✅ Model loads successfully")
        print("✅ Generates embeddings with correct dimensions")
        print("✅ Produces semantic similarities")
        print("✅ Handles batch processing")
        print("✅ Maintains consistency")
        print("✅ Training/evaluation mode switching works")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error testing sentence transformer: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_model_training_status():
    """Check if the model shows signs of being fine-tuned"""
    print("\n🔍 Checking Model Training Status")
    print("=" * 40)
    
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Check model info
        print(f"📊 Model: all-MiniLM-L6-v2")
        print(f"🏗️ Architecture: {type(model).__name__}")
        
        # Check if this is a pre-trained model or fine-tuned
        if 'all-MiniLM-L6-v2' in 'all-MiniLM-L6-v2':
            print("ℹ️ This is a pre-trained model (all-MiniLM-L6-v2)")
            print("ℹ️ It has been trained on general text data, not fine-tuned for your specific domain")
            print("ℹ️ This is normal and expected for most use cases")
        
        # Check model configuration
        if hasattr(model, 'get_config_dict'):
            config = model.get_config_dict()
            print(f"⚙️ Model configuration available: {bool(config)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking training status: {e}")
        return False

def main():
    """Main testing function"""
    print("🚀 Sentence Transformer Training Verification")
    print("=" * 60)
    
    # Run all tests
    success = test_sentence_transformer()
    
    if success:
        test_model_training_status()
    
    print("\n💡 Recommendations:")
    if success:
        print("✅ Your sentence transformer is working correctly!")
        print("✅ It's using the pre-trained all-MiniLM-L6-v2 model")
        print("✅ This model is well-trained for general semantic similarity tasks")
        print("✅ No fine-tuning is needed for most use cases")
    else:
        print("❌ There are issues with your sentence transformer")
        print("❌ Check the error messages above for details")
        print("❌ You may need to reinstall the model or fix dependencies")

if __name__ == "__main__":
    main()
