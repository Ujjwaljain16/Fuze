#!/usr/bin/env python3
"""
Simple LinkedIn Scraper - Basic approach to avoid timeouts
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import json
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class SimpleLinkedInScraper:
    """Simple LinkedIn scraper using basic requests approach"""
    
    def __init__(self):
        self.session = requests.Session()
        self.setup_session()
    
    def setup_session(self):
        """Setup session with LinkedIn-friendly headers"""
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        })
    
    def scrape_linkedin_post(self, url: str) -> Dict:
        """Scrape LinkedIn post using simple requests approach"""
        try:
            print(f"🔍 Attempting to scrape: {url}")
            
            # Make the request
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract content using multiple strategies
            result = self.extract_content_from_html(soup, url)
            
            return result
            
        except requests.exceptions.Timeout:
            logger.error("Request timed out")
            return self.get_fallback_content(url, "Timeout")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return self.get_fallback_content(url, f"Request error: {e}")
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            return self.get_fallback_content(url, f"General error: {e}")
    
    def extract_content_from_html(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract content from HTML using multiple strategies"""
        
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
        
        # Extract main content using multiple strategies
        content = self.extract_main_content(soup)
        
        # Clean and structure the content
        structured_content = self.structure_content(content, title, meta_desc)
        
        # Calculate quality score
        quality_score = self.calculate_quality_score(structured_content, title, meta_desc)
        
        result = {
            'title': title,
            'content': structured_content,
            'headings': [],
            'meta_description': meta_desc,
            'quality_score': quality_score,
            'success': len(structured_content) > 100,  # Consider successful if we got substantial content
            'url': url,
            'raw_content_length': len(content)
        }
        
        return result
    
    def extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content using multiple strategies"""
        content = ""
        
        # Strategy 1: Look for LinkedIn-specific content areas
        linkedin_selectors = [
            '.feed-shared-update-v2__description',
            '.feed-shared-text',
            '.feed-shared-update-v2__description-wrapper',
            '.feed-shared-text__text',
            '.feed-shared-update-v2__content',
            '[data-test-id="post-content"]',
            '.feed-shared-update-v2',
            '.feed-shared-post'
        ]
        
        for selector in linkedin_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(separator=" ", strip=True)
                    if content and len(content) > 100:
                        break
            except:
                continue
        
        # Strategy 2: Look for article or main content
        if not content or len(content) < 100:
            main_selectors = ['article', 'main', '.content', '.post-content', '.entry-content']
            for selector in main_selectors:
                try:
                    element = soup.select_one(selector)
                    if element:
                        content = element.get_text(separator=" ", strip=True)
                        if content and len(content) > 100:
                            break
                except:
                    continue
        
        # Strategy 3: Look for any div with substantial text
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
            'privacy policy', 'terms of service', 'cookie policy'
        ]
        
        text_lower = text.lower()
        ui_count = sum(1 for indicator in ui_indicators if indicator in text_lower)
        
        # If more than 3 UI indicators found, likely UI content
        return ui_count > 3
    
    def structure_content(self, content: str, title: str, meta_desc: str) -> str:
        """Structure and clean the content"""
        if not content:
            return ""
        
        # Clean the content
        content = self.clean_content(content)
        
        # Structure the content
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
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove common LinkedIn UI patterns
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
            r'User Agreement'
        ]
        
        for pattern in ui_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # Remove lines that are just numbers or very short
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip very short lines or just numbers
            if len(line) < 10 or line.isdigit():
                continue
            
            # Skip lines that are just UI elements
            if any(ui in line.lower() for ui in ['like', 'comment', 'share', 'follow', 'connect']):
                continue
            
            cleaned_lines.append(line)
        
        # Join and clean up
        content = ' '.join(cleaned_lines)
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def calculate_quality_score(self, content: str, title: str, meta_description: str) -> int:
        """Calculate quality score for the content"""
        score = 10
        
        # Content length scoring
        if len(content) < 100:
            score -= 5
        elif len(content) < 500:
            score -= 2
        elif len(content) > 2000:
            score += 2
        
        # Title presence
        if title and title != "LinkedIn":
            score += 1
        
        # Meta description presence
        if meta_description:
            score += 1
        
        # Content quality indicators
        content_lower = content.lower()
        tech_keywords = ['tutorial', 'api', 'how to', 'guide', 'documentation', 'example', 'code', 'javascript', 'python', 'react', 'problem', 'solution', 'algorithm', 'performance', 'service', 'rust', 'go', 'tiktok']
        for keyword in tech_keywords:
            if keyword in content_lower:
                score += 1
                break
        
        # Clamp score
        score = max(1, min(10, score))
        return score
    
    def get_fallback_content(self, url: str, error: str) -> Dict:
        """Generate fallback content when scraping fails"""
        return {
            'title': 'LinkedIn Post',
            'content': f'Unable to extract content from LinkedIn post: {url}. Error: {error}. LinkedIn requires authentication for most content.',
            'headings': [],
            'meta_description': 'LinkedIn post - extraction failed',
            'quality_score': 3,
            'success': False,
            'url': url,
            'error': error
        }

def test_simple_linkedin_scraping():
    """Test the simple LinkedIn scraper"""
    print("🔍 Testing Simple LinkedIn Post Scraping...")
    
    # LinkedIn post URL
    linkedin_url = "https://www.linkedin.com/feed/update/urn:li:activity:7357027266016530434?updateEntityUrn=urn%3Ali%3Afs_updateV2%3A%28urn%3Ali%3Aactivity%3A7357027266016530434%2CFEED_DETAIL%2CEMPTY%2CDEFAULT%2Cfalse%29"
    
    print(f"📝 Testing URL: {linkedin_url}")
    
    # Initialize scraper
    scraper = SimpleLinkedInScraper()
    
    try:
        print("🚀 Starting simple scraping...")
        result = scraper.scrape_linkedin_post(linkedin_url)
        
        print("\n" + "="*50)
        print("📊 SIMPLE SCRAPING RESULTS")
        print("="*50)
        
        # Print key results
        print(f"✅ Success: {result.get('success', False)}")
        print(f"📝 Title: {result.get('title', 'N/A')}")
        print(f"🔗 URL: {result.get('url', 'N/A')}")
        print(f"📄 Content Length: {len(result.get('content', ''))} characters")
        print(f"📄 Raw Content Length: {result.get('raw_content_length', 0)} characters")
        print(f"⭐ Quality Score: {result.get('quality_score', 0)}")
        
        if result.get('error'):
            print(f"❌ Error: {result.get('error')}")
        
        # Print content preview
        content = result.get('content', '')
        if content:
            print(f"\n📄 Content Preview (first 800 chars):")
            print("-" * 40)
            print(content[:800] + "..." if len(content) > 800 else content)
            print("-" * 40)
        
        # Save full result to file for inspection
        with open('simple_linkedin_scraping_result.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Full result saved to: simple_linkedin_scraping_result.json")
        
        return result
        
    except Exception as e:
        print(f"❌ Scraping failed with error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_simple_linkedin_scraping() 