"""Remove markup that carries no meaning for search/embeddings from extracted Markdown bodies."""

import re

_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")             # ![alt](src)
_EMPTY_LINK = re.compile(r"\[\s*\]\([^)]*\)")            # [](href) left behind by badges
# Inline HTML in READMEs. Only real tag names with well-formed attributes match, so code like
# List<String>, Vec<u8> or "a<b and c>d" is left alone.
_TAG_NAMES = (
    "a|abbr|b|blockquote|br|center|code|dd|del|details|div|dl|dt|em|figcaption|figure|font|"
    "h[1-6]|hr|i|img|ins|kbd|li|ol|p|picture|pre|s|samp|small|source|span|strike|strong|sub|"
    "summary|sup|table|tbody|td|tfoot|th|thead|tr|tt|u|ul|var|video"
)
_ATTRIBUTE = r"""\s+(?:[\w:-]+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'<>]+)|open|hidden|controls|autoplay|loop|muted)"""
_HTML_TAG = re.compile(rf"</?((?:{_TAG_NAMES}))(?:{_ATTRIBUTE})*\s*/?>", re.IGNORECASE)
_BLOCK_TAGS = {"blockquote", "br", "center", "dd", "details", "div", "dl", "dt", "figcaption", "figure",
               "h1", "h2", "h3", "h4", "h5", "h6", "hr", "li", "ol", "p", "pre", "summary", "table",
               "tbody", "td", "tfoot", "th", "thead", "tr", "ul"}


def _replace_tag(match: "re.Match") -> str:
    # Block tags separate text; dropping them outright glued words together ("MoreBody").
    return "\n" if match.group(1).lower() in _BLOCK_TAGS else ""
_PIPE_ONLY_LINE = re.compile(r"^[\s|:\-]*\|[\s|:\-]*$")   # layout-table rows with no content
_BLANK_RUNS = re.compile(r"\n{3,}")


def clean_body(text: str) -> str:
    if not text:
        return ""
    text = _IMAGE.sub("", text)
    text = _EMPTY_LINK.sub("", text)
    text = _HTML_TAG.sub(_replace_tag, text)
    lines = [line.rstrip() for line in text.splitlines()]
    lines = [line for line in lines if not _PIPE_ONLY_LINE.match(line)]
    text = "\n".join(lines)
    text = re.sub(r"^\s*\|(\s*\|)*\s*", "", text)  # leading empty-cell run on the first line
    return _BLANK_RUNS.sub("\n\n", text).strip()
