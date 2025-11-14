#!/usr/bin/env python3
"""
Diagnose Missing Content and Test Improved Scraping
Analyzes bookmarks without extracted text and tests better scraping techniques
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, SavedContent
from utils_web_scraper import scrape_url
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import time

class ContentDiagnostic:
    """
    Diagnostic tool to analyze missing content and test improved scraping
    """
    
    def __init__(self):
        self.test_results = []
        
    def get_bookmarks_without_content(self) -> List[SavedContent]:
        """Get bookmarks that don't have extracted text"""
        try:
            with app.app_context():
                bookmarks = db.session.query(SavedContent).filter(
                    (SavedContent.extracted_text.is_(None)) |
                    (SavedContent.extracted_text == '') |
                    (SavedContent.extracted_text == 'null')
                ).all()
                return bookmarks
        except Exception as e:
            logger.error(f"Error getting bookmarks without content: {e}")
            return []
    
    def get_bookmarks_with_content(self) -> List[SavedContent]:
        """Get bookmarks that have extracted text"""
        try:
            with app.app_context():
                bookmarks = db.session.query(SavedContent).filter(
                    SavedContent.extracted_text.isnot(None),
                    SavedContent.extracted_text != '',
                    SavedContent.extracted_text != 'null'
                ).all()
                return bookmarks
        except Exception as e:
            logger.error(f"Error getting bookmarks with content: {e}")
            return []
    
    def analyze_content_distribution(self):
        """Analyze the distribution of content across bookmarks"""
        try:
            with app.app_context():
                total_bookmarks = db.session.query(SavedContent).count()
                bookmarks_with_content = db.session.query(SavedContent).filter(
                    SavedContent.extracted_text.isnot(None),
                    SavedContent.extracted_text != '',
                    SavedContent.extracted_text != 'null'
                ).count()
                bookmarks_without_content = total_bookmarks - bookmarks_with_content
                
                print(f"\n📊 CONTENT DISTRIBUTION ANALYSIS")
                print("=" * 50)
                print(f"Total bookmarks: {total_bookmarks}")
                print(f"With extracted text: {bookmarks_with_content}")
                print(f"Without extracted text: {bookmarks_without_content}")
                print(f"Content coverage: {(bookmarks_with_content/total_bookmarks)*100:.1f}%")
                
                return {
                    'total': total_bookmarks,
                    'with_content': bookmarks_with_content,
                    'without_content': bookmarks_without_content,
                    'coverage': (bookmarks_with_content/total_bookmarks)*100
                }
        except Exception as e:
            logger.error(f"Error analyzing content distribution: {e}")
            return {}
    
    def test_improved_scraping(self, url: str) -> Dict:
        """Test multiple scraping techniques on a URL"""
        results = {
            'url': url,
            'original_scraper': None,
            'enhanced_static': None,
            'playwright_only': None,
            'best_result': None
        }
        
        print(f"\n🔍 Testing improved scraping for: {url}")
        print("-" * 60)
        
        # 1. Test original scraper
        try:
            print("1. Testing original scraper...")
            start_time = time.time()
            original_result = scrape_url(url, use_playwright_fallback=False)
            original_time = time.time() - start_time
            
            results['original_scraper'] = {
                'content_length': len(original_result.get('content', '')),
                'title': original_result.get('title', ''),
                'time_taken': original_time,
                'quality_score': original_result.get('quality_score', 0)
            }
            print(f"   Content length: {results['original_scraper']['content_length']} chars")
            print(f"   Time taken: {original_time:.2f}s")
            print(f"   Quality score: {results['original_scraper']['quality_score']}")
            
        except Exception as e:
            print(f"   ❌ Original scraper failed: {e}")
        
        # 2. Test enhanced static scraping
        try:
            print("2. Testing enhanced static scraping...")
            start_time = time.time()
            enhanced_result = self.enhanced_static_scraping(url)
            enhanced_time = time.time() - start_time
            
            results['enhanced_static'] = {
                'content_length': len(enhanced_result.get('content', '')),
                'title': enhanced_result.get('title', ''),
                'time_taken': enhanced_time,
                'quality_score': enhanced_result.get('quality_score', 0)
            }
            print(f"   Content length: {results['enhanced_static']['content_length']} chars")
            print(f"   Time taken: {enhanced_time:.2f}s")
            print(f"   Quality score: {results['enhanced_static']['quality_score']}")
            
        except Exception as e:
            print(f"   ❌ Enhanced static scraping failed: {e}")
        
        # 3. Test Playwright-only scraping
        try:
            print("3. Testing Playwright-only scraping...")
            start_time = time.time()
            playwright_result = self.playwright_only_scraping(url)
            playwright_time = time.time() - start_time
            
            results['playwright_only'] = {
                'content_length': len(playwright_result.get('content', '')),
                'title': playwright_result.get('title', ''),
                'time_taken': playwright_time,
                'quality_score': playwright_result.get('quality_score', 0)
            }
            print(f"   Content length: {results['playwright_only']['content_length']} chars")
            print(f"   Time taken: {playwright_time:.2f}s")
            print(f"   Quality score: {results['playwright_only']['quality_score']}")
            
        except Exception as e:
            print(f"   ❌ Playwright-only scraping failed: {e}")
        
        # Determine best result
        best_result = None
        best_score = 0
        
        for method, result in results.items():
            if method != 'url' and method != 'best_result' and result:
                score = result['content_length'] * result['quality_score']
                if score > best_score:
                    best_score = score
                    best_result = method
        
        results['best_result'] = best_result
        print(f"\n🏆 Best method: {best_result}")
        
        return results
    
    def enhanced_static_scraping(self, url: str) -> Dict:
        """Enhanced static scraping with better content extraction"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            html = response.text
            
            soup = BeautifulSoup(html, "html.parser")
            
            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
                element.decompose()
            
            # Try multiple content extraction strategies
            content = ""
            
            # Strategy 1: Look for article tags
            article = soup.find('article')
            if article:
                content = article.get_text(separator=" ", strip=True)
            
            # Strategy 2: Look for main content areas
            if not content or len(content) < 200:
                main_content = soup.find('main') or soup.find(class_='content') or soup.find(class_='post-content') or soup.find(class_='entry-content')
                if main_content:
                    content = main_content.get_text(separator=" ", strip=True)
            
            # Strategy 3: Look for div with content-like classes
            if not content or len(content) < 200:
                content_classes = ['content', 'post', 'article', 'entry', 'text', 'body']
                for class_name in content_classes:
                    content_div = soup.find(class_=class_name)
                    if content_div:
                        content = content_div.get_text(separator=" ", strip=True)
                        if len(content) > 200:
                            break
            
            # Strategy 4: Fallback to all text
            if not content or len(content) < 200:
                content = soup.get_text(separator=" ", strip=True)
            
            # Clean up content
            content = ' '.join(content.split())  # Remove extra whitespace
            content = content[:8000]  # Limit to 8000 chars
            
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
            
            result = {
                'title': title,
                'content': content,
                'headings': headings,
                'meta_description': meta_desc,
                'quality_score': self.compute_quality_score(content, title, meta_desc, url)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Enhanced static scraping failed for {url}: {e}")
            return {'title': '', 'content': '', 'headings': [], 'meta_description': '', 'quality_score': 0}
    
    def playwright_only_scraping(self, url: str) -> Dict:
        """Playwright-only scraping for JavaScript-heavy sites"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Set viewport and user agent
                page.set_viewport_size({"width": 1280, "height": 720})
                page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                })
                
                # Navigate to page
                page.goto(url, timeout=30000)
                
                # Wait for content to load
                page.wait_for_load_state('networkidle', timeout=10000)
                time.sleep(2)  # Additional wait for dynamic content
                
                # Try to wait for content to appear
                try:
                    page.wait_for_selector('article, main, .content, .post-content', timeout=5000)
                except:
                    pass  # Continue if no specific content selector found
                
                # Get the HTML content
                html = page.content()
                browser.close()
                
                # Parse the HTML
                soup = BeautifulSoup(html, "html.parser")
                
                # Remove unwanted elements
                for element in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
                    element.decompose()
                
                # Extract content using multiple strategies
                content = ""
                
                # Strategy 1: Look for article tags
                article = soup.find('article')
                if article:
                    content = article.get_text(separator=" ", strip=True)
                
                # Strategy 2: Look for main content areas
                if not content or len(content) < 200:
                    main_content = soup.find('main') or soup.find(class_='content') or soup.find(class_='post-content') or soup.find(class_='entry-content')
                    if main_content:
                        content = main_content.get_text(separator=" ", strip=True)
                
                # Strategy 3: Look for div with content-like classes
                if not content or len(content) < 200:
                    content_classes = ['content', 'post', 'article', 'entry', 'text', 'body']
                    for class_name in content_classes:
                        content_div = soup.find(class_=class_name)
                        if content_div:
                            content = content_div.get_text(separator=" ", strip=True)
                            if len(content) > 200:
                                break
                
                # Strategy 4: Fallback to all text
                if not content or len(content) < 200:
                    content = soup.get_text(separator=" ", strip=True)
                
                # Clean up content
                content = ' '.join(content.split())  # Remove extra whitespace
                content = content[:8000]  # Limit to 8000 chars
                
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
                
                result = {
                    'title': title,
                    'content': content,
                    'headings': headings,
                    'meta_description': meta_desc,
                    'quality_score': self.compute_quality_score(content, title, meta_desc, url)
                }
                
                return result
                
        except Exception as e:
            logger.error(f"Playwright-only scraping failed for {url}: {e}")
            return {'title': '', 'content': '', 'headings': [], 'meta_description': '', 'quality_score': 0}
    
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
        tech_keywords = ['tutorial', 'api', 'how to', 'guide', 'documentation', 'example', 'code', 'javascript', 'python', 'react']
        for keyword in tech_keywords:
            if keyword in content_lower:
                score += 1
                break
        
        # Clamp score
        score = max(1, min(10, score))
        return score
    
    def test_sample_bookmarks(self, sample_size: int = 5):
        """Test improved scraping on a sample of bookmarks without content"""
        bookmarks_without_content = self.get_bookmarks_without_content()
        
        if not bookmarks_without_content:
            print("✅ All bookmarks have extracted content!")
            return
        
        print(f"\n🧪 Testing improved scraping on {min(sample_size, len(bookmarks_without_content))} bookmarks without content")
        print("=" * 70)
        
        sample_bookmarks = bookmarks_without_content[:sample_size]
        
        for i, bookmark in enumerate(sample_bookmarks, 1):
            print(f"\n📝 Test {i}/{len(sample_bookmarks)}: {bookmark.title}")
            print(f"   URL: {bookmark.url}")
            
            try:
                result = self.test_improved_scraping(bookmark.url)
                self.test_results.append(result)
                
                # Show summary
                best_method = result.get('best_result')
                if best_method and best_method in result:
                    best_data = result[best_method]
                    print(f"   🏆 Best: {best_method} - {best_data['content_length']} chars, Quality: {best_data['quality_score']}")
                
            except Exception as e:
                print(f"   ❌ Test failed: {e}")
        
        # Summary
        print(f"\n📊 TEST SUMMARY")
        print("=" * 50)
        successful_tests = [r for r in self.test_results if r.get('best_result')]
        print(f"Successful tests: {len(successful_tests)}/{len(sample_bookmarks)}")
        
        if successful_tests:
            method_counts = {}
            for result in successful_tests:
                method = result.get('best_result')
                method_counts[method] = method_counts.get(method, 0) + 1
            
            print("Best methods:")
            for method, count in method_counts.items():
                print(f"  {method}: {count} times")

def main():
    """Main diagnostic function"""
    diagnostic = ContentDiagnostic()
    
    print("🔍 CONTENT DIAGNOSTIC TOOL")
    print("=" * 50)
    
    # Analyze content distribution
    distribution = diagnostic.analyze_content_distribution()
    
    # Test improved scraping on sample bookmarks
    diagnostic.test_sample_bookmarks(sample_size=3)
    
    print(f"\n💡 RECOMMENDATIONS")
    print("=" * 50)
    
    if distribution.get('coverage', 0) < 80:
        print("⚠️  Low content coverage detected!")
        print("Recommendations:")
        print("1. Implement enhanced static scraping with better content extraction")
        print("2. Use Playwright for JavaScript-heavy sites")
        print("3. Add retry mechanisms for failed scrapes")
        print("4. Implement content quality scoring")
        print("5. Add fallback content extraction strategies")
    else:
        print("✅ Good content coverage!")
        print("Consider testing improved scraping for better quality content.")

if __name__ == "__main__":
    main() 