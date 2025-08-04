#!/usr/bin/env python3
"""
Test Enhanced Scraper
Compare enhanced scraper with original scraper on problematic URLs
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_web_scraper import scrape_url_enhanced
from utils_web_scraper import scrape_url

def test_scrapers():
    """Test both scrapers on problematic URLs"""
    
    # Test URLs that were failing
    test_urls = [
        "https://leetcode.com/problems/classes-more-than-5-students/description/",
        "https://leetcode.com/discuss/career/448024/topic-wise-problems-for-beginners",
        "https://github.com/facebook/react",
        "https://stackoverflow.com/questions/123456/how-to-do-something"
    ]
    
    print("🧪 TESTING ENHANCED SCRAPER")
    print("=" * 60)
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n📝 Test {i}: {url}")
        print("-" * 50)
        
        # Test original scraper
        print("1. Original scraper:")
        try:
            start_time = time.time()
            original_result = scrape_url(url, use_playwright_fallback=False)
            original_time = time.time() - start_time
            
            print(f"   Content length: {len(original_result.get('content', ''))} chars")
            print(f"   Time taken: {original_time:.2f}s")
            print(f"   Quality score: {original_result.get('quality_score', 0)}")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
        
        # Test enhanced scraper
        print("2. Enhanced scraper:")
        try:
            start_time = time.time()
            enhanced_result = scrape_url_enhanced(url)
            enhanced_time = time.time() - start_time
            
            print(f"   Content length: {len(enhanced_result.get('content', ''))} chars")
            print(f"   Time taken: {enhanced_time:.2f}s")
            print(f"   Quality score: {enhanced_result.get('quality_score', 0)}")
            print(f"   Strategy used: {enhanced_result.get('strategy', 'unknown')}")
            
            # Show a preview of the content
            content = enhanced_result.get('content', '')
            if content:
                preview = content[:200] + "..." if len(content) > 200 else content
                print(f"   Content preview: {preview}")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
        
        print()

if __name__ == "__main__":
    test_scrapers() 