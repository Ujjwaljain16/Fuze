"""
Source adapters: for sites with an official public API, read the content through it instead of
parsing the page. The result is the real text (a repo's README, a paper's abstract, a question
and its answers) without layout noise, and it uses documented, rate-limited access.

"Official API" here means a documented public endpoint that needs no key: REST APIs, oEmbed
(YouTube, Reddit, X), RSS (Medium) and Reddit's .json listings. No scraping tricks: an adapter
that reads a page at all (YouTube's description) checks robots.txt first. The one exception is
LinkedIn, below: a documented, switchable decision, not an API.

Each adapter returns SourceContent or None (unknown URL shape / API error); the caller then
falls back to the normal HTML pipeline.
"""

import json
import os
import re
import threading
import time
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

import requests

from core.logging_config import get_logger
from scrapers.safe_http import SafeResponse, safe_get

logger = get_logger(__name__)

USER_AGENT = "FuzeBot/1.0 (+https://itsfuze.vercel.app; bookmark content extraction on user request)"
TIMEOUT = 10
MAX_ANSWERS = 3


@dataclass
class SourceContent:
    source: str  # short name, stored as strategy "API:<source>"
    title: str
    text: str  # markdown / plain text body
    author: Optional[str] = None
    published_at: Optional[str] = None
    description: Optional[str] = None
    canonical_url: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    raw: Dict = field(default_factory=dict)
    # The item points at an external page that is the real content (e.g. an HN link post).
    follow_url: Optional[str] = None


def _get(url: str, params: Optional[Dict] = None, accept: Optional[str] = None) -> SafeResponse:
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    resp = safe_get(url, params=params, headers=headers, timeout=TIMEOUT, max_bytes=5 * 1024 * 1024)
    resp.raise_for_status()
    return resp


def _html_to_text(html: str) -> str:
    if not html:
        return ""
    try:
        import trafilatura
        text = trafilatura.extract(f"<html><body><article>{html}</article></body></html>",
                                   output_format="markdown", include_tables=True, include_comments=False)
        if text:
            return text.strip()
    except Exception:
        pass
    from bs4 import BeautifulSoup
    return BeautifulSoup(html, "html.parser").get_text("\n", strip=True)


# --- GitHub ------------------------------------------------------------------------------

_GH_RESERVED = {"settings", "orgs", "topics", "marketplace", "features", "about", "login", "search", "explore"}


def github(url: str) -> Optional[SourceContent]:
    parts = [p for p in urlparse(url).path.split("/") if p]
    if len(parts) < 2 or parts[0] in _GH_RESERVED:
        return None
    owner, repo = parts[0], parts[1].removesuffix(".git")
    api = f"https://api.github.com/repos/{owner}/{repo}"
    if len(parts) >= 4 and parts[2] in ("issues", "pull") and parts[3].isdigit():
        issue = _get(f"{api}/issues/{parts[3]}", accept="application/vnd.github+json").json()
        body = issue.get("body") or ""
        return SourceContent("github", issue.get("title") or f"{owner}/{repo}#{parts[3]}", body,
                             author=(issue.get("user") or {}).get("login"), published_at=issue.get("created_at"),
                             canonical_url=issue.get("html_url"), keywords=[l["name"] for l in issue.get("labels", [])],
                             raw={"type": "issue", "repo": f"{owner}/{repo}", "state": issue.get("state")})
    meta = _get(api, accept="application/vnd.github+json").json()
    try:
        readme = _get(f"{api}/readme", accept="application/vnd.github.raw").text
    except requests.RequestException:
        readme = ""
    description = meta.get("description") or ""
    text = "\n\n".join(p for p in (description, readme) if p)
    return SourceContent("github", meta.get("full_name") or f"{owner}/{repo}", text,
                         author=(meta.get("owner") or {}).get("login"), published_at=meta.get("created_at"),
                         description=description, canonical_url=meta.get("html_url"), keywords=meta.get("topics") or [],
                         raw={"type": "repo", "language": meta.get("language"), "stars": meta.get("stargazers_count")})


# --- arXiv -------------------------------------------------------------------------------

_ARXIV_ID = re.compile(r"/(?:abs|pdf|html)/([^/?#]+?)(?:v\d+)?(?:\.pdf)?$")
_ATOM = {"a": "http://www.w3.org/2005/Atom"}


def arxiv(url: str) -> Optional[SourceContent]:
    m = _ARXIV_ID.search(urlparse(url).path)
    if not m:
        return None
    feed = ET.fromstring(_get("https://export.arxiv.org/api/query", params={"id_list": m.group(1)}).content)
    entry = feed.find("a:entry", _ATOM)
    if entry is None or entry.find("a:title", _ATOM) is None:
        return None
    title = " ".join(entry.findtext("a:title", "", _ATOM).split())
    abstract = " ".join(entry.findtext("a:summary", "", _ATOM).split())
    authors = [a.findtext("a:name", "", _ATOM) for a in entry.findall("a:author", _ATOM)]
    return SourceContent("arxiv", title, abstract, author=", ".join(authors[:10]) or None,
                         published_at=entry.findtext("a:published", None, _ATOM), description=abstract[:300],
                         canonical_url=f"https://arxiv.org/abs/{m.group(1)}", raw={"arxiv_id": m.group(1)})


# --- Wikipedia ---------------------------------------------------------------------------

def wikipedia(url: str) -> Optional[SourceContent]:
    parsed = urlparse(url)
    if not parsed.path.startswith("/wiki/"):
        return None
    title = unquote(parsed.path[len("/wiki/"):])
    if not title or ":" in title:  # special/talk/file pages
        return None
    data = _get(f"{parsed.scheme}://{parsed.netloc}/w/api.php", params={
        "action": "query", "prop": "extracts", "explaintext": 1, "redirects": 1,
        "titles": title, "format": "json", "formatversion": 2,
    }).json()
    pages = (data.get("query") or {}).get("pages") or []
    if not pages or pages[0].get("missing") or not pages[0].get("extract"):
        return None
    page = pages[0]
    return SourceContent("wikipedia", page["title"], page["extract"],
                         canonical_url=f"{parsed.scheme}://{parsed.netloc}/wiki/{page['title'].replace(' ', '_')}",
                         raw={"pageid": page.get("pageid")})


# --- Stack Exchange ----------------------------------------------------------------------

_SE_SITES = {"stackoverflow.com": "stackoverflow", "superuser.com": "superuser", "serverfault.com": "serverfault",
             "askubuntu.com": "askubuntu", "math.stackexchange.com": "math", "unix.stackexchange.com": "unix"}


def stackexchange(url: str) -> Optional[SourceContent]:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    site = _SE_SITES.get(host) or (host.split(".")[0] if host.endswith(".stackexchange.com") else None)
    m = re.match(r"^/(?:questions|q)/(\d+)", parsed.path)
    if not site or not m:
        return None
    qid = m.group(1)
    base = "https://api.stackexchange.com/2.3"
    q_items = _get(f"{base}/questions/{qid}", params={"site": site, "filter": "withbody"}).json().get("items") or []
    if not q_items:
        return None
    q = q_items[0]
    answers = _get(f"{base}/questions/{qid}/answers",
                   params={"site": site, "filter": "withbody", "sort": "votes", "order": "desc"}).json().get("items") or []
    answers.sort(key=lambda a: (not a.get("is_accepted"), -a.get("score", 0)))
    parts = [_html_to_text(q.get("body", ""))]
    for a in answers[:MAX_ANSWERS]:
        label = "Accepted answer" if a.get("is_accepted") else f"Answer ({a.get('score', 0)} votes)"
        parts.append(f"## {label}\n\n{_html_to_text(a.get('body', ''))}")
    import html as html_lib
    return SourceContent("stackexchange", html_lib.unescape(q.get("title", "")), "\n\n".join(p for p in parts if p),
                         author=(q.get("owner") or {}).get("display_name"), canonical_url=q.get("link"),
                         keywords=q.get("tags") or [], raw={"site": site, "question_id": int(qid), "score": q.get("score")})


# --- dev.to ------------------------------------------------------------------------------

def devto(url: str) -> Optional[SourceContent]:
    parts = [p for p in urlparse(url).path.split("/") if p]
    if len(parts) != 2:
        return None
    article = _get(f"https://dev.to/api/articles/{parts[0]}/{parts[1]}").json()
    body = article.get("body_markdown") or ""
    if not body:
        return None
    tags = article.get("tags") or article.get("tag_list") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    return SourceContent("devto", article.get("title") or "", body, author=(article.get("user") or {}).get("name"),
                         published_at=article.get("published_at"), description=article.get("description"),
                         canonical_url=article.get("canonical_url") or article.get("url"), keywords=tags,
                         raw={"id": article.get("id")})


# --- Hacker News -------------------------------------------------------------------------

def hackernews(url: str) -> Optional[SourceContent]:
    item_id = (parse_qs(urlparse(url).query).get("id") or [None])[0]
    if not item_id or not item_id.isdigit():
        return None
    item = _get(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json").json() or {}
    if item.get("type") not in ("story", "ask", "job", "poll") or not item.get("title"):
        return None
    text = _html_to_text(item.get("text", "")) if item.get("text") else ""
    if item.get("url"):
        text = "\n\n".join(p for p in (text, f"Link: {item['url']}") if p)
    return SourceContent("hackernews", item["title"], text, author=item.get("by"),
                         canonical_url=f"https://news.ycombinator.com/item?id={item_id}",
                         raw={"id": int(item_id), "score": item.get("score"), "linked_url": item.get("url")},
                         follow_url=item.get("url"))


# --- YouTube -----------------------------------------------------------------------------

_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _youtube_id(url: str) -> Optional[str]:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    parts = [p for p in parsed.path.split("/") if p]
    vid = None
    if host == "youtu.be" and parts:
        vid = parts[0]
    elif parsed.path == "/watch":
        vid = (parse_qs(parsed.query).get("v") or [None])[0]
    elif len(parts) >= 2 and parts[0] in ("shorts", "live", "embed"):
        vid = parts[1]
    return vid if vid and _YT_ID.match(vid) else None


def _youtube_page_details(watch_url: str) -> Dict[str, Optional[str]]:
    """Description and upload date from the watch page's JSON-LD (VideoObject), falling back to its
    standard description meta tags. Only when robots.txt allows us the page; never fatal."""
    from scrapers.robots_manager import RobotsManager
    details: Dict[str, Optional[str]] = {"description": None, "published_at": None}
    try:
        if not RobotsManager().can_fetch(watch_url):
            return details
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(_get(watch_url, params={"hl": "en"}, accept="text/html").text, "html.parser")
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except ValueError:
                continue
            for item in data if isinstance(data, list) else [data]:
                if isinstance(item, dict) and item.get("@type") == "VideoObject":
                    details["description"] = details["description"] or item.get("description")
                    details["published_at"] = details["published_at"] or item.get("uploadDate")
        if not details["description"]:
            meta = (soup.find("meta", attrs={"name": "description"})
                    or soup.find("meta", attrs={"property": "og:description"}))
            if meta:
                details["description"] = (meta.get("content") or "").strip() or None
    except (requests.RequestException, ValueError) as e:
        logger.info("youtube_page_details_unavailable", extra={"url": watch_url, "error": str(e)})
    return details


def youtube(url: str) -> Optional[SourceContent]:
    vid = _youtube_id(url)
    if not vid:
        return None
    watch = f"https://www.youtube.com/watch?v={vid}"
    data = _get("https://www.youtube.com/oembed", params={"url": watch, "format": "json"}).json()
    title = data.get("title")
    if not title:
        return None
    author = data.get("author_name")
    details = _youtube_page_details(watch)
    description = details["description"]
    text = description or f"YouTube video by {author or 'unknown'}: {title}"
    return SourceContent("youtube", title, text, author=author, published_at=details["published_at"],
                         description=(description or "")[:300] or None, canonical_url=watch,
                         raw={"video_id": vid, "thumbnail_url": data.get("thumbnail_url"),
                              "author_url": data.get("author_url")})


# --- Reddit ------------------------------------------------------------------------------

_REDDIT_HOSTS = {"reddit.com", "old.reddit.com", "new.reddit.com", "np.reddit.com", "m.reddit.com"}
_REDDIT_POST = re.compile(r"^/r/([^/]+)/comments/([a-z0-9]+)(?:/[^/]*)?/?$", re.IGNORECASE)


def _reddit_oembed(post_url: str, subreddit: str, post_id: str) -> Optional[SourceContent]:
    """Title, author and subreddit from Reddit's public embed endpoint."""
    data = _get("https://www.reddit.com/oembed", params={"url": post_url}).json()
    title = (data.get("title") or "").strip()
    if not title:
        return None
    author = data.get("author_name") or None
    byline = f" by u/{author}" if author else ""
    return SourceContent("reddit", title, f"Reddit post in r/{subreddit}{byline}: {title}", author=author,
                         canonical_url=post_url, keywords=[subreddit],
                         raw={"post_id": post_id, "subreddit": subreddit, "via": "oembed"})


def reddit(url: str) -> Optional[SourceContent]:
    parsed = urlparse(url)
    m = _REDDIT_POST.match(parsed.path)
    if not m:
        return None
    subreddit, post_id = m.group(1), m.group(2).lower()
    post_url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}/"
    try:
        listing = _get(f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json",
                       params={"raw_json": 1, "limit": 20, "sort": "top"}).json()
    except requests.HTTPError as e:
        # Reddit has answered unauthenticated .json requests with 403 since mid-2026. The embed
        # endpoint still names the post, which beats an empty bookmark.
        logger.info("reddit_json_refused", extra={"url": url, "error": str(e)})
        return _reddit_oembed(post_url, subreddit, post_id)
    post = listing[0]["data"]["children"][0]["data"]
    comments = [c["data"] for c in listing[1]["data"]["children"] if c.get("kind") == "t1"] if len(listing) > 1 else []
    comments = [c for c in comments if c.get("body") and c.get("body") not in ("[deleted]", "[removed]")]
    comments.sort(key=lambda c: -c.get("score", 0))
    parts = [post.get("selftext") or ""]
    linked = None if post.get("is_self") else post.get("url_overridden_by_dest") or post.get("url")
    if linked:
        parts.append(f"Link: {linked}")
    for c in comments[:MAX_ANSWERS]:
        parts.append(f"## Comment by u/{c.get('author')} ({c.get('score', 0)} points)\n\n{c['body']}")
    published = post.get("created_utc")
    if isinstance(published, (int, float)):
        from datetime import datetime, timezone
        published = datetime.fromtimestamp(published, tz=timezone.utc).isoformat()
    return SourceContent("reddit", post.get("title") or "", "\n\n".join(p for p in parts if p),
                         author=post.get("author"), published_at=published,
                         canonical_url=f"https://www.reddit.com{post['permalink']}" if post.get("permalink") else post_url,
                         keywords=[post.get("subreddit") or subreddit],
                         raw={"post_id": post_id, "subreddit": post.get("subreddit") or subreddit,
                              "score": post.get("score"), "num_comments": post.get("num_comments"), "via": "json"},
                         follow_url=linked)


# --- Medium ------------------------------------------------------------------------------

_MEDIUM_POST_ID = re.compile(r"(?:^|-)([0-9a-f]{8,12})$")
_RSS_NS = {"content": "http://purl.org/rss/1.0/modules/content/", "dc": "http://purl.org/dc/elements/1.1/"}
_MEDIUM_RESERVED = {"p", "m", "tag", "topic", "search", "me", "plans", "membership", "about"}


def _medium_feed_and_post(url: str):
    """(feed URL, post id) for a Medium story URL, or None. Medium publishes an RSS feed per author
    (medium.com/feed/@user) and per publication (medium.com/feed/<publication>)."""
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return None
    m = _MEDIUM_POST_ID.search(parts[-1])
    if not m:
        return None
    if host == "medium.com":
        if len(parts) < 2 or parts[0] in _MEDIUM_RESERVED:
            return None
        return f"https://medium.com/feed/{parts[0]}", m.group(1)
    user = host[:-len(".medium.com")]
    if len(parts) != 1 or not re.fullmatch(r"[a-z0-9_.-]+", user):
        return None
    return f"https://medium.com/feed/@{user}", m.group(1)


def medium(url: str) -> Optional[SourceContent]:
    found = _medium_feed_and_post(url)
    if not found:
        return None
    feed_url, post_id = found
    channel = ET.fromstring(_get(feed_url, accept="application/rss+xml").content).find("channel")
    if channel is None:
        return None
    # The feed holds the latest stories only; an older one falls back to the page.
    for item in channel.findall("item"):
        guid = (item.findtext("guid") or "").rstrip("/")
        link = (item.findtext("link") or "").split("?")[0]
        if not (guid.endswith(f"/p/{post_id}") or link.endswith(post_id)):
            continue
        body = _html_to_text(item.findtext("content:encoded", "", _RSS_NS))
        if not body:
            return None
        published = item.findtext("pubDate")
        if published:
            from email.utils import parsedate_to_datetime
            try:
                published = parsedate_to_datetime(published).isoformat()
            except (TypeError, ValueError):
                pass
        return SourceContent("medium", (item.findtext("title") or "").strip(), body,
                             author=item.findtext("dc:creator", None, _RSS_NS), published_at=published,
                             canonical_url=link or url, keywords=[c.text for c in item.findall("category") if c.text],
                             raw={"post_id": post_id, "feed": feed_url})
    return None


# --- X / Twitter -------------------------------------------------------------------------

_X_HOSTS = {"twitter.com", "x.com", "mobile.twitter.com", "mobile.x.com"}
_X_STATUS = re.compile(r"^/([A-Za-z0-9_]{1,15})/status(?:es)?/(\d+)")


def twitter(url: str) -> Optional[SourceContent]:
    m = _X_STATUS.match(urlparse(url).path)
    if not m:
        return None
    user, status_id = m.groups()
    post_url = f"https://twitter.com/{user}/status/{status_id}"
    # X's public embed endpoint; dnt asks it not to use the embed for personalisation.
    data = _get("https://publish.twitter.com/oembed",
                params={"url": post_url, "omit_script": "true", "dnt": "true"}).json()
    html = data.get("html") or ""
    from bs4 import BeautifulSoup
    quote = BeautifulSoup(html, "html.parser").find("blockquote")
    if quote is None:
        return None
    paragraph = quote.find("p")
    text = paragraph.get_text(" ", strip=True) if paragraph else ""
    links = quote.find_all("a")
    posted = links[-1].get_text(strip=True) if links else None  # "March 21, 2006"
    if posted:
        from datetime import datetime
        try:
            posted = datetime.strptime(posted, "%B %d, %Y").date().isoformat()
        except ValueError:
            posted = None
    author = data.get("author_name") or user
    if not text:
        return None
    title = f"{author} on X: \"{text[:80]}{'...' if len(text) > 80 else ''}\""
    return SourceContent("twitter", title, text, author=author, published_at=posted,
                         canonical_url=data.get("url") or post_url,
                         raw={"status_id": status_id, "user": user, "author_url": data.get("author_url")})


# --- LinkedIn: a deliberate exception -------------------------------------------------------
#
# LinkedIn's robots.txt forbids every crawler but its own (`User-agent: *  Disallow: /`), so the normal pipeline
# refuses a LinkedIn link (DISALLOWED), and the rest of this module only reads documented APIs. This adapter is
# the one exception, added at the owner's decision for a personal bookmark manager: when the user saves a link to
# a public LinkedIn post, ONE GET fetches that post's public page with an ordinary desktop browser identity and
# reads its structured data (JSON-LD), the same text a logged-out visitor sees. It does not log in, send cookies,
# rotate identities or addresses, retry, or read anything behind a login; redirects are SSRF-checked; and
# requests are spaced out so a bulk import does not hammer the site.
#
# LinkedIn's terms prohibit automated access, so this is a risk the operator accepts. LINKEDIN_PUBLIC_FETCH_ENABLED
# =false turns it off, and the link is DISALLOWED again, as before.

_LINKEDIN_BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36")
_LINKEDIN_POST_PATHS = ("/posts/", "/pulse/", "/feed/update/")
_LINKEDIN_WALL_PATHS = ("/authwall", "/login", "/uas/login", "/checkpoint")
_LINKEDIN_MIN_SECONDS_BETWEEN_REQUESTS = 5.0
_linkedin_lock = threading.Lock()
_linkedin_last_request = 0.0


def linkedin_fetch_enabled() -> bool:
    """LINKEDIN_PUBLIC_FETCH_ENABLED (default on)."""
    return os.environ.get("LINKEDIN_PUBLIC_FETCH_ENABLED", "true").strip().lower() not in ("0", "false", "no", "off")


def _linkedin_wait_turn(now=time.monotonic, sleep=time.sleep) -> None:
    """At most one request per interval from this process, however many bookmarks are waiting."""
    global _linkedin_last_request
    with _linkedin_lock:
        wait = _linkedin_last_request + _LINKEDIN_MIN_SECONDS_BETWEEN_REQUESTS - now()
        if wait > 0:
            sleep(wait)
        _linkedin_last_request = now()


def _is_linkedin_host(host: str) -> bool:
    host = host.lower()
    return host == "linkedin.com" or host.endswith(".linkedin.com")


def _linkedin_post_data(html: str) -> Optional[Dict]:
    """The post's text, title, author and date from its public page, or None when the page has no post."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    def meta(name: str) -> str:
        tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        return (tag.get("content") or "").strip() if tag else ""

    body = headline = author = published = ""
    for block in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(block.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for item in (data if isinstance(data, list) else [data]):
            if not isinstance(item, dict) or item.get("@type") not in ("SocialMediaPosting", "Article", "NewsArticle"):
                continue
            body = str(item.get("articleBody") or item.get("text") or "").strip()
            headline = str(item.get("headline") or "").strip()
            published = str(item.get("datePublished") or "").strip()
            who = item.get("author")
            author = str(who.get("name") or "").strip() if isinstance(who, dict) else ""
            break
        if body:
            break
    if len(body) < 30:
        body = meta("og:description")        # same text in the page's link preview when there is no JSON-LD
    if len(body) < 30:
        return None
    # og:title reads "Topic | Author posted on the topic | LinkedIn": the topic is the useful part.
    title = (meta("og:title").split(" | ")[0] or headline).strip()
    canonical = soup.find("link", rel="canonical")
    # Posts often style words with Unicode "bold" letters (the mathematical alphanumerics), which search and the
    # embedding model do not read as the ordinary word: NFKC turns them back into letters. The title and author get
    # the same treatment; emoji, line breaks and ordinary accents are untouched.
    nfkc = lambda text: unicodedata.normalize("NFKC", text) if text else text
    return {"body": nfkc(body), "title": nfkc(title or headline), "author": nfkc(author) or None,
            "published": published or None, "canonical": (canonical.get("href") if canonical else None)}


def linkedin(url: str) -> Optional[SourceContent]:
    if not linkedin_fetch_enabled():
        return None
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    # lnkd.in short links hide the real path until they redirect, so they are checked after the fetch.
    if _is_linkedin_host(host) and not any(p in parsed.path for p in _LINKEDIN_POST_PATHS):
        return None
    _linkedin_wait_turn()
    resp = safe_get(url, headers={"User-Agent": _LINKEDIN_BROWSER_UA, "Accept": "text/html,application/xhtml+xml",
                                  "Accept-Language": "en-US,en;q=0.9"},
                    timeout=TIMEOUT, max_bytes=3 * 1024 * 1024)
    final = urlparse(resp.url)
    if resp.status_code != 200 or not _is_linkedin_host(final.netloc):
        return None
    if any(final.path.startswith(p) for p in _LINKEDIN_WALL_PATHS) or not any(p in final.path for p in _LINKEDIN_POST_PATHS):
        return None                          # a login wall, or a profile/company page rather than a post
    post = _linkedin_post_data(resp.content.decode("utf-8", errors="replace"))
    if post is None:
        return None
    return SourceContent(source="linkedin", title=post["title"], text=post["body"], author=post["author"],
                         published_at=post["published"], description=post["body"][:300],
                         canonical_url=post["canonical"])


# --- dispatch ----------------------------------------------------------------------------

_ADAPTERS: Dict[str, Callable[[str], Optional[SourceContent]]] = {
    "github.com": github,
    "arxiv.org": arxiv,
    "dev.to": devto,
    "news.ycombinator.com": hackernews,
    "youtube.com": youtube,
    "m.youtube.com": youtube,
    "youtu.be": youtube,
    **{host: reddit for host in _REDDIT_HOSTS},
    **{host: twitter for host in _X_HOSTS},
    "linkedin.com": linkedin,
    "lnkd.in": linkedin,
}


def adapter_for(url: str) -> Optional[Callable[[str], Optional[SourceContent]]]:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if host in _ADAPTERS:
        return _ADAPTERS[host]
    if host.endswith(".wikipedia.org"):
        return wikipedia
    if host.endswith(".linkedin.com"):
        return linkedin
    if host == "medium.com" or host.endswith(".medium.com"):
        return medium
    if host in _SE_SITES or host.endswith(".stackexchange.com"):
        return stackexchange
    return None


def fetch_from_source(url: str) -> Optional[SourceContent]:
    """Content via the site's official API, or None to fall back to page extraction."""
    adapter = adapter_for(url)
    if adapter is None:
        return None
    try:
        content = adapter(url)
    except (requests.RequestException, ValueError, ET.ParseError, json.JSONDecodeError,
            KeyError, IndexError, TypeError) as e:  # the last three: an API answered in an unexpected shape
        logger.warning("source_adapter_failed", extra={"url": url, "adapter": adapter.__name__, "error": str(e)})
        return None
    if content is None or not ((content.text or "").strip() or content.follow_url):
        return None
    from scrapers.text_cleanup import clean_body
    content.text = clean_body(content.text)
    logger.info("source_adapter_used", extra={"url": url, "source": content.source, "chars": len(content.text)})
    return content
