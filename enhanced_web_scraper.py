#!/usr/bin/env python3
"""
Enhanced Web Scraper with Advanced Content Extraction
Handles blocked sites, JavaScript-heavy content, and provides multiple fallback strategies
"""

import requests
from bs4 import BeautifulSoup
from readability import Document
import re
import time
import json
from typing import Dict, Optional, List
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

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
        
        # User agents for rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
        ]
    
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
                return self.leetcode_playwright_scraping(url, problem_slug)
            
            # For discussion URLs, try enhanced Playwright
            return self.enhanced_playwright_scraping(url, site_specific=True)
            
        except Exception as e:
            logger.error(f"LeetCode handling failed: {e}")
            return self.get_fallback_content(url, "LeetCode")
    
    def handle_github_url(self, url: str) -> Dict:
        """Handle GitHub URLs"""
        try:
            return self.github_playwright_scraping(url)
        except Exception as e:
            logger.error(f"GitHub handling failed: {e}")
            return self.get_fallback_content(url, "GitHub")
    
    def handle_stackoverflow_url(self, url: str) -> Dict:
        """Handle Stack Overflow URLs"""
        try:
            return self.enhanced_playwright_scraping(url, site_specific=True)
        except Exception as e:
            logger.error(f"Stack Overflow handling failed: {e}")
            return self.get_fallback_content(url, "Stack Overflow")
    
    def handle_medium_url(self, url: str) -> Dict:
        """Handle Medium URLs"""
        try:
            return self.enhanced_playwright_scraping(url, site_specific=True)
        except Exception as e:
            logger.error(f"Medium handling failed: {e}")
            return self.get_fallback_content(url, "Medium")
    
    def handle_devto_url(self, url: str) -> Dict:
        """Handle Dev.to URLs"""
        try:
            return self.enhanced_playwright_scraping(url, site_specific=True)
        except Exception as e:
            logger.error(f"Dev.to handling failed: {e}")
            return self.get_fallback_content(url, "Dev.to")
    
    def enhanced_static_scraping(self, url: str) -> Dict:
        """Enhanced static scraping with multiple strategies"""
        try:
            # Rotate user agents
            user_agent = self.user_agents[hash(url) % len(self.user_agents)]
            headers = {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            html = response.text
            
            return self.parse_html_content(html, url)
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Static scraping failed for {url}: {e}")
            # Fallback to Playwright
            return self.enhanced_playwright_scraping(url)
    
    def enhanced_playwright_scraping(self, url: str, site_specific: bool = False) -> Dict:
        """Enhanced Playwright scraping with site-specific optimizations"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Set viewport and user agent
                page.set_viewport_size({"width": 1280, "height": 720})
                user_agent = self.user_agents[hash(url) % len(self.user_agents)]
                page.set_extra_http_headers({"User-Agent": user_agent})
                
                # Site-specific configurations
                if site_specific:
                    if 'leetcode.com' in url:
                        # Wait longer for LeetCode content
                        page.goto(url, timeout=30000)
                        page.wait_for_load_state('networkidle', timeout=15000)
                        time.sleep(3)
                    elif 'stackoverflow.com' in url:
                        # Handle Stack Overflow's dynamic content
                        page.goto(url, timeout=30000)
                        page.wait_for_load_state('networkidle', timeout=10000)
                        time.sleep(2)
                    else:
                        # Default enhanced behavior
                        page.goto(url, timeout=30000)
                        page.wait_for_load_state('networkidle', timeout=10000)
                        time.sleep(2)
                else:
                    # Standard behavior
                    page.goto(url, timeout=30000)
                    page.wait_for_load_state('networkidle', timeout=10000)
                    time.sleep(2)
                
                # Try to wait for content to appear
                try:
                    page.wait_for_selector('article, main, .content, .post-content, .entry-content', timeout=5000)
                except:
                    pass
                
                html = page.content()
                browser.close()
                
                return self.parse_html_content(html, url)
                
        except Exception as e:
            logger.error(f"Playwright scraping failed for {url}: {e}")
            return self.get_fallback_content(url, "Playwright")
    
    def leetcode_playwright_scraping(self, url: str, problem_slug: str) -> Dict:
        """Specialized LeetCode scraping"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Set viewport and user agent
                page.set_viewport_size({"width": 1280, "height": 720})
                page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                })
                
                # Navigate to LeetCode
                page.goto(url, timeout=30000)
                
                # Wait for content to load
                page.wait_for_load_state('networkidle', timeout=15000)
                time.sleep(3)
                
                # Try to extract problem content
                try:
                    # Wait for problem description
                    page.wait_for_selector('[data-track-load="description_content"]', timeout=10000)
                except:
                    pass
                
                html = page.content()
                browser.close()
                
                return self.parse_html_content(html, url)
                
        except Exception as e:
            logger.error(f"LeetCode Playwright scraping failed: {e}")
            return self.get_fallback_content(url, "LeetCode")
    
    def github_playwright_scraping(self, url: str) -> Dict:
        """Specialized GitHub scraping"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                page.set_viewport_size({"width": 1280, "height": 720})
                page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                })
                
                page.goto(url, timeout=30000)
                page.wait_for_load_state('networkidle', timeout=10000)
                time.sleep(2)
                
                # Try to wait for README or content
                try:
                    page.wait_for_selector('.markdown-body, .readme', timeout=5000)
                except:
                    pass
                
                html = page.content()
                browser.close()
                
                return self.parse_html_content(html, url)
                
        except Exception as e:
            logger.error(f"GitHub Playwright scraping failed: {e}")
            return self.get_fallback_content(url, "GitHub")
    
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
        domain = urlparse(url).netloc
        
        return {
            'title': f'Content from {domain}',
            'content': f'Unable to extract content from {url}. This may be due to access restrictions or the site requiring authentication. Source: {source}',
            'headings': [],
            'meta_description': f'Content from {domain} - extraction failed',
            'quality_score': 3
        }

# Global instance
enhanced_scraper = EnhancedWebScraper()

def scrape_url_enhanced(url: str) -> Dict:
    """
    Enhanced URL scraping function
    """
    return enhanced_scraper.scrape_url_enhanced(url) 