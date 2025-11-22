#!/usr/bin/env python3
"""
Scrapling-Enhanced Web Scraper
Uses Scrapling library for better extraction on problematic sites
"""

import logging
from typing import Dict, Optional
from urllib.parse import urlparse
import os
import asyncio
import threading
import re
import requests

logger = logging.getLogger(__name__)

# Try to import Scrapling - make it optional
# Handle multiple types of import errors (missing package, missing dependencies, etc.)
SCRAPLING_AVAILABLE = False
StealthyFetcher = None
DynamicFetcher = None
Fetcher = None

try:
    from scrapling.fetchers import StealthyFetcher, DynamicFetcher, Fetcher
    # Test if we can actually use it (browsers might not be installed)
    SCRAPLING_AVAILABLE = True
    logger.info("Scrapling imported successfully")
except ImportError as e:
    SCRAPLING_AVAILABLE = False
    logger.warning(f" Scrapling not installed. Install with: pip install 'scrapling[all]' 'camoufox[geoip]'")
    logger.info("   Will use standard scraper instead")
except (FileNotFoundError, AttributeError, ModuleNotFoundError) as e:
    # Handle errors like missing camoufox, browser dependencies, etc.
    SCRAPLING_AVAILABLE = False
    error_msg = str(e)
    if 'camoufox' in error_msg.lower() or 'fetch' in error_msg.lower() or 'version.json' in error_msg.lower():
        logger.warning(f" Scrapling installed but camoufox browser not set up.")
        logger.warning(f"   Run: camoufox fetch")
        logger.warning(f"   Or: python scripts/setup_scrapling.py")
        logger.info("   Will use standard scraper until browsers are installed")
    else:
        logger.warning(f" Scrapling import failed: {error_msg[:150]}")
        logger.info("   Will use standard scraper instead")
except Exception as e:
    # Catch any other errors during import
    SCRAPLING_AVAILABLE = False
    error_msg = str(e)
    logger.warning(f" Scrapling import error: {error_msg[:150]}")
    logger.info("   Will use standard scraper instead")

# Import existing scraper as fallback
from scrapers.enhanced_web_scraper import EnhancedWebScraper
from bs4 import BeautifulSoup

class ScraplingEnhancedScraper:
    """
    Enhanced scraper using Scrapling for problematic sites
    Falls back to existing scraper if Scrapling fails or is unavailable
    """
    
    def __init__(self):
        self.fallback_scraper = EnhancedWebScraper()
        self._browsers_installed = None  # Cache browser installation status
        self._adaptive_enabled = False  # Track if adaptive mode is available
        
        # Domains that benefit from Scrapling - expanded list
        self.scrapling_domains = {
            # Anti-bot protected sites
            'github.com': 'stealthy',
            'leetcode.com': 'stealthy',
            'codeforces.com': 'stealthy',
            'medium.com': 'stealthy',
            'dev.to': 'stealthy',
            'flaviocopes.com': 'stealthy',
            'stackoverflow.com': 'stealthy',
            'neetishop.medium.com': 'stealthy',
            'people.cs.rutgers.edu': 'stealthy',
            'www.npci.org.in': 'stealthy',
            'learnxinyminutes.com': 'stealthy',
            'decentro.tech': 'stealthy',
            'newline.co': 'stealthy',  # Added
            'willendless.github.io': 'stealthy',  # Added
            # JavaScript-heavy/SPA sites
            'andreasbm.github.io': 'dynamic',
            'devdocs.io': 'dynamic',
            'dashboard.render.com': 'dynamic',
            'neetcode.io': 'dynamic',
            'masterjs.vercel.app': 'dynamic',
            'mohiyaddeenraza.vercel.app': 'dynamic',
            'lovable.dev': 'dynamic',
            'openml.org': 'dynamic',
            'www.openml.org': 'dynamic',
            'vision.hack2skill.com': 'dynamic',
            'www.lintcode.com': 'dynamic',
            'status.setu.co': 'dynamic',
        }
        
        # Domains that require auth (skip scraping)
        self.auth_required_domains = {
            'chatgpt.com',
            'claude.ai',
            'gemini.google.com',
            'chat.deepseek.com',
            'colab.research.google.com',
            'learning.edx.org',
            'app.expense.fyi',
        }
    
    def _intelligent_content_extraction(self, page, url: str) -> str:
        """
        Intelligent content extraction that tries multiple strategies and picks the best result
        Uses heuristics to find the main content area automatically
        """
        candidates = []
        
        try:
            # Strategy 1: Semantic HTML5 elements (highest priority)
            semantic_selectors = [
                'article',
                'main',
                '[role="main"]',
                '[role="article"]',
                'section[role="main"]',
            ]
            
            for selector in semantic_selectors:
                try:
                    elem = page.css_first(selector)
                    if elem:
                        text = elem.get_all_text(separator=' ', strip=True,
                                                ignore_tags=('script', 'style', 'noscript', 'nav', 'header', 'footer', 'aside'),
                                                valid_values=True)
                        if text:
                            text_str = str(text).strip()
                            if len(text_str) > 100:
                                # Score based on length and content quality
                                score = self._score_content_quality(text_str)
                                candidates.append((text_str, score, 'semantic'))
                except:
                    continue
            
            # Strategy 2: Common content class patterns (intelligent detection)
            content_patterns = [
                # High confidence patterns
                '.content', '.post-content', '.article-content', '.entry-content',
                '.post-body', '.article-body', '.main-content', '.page-content',
                '.markdown-body', '.repository-content', '.documentation-content',
                # Medium confidence
                '.post', '.article', '.entry', '.text', '.body', '.description',
                # Lower confidence but common
                '[class*="content"]', '[class*="article"]', '[class*="post"]',
                '[class*="main"]', '[id*="content"]', '[id*="article"]',
            ]
            
            for pattern in content_patterns:
                try:
                    elems = page.css(pattern)
                    for elem in elems[:5]:  # Check first 5 matches
                        try:
                            text = elem.get_all_text(separator=' ', strip=True,
                                                    ignore_tags=('script', 'style', 'noscript', 'nav', 'header', 'footer'),
                                                    valid_values=True)
                            if text:
                                text_str = str(text).strip()
                                if len(text_str) > 200:
                                    score = self._score_content_quality(text_str)
                                    candidates.append((text_str, score, 'pattern'))
                        except:
                            continue
                except:
                    continue
            
            # Strategy 3: Find largest text block (heuristic approach)
            try:
                # Get all divs and find the one with most text
                all_divs = page.css('div')
                for div in all_divs[:20]:  # Check first 20 divs
                    try:
                        text = div.get_all_text(separator=' ', strip=True,
                                               ignore_tags=('script', 'style', 'noscript', 'nav', 'header', 'footer', 'aside'),
                                               valid_values=True)
                        if text:
                            text_str = str(text).strip()
                            # Only consider substantial content
                            if len(text_str) > 300:
                                score = self._score_content_quality(text_str)
                                candidates.append((text_str, score, 'largest'))
                    except:
                        continue
            except:
                pass
            
            # Strategy 4: Body text as fallback
            try:
                body = page.css_first('body')
                if body:
                    text = body.get_all_text(separator=' ', strip=True,
                                            ignore_tags=('script', 'style', 'noscript', 'nav', 'header', 'footer', 'aside'),
                                            valid_values=True)
                    if text:
                        text_str = str(text).strip()
                        if len(text_str) > 200:
                            score = self._score_content_quality(text_str)
                            candidates.append((text_str, score, 'body'))
            except:
                pass
            
            # Strategy 5: Full page text (last resort)
            try:
                text = page.get_all_text(separator=' ', strip=True,
                                        ignore_tags=('script', 'style', 'noscript'),
                                        valid_values=True)
                if text:
                    text_str = str(text).strip()
                    if len(text_str) > 200:
                        score = self._score_content_quality(text_str)
                        candidates.append((text_str, score, 'full'))
            except:
                pass
            
            # Pick the best candidate based on score
            if candidates:
                # Sort by score (higher is better), then by length
                candidates.sort(key=lambda x: (x[1], len(x[0])), reverse=True)
                best_content = candidates[0][0]
                logger.debug(f"Selected content from strategy '{candidates[0][2]}' with score {candidates[0][1]}")
                return best_content
            
        except Exception as e:
            logger.debug(f"Intelligent extraction failed: {e}")
        
        return ""
    
    def _score_content_quality(self, content: str) -> float:
        """
        Score content quality based on heuristics
        Higher score = better content
        """
        if not content or len(content) < 50:
            return 0.0
        
        score = 0.0
        content_lower = content.lower()
        
        # Length scoring (longer is generally better, but not too long)
        length = len(content)
        if 200 <= length <= 50000:
            score += min(length / 1000, 10.0)  # Up to 10 points for length
        elif length > 50000:
            score += 5.0  # Very long might be noise
        
        # Penalize CSS/JS patterns
        special_chars = sum(1 for c in content if c in '{}(),;:[]=+-*/%<>!&|')
        special_ratio = special_chars / length if length > 0 else 0
        if special_ratio > 0.3:  # More than 30% special chars = likely CSS/JS
            score -= 20.0  # Heavy penalty
        
        # Reward meaningful content indicators
        meaningful_indicators = [
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has',
            'this', 'that', 'with', 'from', 'about', 'into', 'through'
        ]
        word_count = len(content.split())
        meaningful_word_ratio = sum(1 for word in content_lower.split() if word in meaningful_indicators) / word_count if word_count > 0 else 0
        if meaningful_word_ratio > 0.1:  # At least 10% common words
            score += 5.0
        
        # Reward paragraph structure (newlines indicate structure)
        newline_count = content.count('\n')
        if newline_count > 5:
            score += 2.0
        
        # Reward sentence structure (periods indicate sentences)
        sentence_count = content.count('.')
        if sentence_count > 5:
            score += 3.0
        
        # Penalize repetitive content
        words = content_lower.split()
        if len(words) > 0:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:  # Less than 30% unique words = repetitive
                score -= 5.0
        
        # Reward technical/content keywords
        tech_keywords = ['tutorial', 'guide', 'documentation', 'example', 'code',
                        'function', 'class', 'method', 'api', 'how', 'what', 'why',
                        'learn', 'understand', 'explain', 'introduction', 'overview']
        keyword_count = sum(1 for keyword in tech_keywords if keyword in content_lower)
        score += min(keyword_count * 0.5, 5.0)  # Up to 5 points
        
        return max(0.0, score)  # Ensure non-negative
    
    def _extract_from_scrapling_page(self, page, url: str) -> Dict:
        """Extract content from Scrapling Response/Selector using native API"""
        try:
            # Extract title using Scrapling's native API
            title = ""
            try:
                title = page.css_first('title::text')
                if title:
                    title = str(title).strip()
                if not title:
                    og_title = page.css_first('meta[property="og:title"]::attr(content)')
                    if og_title:
                        title = str(og_title).strip()
                if not title:
                    h1 = page.css_first('h1::text')
                    if h1:
                        title = str(h1).strip()
            except Exception as e:
                logger.debug(f"Title extraction failed: {e}")
            
            # Extract meta description
            meta_desc = ""
            try:
                meta = page.css_first('meta[name="description"]::attr(content)')
                if not meta:
                    meta = page.css_first('meta[property="og:description"]::attr(content)')
                if meta:
                    meta_desc = str(meta).strip()
            except Exception as e:
                logger.debug(f"Meta extraction failed: {e}")
            
            # Extract headings
            headings = []
            try:
                for tag in ['h1', 'h2', 'h3']:
                    heading_elems = page.css(f'{tag}::text')
                    for h in heading_elems[:10]:
                        heading_text = str(h).strip()
                        if heading_text and heading_text not in headings:
                            headings.append(heading_text)
            except Exception as e:
                logger.debug(f"Heading extraction failed: {e}")
            
            # Intelligent content extraction - try multiple strategies and pick the best
            content = self._intelligent_content_extraction(page, url)
            
            # Clean content
            content = self._clean_and_optimize_content(content)
            
            # GitHub-specific extraction - always try API for better content
            if 'github.com' in url:
                github_content = self._extract_github_content(url, page)
                if github_content and len(github_content) > len(content):
                    content = github_content
            
            # Try domain-specific extractors for better content
            if not content or len(content.strip()) < 50:
                try:
                    from scrapers.domain_specific_extractors import DomainSpecificExtractors
                    domain_content = DomainSpecificExtractors.extract_domain_specific_content(url)
                    if domain_content and len(domain_content) > len(content or ''):
                        content = domain_content
                except Exception as e:
                    logger.debug(f"Domain-specific extraction failed: {e}")
            
            # Fallback content generation
            if not content or len(content.strip()) < 50:
                content = self._generate_fallback_content(url, title)
            
            # Ensure we have meaningful content
            if not content or len(content.strip()) < 20:
                fallback = self._generate_basic_fallback(url)
                return {
                    'title': fallback['title'],
                    'content': fallback['content'],
                    'headings': fallback['headings'],
                    'meta_description': fallback['meta_description'],
                    'quality_score': fallback['quality_score']
                }

            return {
                'title': title or 'Untitled',
                'content': content,
                'headings': headings,
                'meta_description': meta_desc
            }
        except Exception as e:
            logger.error(f"Error in _extract_from_scrapling_page: {e}")
            return {
                'title': 'Untitled',
                'content': self._generate_fallback_content(url, ''),
                'headings': [],
                'meta_description': ''
            }
    
    def _extract_github_content(self, url: str, page=None) -> Optional[str]:
        """Extract content from GitHub repositories using API (most reliable method)"""
        content_parts = []
        
        try:
            import requests
            import base64
            from urllib.parse import urlparse
            parsed = urlparse(url)
            parts = [p for p in parsed.path.strip('/').split('/') if p]
            
            if len(parts) < 2:
                return None
            
            owner = parts[0]
            repo = parts[1]
            
            # Handle different GitHub URL types
            url_type = None
            file_path = None
            branch = 'main'  # Default branch
            
            if len(parts) >= 3:
                if parts[2] == 'tree':
                    url_type = 'tree'
                    branch = parts[3] if len(parts) > 3 else 'main'
                elif parts[2] == 'blob':
                    url_type = 'blob'
                    branch = parts[3] if len(parts) > 3 else 'main'
                    file_path = '/'.join(parts[4:]) if len(parts) > 4 else None
                elif parts[2] == 'commit':
                    url_type = 'commit'
                elif parts[2] == 'issues' or parts[2] == 'pull':
                    url_type = parts[2]
            
            # Get repository info from API
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Mozilla/5.0 (Fuze Bookmark Scraper)"
            }
            
            try:
                response = requests.get(api_url, timeout=15, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Add repository name and description
                    repo_name = data.get('full_name', f"{owner}/{repo}")
                    description = data.get('description', '')
                    if description:
                        content_parts.append(f"Repository: {repo_name}\nDescription: {description}")
                    else:
                        content_parts.append(f"Repository: {repo_name}")
                    
                    # Add topics/tags
                    topics = data.get('topics', [])
                    if topics:
                        content_parts.append(f"Topics: {', '.join(topics[:10])}")
                    
                    # Add language
                    language = data.get('language', '')
                    if language:
                        content_parts.append(f"Primary Language: {language}")
                    
                    # Add stars, forks, etc.
                    stars = data.get('stargazers_count', 0)
                    forks = data.get('forks_count', 0)
                    if stars > 0 or forks > 0:
                        content_parts.append(f"Stars: {stars}, Forks: {forks}")
                    
                    # Try to get README content from API (highest priority)
                    readme_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
                    try:
                        readme_response = requests.get(readme_url, timeout=15, headers=headers)
                        if readme_response.status_code == 200:
                            readme_data = readme_response.json()
                            readme_content = base64.b64decode(readme_data.get('content', '')).decode('utf-8', errors='ignore')
                            if readme_content and len(readme_content) > 50:
                                # Limit README to first 8000 chars (keep more content)
                                if len(readme_content) > 8000:
                                    readme_content = readme_content[:8000] + "\n\n... (truncated)"
                                content_parts.append(f"\nREADME:\n{readme_content}")
                        elif readme_response.status_code == 404:
                            # No README, try to get default branch content
                            logger.debug(f"No README found for {owner}/{repo}")
                    except Exception as e:
                        logger.debug(f"GitHub README API failed: {e}")
                    
                    # For specific files (blob URLs), try to get file content
                    if url_type == 'blob' and file_path:
                        try:
                            # Try to get file content from raw URL (simpler than API)
                            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
                            file_response = requests.get(raw_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                            if file_response.status_code == 200:
                                file_content = file_response.text
                                # Limit file content to 5000 chars
                                if len(file_content) > 5000:
                                    file_content = file_content[:5000] + "\n... (truncated)"
                                content_parts.append(f"\nFile Content ({file_path}):\n{file_content}")
                        except Exception as e:
                            logger.debug(f"Failed to get file content: {e}")
                    
                elif response.status_code == 404:
                    logger.debug(f"Repository {owner}/{repo} not found or private")
                else:
                    logger.debug(f"GitHub API returned status {response.status_code}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"GitHub API timeout for {url}")
            except requests.exceptions.RequestException as e:
                logger.debug(f"GitHub API request failed: {e}")
                
        except Exception as e:
            logger.debug(f"GitHub API extraction error: {e}")
        
        # Try to extract from page if available (fallback)
        if page and len(content_parts) == 0:
            try:
                # Try to get README content from page
                readme = page.css_first('.markdown-body')
                if readme:
                    content = readme.get_all_text(separator=' ', strip=True, ignore_tags=('script', 'style'), valid_values=True)
                    if content and len(str(content)) > 100:
                        content_parts.append(str(content))
            except Exception as e:
                logger.debug(f"GitHub page extraction failed: {e}")
        
        if content_parts:
            return '\n\n'.join(content_parts)
        
        return None
    
    def _generate_basic_fallback(self, url: str) -> Dict:
        """Generate basic fallback content when all scraping methods fail"""
        try:
            from urllib.parse import urlparse, unquote
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            path_parts = [p for p in parsed.path.strip('/').split('/') if p]

            # Create meaningful title
            if path_parts:
                title = f"{domain} - {' '.join(path_parts[:2])}"
            else:
                title = domain

            # Create meaningful content
            content_parts = [f"Content from {domain}"]
            if path_parts:
                meaningful_parts = [unquote(p).replace('-', ' ').replace('_', ' ')
                                  for p in path_parts if p.lower() not in {'www', 'index', 'home', 'page', 'post', 'article'}]
                if meaningful_parts:
                    content_parts.append('Topic: ' + ' '.join(meaningful_parts[:3]))

            content = '. '.join(content_parts)
            if len(content) < 100:
                content += f". URL: {url}"

            return {
                'title': title,
                'content': content,
                'headings': [],
                'meta_description': f"Content from {domain}",
                'quality_score': 3  # Low but not zero
            }
        except Exception as e:
            logger.debug(f"Basic fallback generation failed: {e}")
            return {
                'title': 'Web Content',
                'content': f'Content from {url}',
                'headings': [],
                'meta_description': 'Web content',
                'quality_score': 3
            }

    def _generate_fallback_content(self, url: str, title: str) -> str:
        """Generate fallback content from URL and title when extraction fails"""
        content_parts = []
        
        if title and title.strip():
            content_parts.append(title.strip())
        
        # Extract meaningful info from URL
        try:
            from urllib.parse import urlparse, unquote
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            path_parts = [p for p in parsed.path.strip('/').split('/') if p]
            
            # Add domain info
            if domain:
                content_parts.append(f"Content from {domain}")
            
            # Add meaningful path parts (skip common paths)
            skip_paths = {'www', 'index', 'home', 'page', 'post', 'article'}
            meaningful_parts = [unquote(p).replace('-', ' ').replace('_', ' ') 
                              for p in path_parts if p.lower() not in skip_paths]
            if meaningful_parts:
                content_parts.append(' '.join(meaningful_parts[:3]))  # Limit to 3 parts
        except:
            pass
        
        return ' '.join(content_parts) if content_parts else "Web content"
    
    def _check_browsers_installed(self) -> bool:
        """Check if browsers are installed for Scrapling - thread-safe"""
        if not SCRAPLING_AVAILABLE:
            return False
        
        # Cache the result to avoid repeated checks
        if self._browsers_installed is not None:
            return self._browsers_installed
        
        try:
            # Check for Camoufox first (used by StealthyFetcher)
            try:
                import camoufox
                from pathlib import Path
                # Check multiple possible locations
                possible_paths = [
                    Path.home() / "AppData" / "Local" / "camoufox",
                    Path.home() / ".local" / "share" / "camoufox",
                    Path.home() / ".camoufox",
                ]
                for path in possible_paths:
                    if path.exists() and (path / "version.json").exists():
                        self._browsers_installed = True
                        return True
            except Exception as e:
                logger.debug(f"Camoufox check failed: {e}")
            
            # Try to check if Playwright browsers exist (used by DynamicFetcher)
            # Run in a thread to avoid async conflicts
            try:
                def check_playwright():
                    try:
                        from playwright.sync_api import sync_playwright
                        with sync_playwright() as p:
                            browser_path = p.chromium.executable_path
                            return browser_path and os.path.exists(browser_path)
                    except:
                        return False
                
                # Check if we're in async context
                try:
                    asyncio.get_running_loop()
                    # In async context, run check in thread
                    result, _ = self._run_fetcher_in_thread(check_playwright, timeout=5)
                    if result:
                        self._browsers_installed = True
                        return True
                except RuntimeError:
                    # Not in async context, safe to run directly
                    if check_playwright():
                        self._browsers_installed = True
                        return True
            except Exception as e:
                logger.debug(f"Playwright check failed: {e}")
            
            self._browsers_installed = False
            return False
        except Exception as e:
            logger.debug(f"Browser check failed: {e}")
            self._browsers_installed = False
            return False
    
    def _safe_css(self, page, selector, adaptive=False, auto_save=False):
        """Safely call page.css with adaptive/auto_save, falling back if not supported"""
        # Don't use adaptive/auto_save if not enabled on the page/fetcher
        # This prevents warnings about adaptive not being enabled
        try:
            # Check if page has adaptive mode enabled by trying a simple adaptive call
            # If it fails with the warning, we know adaptive isn't enabled
            if adaptive or auto_save:
                # Try without adaptive first to avoid warnings
                return page.css(selector)
            else:
                return page.css(selector)
        except Exception as e:
            logger.debug(f"CSS selector failed: {e}")
            return []
    
    def _safe_css_first(self, page, selector, adaptive=False):
        """Safely call page.css_first with adaptive, falling back if not supported"""
        # Don't use adaptive if not enabled to avoid warnings
        try:
            return page.css_first(selector)
        except Exception as e:
            logger.debug(f"CSS first selector failed: {e}")
            return None
    
    def scrape_url_enhanced(self, url: str) -> Dict:
        """
        Enhanced URL scraping with Scrapling for problematic sites
        """
        try:
            domain = urlparse(url).netloc.lower()
            
            # Check if auth required
            if any(auth_domain in domain for auth_domain in self.auth_required_domains):
                return self._get_auth_required_content(url, domain)
            
            # For LinkedIn URLs, ALWAYS use enhanced LinkedIn scraper first (best method)
            if 'linkedin.com' in domain:
                try:
                    from scrapers.easy_linkedin_scraper import EasyLinkedInScraper
                    linkedin_scraper = EasyLinkedInScraper()
                    linkedin_result = linkedin_scraper.scrape_post(url)
                    
                    if linkedin_result and linkedin_result.get('success') and len(linkedin_result.get('content', '')) > 100:
                        # Convert LinkedIn scraper format to our standard format
                        result = {
                            'title': linkedin_result.get('title', 'LinkedIn Post'),
                            'content': linkedin_result.get('content', ''),
                            'headings': [],
                            'meta_description': linkedin_result.get('meta_description', ''),
                            'quality_score': linkedin_result.get('quality_score', 7)
                        }
                        logger.info(f" LinkedIn scraper extraction successful: {len(result['content'])} chars, quality={result['quality_score']}")
                        return result
                    else:
                        logger.warning(f"LinkedIn scraper returned low quality result, trying fallback")
                except Exception as linkedin_error:
                    logger.warning(f"LinkedIn scraper failed: {linkedin_error}, trying fallback")
            
            # For GitHub URLs, ALWAYS try API first (most reliable method)
            # This ensures we get README, description, topics even if Scrapling fails
            github_api_result = None
            if 'github.com' in url:
                github_content = self._extract_github_content(url, page=None)
                if github_content and len(github_content) > 100:
                    # Got good content from GitHub API
                    parsed = urlparse(url)
                    parts = [p for p in parsed.path.strip('/').split('/') if p]
                    title = f"{parts[0]}/{parts[1]}" if len(parts) >= 2 else "GitHub Repository"
                    
                    github_api_result = {
                        'title': title,
                        'content': github_content,
                        'headings': [],
                        'meta_description': github_content[:200] if len(github_content) > 200 else github_content,
                        'quality_score': 8  # High quality for GitHub API content
                    }
                    # For GitHub, prefer API result - return immediately
                    logger.info(f" GitHub API extraction successful: {len(github_content)} chars")
                    return github_api_result
                # If GitHub API failed, continue with Scrapling (might get better content)
            
            # Check if Scrapling should be used
            if SCRAPLING_AVAILABLE:
                strategy = self._get_scrapling_strategy(domain)
                if strategy:
                    logger.info(f"Using Scrapling ({strategy}) for {url}")
                    try:
                        result = self._scrape_with_scrapling(url, strategy)
                        if result and result.get('quality_score', 0) >= 5:
                            logger.info(f" Scrapling extraction successful: quality={result.get('quality_score')}, content_length={len(result.get('content', ''))}")
                            return result
                        elif result:
                            logger.warning(f"Scrapling extraction had low quality ({result.get('quality_score')}), trying fallback scraper")
                        else:
                            logger.warning(f"Scrapling extraction returned None, trying fallback scraper")
                    except Exception as scrapling_error:
                        logger.warning(f"Scrapling extraction failed: {scrapling_error}, trying fallback scraper")
                else:
                    # Try Scrapling standard Fetcher for unknown sites as first attempt
                    logger.debug(f"No specific Scrapling strategy for {domain}, trying standard Fetcher first")
                    try:
                        if SCRAPLING_AVAILABLE:
                            result = self._scrape_standard(url)
                            if result and result.get('quality_score', 0) >= 5:
                                return result
                    except:
                        pass
            
            # Fallback to existing scraper
            logger.info(f"Using fallback scraper for {url}")
            try:
                result = self.fallback_scraper.scrape_url_enhanced(url)
                if result and result.get('content') and len(result.get('content', '')) > 50:
                    return result
                else:
                    logger.warning(f"Fallback scraper returned poor quality result, using basic fallback")
            except Exception as fallback_error:
                logger.warning(f"Fallback scraper failed: {fallback_error}")

            # Try domain-specific extractors before ultimate fallback
            try:
                from scrapers.domain_specific_extractors import DomainSpecificExtractors
                domain_content = DomainSpecificExtractors.extract_domain_specific_content(url)
                if domain_content:
                    parsed = urlparse(url)
                    domain = parsed.netloc.replace('www.', '')
                    return {
                        'title': f"Content from {domain}",
                        'content': domain_content,
                        'headings': [],
                        'meta_description': domain_content[:200] if len(domain_content) > 200 else domain_content,
                        'quality_score': 4  # Better than basic fallback
                    }
            except Exception as e:
                logger.debug(f"Domain-specific extraction failed: {e}")
            
            # Ultimate fallback - generate basic content from URL
            return self._generate_basic_fallback(url)
            
        except Exception as e:
            logger.error(f"Error in ScraplingEnhancedScraper for {url}: {e}")
            # Final fallback
            try:
                return self.fallback_scraper.scrape_url_enhanced(url)
            except Exception as final_error:
                logger.error(f"Final fallback also failed: {final_error}")
                return self._generate_basic_fallback(url)
    
    def _get_scrapling_strategy(self, domain: str) -> Optional[str]:
        """Determine which Scrapling fetcher to use"""
        for scrapling_domain, strategy in self.scrapling_domains.items():
            if scrapling_domain in domain:
                return strategy
        return None
    
    def _scrape_with_scrapling(self, url: str, strategy: str) -> Optional[Dict]:
        """Scrape using Scrapling library"""
        try:
            if strategy == 'stealthy':
                return self._scrape_stealthy(url)
            elif strategy == 'dynamic':
                return self._scrape_dynamic(url)
            else:
                return self._scrape_standard(url)
        except Exception as e:
            logger.error(f"Scrapling scraping failed for {url}: {e}")
            return None
    
    def _run_fetcher_in_thread(self, fetcher_func, timeout=90):
        """Run a fetcher function in a separate thread to avoid async conflicts"""
        result = None
        exception = None
        thread_done = threading.Event()
        
        def run_in_thread():
            nonlocal result, exception
            try:
                result = fetcher_func()
            except Exception as e:
                exception = e
            finally:
                thread_done.set()
        
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        
        # Wait for completion or timeout
        if thread_done.wait(timeout=timeout):
            thread.join(timeout=1)  # Give thread a moment to finish
        else:
            logger.warning(f"Fetcher timeout after {timeout}s")
            return None, TimeoutError("Fetcher operation timed out")
        
        return result, exception
    
    def _scrape_stealthy(self, url: str) -> Dict:
        """Use StealthyFetcher for sites with anti-bot protection"""
        if not SCRAPLING_AVAILABLE or StealthyFetcher is None:
            logger.warning("StealthyFetcher not available, cannot use stealthy scraping")
            return None
        
        # Check if browsers are installed before attempting
        if not self._check_browsers_installed():
            logger.debug(f"Browsers not installed, skipping StealthyFetcher for {url}")
            return None
        
        try:
            # Define the fetcher function
            def fetch_page():
                return StealthyFetcher.fetch(
                    url,
                    headless=True,
                    network_idle=True,
                    solve_cloudflare=True,  # Auto-solve Cloudflare challenges
                    timeout=90000,  # 90 seconds for Cloudflare solving
                    wait=2000  # Wait 2 seconds after page loads
                )
            
            # Check if we're in an async event loop - if so, run in a new thread
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, need to run in a thread
                logger.debug(f"Running StealthyFetcher in thread to avoid async conflict")
                page, exception = self._run_fetcher_in_thread(fetch_page, timeout=120)  # 120s for Cloudflare
                
                if exception:
                    if isinstance(exception, TimeoutError):
                        logger.warning(f"StealthyFetcher timeout for {url}")
                        return None
                    # Check if it's a browser installation error
                    error_str = str(exception).lower()
                    if 'executable doesn\'t exist' in error_str or 'playwright' in error_str or 'camoufox' in error_str or 'browser' in error_str:
                        logger.debug(f"Browsers not installed. Run: camoufox fetch or scrapling install")
                        self._browsers_installed = False  # Update cache
                        return None
                    # Check for Cloudflare-specific errors
                    if 'cloudflare' in error_str or 'challenge' in error_str or 'turnstile' in error_str:
                        logger.warning(f"Cloudflare challenge failed for {url}: {exception}")
                        return None
                    # Re-raise other exceptions
                    raise exception
                
            except RuntimeError:
                # No event loop running, safe to use sync API directly
                try:
                    page = fetch_page()
                except Exception as e:
                    # Check if it's a browser installation error
                    error_str = str(e).lower()
                    if 'executable doesn\'t exist' in error_str or 'playwright' in error_str or 'camoufox' in error_str or 'browser' in error_str:
                        logger.debug(f"Browsers not installed. Run: scrapling install or camoufox fetch")
                        self._browsers_installed = False  # Update cache
                        return None
                    # Check for Cloudflare-specific errors
                    if 'cloudflare' in error_str or 'challenge' in error_str:
                        logger.warning(f"Cloudflare challenge failed for {url}: {e}")
                        return None
                    raise
            
            if not page:
                logger.warning(f"StealthyFetcher returned None for {url}")
                return None
            
            # Use Scrapling's native Selector API directly (Response IS a Selector!)
            extracted = self._extract_from_scrapling_page(page, url)
            title = extracted['title']
            content = extracted['content']
            headings = extracted['headings']
            meta_desc = extracted['meta_description']
            
            # Limit to 100K chars but keep best content
            if len(content) > 100000:
                content = content[:80000] + " ... " + content[-20000:]
            
            # Compute quality score
            quality_score = self._compute_quality_score(content, title, meta_desc)
            
            # Log extraction quality
            logger.info(f"Scrapling (stealthy) extraction: {len(content)} chars, quality: {quality_score}, title: {title[:50]}")
            
            return {
                'title': title or 'Untitled',
                'content': content,
                'headings': headings,
                'meta_description': meta_desc,
                'quality_score': quality_score
            }
            
        except Exception as e:
            logger.error(f"StealthyFetcher error for {url}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def _scrape_dynamic(self, url: str) -> Dict:
        """Use DynamicFetcher for JavaScript-heavy sites"""
        if not SCRAPLING_AVAILABLE or DynamicFetcher is None:
            logger.warning("DynamicFetcher not available, cannot use dynamic scraping")
            return None
        
        # Check if browsers are installed before attempting
        if not self._check_browsers_installed():
            logger.debug(f"Browsers not installed, skipping DynamicFetcher for {url}")
            return None
        
        try:
            # Define the fetcher function
            def fetch_page():
                return DynamicFetcher.fetch(
                    url,
                    headless=True,
                    network_idle=True,
                    disable_resources=False,  # Load all resources for JS-heavy sites
                    timeout=60000,  # 60 seconds timeout
                    wait=2000  # Wait 2 seconds after page loads
                )
            
            # Check if we're in an async event loop - if so, run in a new thread
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, need to run in a thread
                logger.debug(f"Running DynamicFetcher in thread to avoid async conflict")
                page, exception = self._run_fetcher_in_thread(fetch_page, timeout=90)
                
                if exception:
                    if isinstance(exception, TimeoutError):
                        logger.warning(f"DynamicFetcher timeout for {url}")
                        return None
                    # Check if it's a browser installation error
                    error_str = str(exception).lower()
                    if 'executable doesn\'t exist' in error_str or 'playwright' in error_str or 'browser' in error_str:
                        logger.debug(f"Browsers not installed. Run: scrapling install or camoufox fetch")
                        self._browsers_installed = False  # Update cache
                        return None
                    # Re-raise other exceptions
                    raise exception
                
            except RuntimeError:
                # No event loop running, safe to use sync API directly
                try:
                    page = fetch_page()
                except Exception as e:
                    # Check if it's a browser installation error
                    error_str = str(e).lower()
                    if 'executable doesn\'t exist' in error_str or 'playwright' in error_str or 'browser' in error_str:
                        logger.warning(f"Playwright browsers not installed. Run: playwright install")
                        self._browsers_installed = False  # Update cache
                        return None
                    # Check for Playwright-specific errors
                    if 'playwright' in error_str and ('timeout' in error_str or 'navigation' in error_str or 'target closed' in error_str):
                        logger.warning(f"Playwright navigation issue for {url}: {e}")
                        return None
                    raise
            
            if not page:
                logger.warning(f"DynamicFetcher returned None for {url}")
                return None
            
            # Use Scrapling's native Selector API
            extracted = self._extract_from_scrapling_page(page, url)
            title = extracted['title']
            content = extracted['content']
            headings = extracted['headings']
            meta_desc = extracted['meta_description']
            
            # Limit to 100K chars
            if len(content) > 100000:
                content = content[:80000] + " ... " + content[-20000:]
            
            quality_score = self._compute_quality_score(content, title, meta_desc)
            
            logger.info(f"Scrapling (dynamic) extraction: {len(content)} chars, quality: {quality_score}, title: {title[:50]}")
            
            return {
                'title': title or 'Untitled',
                'content': content,
                'headings': headings,
                'meta_description': meta_desc,
                'quality_score': quality_score
            }
            
        except Exception as e:
            logger.error(f"DynamicFetcher error for {url}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def _scrape_standard(self, url: str) -> Dict:
        """Use standard Fetcher for simple sites"""
        if not SCRAPLING_AVAILABLE or Fetcher is None:
            logger.warning("Fetcher not available, cannot use standard Scrapling fetcher")
            return None
        
        try:
            # Use stealthy headers for better success rate
            page = Fetcher.get(url, impersonate='chrome', stealthy_headers=True)
            
            if not page:
                return None
            
            # Use Scrapling's native Selector API
            extracted = self._extract_from_scrapling_page(page, url)
            title = extracted['title']
            content = extracted['content']
            headings = extracted['headings']
            meta_desc = extracted['meta_description']
            
            # Limit to 100K chars
            if len(content) > 100000:
                content = content[:80000] + " ... " + content[-20000:]
            
            quality_score = self._compute_quality_score(content, title, meta_desc)
            
            return {
                'title': title or 'Untitled',
                'content': content,
                'headings': headings,
                'meta_description': meta_desc,
                'quality_score': quality_score
            }
            
        except Exception as e:
            logger.error(f"Standard Fetcher error for {url}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def _clean_and_optimize_content(self, content: str) -> str:
        """Clean and optimize content for better quality"""
        if not content:
            return ""
        
        import re
        
        # Remove CSS styles (e.g., .class-name { property: value; })
        # Match CSS selectors and rules
        content = re.sub(r'\.[a-zA-Z0-9_-]+\s*\{[^}]*\}', '', content)
        content = re.sub(r'#[a-zA-Z0-9_-]+\s*\{[^}]*\}', '', content)
        content = re.sub(r'[a-zA-Z0-9_-]+\s*\{[^}]*\}', '', content)
        content = re.sub(r'@media[^{]*\{[^}]*\}', '', content, flags=re.DOTALL)
        
        # Remove inline styles (style="...")
        content = re.sub(r'style\s*=\s*["\'][^"\']*["\']', '', content, flags=re.IGNORECASE)
        
        # Remove JSON-like configuration objects (common in modern web apps)
        # Match { "key": "value", ... } patterns that look like config
        content = re.sub(r'\{\s*"[^"]+":\s*"[^"]*",?\s*\}', '', content)
        content = re.sub(r'\{\s*"[^"]+":\s*\[[^\]]*\],?\s*\}', '', content)
        
        # Remove CSS property patterns (property: value;)
        content = re.sub(r'[a-zA-Z-]+\s*:\s*[^;]+;', '', content)
        
        # Remove HTML entity codes and encoded content
        content = re.sub(r'&[a-zA-Z0-9#]+;', ' ', content)
        
        # Remove class names and IDs that look like CSS (e.g., ._23tra1HsiiP6cT-Cka-ycB)
        content = re.sub(r'\.[a-zA-Z0-9_-]{20,}', '', content)  # Long class names
        content = re.sub(r'#[a-zA-Z0-9_-]{20,}', '', content)  # Long IDs
        
        # Remove CSS selectors (e.g., div[dir="rtl"])
        content = re.sub(r'[a-zA-Z]+\[[^\]]+\]', '', content)
        
        # Remove color codes and hex colors
        content = re.sub(r'#[0-9a-fA-F]{3,6}\b', '', content)
        content = re.sub(r'rgba?\([^)]+\)', '', content)
        
        # Remove CSS units and measurements
        content = re.sub(r'\d+px\b', '', content)
        content = re.sub(r'\d+%', '', content)
        content = re.sub(r'\d+em\b', '', content)
        content = re.sub(r'\d+rem\b', '', content)
        
        # Remove CSS media queries
        content = re.sub(r'@media[^\{]*', '', content, flags=re.IGNORECASE)
        
        # Remove common CSS keywords
        css_keywords = [
            'position', 'display', 'top', 'left', 'right', 'bottom', 'width', 'height',
            'margin', 'padding', 'border', 'background', 'color', 'font', 'z-index',
            'transition', 'transform', 'opacity', 'box-shadow', 'cursor', 'outline',
            'float', 'clear', 'overflow', 'text-align', 'vertical-align', 'line-height',
            'font-size', 'font-weight', 'font-family', 'text-decoration', 'box-sizing',
            'flex', 'grid', 'align', 'justify', 'gap', 'min-width', 'max-width',
            'min-height', 'max-height', 'calc', '!important'
        ]
        for keyword in css_keywords:
            content = re.sub(rf'\b{re.escape(keyword)}\s*:', '', content, flags=re.IGNORECASE)
        
        # Remove JavaScript-like patterns
        content = re.sub(r'function\s*\([^)]*\)\s*\{[^}]*\}', '', content)
        content = re.sub(r'const\s+\w+\s*=\s*\{[^}]*\}', '', content)
        content = re.sub(r'let\s+\w+\s*=\s*\{[^}]*\}', '', content)
        content = re.sub(r'var\s+\w+\s*=\s*\{[^}]*\}', '', content)
        
        # Remove JSON-like feature flags arrays
        content = re.sub(r'"featureFlags":\s*\[[^\]]*\]', '', content, flags=re.IGNORECASE)
        
        # Remove URLs in content (but keep text)
        content = re.sub(r'https?://[^\s]+', '', content)
        
        # Remove email-like patterns that are actually CSS/JS
        content = re.sub(r'[a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]{2,}', '', content)
        
        # Remove extra whitespace but preserve structure
        content = re.sub(r' +', ' ', content)
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        content = content.strip()
        
        # Remove lines that are mostly CSS/JS patterns (more than 50% special chars)
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Skip lines that are mostly CSS/JS
            special_chars = sum(1 for c in line_stripped if c in '{}(),;:[]=+-*/%<>!&|')
            if len(line_stripped) > 0 and special_chars / len(line_stripped) > 0.5:
                continue
            
            # Skip lines that look like CSS selectors
            if re.match(r'^[.#]?[a-zA-Z0-9_-]+\s*\{', line_stripped):
                continue
            
            # Skip lines that are just CSS properties
            if re.match(r'^\s*[a-zA-Z-]+\s*:\s*[^;]+;\s*$', line_stripped):
                continue
            
            cleaned_lines.append(line)
        
        content = '\n'.join(cleaned_lines)
        
        # Remove common boilerplate that doesn't add value
        boilerplate_patterns = [
            r'cookie\s+policy.*?\.',
            r'privacy\s+policy.*?\.',
            r'terms\s+of\s+service.*?\.',
            r'sign\s+in\s+to\s+continue.*?\.',
            r'please\s+enable\s+javascript.*?\.',
            r'javascript\s+required.*?\.',
            r'skip\s+to\s+content',
            r'navigation\s+menu',
        ]
        
        for pattern in boilerplate_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # Final cleanup
        content = re.sub(r' +', ' ', content)
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        content = content.strip()
        
        return content
    
    def _compute_quality_score(self, content: str, title: str, meta_description: str) -> int:
        """Compute quality score for scraped content - enhanced version"""
        score = 10
        
        # Content length scoring (more nuanced)
        content_length = len(content)
        if content_length < 50:
            score -= 6  # Very poor
        elif content_length < 100:
            score -= 5
        elif content_length < 200:
            score -= 3
        elif content_length < 500:
            score -= 1
        elif content_length > 1000:
            score += 1
        elif content_length > 5000:
            score += 2  # Very comprehensive
        
        # Title presence and quality
        if title and len(title) > 10:
            score += 1
            # Bonus for descriptive titles
            if len(title) > 30 and any(word in title.lower() for word in ['guide', 'tutorial', 'how', 'learn']):
                score += 1
        
        # Meta description presence
        if meta_description and len(meta_description) > 20:
            score += 1
        
        # Content quality indicators (check for meaningful content)
        content_lower = content.lower()
        
        # Technical content indicators
        tech_keywords = [
            'tutorial', 'api', 'how to', 'guide', 'documentation', 'example', 
            'code', 'javascript', 'python', 'react', 'problem', 'solution', 
            'algorithm', 'function', 'class', 'method', 'variable', 'implementation',
            'explanation', 'concept', 'learn', 'practice', 'exercise'
        ]
        keyword_count = sum(1 for keyword in tech_keywords if keyword in content_lower)
        if keyword_count >= 3:
            score += 2  # Rich technical content
        elif keyword_count >= 1:
            score += 1
        
        # Check for code blocks (indicates technical content)
        if '```' in content or '<code>' in content or 'function' in content_lower:
            score += 1
        
        # Check for structured content (headings, lists)
        if any(marker in content for marker in ['#', '##', '###', '- ', '* ', '1. ']):
            score += 1
        
        # Penalize if content is mostly CSS/JS (high special char ratio)
        if content_length > 0:
            special_chars = sum(1 for c in content if c in '{}(),;:[]=+-*/%<>!&|')
            special_char_ratio = special_chars / content_length
            if special_char_ratio > 0.3:  # More than 30% special chars = likely CSS/JS
                score -= 5  # Heavy penalty for CSS/JS content
                logger.debug(f"Content appears to be CSS/JS (special char ratio: {special_char_ratio:.2f})")
        
        # Penalize if content looks like error message
        error_indicators = ['unable to extract', 'extraction failed', 'error', 'not found', 'access denied']
        if any(indicator in content_lower for indicator in error_indicators):
            score -= 5
        
        # Clamp score
        score = max(1, min(10, score))
        return score
    
    def _get_auth_required_content(self, url: str, domain: str) -> Dict:
        """Return content for URLs that require authentication"""
        return {
            'title': f'Content from {domain}',
            'content': f'This URL requires authentication to access. Content cannot be extracted without login credentials.',
            'headings': [],
            'meta_description': f'Content from {domain} - authentication required',
            'quality_score': 3
        }

# Global instance
scrapling_enhanced_scraper = ScraplingEnhancedScraper()

def scrape_url_enhanced(url: str) -> Dict:
    """
    Enhanced URL scraping function with Scrapling support
    """
    return scrapling_enhanced_scraper.scrape_url_enhanced(url)

