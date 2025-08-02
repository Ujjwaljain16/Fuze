#!/usr/bin/env python3
"""
Network connectivity test to diagnose connection issues
"""

import socket
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_network_connectivity():
    """Test basic network connectivity"""
    
    print("🔍 Testing Network Connectivity")
    
    # Test 1: Basic DNS resolution
    print("\n1. Testing DNS resolution...")
    try:
        ip = socket.gethostbyname("google.com")
        print(f"✅ DNS resolution works: google.com -> {ip}")
    except Exception as e:
        print(f"❌ DNS resolution failed: {e}")
        return False
    
    # Test 2: Test connection to Google
    print("\n2. Testing HTTP connection to Google...")
    try:
        response = requests.get("https://www.google.com", timeout=10)
        print(f"✅ HTTP connection works: Status {response.status_code}")
    except Exception as e:
        print(f"❌ HTTP connection failed: {e}")
        return False
    
    # Test 3: Test Supabase domain resolution
    supabase_url = os.environ.get("SUPABASE_URL")
    if supabase_url:
        print(f"\n3. Testing Supabase domain resolution...")
        try:
            # Extract domain from URL
            domain = supabase_url.replace("https://", "").replace("http://", "")
            ip = socket.gethostbyname(domain)
            print(f"✅ Supabase DNS resolution works: {domain} -> {ip}")
        except Exception as e:
            print(f"❌ Supabase DNS resolution failed: {e}")
            return False
        
        # Test 4: Test HTTP connection to Supabase
        print(f"\n4. Testing HTTP connection to Supabase...")
        try:
            response = requests.get(supabase_url, timeout=10)
            print(f"✅ Supabase HTTP connection works: Status {response.status_code}")
        except Exception as e:
            print(f"❌ Supabase HTTP connection failed: {e}")
            return False
    
    print("\n✅ All network tests passed!")
    return True

if __name__ == "__main__":
    test_network_connectivity() 