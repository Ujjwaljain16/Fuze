import requests
import time
import argparse
import statistics
import json
import uuid

def authenticate(base_url, username, password):
    print(f"Authenticating as {username}...")
    url = f"{base_url}/api/auth/login"
    try:
        response = requests.post(url, json={"username": username, "password": password})
        if response.status_code == 200:
            token = response.json().get("access_token")
            print("Authentication successful!")
            return token
        else:
            print(f"Authentication failed: {response.text}")
            return None
    except Exception as e:
        print(f"Auth error: {e}")
        return None

def benchmark_model_load(base_url, token):
    print("\n--- Benchmarking Model Load (Cold vs Warm) ---")
    headers = {"Authorization": f"Bearer {token}"}
    
    # We will trigger the embedding by performing a semantic search
    # First request - Cold start
    search_payload = {"query": f"test cold {uuid.uuid4()}", "limit": 1}
    
    start_time = time.perf_counter()
    resp = requests.post(f"{base_url}/api/search/semantic", json=search_payload, headers=headers)
    end_time = time.perf_counter()
    
    if resp.status_code != 200:
        print(f"Search failed: {resp.status_code} - {resp.text}")
        return
        
    cold_time = (end_time - start_time) * 1000
    print(f"First request (Cold / First embedding): {cold_time:.2f} ms")
    
    # Next 10 requests - Warm
    warm_times = []
    for i in range(10):
        search_payload = {"query": f"test warm {uuid.uuid4()}", "limit": 1}
        start_time = time.perf_counter()
        requests.post(f"{base_url}/api/search/semantic", json=search_payload, headers=headers)
        end_time = time.perf_counter()
        warm_times.append((end_time - start_time) * 1000)
    
    avg_warm = sum(warm_times) / len(warm_times)
    print(f"Next 10 requests (Warm avg): {avg_warm:.2f} ms")
    print(f"Min warm: {min(warm_times):.2f} ms | Max warm: {max(warm_times):.2f} ms")


def benchmark_cache_hit_rate(base_url, token, n_requests=20):
    print(f"\n--- Benchmarking Cache Hit Rate ({n_requests} requests) ---")
    headers = {"Authorization": f"Bearer {token}"}
    
    # For embedding cache, we need to save bookmarks with the same content vs unique content
    # But since bookmark saving hits external URLs for scraping, it might be slow.
    # We can hit the search endpoint with the SAME query (triggering embedding cache).
    
    static_query = "this is a static query for cache testing"
    
    same_query_times = []
    for _ in range(n_requests):
        start_time = time.perf_counter()
        requests.post(f"{base_url}/api/search/semantic", json={"query": static_query, "limit": 1}, headers=headers)
        end_time = time.perf_counter()
        same_query_times.append((end_time - start_time) * 1000)
        
    avg_same = sum(same_query_times) / len(same_query_times)
    
    unique_query_times = []
    for _ in range(n_requests):
        unique_query = f"unique query {uuid.uuid4()}"
        start_time = time.perf_counter()
        requests.post(f"{base_url}/api/search/semantic", json={"query": unique_query, "limit": 1}, headers=headers)
        end_time = time.perf_counter()
        unique_query_times.append((end_time - start_time) * 1000)
        
    avg_unique = sum(unique_query_times) / len(unique_query_times)
    
    print(f"Same query (Cache hits) avg time:   {avg_same:.2f} ms")
    print(f"Unique queries (Cache misses) avg time: {avg_unique:.2f} ms")
    
    # Calculate relative speedup
    if avg_same > 0:
        speedup = avg_unique / avg_same
        print(f"Cache speedup factor: {speedup:.2f}x faster")


def benchmark_search_latency(base_url, token, n_requests=50):
    print(f"\n--- Benchmarking Search Endpoint Latency ({n_requests} sequential requests) ---")
    headers = {"Authorization": f"Bearer {token}"}
    
    latencies = []
    for i in range(n_requests):
        # Using unique queries to avoid embedding cache and measure full model + DB latency
        search_payload = {"query": f"production latency test {uuid.uuid4()}", "limit": 10}
        
        start_time = time.perf_counter()
        resp = requests.post(f"{base_url}/api/search/semantic", json=search_payload, headers=headers)
        end_time = time.perf_counter()
        
        if resp.status_code == 200:
            latencies.append((end_time - start_time) * 1000)
        else:
            print(f"Request {i} failed: {resp.status_code}")
            
    if not latencies:
        print("All requests failed.")
        return
        
    latencies.sort()
    
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    avg = sum(latencies) / len(latencies)
    
    print(f"p50: {p50:.2f} ms")
    print(f"p95: {p95:.2f} ms")
    print(f"p99: {p99:.2f} ms")
    print(f"Avg: {avg:.2f} ms")
    print(f"Min: {latencies[0]:.2f} ms | Max: {latencies[-1]:.2f} ms")


def benchmark_async_pipeline(base_url, token):
    print("\n--- Benchmarking Async Pipeline Latency ---")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Since quick-save endpoint triggers a background process (process_bookmark_content_async),
    # we can poll the search endpoint to see when the bookmark becomes searchable (embedded).
    # This might require waiting.
    
    test_url = f"https://example.com/test-{uuid.uuid4()}"
    save_payload = {
        "url": test_url,
        "title": "Async Benchmark Test",
        "description": "Testing async processing pipeline"
    }
    
    print(f"Submitting bookmark for async processing: {test_url}")
    start_time = time.perf_counter()
    resp = requests.post(f"{base_url}/api/bookmarks/quick-save", json=save_payload, headers=headers)
    api_return_time = time.perf_counter()
    
    if resp.status_code != 201 and resp.status_code != 200:
        print(f"Failed to submit bookmark: {resp.status_code} - {resp.text}")
        return
        
    print(f"API returned in {(api_return_time - start_time)*1000:.2f} ms (Non-blocking success)")
    
    # Now poll the search endpoint until this URL appears in results for a relevant query
    # The quick-save saves minimal data immediately and starts background job for embeddings
    
    max_wait = 60 # seconds
    poll_interval = 1 # second
    
    print("Polling search endpoint until embedding is available...")
    found = False
    
    for i in range(max_wait):
        time.sleep(poll_interval)
        
        # Search for the exact title to see if it's indexed
        search_resp = requests.post(
            f"{base_url}/api/search/semantic", 
            json={"query": "Async Benchmark Test", "limit": 5}, 
            headers=headers
        )
        
        if search_resp.status_code == 200:
            results = search_resp.json().get("results", [])
            for r in results:
                if r.get("url") == test_url:
                    found = True
                    break
        
        if found:
            end_time = time.perf_counter()
            total_processing_time = end_time - start_time
            print(f"Pipeline completed! Bookmark is searchable after {total_processing_time:.2f} seconds.")
            break
            
    if not found:
        print(f"Pipeline did not complete within {max_wait} seconds.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fuze Performance Benchmark")
    parser.add_argument("--url", required=True, help="Base URL (e.g. http://localhost:5000 or https://xyz.hf.space)")
    parser.add_argument("--username", required=True, help="Test account username")
    parser.add_argument("--password", required=True, help="Test account password")
    
    args = parser.parse_args()
    
    token = authenticate(args.url, args.username, args.password)
    
    if token:
        benchmark_model_load(args.url, token)
        benchmark_cache_hit_rate(args.url, token, n_requests=20)
        benchmark_search_latency(args.url, token, n_requests=50)
        benchmark_async_pipeline(args.url, token)
        
        print("\nBenchmark complete!")
