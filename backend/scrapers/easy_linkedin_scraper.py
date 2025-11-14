#!/usr/bin/env python3
"""
Easy LinkedIn Post Scraper - User-friendly tool for scraping LinkedIn posts
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EasyLinkedInScraper:
    """Easy-to-use LinkedIn post scraper with multiple strategies"""
    
    def __init__(self):
        self.session = requests.Session()
        self.setup_session()
        self.results = []
    
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
    
    def scrape_post(self, url: str) -> Dict:
        """Main method to scrape a LinkedIn post"""
        print(f"🔍 Scraping LinkedIn post: {url}")
        
        # Strategy 1: Try direct scraping
        result = self.try_direct_scraping(url)
        if result.get('success') and len(result.get('content', '')) > 200:
            return result
        
        # Strategy 2: Try with different headers
        result = self.try_alternative_headers(url)
        if result.get('success') and len(result.get('content', '')) > 200:
            return result
        
        # Strategy 3: Try mobile user agent
        result = self.try_mobile_user_agent(url)
        if result.get('success') and len(result.get('content', '')) > 200:
            return result
        
        # Strategy 4: Fallback - return what we have
        return result
    
    def try_direct_scraping(self, url: str) -> Dict:
        """Try direct scraping with standard headers"""
        try:
            response = self.session.get(url, timeout=15)
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
        # Try multiple title sources
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
        
        # If more than 3 UI indicators found, likely UI content
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
            r'User Agreement',
            r'See more',
            r'See less',
            r'Show more',
            r'Show less'
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
    
    def save_results(self, filename: str = None) -> str:
        """Save results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linkedin_scraping_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        return filename

def main():
    """Main function for easy usage"""
    print("🚀 Easy LinkedIn Post Scraper")
    print("=" * 50)
    
    # Get URL from user
    url = input("Enter LinkedIn post URL: ").strip()
    
    if not url:
        print("❌ No URL provided. Exiting.")
        return
    
    if "linkedin.com" not in url:
        print("❌ Please provide a valid LinkedIn URL.")
        return
    
    # Initialize scraper
    scraper = EasyLinkedInScraper()
    
    print(f"\n🔍 Scraping: {url}")
    print("⏳ This may take a few seconds...")
    
    # Scrape the post
    result = scraper.scrape_post(url)
    
    # Display results
    print("\n" + "=" * 50)
    print("📊 SCRAPING RESULTS")
    print("=" * 50)
    
    print(f"✅ Success: {result.get('success', False)}")
    print(f"📝 Title: {result.get('title', 'N/A')}")
    print(f"🔗 URL: {result.get('url', 'N/A')}")
    print(f"📄 Content Length: {len(result.get('content', ''))} characters")
    print(f"⭐ Quality Score: {result.get('quality_score', 0)}")
    print(f"🔧 Method Used: {result.get('method_used', 'N/A')}")
    
    if result.get('metadata'):
        print(f"👤 Author: {result.get('metadata', {}).get('author', 'N/A')}")
        print(f"⏰ Post Time: {result.get('metadata', {}).get('post_time', 'N/A')}")
    
    if result.get('error'):
        print(f"❌ Error: {result.get('error')}")
    
    # Show content preview
    content = result.get('content', '')
    if content:
        print(f"\n📄 Content Preview (first 500 chars):")
        print("-" * 40)
        print(content[:500] + "..." if len(content) > 500 else content)
        print("-" * 40)
    
    # Save results
    filename = scraper.save_results()
    print(f"\n💾 Results saved to: {filename}")
    
    # Ask if user wants to save content to text file
    save_text = input("\n💾 Save content to text file? (y/n): ").strip().lower()
    if save_text == 'y':
        text_filename = f"linkedin_content_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(text_filename, 'w', encoding='utf-8') as f:
            f.write(f"LinkedIn Post Content\n")
            f.write(f"URL: {url}\n")
            f.write(f"Title: {result.get('title', 'N/A')}\n")
            f.write(f"Scraped at: {result.get('scraped_at', 'N/A')}\n")
            f.write(f"Quality Score: {result.get('quality_score', 0)}\n")
            f.write(f"Method Used: {result.get('method_used', 'N/A')}\n")
            f.write("\n" + "="*50 + "\n\n")
            f.write(content)
        
        print(f"📄 Content saved to: {text_filename}")
    
    print("\n✅ Scraping completed!")

if __name__ == "__main__":
    main() 