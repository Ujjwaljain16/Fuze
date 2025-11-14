#!/usr/bin/env python3
"""
Comprehensive Performance Diagnosis for Fuze
Identifies the root cause of 2+ second latency
"""

import time
import requests
import json
import socket
import subprocess
import platform
import psutil
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:5000"
LOGIN_DATA = {
    "username": "ujjwaljain16",
    "password": "Jainsahab@16"
}

def test_dns_resolution():
    """Test DNS resolution time"""
    print("\n🔍 Testing DNS Resolution...")
    print("-" * 40)
    
    start_time = time.time()
    try:
        socket.gethostbyname("localhost")
        dns_time = time.time() - start_time
        print(f"✅ DNS resolution: {dns_time:.3f}s")
        return dns_time
    except Exception as e:
        print(f"❌ DNS resolution failed: {e}")
        return None

def test_tcp_connection():
    """Test TCP connection time"""
    print("\n🔍 Testing TCP Connection...")
    print("-" * 40)
    
    start_time = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(("localhost", 5000))
        sock.close()
        tcp_time = time.time() - start_time
        print(f"✅ TCP connection: {tcp_time:.3f}s")
        return tcp_time
    except Exception as e:
        print(f"❌ TCP connection failed: {e}")
        return None

def test_system_resources():
    """Test system resource usage"""
    print("\n🔍 Testing System Resources...")
    print("-" * 40)
    
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"✅ CPU usage: {cpu_percent:.1f}%")
    
    # Memory usage
    memory = psutil.virtual_memory()
    print(f"✅ Memory usage: {memory.percent:.1f}% ({memory.available / 1024**3:.1f}GB available)")
    
    # Disk usage
    disk = psutil.disk_usage('/')
    print(f"✅ Disk usage: {disk.percent:.1f}% ({disk.free / 1024**3:.1f}GB available)")
    
    return {
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'disk_percent': disk.percent
    }

def test_database_connection():
    """Test database connection directly"""
    print("\n🔍 Testing Database Connection...")
    print("-" * 40)
    
    try:
        from app import create_app
        from models import db
        
        app = create_app()
        with app.app_context():
            start_time = time.time()
            # Simple query
            result = db.session.execute("SELECT 1").fetchone()
            db_time = time.time() - start_time
            print(f"✅ Database query: {db_time:.3f}s")
            return db_time
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def test_redis_connection():
    """Test Redis connection directly"""
    print("\n🔍 Testing Redis Connection...")
    print("-" * 40)
    
    try:
        from redis_utils import redis_cache
        
        start_time = time.time()
        # Simple Redis operation
        redis_cache.set_cache("test_key", "test_value", 60)
        result = redis_cache.get_cache("test_key")
        redis_time = time.time() - start_time
        print(f"✅ Redis operation: {redis_time:.3f}s")
        return redis_time
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return None

def test_http_components():
    """Test HTTP request components"""
    print("\n🔍 Testing HTTP Components...")
    print("-" * 40)
    
    # Test with different HTTP clients
    import urllib.request
    import urllib.parse
    
    # Test with urllib
    start_time = time.time()
    try:
        response = urllib.request.urlopen(f"{BASE_URL}/", timeout=10)
        urllib_time = time.time() - start_time
        print(f"✅ urllib request: {urllib_time:.3f}s")
    except Exception as e:
        print(f"❌ urllib request failed: {e}")
        urllib_time = None
    
    # Test with requests (session)
    start_time = time.time()
    try:
        session = requests.Session()
        response = session.get(f"{BASE_URL}/", timeout=10)
        session_time = time.time() - start_time
        print(f"✅ requests session: {session_time:.3f}s")
    except Exception as e:
        print(f"❌ requests session failed: {e}")
        session_time = None
    
    return urllib_time, session_time

def test_flask_internals():
    """Test Flask internal components"""
    print("\n🔍 Testing Flask Internals...")
    print("-" * 40)
    
    try:
        from app import create_app
        
        app = create_app()
        
        # Test app creation time
        start_time = time.time()
        app = create_app()
        creation_time = time.time() - start_time
        print(f"✅ App creation: {creation_time:.3f}s")
        
        # Test with test client
        with app.test_client() as client:
            start_time = time.time()
            response = client.get('/')
            test_client_time = time.time() - start_time
            print(f"✅ Test client request: {test_client_time:.3f}s")
        
        return creation_time, test_client_time
    except Exception as e:
        print(f"❌ Flask internal test failed: {e}")
        return None, None

def test_network_latency():
    """Test network latency with different methods"""
    print("\n🔍 Testing Network Latency...")
    print("-" * 40)
    
    # Test ping
    try:
        start_time = time.time()
        result = subprocess.run(['ping', '-n', '1', 'localhost'], 
                              capture_output=True, text=True, timeout=5)
        ping_time = time.time() - start_time
        print(f"✅ Ping localhost: {ping_time:.3f}s")
    except Exception as e:
        print(f"❌ Ping failed: {e}")
        ping_time = None
    
    # Test curl (if available)
    try:
        start_time = time.time()
        result = subprocess.run(['curl', '-s', 'http://localhost:5000/'], 
                              capture_output=True, text=True, timeout=10)
        curl_time = time.time() - start_time
        print(f"✅ curl request: {curl_time:.3f}s")
    except Exception as e:
        print(f"❌ curl failed: {e}")
        curl_time = None
    
    return ping_time, curl_time

def main():
    """Main diagnostic function"""
    print("🚀 Fuze Performance Diagnosis")
    print("=" * 50)
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💻 Platform: {platform.platform()}")
    print(f"🐍 Python: {platform.python_version()}")
    
    # Run all diagnostics
    results = {}
    
    # System tests
    results['dns_resolution'] = test_dns_resolution()
    results['tcp_connection'] = test_tcp_connection()
    results['system_resources'] = test_system_resources()
    
    # Component tests
    results['database_connection'] = test_database_connection()
    results['redis_connection'] = test_redis_connection()
    results['http_components'] = test_http_components()
    results['flask_internals'] = test_flask_internals()
    results['network_latency'] = test_network_latency()
    
    # Analysis
    print("\n" + "=" * 80)
    print("📊 DIAGNOSIS ANALYSIS")
    print("=" * 80)
    
    # Identify bottlenecks
    bottlenecks = []
    
    if results['dns_resolution'] and results['dns_resolution'] > 0.1:
        bottlenecks.append(f"DNS resolution: {results['dns_resolution']:.3f}s")
    
    if results['tcp_connection'] and results['tcp_connection'] > 0.1:
        bottlenecks.append(f"TCP connection: {results['tcp_connection']:.3f}s")
    
    if results['database_connection'] and results['database_connection'] > 1.0:
        bottlenecks.append(f"Database connection: {results['database_connection']:.3f}s")
    
    if results['redis_connection'] and results['redis_connection'] > 0.1:
        bottlenecks.append(f"Redis connection: {results['redis_connection']:.3f}s")
    
    if results['system_resources']['cpu_percent'] > 80:
        bottlenecks.append(f"High CPU usage: {results['system_resources']['cpu_percent']:.1f}%")
    
    if results['system_resources']['memory_percent'] > 90:
        bottlenecks.append(f"High memory usage: {results['system_resources']['memory_percent']:.1f}%")
    
    # Recommendations
    print(f"\n🎯 BOTTLENECKS FOUND: {len(bottlenecks)}")
    for bottleneck in bottlenecks:
        print(f"  ⚠️ {bottleneck}")
    
    if not bottlenecks:
        print("  ✅ No obvious bottlenecks found")
    
    print(f"\n💡 RECOMMENDATIONS:")
    if len(bottlenecks) > 0:
        print("  🔧 Address the identified bottlenecks above")
    else:
        print("  🔍 The issue might be:")
        print("     - Antivirus/firewall interference")
        print("     - Network adapter issues")
        print("     - System-wide performance problems")
        print("     - Flask application logic")
    
    # Save results
    with open('performance_diagnosis_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📊 Detailed results saved to performance_diagnosis_results.json")

if __name__ == "__main__":
    main() 