import requests
from bs4 import BeautifulSoup
from readability import Document
import re
from collections import Counter
from playwright.sync_api import sync_playwright
import time
from redis_utils import redis_cache

def fetch_with_playwright(url, timeout=15):
    """
    Fetch page content using Playwright (headless browser, JS-rendered).
    Returns the HTML content as a string.
    """
    html = ''
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=timeout * 1000)
            # Wait for network to be idle or a short delay
            page.wait_for_load_state('networkidle', timeout=timeout * 1000)
            time.sleep(1)  # Give JS a moment to render
            html = page.content()
            browser.close()
    except Exception as e:
        print(f"Playwright error for {url}: {e}")
    return html

def scrape_url(url, use_playwright_fallback=True):
    """
    Scrape a URL and extract title, main content, headings, and meta description.
    Tries static scraping first, then Playwright if content is too short or empty.
    Returns a dict with keys: title, content, headings, meta_description
    """
    # Check Redis cache first
    cached_content = redis_cache.get_cached_scraped_content(url)
    if cached_content is not None:
        print(f"📦 Using cached content for {url}")
        return cached_content
    
    def parse_html(html):
        result = {
            'title': '',
            'content': '',
            'headings': [],
            'meta_description': ''
        }
        soup = BeautifulSoup(html, "html.parser")
        # Title
        title_tag = soup.find('title')
        result['title'] = title_tag.get_text(strip=True) if title_tag else ''
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc:
            meta_desc = soup.find('meta', attrs={'property': 'og:description'})
        result['meta_description'] = meta_desc['content'].strip() if meta_desc and meta_desc.get('content') else ''
        # Headings (h1, h2, h3)
        headings = []
        for tag in ['h1', 'h2', 'h3']:
            headings.extend([h.get_text(strip=True) for h in soup.find_all(tag)])
        result['headings'] = headings
        # Main content using readability if possible
        try:
            doc = Document(html)
            summary_html = doc.summary()
            content_soup = BeautifulSoup(summary_html, "html.parser")
            main_text = content_soup.get_text(separator=" ", strip=True)
        except Exception:
            # Fallback: remove script/style and get all text
            for script in soup(["script", "style"]):
                script.decompose()
            main_text = soup.get_text(separator=" ", strip=True)
        result['content'] = main_text[:5000]  # Limit to 5000 chars
        return result

    # 1. Try static scraping
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; FuzeBot/1.0)"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        html = response.text
        result = parse_html(html)
        result['quality_score'] = compute_content_quality(result['content'], result['title'], result['meta_description'], url, html)
        # If main content is too short, try Playwright
        if use_playwright_fallback and (len(result['content']) < 200):
            print(f"Static scrape too short ({len(result['content'])} chars), trying Playwright for {url}")
            html = fetch_with_playwright(url)
            if html:
                result = parse_html(html)
                result['quality_score'] = compute_content_quality(result['content'], result['title'], result['meta_description'], url, html)
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        result = {'title': '', 'content': '', 'headings': [], 'meta_description': ''}
    
    # Cache the result
    redis_cache.cache_scraped_content(url, result)
    
    return result

def compute_content_quality(content, title, meta_description, url, html=None):
    score = 10
    lowered = (title or '').lower() + ' ' + (meta_description or '').lower() + ' ' + (content or '').lower()
    url_lower = (url or '').lower()
    login_keywords = ['login', 'sign in', 'signin', 'signup', 'register', 'log in', 'logon', 'log on', 'homepage', 'home page', 'access denied', 'error', '404', 'welcome']
    tech_keywords = ['tutorial', 'api', 'how to', 'guide', 'case study', 'reference', 'documentation', 'example', 'walkthrough', 'deep dive', 'introduction', 'overview']
    # 1. Keyword filtering
    for kw in login_keywords:
        if kw in lowered or kw in url_lower:
            score -= 5
    for kw in tech_keywords:
        if kw in lowered:
            score += 1
    # 2. Content length
    if len(content or '') < 500:
        score -= 3
    if len(content or '') < 200:
        score -= 2
    # 3. Structural analysis (prefer article/main/post-content)
    if html:
        soup = BeautifulSoup(html, 'html.parser')
        if soup.find('article') or soup.find(class_='post-content') or soup.find('main'):
            score += 2
        # Penalize if most text is in nav/footer/form
        nav_text = ' '.join([n.get_text() for n in soup.find_all(['nav', 'footer', 'form'])])
        if len(nav_text) > 0.5 * len(content):
            score -= 2
        # Content density: text vs. tags
        num_tags = len(soup.find_all())
        if num_tags > 0 and len(content) / num_tags < 2:
            score -= 2
        # Link density
        num_links = len(soup.find_all('a'))
        if num_links > 0 and len(content) / num_links < 5:
            score -= 1
        # Media/code presence
        if soup.find('code') or soup.find('pre'):
            score += 1
        if soup.find('img') or soup.find('svg'):
            score += 1
    # 4. Readability (Flesch-Kincaid, simple version)
    def flesch_kincaid(text):
        words = re.findall(r'\w+', text)
        sentences = re.split(r'[.!?]', text)
        syllables = sum(len(re.findall(r'[aeiouy]+', w.lower())) for w in words)
        if len(words) == 0 or len(sentences) == 0:
            return 0
        return 206.835 - 1.015 * (len(words) / max(1, len(sentences))) - 84.6 * (syllables / max(1, len(words)))
    fk_score = flesch_kincaid(content)
    if fk_score < 30:
        score -= 1
    elif fk_score > 60:
        score += 1
    # 5. Uniqueness
    if title and content and title.strip().lower() in content.strip().lower():
        if len(content.strip()) / max(1, len(title.strip())) < 10:
            score -= 2
    # Clamp score
    score = max(1, min(10, score))
    return score 