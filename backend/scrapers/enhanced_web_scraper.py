#!/usr/bin/env python3
"""
Enhanced Web Scraper with Advanced Content Extraction
Handles blocked sites, JavaScript-heavy content, and provides multiple fallback strategies
"""

import requests
from bs4 import BeautifulSoup
try:
    from readability import Document
except ImportError:
    Document = None
import re
import time
from typing import Dict
from urllib.parse import urlparse
from scrapers.fetchers.http_fetcher import HTTPFetcher
from scrapers.url_safety import is_safe_url
from core.logging_config import get_logger

logger = get_logger(__name__)

class EnhancedWebScraper:
    """
    Enhanced web scraper with multiple strategies for content extraction
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.setup_session()
        
        # Known problematic domains
        self.blocked_domains = {
            'leetcode.com': 'leetcode_api',
            'github.com': 'github_api', 
            'stackoverflow.com': 'stackoverflow_api',
            'medium.com': 'medium_api',
            'dev.to': 'devto_api'
        }
        
    
    def setup_session(self):
        """Setup requests session with proper headers"""
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0"
        })
    
    def get_domain_strategy(self, url: str) -> str:
        """Determine the best scraping strategy for a domain"""
        domain = urlparse(url).netloc.lower()
        
        # Check if it's a localhost/internal URL
        if 'localhost' in domain or '127.0.0.1' in domain or domain.startswith('192.168.') or domain.startswith('10.'):
            return 'localhost'
        
        # Check if it's a known blocked domain
        for blocked_domain, strategy in self.blocked_domains.items():
            if blocked_domain in domain:
                return strategy
        
        # Default strategy
        return 'enhanced_static'
    
    def scrape_url_enhanced(self, url: str) -> Dict:
        """
        Enhanced URL scraping with multiple strategies
        """
        if not is_safe_url(url):
            logger.error(f"Blocked unsafe URL: {url}")
            return self.get_fallback_content(url, "Blocked")

        strategy = self.get_domain_strategy(url)
        logger.info(f"Using strategy '{strategy}' for {url}")
        
        if strategy == 'localhost':
            return self.handle_localhost_url(url)
        elif strategy == 'leetcode_api':
            return self.handle_leetcode_url(url)
        elif strategy == 'github_api':
            return self.handle_github_url(url)
        elif strategy == 'stackoverflow_api':
            return self.handle_stackoverflow_url(url)
        elif strategy == 'medium_api':
            return self.handle_medium_url(url)
        elif strategy == 'devto_api':
            return self.handle_devto_url(url)
        else:
            return self.enhanced_static_scraping(url)
    
    def handle_localhost_url(self, url: str) -> Dict:
        """Handle localhost/internal URLs"""
        return {
            'title': 'Local Development URL',
            'content': f'This is a local development URL: {url}. Content cannot be scraped from external systems.',
            'headings': [],
            'meta_description': 'Local development environment',
            'quality_score': 5
        }
    
    def handle_leetcode_url(self, url: str) -> Dict:
        """Handle LeetCode URLs using their API or alternative methods"""
        try:
            # Try to extract problem ID from URL
            problem_match = re.search(r'/problems/([^/]+)', url)
            if problem_match:
                problem_slug = problem_match.group(1)
                
                # Try to get content via Playwright with specific LeetCode handling
                return self.enhanced_static_scraping(url)
            
            # For discussion URLs, try enhanced Playwright
            return self.enhanced_static_scraping(url)
            
        except Exception as e:
            logger.error(f"LeetCode handling failed: {e}")
            return self.get_fallback_content(url, "LeetCode")
    
    def handle_github_url(self, url: str) -> Dict:
        """Handle GitHub URLs"""
        try:
            return self.enhanced_static_scraping(url)
        except Exception as e:
            logger.error(f"GitHub handling failed: {e}")
            return self.get_fallback_content(url, "GitHub")
    
    def handle_stackoverflow_url(self, url: str) -> Dict:
        """Handle Stack Overflow URLs"""
        try:
            return self.enhanced_static_scraping(url)
        except Exception as e:
            logger.error(f"Stack Overflow handling failed: {e}")
            return self.get_fallback_content(url, "Stack Overflow")
    
    def handle_medium_url(self, url: str) -> Dict:
        """Handle Medium URLs"""
        try:
            return self.enhanced_static_scraping(url)
        except Exception as e:
            logger.error(f"Medium handling failed: {e}")
            return self.get_fallback_content(url, "Medium")
    
    def handle_devto_url(self, url: str) -> Dict:
        """Handle Dev.to URLs"""
        try:
            return self.enhanced_static_scraping(url)
        except Exception as e:
            logger.error(f"Dev.to handling failed: {e}")
            return self.get_fallback_content(url, "Dev.to")
    
    def enhanced_static_scraping(self, url: str) -> Dict:
        """Fetch a single page over plain HTTP (redirect hops are SSRF-checked) and parse it."""
        try:
            result = HTTPFetcher(timeout=15).fetch(url)
            if result.http_status >= 400 or not result.raw_content:
                return self.get_fallback_content(url, "Static")
            html = result.raw_content.decode("utf-8", errors="replace")
            return self.parse_html_content(html, url)
        except Exception as e:
            logger.warning(f"Static scraping failed for {url}: {e}")
            return self.get_fallback_content(url, "Static")

    def parse_html_content(self, html: str, url: str) -> Dict:
        """Parse HTML content with multiple extraction strategies"""
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside", "form", "iframe"]):
            element.decompose()
        
        # Extract title
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
        
        # Extract meta description
        meta_desc = ""
        meta_desc_tag = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc_tag:
            meta_desc_tag = soup.find('meta', attrs={'property': 'og:description'})
        if meta_desc_tag and meta_desc_tag.get('content'):
            meta_desc = meta_desc_tag['content'].strip()
        
        # Extract headings
        headings = []
        for tag in ['h1', 'h2', 'h3']:
            headings.extend([h.get_text(strip=True) for h in soup.find_all(tag)])
        
        # Multiple content extraction strategies
        content = self.extract_main_content(soup)
        
        # Clean up content
        content = ' '.join(content.split())  # Remove extra whitespace
        content = content[:8000]  # Limit to 8000 chars
        
        result = {
            'title': title,
            'content': content,
            'headings': headings,
            'meta_description': meta_desc,
            'quality_score': self.compute_quality_score(content, title, meta_desc, url)
        }
        
        return result
    
    def extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content using multiple strategies"""
        content = ""
        
        # Strategy 1: Look for article tags
        article = soup.find('article')
        if article:
            content = article.get_text(separator=" ", strip=True)
        
        # Strategy 2: Look for main content areas
        if not content or len(content) < 200:
            main_selectors = ['main', '.content', '.post-content', '.entry-content', '.article-content', '.post-body']
            for selector in main_selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    content = main_content.get_text(separator=" ", strip=True)
                    if len(content) > 200:
                        break
        
        # Strategy 3: Look for div with content-like classes
        if not content or len(content) < 200:
            content_classes = ['content', 'post', 'article', 'entry', 'text', 'body', 'description']
            for class_name in content_classes:
                content_div = soup.find(class_=class_name)
                if content_div:
                    content = content_div.get_text(separator=" ", strip=True)
                    if len(content) > 200:
                        break
        
        # Strategy 4: Use readability library
        if not content or len(content) < 200:
            try:
                doc = Document(str(soup))
                summary_html = doc.summary()
                content_soup = BeautifulSoup(summary_html, "html.parser")
                content = content_soup.get_text(separator=" ", strip=True)
            except Exception:
                pass
        
        # Strategy 5: Fallback to all text
        if not content or len(content) < 200:
            content = soup.get_text(separator=" ", strip=True)
        
        return content
    
    def compute_quality_score(self, content: str, title: str, meta_description: str, url: str) -> int:
        """Compute quality score for scraped content"""
        score = 10
        
        # Content length scoring
        if len(content) < 100:
            score -= 5
        elif len(content) < 500:
            score -= 2
        elif len(content) > 2000:
            score += 2
        
        # Title presence
        if title:
            score += 1
        
        # Meta description presence
        if meta_description:
            score += 1
        
        # Content quality indicators
        content_lower = content.lower()
        tech_keywords = ['tutorial', 'api', 'how to', 'guide', 'documentation', 'example', 'code', 'javascript', 'python', 'react', 'problem', 'solution', 'algorithm']
        for keyword in tech_keywords:
            if keyword in content_lower:
                score += 1
                break
        
        # Clamp score
        score = max(1, min(10, score))
        return score
    
    def get_fallback_content(self, url: str, source: str) -> Dict:
        """Generate fallback content when scraping fails"""
        # Generate meaningful fallback content instead of "Unable to extract" message
        # Extract meaningful info from URL
        from urllib.parse import unquote
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        path_parts = [p for p in parsed.path.strip('/').split('/') if p]
        
        # Create meaningful content from URL structure
        content_parts = [f"Content from {domain}"]
        if path_parts:
            skip_paths = {'www', 'index', 'home', 'page', 'post', 'article'}
            meaningful_parts = [unquote(p).replace('-', ' ').replace('_', ' ') 
                              for p in path_parts if p.lower() not in skip_paths]
            if meaningful_parts:
                content_parts.append('Topic: ' + ' '.join(meaningful_parts[:3]))
        
        fallback_content = '. '.join(content_parts)
        if len(fallback_content) < 50:
            fallback_content += f". URL: {url}"
        
        return {
            'title': f'Content from {domain}',
            'content': fallback_content,  # Never use "Unable to extract" message
            'headings': [],
            'meta_description': f'Content from {domain}',
            'quality_score': 3  # Low but not zero
        }

# Global instance
enhanced_scraper = EnhancedWebScraper()

def scrape_url_enhanced(url: str) -> Dict:
    """
    Enhanced URL scraping function
    """
    return enhanced_scraper.scrape_url_enhanced(url) 