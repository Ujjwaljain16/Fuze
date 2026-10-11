"""
Source adapters: for sites with an official public API, read the content through it instead of
parsing the page. The result is the real text (a repo's README, a paper's abstract, a question
and its answers) without layout noise, and it uses documented, rate-limited access.

Each adapter returns SourceContent or None (unknown URL shape / API error); the caller then
falls back to the normal HTML pipeline.
"""

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

import requests

from core.logging_config import get_logger

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


def _get(url: str, params: Optional[Dict] = None, accept: Optional[str] = None) -> requests.Response:
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    resp = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
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


# --- dispatch ----------------------------------------------------------------------------

_ADAPTERS: Dict[str, Callable[[str], Optional[SourceContent]]] = {
    "github.com": github,
    "arxiv.org": arxiv,
    "dev.to": devto,
    "news.ycombinator.com": hackernews,
}


def adapter_for(url: str) -> Optional[Callable[[str], Optional[SourceContent]]]:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if host in _ADAPTERS:
        return _ADAPTERS[host]
    if host.endswith(".wikipedia.org"):
        return wikipedia
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
    except (requests.RequestException, ValueError, ET.ParseError, json.JSONDecodeError) as e:
        logger.warning("source_adapter_failed", extra={"url": url, "adapter": adapter.__name__, "error": str(e)})
        return None
    if content is None or not ((content.text or "").strip() or content.follow_url):
        return None
    from scrapers.text_cleanup import clean_body
    content.text = clean_body(content.text)
    logger.info("source_adapter_used", extra={"url": url, "source": content.source, "chars": len(content.text)})
    return content
