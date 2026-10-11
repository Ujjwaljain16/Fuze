"""Remove markup that carries no meaning for search/embeddings from extracted Markdown bodies."""

import re

_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")             # ![alt](src)
_EMPTY_LINK = re.compile(r"\[\s*\]\([^)]*\)")            # [](href) left behind by badges
_HTML_TAG = re.compile(r"</?[a-zA-Z][^>\n]*>")           # inline HTML in READMEs
_PIPE_ONLY_LINE = re.compile(r"^[\s|:\-]*\|[\s|:\-]*$")   # layout-table rows with no content
_BLANK_RUNS = re.compile(r"\n{3,}")


def clean_body(text: str) -> str:
    if not text:
        return ""
    text = _IMAGE.sub("", text)
    text = _EMPTY_LINK.sub("", text)
    text = _HTML_TAG.sub("", text)
    lines = [line.rstrip() for line in text.splitlines()]
    lines = [line for line in lines if not _PIPE_ONLY_LINE.match(line)]
    text = "\n".join(lines)
    text = re.sub(r"^\s*\|(\s*\|)*\s*", "", text)  # leading empty-cell run on the first line
    return _BLANK_RUNS.sub("\n\n", text).strip()
