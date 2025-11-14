#!/usr/bin/env python3
"""
Improved LinkedIn Scraper with Better Content Extraction
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import json
from typing import Dict
from playwright.sync_api import sync_playwright
import logging

logger = logging.getLogger(__name__)

class ImprovedLinkedInScraper:
    """Improved LinkedIn scraper with better content extraction"""
    
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
    
    def scrape_linkedin_post(self, url: str) -> Dict:
        """Scrape LinkedIn post with improved content extraction"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Set viewport and user agent
                page.set_viewport_size({"width": 1280, "height": 720})
                page.set_extra_http_headers({
                    "User-Agent": self.user_agents[0],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1"
                })
                
                # Navigate to LinkedIn post
                page.goto(url, timeout=30000)
                page.wait_for_load_state('networkidle', timeout=15000)
                time.sleep(5)  # Wait longer for content to load
                
                # Extract LinkedIn content with improved selectors
                linkedin_data = self.extract_linkedin_content_improved(page)
                
                html = page.content()
                browser.close()
                
                # Parse and clean the content
                result = self.parse_and_clean_content(html, url, linkedin_data)
                
                return result
                
        except Exception as e:
            logger.error(f"LinkedIn scraping failed: {e}")
            return self.get_fallback_content(url)
    
    def extract_linkedin_content_improved(self, page) -> Dict:
        """Extract LinkedIn content with improved selectors and logic"""
        try:
            linkedin_data = {}
            
            # Wait for content to load
            page.wait_for_timeout(3000)
            
            # Extract main post content with multiple strategies
            post_content = self.extract_main_post_content(page)
            
            # Extract author information
            author_info = self.extract_author_info(page)
            
            # Extract engagement metrics
            engagement = self.extract_engagement_metrics(page)
            
            # Extract comments (limited to first few)
            comments = self.extract_comments(page)
            
            # Build the result
            if post_content:
                linkedin_data = {
                    'post_content': post_content,
                    'author': author_info,
                    'engagement': engagement,
                    'comments': comments,
                    'success': True
                }
            
            return linkedin_data
            
        except Exception as e:
            logger.error(f"LinkedIn content extraction failed: {e}")
            return {}
    
    def extract_main_post_content(self, page) -> str:
        """Extract the main post content using multiple strategies"""
        # Strategy 1: Try specific LinkedIn post selectors
        post_selectors = [
            '[data-test-id="post-content"]',
            '.feed-shared-update-v2__description',
            '.feed-shared-text',
            '.feed-shared-update-v2__description-wrapper',
            '.feed-shared-text__text',
            '.feed-shared-update-v2__content',
            '.feed-shared-update-v2__description-wrapper .feed-shared-text__text',
            '.feed-shared-update-v2__description .feed-shared-text__text',
            '.feed-shared-text__text',
            '.feed-shared-update-v2__description'
        ]
        
        for selector in post_selectors:
            try:
                element = page.query_selector(selector)
                if element:
                    content = element.inner_text().strip()
                    if content and len(content) > 50:
                        # Clean the content
                        content = self.clean_post_content(content)
                        if content:
                            return content
            except:
                continue
        
        # Strategy 2: Try to find content by looking for the main post area
        try:
            # Look for the main post container
            main_post_selectors = [
                '.feed-shared-update-v2',
                '.feed-shared-post',
                '.feed-shared-update-v2__content',
                '[data-test-id="post-content"]'
            ]
            
            for selector in main_post_selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        # Get all text content and try to extract the main post
                        all_text = element.inner_text()
                        # Try to extract the main post by looking for patterns
                        main_post = self.extract_main_post_from_text(all_text)
                        if main_post:
                            return main_post
                except:
                    continue
        except:
            pass
        
        return ""
    
    def extract_main_post_from_text(self, text: str) -> str:
        """Extract main post content from mixed text"""
        # Split by common LinkedIn UI elements
        lines = text.split('\n')
        main_post_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip UI elements and comments
            if any(skip in line.lower() for skip in [
                'like', 'comment', 'share', 'report', 'reactions', 
                'reply', 'follow', 'connect', 'send message',
                'view profile', 'see more', 'sign in', 'join now'
            ]):
                continue
            
            # Skip short lines that are likely UI elements
            if len(line) < 10:
                continue
            
            # Skip lines that are just numbers (reaction counts)
            if line.isdigit():
                continue
            
            # Skip lines that are just emojis or very short
            if len(line) < 20 and not any(char.isalpha() for char in line):
                continue
            
            main_post_lines.append(line)
        
        # Join the main post lines
        main_post = '\n'.join(main_post_lines)
        
        # Clean up the post
        main_post = self.clean_post_content(main_post)
        
        return main_post
    
    def clean_post_content(self, content: str) -> str:
        """Clean and format post content"""
        if not content:
            return ""
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove common LinkedIn UI text
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
            r'Explore topics'
        ]
        
        for pattern in ui_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # Clean up extra whitespace again
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def extract_author_info(self, page) -> Dict:
        """Extract author information"""
        author_info = {}
        
        # Try to extract author name
        author_selectors = [
            '.feed-shared-actor__name',
            '.feed-shared-actor__title',
            '.feed-shared-actor__description',
            '[data-test-id="post-author"]',
            '.feed-shared-actor__name-link'
        ]
        
        for selector in author_selectors:
            try:
                element = page.query_selector(selector)
                if element:
                    author_name = element.inner_text().strip()
                    if author_name and len(author_name) > 2:
                        author_info['name'] = author_name
                        break
            except:
                continue
        
        return author_info
    
    def extract_engagement_metrics(self, page) -> Dict:
        """Extract engagement metrics"""
        engagement = {}
        
        # Try to extract likes, comments, shares
        engagement_selectors = [
            '.social-details-social-actions',
            '.feed-shared-social-action-bar',
            '.social-actions',
            '.feed-shared-social-action-bar__action-count'
        ]
        
        for selector in engagement_selectors:
            try:
                element = page.query_selector(selector)
                if element:
                    engagement_text = element.inner_text().strip()
                    if engagement_text:
                        engagement['text'] = engagement_text
                        break
            except:
                continue
        
        return engagement
    
    def extract_comments(self, page) -> list:
        """Extract comments (limited to first few)"""
        comments = []
        
        # Try to extract comments
        comment_selectors = [
            '.feed-shared-comment',
            '.comment',
            '.feed-shared-update-v2__comments .feed-shared-comment',
            '.feed-shared-comment__text'
        ]
        
        for selector in comment_selectors:
            try:
                comment_elements = page.query_selector_all(selector)
                for element in comment_elements[:3]:  # Limit to first 3 comments
                    comment_text = element.inner_text().strip()
                    if comment_text and len(comment_text) > 20:
                        # Clean comment text
                        clean_comment = self.clean_post_content(comment_text)
                        if clean_comment:
                            comments.append(clean_comment)
            except:
                continue
        
        return comments
    
    def parse_and_clean_content(self, html: str, url: str, linkedin_data: Dict) -> Dict:
        """Parse HTML and create final result"""
        soup = BeautifulSoup(html, "html.parser")
        
        # Extract title from page
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
        
        # Build the final content
        content_parts = []
        
        if linkedin_data.get('post_content'):
            content_parts.append(f"Post Content: {linkedin_data['post_content']}")
        
        if linkedin_data.get('author', {}).get('name'):
            content_parts.append(f"Author: {linkedin_data['author']['name']}")
        
        if linkedin_data.get('engagement', {}).get('text'):
            content_parts.append(f"Engagement: {linkedin_data['engagement']['text']}")
        
        if linkedin_data.get('comments'):
            content_parts.append("Comments:")
            for i, comment in enumerate(linkedin_data['comments'], 1):
                content_parts.append(f"{i}. {comment}")
        
        final_content = "\n\n".join(content_parts) if content_parts else ""
        
        # Calculate quality score
        quality_score = self.calculate_quality_score(final_content, title, meta_desc)
        
        result = {
            'title': title,
            'content': final_content,
            'headings': [],
            'meta_description': meta_desc,
            'quality_score': quality_score,
            'success': linkedin_data.get('success', False),
            'url': url,
            'linkedin_data': linkedin_data
        }
        
        return result
    
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
        if title:
            score += 1
        
        # Meta description presence
        if meta_description:
            score += 1
        
        # Content quality indicators
        content_lower = content.lower()
        tech_keywords = ['tutorial', 'api', 'how to', 'guide', 'documentation', 'example', 'code', 'javascript', 'python', 'react', 'problem', 'solution', 'algorithm', 'performance', 'service', 'rust', 'go']
        for keyword in tech_keywords:
            if keyword in content_lower:
                score += 1
                break
        
        # Clamp score
        score = max(1, min(10, score))
        return score
    
    def get_fallback_content(self, url: str) -> Dict:
        """Generate fallback content when scraping fails"""
        return {
            'title': 'LinkedIn Post',
            'content': f'Unable to extract content from LinkedIn post: {url}. This may be due to access restrictions or the site requiring authentication.',
            'headings': [],
            'meta_description': 'LinkedIn post - extraction failed',
            'quality_score': 3,
            'success': False,
            'url': url
        }

def test_improved_linkedin_scraping():
    """Test the improved LinkedIn scraper"""
    print("🔍 Testing Improved LinkedIn Post Scraping...")
    
    # LinkedIn post URL
    linkedin_url = "https://www.linkedin.com/feed/update/urn:li:activity:7357027266016530434?updateEntityUrn=urn%3Ali%3Afs_updateV2%3A%28urn%3Ali%3Aactivity%3A7357027266016530434%2CFEED_DETAIL%2CEMPTY%2CDEFAULT%2Cfalse%29"
    
    print(f"📝 Testing URL: {linkedin_url}")
    
    # Initialize scraper
    scraper = ImprovedLinkedInScraper()
    
    try:
        print("🚀 Starting improved scraping...")
        result = scraper.scrape_linkedin_post(linkedin_url)
        
        print("\n" + "="*50)
        print("📊 IMPROVED SCRAPING RESULTS")
        print("="*50)
        
        # Print key results
        print(f"✅ Success: {result.get('success', False)}")
        print(f"📝 Title: {result.get('title', 'N/A')}")
        print(f"🔗 URL: {result.get('url', 'N/A')}")
        print(f"📄 Content Length: {len(result.get('content', ''))} characters")
        print(f"⭐ Quality Score: {result.get('quality_score', 0)}")
        
        # Print LinkedIn-specific data
        linkedin_data = result.get('linkedin_data', {})
        if linkedin_data:
            print(f"👤 Author: {linkedin_data.get('author', {}).get('name', 'N/A')}")
            print(f"📊 Engagement: {linkedin_data.get('engagement', {}).get('text', 'N/A')}")
            print(f"💬 Comments: {len(linkedin_data.get('comments', []))}")
        
        # Print content preview
        content = result.get('content', '')
        if content:
            print(f"\n📄 Content Preview (first 800 chars):")
            print("-" * 40)
            print(content[:800] + "..." if len(content) > 800 else content)
            print("-" * 40)
        
        # Save full result to file for inspection
        with open('improved_linkedin_scraping_result.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Full result saved to: improved_linkedin_scraping_result.json")
        
        return result
        
    except Exception as e:
        print(f"❌ Scraping failed with error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_improved_linkedin_scraping() 