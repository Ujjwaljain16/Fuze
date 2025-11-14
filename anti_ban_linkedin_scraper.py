#!/usr/bin/env python3
"""
Anti-Ban LinkedIn Scraper - Key features to avoid detection
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import json
from datetime import datetime
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AntiBanLinkedInScraper:
    """LinkedIn scraper with anti-ban features"""
    
    def __init__(self, max_requests_per_hour=30):
        self.max_requests_per_hour = max_requests_per_hour
        self.request_times = []
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        ]
        
    def rate_limit_check(self):
        """Enforce rate limiting"""
        current_time = time.time()
        
        # Remove old requests (older than 1 hour)
        self.request_times = [t for t in self.request_times if current_time - t < 3600]
        
        # Check if we've hit the limit
        if len(self.request_times) >= self.max_requests_per_hour:
            sleep_time = 3600 - (current_time - self.request_times[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached. Sleeping for {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
        
        # Random delay between requests (2-8 seconds)
        delay = random.uniform(2, 8)
        time.sleep(delay)
        
        self.request_times.append(current_time)
    
    def get_random_headers(self):
        """Get random headers to avoid detection"""
        user_agent = random.choice(self.user_agents)
        
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        }
        
        return headers
    
    def scrape_post(self, url: str) -> Dict:
        """Scrape a LinkedIn post with anti-ban features"""
        logger.info(f"🔍 Scraping: {url}")
        
        # Rate limiting
        self.rate_limit_check()
        
        # Try multiple strategies
        strategies = [
            self.try_scraping_with_headers,
            self.try_mobile_user_agent,
            self.try_alternative_headers
        ]
        
        for strategy in strategies:
            try:
                result = strategy(url)
                if result.get('success') and len(result.get('content', '')) > 200:
                    return result
            except Exception as e:
                logger.warning(f"Strategy failed: {e}")
                continue
        
        return self.get_fallback_result(url)
    
    def try_scraping_with_headers(self, url: str) -> Dict:
        """Try scraping with random headers"""
        headers = self.get_random_headers()
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        return self.extract_content(soup, url, "Random headers")
    
    def try_mobile_user_agent(self, url: str) -> Dict:
        """Try with mobile user agent"""
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        return self.extract_content(soup, url, "Mobile user agent")
    
    def try_alternative_headers(self, url: str) -> Dict:
        """Try with alternative headers"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        return self.extract_content(soup, url, "Alternative headers")
    
    def extract_content(self, soup, url: str, method: str) -> Dict:
        """Extract content from HTML"""
        # Extract title
        title_tag = soup.find('title')
        title = title_tag.get_text(strip=True) if title_tag else "LinkedIn Post"
        
        # Extract meta description
        meta_desc_tag = soup.find('meta', attrs={'name': 'description'})
        meta_desc = meta_desc_tag.get('content', '') if meta_desc_tag else ""
        
        # Extract main content
        content = self.extract_main_content(soup)
        
        # Structure content
        structured_content = f"Title: {title}\n\nDescription: {meta_desc}\n\nContent: {content}"
        
        # Calculate quality score
        quality_score = self.calculate_quality_score(structured_content, title, meta_desc)
        
        return {
            'title': title,
            'content': structured_content,
            'meta_description': meta_desc,
            'quality_score': quality_score,
            'success': len(content) > 100,
            'url': url,
            'method_used': method,
            'scraped_at': datetime.now().isoformat()
        }
    
    def extract_main_content(self, soup) -> str:
        """Extract main content using multiple strategies"""
        content = ""
        
        # LinkedIn-specific selectors
        selectors = [
            '.feed-shared-update-v2__description',
            '.feed-shared-text',
            '.update-components-text',
            '.post-content',
            '.content-body'
        ]
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(separator=" ", strip=True)
                    if text and len(text) > 100:
                        content = text
                        break
                if content:
                    break
            except:
                continue
        
        # Fallback to all text
        if not content or len(content) < 100:
            content = soup.get_text(separator=" ", strip=True)
        
        return content
    
    def calculate_quality_score(self, content: str, title: str, meta_description: str) -> int:
        """Calculate quality score"""
        score = 10
        
        if len(content) < 100:
            score -= 5
        elif len(content) < 500:
            score -= 2
        elif len(content) > 2000:
            score += 2
        
        if title and title != "LinkedIn":
            score += 1
        
        if meta_description:
            score += 1
        
        return max(1, min(10, score))
    
    def get_fallback_result(self, url: str) -> Dict:
        """Generate fallback result"""
        return {
            'title': 'LinkedIn Post',
            'content': f'Unable to extract content from: {url}',
            'meta_description': 'Extraction failed',
            'quality_score': 3,
            'success': False,
            'url': url,
            'method_used': 'Fallback',
            'scraped_at': datetime.now().isoformat()
        }
    
    def scrape_multiple_posts(self, urls: List[str]) -> List[Dict]:
        """Scrape multiple posts with rate limiting"""
        results = []
        
        for i, url in enumerate(urls, 1):
            logger.info(f"Scraping {i}/{len(urls)}: {url}")
            
            try:
                result = self.scrape_post(url)
                results.append(result)
                
                if result.get('success'):
                    logger.info(f"✅ Success: {len(result.get('content', ''))} chars")
                else:
                    logger.warning(f"❌ Failed to extract content")
                    
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                results.append(self.get_fallback_result(url))
        
        return results

def main():
    """Main function"""
    print("🛡️ Anti-Ban LinkedIn Scraper")
    print("=" * 50)
    
    # Configuration
    max_requests = int(input("Max requests per hour (default 30): ") or "30")
    scraper = AntiBanLinkedInScraper(max_requests_per_hour=max_requests)
    
    # Get URLs
    print("\nEnter LinkedIn URLs (one per line, press Enter twice when done):")
    urls = []
    while True:
        url = input().strip()
        if not url:
            break
        if "linkedin.com" in url:
            urls.append(url)
        else:
            print("❌ Please enter a valid LinkedIn URL")
    
    if not urls:
        print("❌ No URLs provided. Exiting.")
        return
    
    print(f"\n🔍 Scraping {len(urls)} posts with anti-ban protection...")
    
    # Scrape posts
    results = scraper.scrape_multiple_posts(urls)
    
    # Summary
    successful = [r for r in results if r.get('success')]
    print(f"\n✅ Successful: {len(successful)}/{len(urls)}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"antiban_linkedin_results_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Results saved to: {filename}")
    print("✅ Anti-ban scraping completed!")

if __name__ == "__main__":
    main() 