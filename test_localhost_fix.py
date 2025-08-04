#!/usr/bin/env python3
"""
Test Localhost HTTP Client Fix
Verifies the 2+ second latency issue and tests solutions
"""

import time
import requests
import socket
import urllib.request

def test_different_hosts():
    """Test different ways to access localhost"""
    print("🔍 Testing Different Localhost Access Methods...")
    print("=" * 60)
    
    hosts = [
        "http://localhost:5000/",
        "http://127.0.0.1:5000/",
        "http://[::1]:5000/",
        "http://0.0.0.0:5000/"
    ]
    
    for host in hosts:
        print(f"\n🔍 Testing: {host}")
        
        # Test with requests
        start_time = time.time()
        try:
            response = requests.get(host, timeout=10)
            requests_time = time.time() - start_time
            print(f"  ✅ requests: {requests_time:.3f}s (status: {response.status_code})")
        except Exception as e:
            print(f"  ❌ requests failed: {e}")
        
        # Test with urllib
        start_time = time.time()
        try:
            response = urllib.request.urlopen(host, timeout=10)
            urllib_time = time.time() - start_time
            print(f"  ✅ urllib: {urllib_time:.3f}s (status: {response.getcode()})")
        except Exception as e:
            print(f"  ❌ urllib failed: {e}")

def test_session_reuse():
    """Test if session reuse helps"""
    print("\n🔍 Testing Session Reuse...")
    print("=" * 60)
    
    # First request (cold start)
    session = requests.Session()
    start_time = time.time()
    response = session.get("http://localhost:5000/", timeout=10)
    first_time = time.time() - start_time
    print(f"  ✅ First request: {first_time:.3f}s")
    
    # Second request (warm)
    start_time = time.time()
    response = session.get("http://localhost:5000/", timeout=10)
    second_time = time.time() - start_time
    print(f"  ✅ Second request: {second_time:.3f}s")
    
    # Third request (warm)
    start_time = time.time()
    response = session.get("http://localhost:5000/", timeout=10)
    third_time = time.time() - start_time
    print(f"  ✅ Third request: {third_time:.3f}s")

def test_connection_pooling():
    """Test connection pooling settings"""
    print("\n🔍 Testing Connection Pooling...")
    print("=" * 60)
    
    # Test with different connection pool settings
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    session = requests.Session()
    
    # Configure connection pooling
    adapter = HTTPAdapter(
        pool_connections=10,
        pool_maxsize=10,
        max_retries=Retry(total=0)  # No retries
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    start_time = time.time()
    response = session.get("http://localhost:5000/", timeout=10)
    pool_time = time.time() - start_time
    print(f"  ✅ With connection pooling: {pool_time:.3f}s")

def test_direct_socket():
    """Test direct socket connection"""
    print("\n🔍 Testing Direct Socket Connection...")
    print("=" * 60)
    
    # Test direct socket
    start_time = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(("localhost", 5000))
        
        # Send HTTP request
        request = b"GET / HTTP/1.1\r\nHost: localhost:5000\r\nConnection: close\r\n\r\n"
        sock.send(request)
        
        # Read response
        response = sock.recv(1024)
        sock.close()
        
        socket_time = time.time() - start_time
        print(f"  ✅ Direct socket: {socket_time:.3f}s")
    except Exception as e:
        print(f"  ❌ Direct socket failed: {e}")

def main():
    """Main test function"""
    print("🚀 Localhost HTTP Client Performance Test")
    print("=" * 60)
    
    test_different_hosts()
    test_session_reuse()
    test_connection_pooling()
    test_direct_socket()
    
    print("\n" + "=" * 60)
    print("💡 RECOMMENDATIONS:")
    print("  🔧 If 127.0.0.1 is faster than localhost:")
    print("     - Use 127.0.0.1 instead of localhost in your code")
    print("     - Add 127.0.0.1 localhost to your hosts file")
    print("  🔧 If session reuse helps:")
    print("     - Reuse requests.Session() objects")
    print("     - Configure connection pooling")
    print("  🔧 If direct socket is fast:")
    print("     - The issue is with HTTP client libraries")

if __name__ == "__main__":
    main() 