#!/usr/bin/env python3
"""
Advanced LinkedIn Post Scraper - Anti-ban features for large-scale scraping
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
import random
from datetime import datetime
from typing import Dict, List, Optional
import logging
import os
from urllib.parse import urlparse
import threading
from queue import Queue

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedLinkedInScraper:
    """Advanced LinkedIn scraper with anti-ban features"""
    
    def __init__(self, max_requests_per_hour=50, delay_range=(2, 8)):
        self.sessions = self.create_session_pool()
        self.current_session = 0
        self.request_count = 0
        self.last_request_time = 0
        self.max_requests_per_hour = max_requests_per_hour
        self.delay_range = delay_range
        self.results = []
        self.failed_urls = []
        
        # Rate limiting
        self.request_times = []
        self.hourly_limit = max_requests_per_hour
        
    def create_session_pool(self) -> List[requests.Session]:
        """Create multiple sessions with different configurations"""
        sessions = []
        
        # Different user agents to rotate
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        ]
        
        # Different header configurations
        header_configs = [
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Cache-Control": "max-age=0"
            },
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            },
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "cross-site"
            }
        ]
        
        for i in range(5):  # Create 5 different sessions
            session = requests.Session()
            user_agent = random.choice(user_agents)
            headers = random.choice(header_configs).copy()
            headers["User-Agent"] = user_agent
            
            session.headers.update(headers)
            sessions.append(session)
            
        return sessions
    
    def get_next_session(self) -> requests.Session:
        """Get next session in rotation"""
        session = self.sessions[self.current_session]
        self.current_session = (self.current_session + 1) % len(self.sessions)
        return session
    
    def rate_limit_check(self):
        """Check and enforce rate limiting"""
        current_time = time.time()
        
        # Remove requests older than 1 hour
        self.request_times = [t for t in self.request_times if current_time - t < 3600]
        
        # Check if we've exceeded hourly limit
        if len(self.request_times) >= self.hourly_limit:
            sleep_time = 3600 - (current_time - self.request_times[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached. Sleeping for {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
        
        # Add random delay between requests
        if self.last_request_time > 0:
            delay = random.uniform(*self.delay_range)
            time.sleep(delay)
        
        self.last_request_time = current_time
        self.request_times.append(current_time)
    
    def scrape_post(self, url: str) -> Dict:
        """Main method to scrape a LinkedIn post with anti-ban features"""
        logger.info(f"🔍 Scraping LinkedIn post: {url}")
        
        # Rate limiting
        self.rate_limit_check()
        
        # Try multiple strategies
        strategies = [
            self.try_direct_scraping,
            self.try_alternative_headers,
            self.try_mobile_user_agent,
            self.try_proxy_rotation  # Placeholder for proxy support
        ]
        
        for strategy in strategies:
            try:
                result = strategy(url)
                if result.get('success') and len(result.get('content', '')) > 200:
                    logger.info(f"✅ Success with {strategy.__name__}")
                    return result
            except Exception as e:
                logger.warning(f"Strategy {strategy.__name__} failed: {e}")
                continue
        
        # Fallback
        return self.get_fallback_result(url, "All strategies failed")
    
    def try_direct_scraping(self, url: str) -> Dict:
        """Try direct scraping with session rotation"""
        try:
            session = self.get_next_session()
            response = session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            return self.extract_content(soup, url, "Direct scraping")
            
        except Exception as e:
            logger.warning(f"Direct scraping failed: {e}")
            return self.get_fallback_result(url, f"Direct scraping failed: {e}")
    
    def try_alternative_headers(self, url: str) -> Dict:
        """Try with alternative headers"""
        try:
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
            
        except Exception as e:
            logger.warning(f"Alternative headers failed: {e}")
            return self.get_fallback_result(url, f"Alternative headers failed: {e}")
    
    def try_mobile_user_agent(self, url: str) -> Dict:
        """Try with mobile user agent"""
        try:
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
            
        except Exception as e:
            logger.warning(f"Mobile user agent failed: {e}")
            return self.get_fallback_result(url, f"Mobile user agent failed: {e}")
    
    def try_proxy_rotation(self, url: str) -> Dict:
        """Placeholder for proxy rotation (implement if needed)"""
        # This would rotate through different proxies
        # For now, just return fallback
        return self.get_fallback_result(url, "Proxy rotation not implemented")
    
    def extract_content(self, soup: BeautifulSoup, url: str, method: str) -> Dict:
        """Extract content from HTML using multiple strategies"""
        
        # Extract title
        title = self.extract_title(soup)
        
        # Extract meta description
        meta_desc = self.extract_meta_description(soup)
        
        # Extract main content using multiple strategies
        content = self.extract_main_content(soup)
        
        # Clean and structure the content
        structured_content = self.structure_content(content, title, meta_desc)
        
        # Calculate quality score
        quality_score = self.calculate_quality_score(structured_content, title, meta_desc)
        
        # Extract additional metadata
        metadata = self.extract_metadata(soup)
        
        result = {
            'title': title,
            'content': structured_content,
            'meta_description': meta_desc,
            'quality_score': quality_score,
            'success': len(structured_content) > 100,
            'url': url,
            'method_used': method,
            'raw_content_length': len(content),
            'metadata': metadata,
            'scraped_at': datetime.now().isoformat()
        }
        
        return result
    
    def extract_title(self, soup: BeautifulSoup) -> str:
        """Extract title from HTML"""
        title_sources = [
            soup.find('title'),
            soup.find('meta', attrs={'property': 'og:title'}),
            soup.find('meta', attrs={'name': 'twitter:title'}),
            soup.find('h1'),
            soup.find('h2')
        ]
        
        for source in title_sources:
            if source:
                if source.name == 'meta':
                    title = source.get('content', '').strip()
                else:
                    title = source.get_text(strip=True)
                
                if title and title.lower() != 'linkedin':
                    return title
        
        return "LinkedIn Post"
    
    def extract_meta_description(self, soup: BeautifulSoup) -> str:
        """Extract meta description"""
        meta_desc_sources = [
            soup.find('meta', attrs={'name': 'description'}),
            soup.find('meta', attrs={'property': 'og:description'}),
            soup.find('meta', attrs={'name': 'twitter:description'})
        ]
        
        for source in meta_desc_sources:
            if source and source.get('content'):
                desc = source.get('content').strip()
                if desc:
                    return desc
        
        return ""
    
    def extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content using multiple strategies"""
        content = ""
        
        # Strategy 1: LinkedIn-specific selectors
        linkedin_selectors = [
            '.feed-shared-update-v2__description',
            '.feed-shared-text',
            '.feed-shared-update-v2__description-wrapper',
            '.feed-shared-text__text',
            '.feed-shared-update-v2__content',
            '[data-test-id="post-content"]',
            '.feed-shared-update-v2',
            '.feed-shared-post',
            '.update-components-text',
            '.post-content',
            '.content-body'
        ]
        
        for selector in linkedin_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(separator=" ", strip=True)
                    if text and len(text) > 100 and not self.is_ui_content(text):
                        content = text
                        break
                if content:
                    break
            except:
                continue
        
        # Strategy 2: Article and main content
        if not content or len(content) < 100:
            main_selectors = ['article', 'main', '.content', '.post-content', '.entry-content', '.post-body']
            for selector in main_selectors:
                try:
                    element = soup.select_one(selector)
                    if element:
                        text = element.get_text(separator=" ", strip=True)
                        if text and len(text) > 100 and not self.is_ui_content(text):
                            content = text
                            break
                except:
                    continue
        
        # Strategy 3: Look for divs with substantial text
        if not content or len(content) < 100:
            divs = soup.find_all('div')
            for div in divs:
                try:
                    text = div.get_text(separator=" ", strip=True)
                    if text and len(text) > 200 and not self.is_ui_content(text):
                        content = text
                        break
                except:
                    continue
        
        # Strategy 4: Fallback to all text
        if not content or len(content) < 100:
            content = soup.get_text(separator=" ", strip=True)
        
        return content
    
    def is_ui_content(self, text: str) -> bool:
        """Check if text is likely UI content"""
        ui_indicators = [
            'like', 'comment', 'share', 'report', 'follow', 'connect',
            'sign in', 'join now', 'welcome back', 'explore topics',
            'privacy policy', 'terms of service', 'cookie policy',
            'see more', 'see less', 'show more', 'show less',
            'add a comment', 'react to this', 'send message'
        ]
        
        text_lower = text.lower()
        ui_count = sum(1 for indicator in ui_indicators if indicator in text_lower)
        
        return ui_count > 3
    
    def extract_metadata(self, soup: BeautifulSoup) -> Dict:
        """Extract additional metadata"""
        metadata = {}
        
        # Try to extract author information
        author_selectors = [
            '.update-components-actor__title',
            '.post-author',
            '.author-name',
            '[data-test-id="post-author"]'
        ]
        
        for selector in author_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    author = element.get_text(strip=True)
                    if author and author.lower() != 'linkedin':
                        metadata['author'] = author
                        break
            except:
                continue
        
        # Try to extract post time
        time_selectors = [
            '.update-components-actor__sub-description',
            '.post-time',
            '.timestamp',
            'time'
        ]
        
        for selector in time_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    time_text = element.get_text(strip=True)
                    if time_text:
                        metadata['post_time'] = time_text
                        break
            except:
                continue
        
        return metadata
    
    def structure_content(self, content: str, title: str, meta_desc: str) -> str:
        """Structure and clean the content"""
        if not content:
            return ""
        
        content = self.clean_content(content)
        
        parts = []
        
        if title and title != "LinkedIn":
            parts.append(f"Title: {title}")
        
        if meta_desc:
            parts.append(f"Description: {meta_desc}")
        
        if content:
            parts.append(f"Content: {content}")
        
        return "\n\n".join(parts)
    
    def clean_content(self, content: str) -> str:
        """Clean the content by removing UI elements and noise"""
        if not content:
            return ""
        
        content = re.sub(r'\s+', ' ', content)
        
        ui_patterns = [
            r'Report this post',
            r'Report this comment',
            r'Like\s+Comment\s+Share',
            r'Copy\s+LinkedIn\s+Facebook\s+Twitter',
            r'See more comments',
            r'To view or add a comment, sign in',
            r'Sign in to view more content',
            r'Join now\s+Sign in',
            r'Welcome back',
            r'Explore topics',
            r'Privacy Policy',
            r'Terms of Service',
            r'Cookie Policy',
            r'User Agreement',
            r'See more',
            r'See less',
            r'Show more',
            r'Show less'
        ]
        
        for pattern in ui_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if len(line) < 10 or line.isdigit():
                continue
            
            if any(ui in line.lower() for ui in ['like', 'comment', 'share', 'follow', 'connect']):
                continue
            
            cleaned_lines.append(line)
        
        content = ' '.join(cleaned_lines)
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def calculate_quality_score(self, content: str, title: str, meta_description: str) -> int:
        """Calculate quality score for the content"""
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
        
        content_lower = content.lower()
        tech_keywords = ['tutorial', 'api', 'how to', 'guide', 'documentation', 'example', 'code', 'javascript', 'python', 'react', 'problem', 'solution', 'algorithm', 'performance', 'service', 'rust', 'go', 'tiktok']
        for keyword in tech_keywords:
            if keyword in content_lower:
                score += 1
                break
        
        score = max(1, min(10, score))
        return score
    
    def get_fallback_result(self, url: str, error: str) -> Dict:
        """Generate fallback result when scraping fails"""
        return {
            'title': 'LinkedIn Post',
            'content': f'Unable to extract content from LinkedIn post: {url}. Error: {error}. LinkedIn requires authentication for most content.',
            'meta_description': 'LinkedIn post - extraction failed',
            'quality_score': 3,
            'success': False,
            'url': url,
            'method_used': 'Fallback',
            'error': error,
            'scraped_at': datetime.now().isoformat()
        }
    
    def scrape_multiple_posts(self, urls: List[str], max_workers=3) -> List[Dict]:
        """Scrape multiple posts with threading and rate limiting"""
        results = []
        
        if len(urls) <= max_workers:
            # Sequential scraping for small batches
            for url in urls:
                try:
                    result = self.scrape_post(url)
                    results.append(result)
                    if not result.get('success'):
                        self.failed_urls.append(url)
                except Exception as e:
                    logger.error(f"Failed to scrape {url}: {e}")
                    self.failed_urls.append(url)
        else:
            # Threaded scraping for large batches
            queue = Queue()
            for url in urls:
                queue.put(url)
            
            def worker():
                while not queue.empty():
                    try:
                        url = queue.get_nowait()
                        result = self.scrape_post(url)
                        results.append(result)
                        if not result.get('success'):
                            self.failed_urls.append(url)
                    except Exception as e:
                        logger.error(f"Worker failed: {e}")
                    finally:
                        queue.task_done()
            
            threads = []
            for _ in range(min(max_workers, len(urls))):
                thread = threading.Thread(target=worker)
                thread.start()
                threads.append(thread)
            
            for thread in threads:
                thread.join()
        
        return results
    
    def save_results(self, filename: str = None) -> str:
        """Save results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"advanced_linkedin_scraping_results_{timestamp}.json"
        
        data = {
            'results': self.results,
            'failed_urls': self.failed_urls,
            'scraping_stats': {
                'total_requests': len(self.request_times),
                'successful_scrapes': len([r for r in self.results if r.get('success')]),
                'failed_scrapes': len(self.failed_urls),
                'scraped_at': datetime.now().isoformat()
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return filename

def main():
    """Main function for advanced usage"""
    print("🚀 Advanced LinkedIn Post Scraper (Anti-Ban)")
    print("=" * 60)
    
    # Configuration
    max_requests_per_hour = int(input("Max requests per hour (default 50): ") or "50")
    delay_min = float(input("Min delay between requests in seconds (default 2): ") or "2")
    delay_max = float(input("Max delay between requests in seconds (default 8): ") or "8")
    
    scraper = AdvancedLinkedInScraper(
        max_requests_per_hour=max_requests_per_hour,
        delay_range=(delay_min, delay_max)
    )
    
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
    
    print(f"\n🔍 Scraping {len(urls)} LinkedIn posts...")
    print("⏳ This may take a while due to rate limiting...")
    
    # Scrape posts
    results = scraper.scrape_multiple_posts(urls)
    
    # Display summary
    print("\n" + "=" * 60)
    print("📊 SCRAPING SUMMARY")
    print("=" * 60)
    
    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]
    
    print(f"✅ Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")
    print(f"📄 Total Content Extracted: {sum(len(r.get('content', '')) for r in successful)} characters")
    
    if successful:
        avg_quality = sum(r.get('quality_score', 0) for r in successful) / len(successful)
        print(f"⭐ Average Quality Score: {avg_quality:.1f}")
    
    # Save results
    filename = scraper.save_results()
    print(f"\n💾 Results saved to: {filename}")
    
    if failed:
        print(f"\n❌ Failed URLs saved to results file")
    
    print("\n✅ Advanced scraping completed!")

if __name__ == "__main__":
    main() 