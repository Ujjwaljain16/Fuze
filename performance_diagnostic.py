#!/usr/bin/env python3
"""
Performance Diagnostic for Fuze Recommendation System
Identifies bottlenecks and provides optimization recommendations
"""

import time
import psutil
import os
import sys
from datetime import datetime
import requests
import json
from redis_utils import redis_cache
from models import db, SavedContent, User, Feedback
from embedding_utils import get_embedding
from sentence_transformers import SentenceTransformer
import numpy as np

class PerformanceDiagnostic:
    def __init__(self):
        self.results = {}
        self.start_time = time.time()
        
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def check_redis_connection(self):
        """Check Redis connection and performance"""
        self.log("🔍 Checking Redis connection...")
        
        try:
            # Test basic connection
            start_time = time.time()
            redis_cache.redis_client.ping()
            ping_time = (time.time() - start_time) * 1000
            
            # Test cache operations
            test_key = "diagnostic_test"
            test_data = {"test": "data", "timestamp": time.time()}
            
            # Test set operation
            start_time = time.time()
            redis_cache.redis_client.setex(test_key, 60, json.dumps(test_data))
            set_time = (time.time() - start_time) * 1000
            
            # Test get operation
            start_time = time.time()
            cached_data = redis_cache.redis_client.get(test_key)
            get_time = (time.time() - start_time) * 1000
            
            # Clean up
            redis_cache.redis_client.delete(test_key)
            
            self.results['redis'] = {
                'connected': True,
                'ping_time_ms': ping_time,
                'set_time_ms': set_time,
                'get_time_ms': get_time,
                'status': '✅ Redis is working well' if ping_time < 10 else '⚠️ Redis is slow'
            }
            
            self.log(f"✅ Redis: ping={ping_time:.1f}ms, set={set_time:.1f}ms, get={get_time:.1f}ms")
            
        except Exception as e:
            self.results['redis'] = {
                'connected': False,
                'error': str(e),
                'status': '❌ Redis connection failed'
            }
            self.log(f"❌ Redis connection failed: {e}")
    
    def check_database_performance(self):
        """Check database query performance"""
        self.log("🔍 Checking database performance...")
        
        try:
            # Test basic queries
            start_time = time.time()
            user_count = User.query.count()
            user_query_time = (time.time() - start_time) * 1000
            
            start_time = time.time()
            content_count = SavedContent.query.count()
            content_query_time = (time.time() - start_time) * 1000
            
            start_time = time.time()
            # Test complex query similar to recommendations
            content_with_embeddings = SavedContent.query.filter(
                SavedContent.embedding.isnot(None),
                SavedContent.quality_score >= 5
            ).order_by(
                SavedContent.quality_score.desc(),
                SavedContent.created_at.desc()
            ).limit(500).all()
            complex_query_time = (time.time() - start_time) * 1000
            
            self.results['database'] = {
                'user_count': user_count,
                'content_count': content_count,
                'content_with_embeddings': len(content_with_embeddings),
                'user_query_time_ms': user_query_time,
                'content_query_time_ms': content_query_time,
                'complex_query_time_ms': complex_query_time,
                'status': '✅ Database queries are fast' if complex_query_time < 100 else '⚠️ Database queries are slow'
            }
            
            self.log(f"✅ Database: {user_count} users, {content_count} content items")
            self.log(f"   Query times: user={user_query_time:.1f}ms, content={content_query_time:.1f}ms, complex={complex_query_time:.1f}ms")
            
        except Exception as e:
            self.results['database'] = {
                'error': str(e),
                'status': '❌ Database query failed'
            }
            self.log(f"❌ Database query failed: {e}")
    
    def check_embedding_performance(self):
        """Check embedding generation performance"""
        self.log("🔍 Checking embedding performance...")
        
        try:
            # Test embedding generation
            test_texts = [
                "Python web development with Flask",
                "Machine learning algorithms and neural networks",
                "React frontend development and state management",
                "Database optimization and query performance",
                "API design and RESTful services"
            ]
            
            # Test single embedding
            start_time = time.time()
            embedding = get_embedding(test_texts[0])
            single_embedding_time = (time.time() - start_time) * 1000
            
            # Test batch embedding (if available)
            try:
                import torch
                model = SentenceTransformer('all-MiniLM-L6-v2')
                
                # Fix meta tensor issue by using to_empty() instead of to()
                if hasattr(torch, 'meta') and torch.meta.is_available():
                    # Use to_empty() for meta tensors
                    model = model.to_empty(device='cpu')
                else:
                    # Fallback to CPU
                    model = model.to('cpu')
                
                start_time = time.time()
                batch_embeddings = model.encode(test_texts, batch_size=5)
                batch_embedding_time = (time.time() - start_time) * 1000
                batch_available = True
            except Exception as e:
                batch_embedding_time = None
                batch_available = False
            
            # Test Redis cache for embeddings
            start_time = time.time()
            cached_embedding = redis_cache.get_cached_embedding(test_texts[0])
            cache_lookup_time = (time.time() - start_time) * 1000
            
            self.results['embeddings'] = {
                'single_embedding_time_ms': single_embedding_time,
                'batch_embedding_time_ms': batch_embedding_time,
                'cache_lookup_time_ms': cache_lookup_time,
                'batch_available': batch_available,
                'embedding_dimensions': len(embedding) if embedding is not None else 0,
                'status': '✅ Embedding generation is fast' if single_embedding_time < 500 else '⚠️ Embedding generation is slow'
            }
            
            self.log(f"✅ Embeddings: single={single_embedding_time:.1f}ms, cache_lookup={cache_lookup_time:.1f}ms")
            if batch_available:
                self.log(f"   Batch: {batch_embedding_time:.1f}ms for {len(test_texts)} texts")
            
        except Exception as e:
            self.results['embeddings'] = {
                'error': str(e),
                'status': '❌ Embedding generation failed'
            }
            self.log(f"❌ Embedding generation failed: {e}")
    
    def check_recommendation_performance(self):
        """Test actual recommendation endpoint performance"""
        self.log("🔍 Testing recommendation endpoint performance...")
        
        try:
            # This would require a running server and authentication
            # For now, we'll simulate the recommendation logic
            start_time = time.time()
            
            # Simulate recommendation computation
            user_id = 1  # Assuming user exists
            user = User.query.get(user_id)
            if not user:
                self.log("⚠️ No test user found, skipping recommendation test")
                return
            
            # Get user's bookmarks
            bookmarks = SavedContent.query.filter_by(user_id=user_id).filter(
                SavedContent.quality_score >= 5
            ).all()
            
            if not bookmarks:
                self.log("⚠️ No bookmarks found for test user")
                return
            
            # Build user profile
            user_embs = [np.array(sc.embedding) for sc in bookmarks if sc.embedding is not None]
            if not user_embs:
                self.log("⚠️ No embeddings found for user bookmarks")
                return
            
            user_profile = np.mean(user_embs, axis=0)
            
            # Get all content for recommendations
            all_content = SavedContent.query.filter(
                SavedContent.user_id != user_id,
                SavedContent.quality_score >= 5
            ).all()
            
            if not all_content:
                self.log("⚠️ No content available for recommendations")
                return
            
            # Compute similarities
            content_embs = [np.array(c.embedding) for c in all_content if c.embedding is not None]
            if not content_embs:
                self.log("⚠️ No embeddings found for content")
                return
            
            content_embs = np.stack(content_embs)
            similarities = np.dot(content_embs, user_profile) / (
                np.linalg.norm(content_embs, axis=1) * np.linalg.norm(user_profile) + 1e-8
            )
            
            # Sort and get top recommendations
            top_indices = np.argsort(similarities)[::-1][:10]
            recommendations = [all_content[i] for i in top_indices]
            
            recommendation_time = (time.time() - start_time) * 1000
            
            self.results['recommendations'] = {
                'computation_time_ms': recommendation_time,
                'user_bookmarks': len(bookmarks),
                'available_content': len(all_content),
                'recommendations_generated': len(recommendations),
                'status': '✅ Recommendations are fast' if recommendation_time < 1000 else '⚠️ Recommendations are slow'
            }
            
            self.log(f"✅ Recommendations: {recommendation_time:.1f}ms for {len(recommendations)} recommendations")
            
        except Exception as e:
            self.results['recommendations'] = {
                'error': str(e),
                'status': '❌ Recommendation computation failed'
            }
            self.log(f"❌ Recommendation computation failed: {e}")
    
    def check_system_resources(self):
        """Check system resource usage"""
        self.log("🔍 Checking system resources...")
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            self.results['system'] = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3),
                'status': '✅ System resources are adequate' if cpu_percent < 80 and memory.percent < 80 else '⚠️ System resources are constrained'
            }
            
            self.log(f"✅ System: CPU={cpu_percent:.1f}%, Memory={memory.percent:.1f}%, Disk={disk.percent:.1f}%")
            
        except Exception as e:
            self.results['system'] = {
                'error': str(e),
                'status': '❌ System resource check failed'
            }
            self.log(f"❌ System resource check failed: {e}")
    
    def identify_bottlenecks(self):
        """Identify performance bottlenecks"""
        self.log("🔍 Identifying bottlenecks...")
        
        bottlenecks = []
        
        # Check Redis performance
        if 'redis' in self.results and self.results['redis'].get('connected'):
            if self.results['redis']['ping_time_ms'] > 10:
                bottlenecks.append("Redis connection is slow")
            if self.results['redis']['get_time_ms'] > 5:
                bottlenecks.append("Redis cache reads are slow")
        
        # Check database performance
        if 'database' in self.results:
            if self.results['database'].get('complex_query_time_ms', 0) > 100:
                bottlenecks.append("Database queries are slow")
        
        # Check embedding performance
        if 'embeddings' in self.results:
            if self.results['embeddings'].get('single_embedding_time_ms', 0) > 500:
                bottlenecks.append("Embedding generation is slow")
        
        # Check recommendation performance
        if 'recommendations' in self.results:
            if self.results['recommendations'].get('computation_time_ms', 0) > 1000:
                bottlenecks.append("Recommendation computation is slow")
        
        # Check system resources
        if 'system' in self.results:
            if self.results['system'].get('cpu_percent', 0) > 80:
                bottlenecks.append("High CPU usage")
            if self.results['system'].get('memory_percent', 0) > 80:
                bottlenecks.append("High memory usage")
        
        self.results['bottlenecks'] = bottlenecks
        
        if bottlenecks:
            self.log("⚠️ Identified bottlenecks:")
            for bottleneck in bottlenecks:
                self.log(f"   - {bottleneck}")
        else:
            self.log("✅ No major bottlenecks identified")
    
    def generate_optimization_recommendations(self):
        """Generate optimization recommendations"""
        self.log("🔍 Generating optimization recommendations...")
        
        recommendations = []
        
        # Redis optimizations
        if 'redis' in self.results and not self.results['redis'].get('connected'):
            recommendations.append("Fix Redis connection - check if Redis server is running")
        
        if 'redis' in self.results and self.results['redis'].get('connected'):
            if self.results['redis']['ping_time_ms'] > 10:
                recommendations.append("Optimize Redis connection - consider using connection pooling")
        
        # Database optimizations
        if 'database' in self.results:
            if self.results['database'].get('complex_query_time_ms', 0) > 100:
                recommendations.append("Add database indexes on embedding and quality_score columns")
                recommendations.append("Consider pagination for large result sets")
        
        # Embedding optimizations
        if 'embeddings' in self.results:
            if self.results['embeddings'].get('single_embedding_time_ms', 0) > 500:
                recommendations.append("Use batch embedding generation instead of single embeddings")
                recommendations.append("Consider using a faster embedding model")
        
        # Recommendation optimizations
        if 'recommendations' in self.results:
            if self.results['recommendations'].get('computation_time_ms', 0) > 1000:
                recommendations.append("Implement recommendation result caching")
                recommendations.append("Use vector similarity search instead of manual computation")
                recommendations.append("Limit the number of content items processed")
        
        # System optimizations
        if 'system' in self.results:
            if self.results['system'].get('cpu_percent', 0) > 80:
                recommendations.append("Consider using async processing for recommendations")
            if self.results['system'].get('memory_percent', 0) > 80:
                recommendations.append("Implement memory-efficient data loading")
        
        self.results['optimization_recommendations'] = recommendations
        
        if recommendations:
            self.log("💡 Optimization recommendations:")
            for i, rec in enumerate(recommendations, 1):
                self.log(f"   {i}. {rec}")
        else:
            self.log("✅ No optimization recommendations needed")
    
    def run_full_diagnostic(self):
        """Run complete performance diagnostic"""
        self.log("🚀 Starting Fuze Performance Diagnostic")
        self.log("=" * 50)
        
        # Run all checks
        self.check_redis_connection()
        self.check_database_performance()
        self.check_embedding_performance()
        self.check_recommendation_performance()
        self.check_system_resources()
        
        # Analyze results
        self.identify_bottlenecks()
        self.generate_optimization_recommendations()
        
        # Summary
        total_time = time.time() - self.start_time
        self.log("=" * 50)
        self.log(f"🎯 Diagnostic completed in {total_time:.2f} seconds")
        
        # Save results
        with open('performance_diagnostic_results.json', 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        self.log("📊 Results saved to performance_diagnostic_results.json")
        
        return self.results

def main():
    """Main function"""
    diagnostic = PerformanceDiagnostic()
    results = diagnostic.run_full_diagnostic()
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    for component, data in results.items():
        if isinstance(data, dict) and 'status' in data:
            print(f"{component.upper()}: {data['status']}")
    
    if results.get('bottlenecks'):
        print(f"\n⚠️  BOTTLENECKS FOUND: {len(results['bottlenecks'])}")
        for bottleneck in results['bottlenecks']:
            print(f"   • {bottleneck}")
    
    if results.get('optimization_recommendations'):
        print(f"\n💡 OPTIMIZATION RECOMMENDATIONS: {len(results['optimization_recommendations'])}")
        for i, rec in enumerate(results['optimization_recommendations'], 1):
            print(f"   {i}. {rec}")

if __name__ == "__main__":
    main() 