import requests
from bs4 import BeautifulSoup
from readability import Document

# Add Playwright imports
from playwright.sync_api import sync_playwright
import time

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
        # If main content is too short, try Playwright
        if use_playwright_fallback and (len(result['content']) < 200):
            print(f"Static scrape too short ({len(result['content'])} chars), trying Playwright for {url}")
            html = fetch_with_playwright(url)
            if html:
                result = parse_html(html)
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        result = {'title': '', 'content': '', 'headings': [], 'meta_description': ''}
    return result 