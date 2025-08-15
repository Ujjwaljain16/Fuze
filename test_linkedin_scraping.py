#!/usr/bin/env python3
"""
Test script to check if enhanced web scraper can handle LinkedIn posts
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_web_scraper import EnhancedWebScraper
import json

def test_linkedin_scraping():
    """Test LinkedIn post scraping"""
    print("🔍 Testing LinkedIn Post Scraping...")
    
    # LinkedIn post URL
    linkedin_url = "https://www.linkedin.com/feed/update/urn:li:activity:7357027266016530434?updateEntityUrn=urn%3Ali%3Afs_updateV2%3A%28urn%3Ali%3Aactivity%3A7357027266016530434%2CFEED_DETAIL%2CEMPTY%2CDEFAULT%2Cfalse%29"
    
    print(f"📝 Testing URL: {linkedin_url}")
    
    # Initialize scraper
    scraper = EnhancedWebScraper()
    
    try:
        print("🚀 Starting scraping...")
        result = scraper.scrape_url_enhanced(linkedin_url)
        
        print("\n" + "="*50)
        print("📊 SCRAPING RESULTS")
        print("="*50)
        
        # Print key results
        print(f"✅ Success: {result.get('success', False)}")
        print(f"📝 Title: {result.get('title', 'N/A')}")
        print(f"🔗 URL: {result.get('url', 'N/A')}")
        print(f"📄 Content Length: {len(result.get('content', ''))} characters")
        print(f"🏷️  Technologies: {result.get('technologies', [])}")
        print(f"⭐ Quality Score: {result.get('quality_score', 0)}")
        print(f"📋 Headings: {len(result.get('headings', []))}")
        print(f"🖼️  Images: {len(result.get('images', []))}")
        print(f"🔗 Links: {len(result.get('links', []))}")
        
        # Print content preview
        content = result.get('content', '')
        if content:
            print(f"\n📄 Content Preview (first 500 chars):")
            print("-" * 40)
            print(content[:500] + "..." if len(content) > 500 else content)
            print("-" * 40)
        
        # Print headings
        headings = result.get('headings', [])
        if headings:
            print(f"\n📋 Headings Found:")
            for i, heading in enumerate(headings[:5], 1):  # Show first 5
                print(f"  {i}. {heading}")
            if len(headings) > 5:
                print(f"  ... and {len(headings) - 5} more")
        
        # Print technologies
        technologies = result.get('technologies', [])
        if technologies:
            print(f"\n🏷️  Technologies Detected:")
            for tech in technologies:
                print(f"  • {tech}")
        
        # Check for any errors
        if result.get('error'):
            print(f"\n❌ Error: {result.get('error')}")
        
        # Save full result to file for inspection
        with open('linkedin_scraping_result.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Full result saved to: linkedin_scraping_result.json")
        
        return result
        
    except Exception as e:
        print(f"❌ Scraping failed with error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_linkedin_scraping() 