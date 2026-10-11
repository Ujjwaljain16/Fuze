"""
Content profile: Gemini's structured understanding of what a saved item is and what
it is useful for. Stored in content_analysis and embedded as a 'profile' row in
content_chunks so retrieval can match an intent against what an item is *for*, not
only against the words it contains.

There is no heuristic fallback: if the model doesn't return a valid profile the
caller records a failed (retryable) analysis.
"""

import json
from typing import Any, Dict, List, Optional

from core.logging_config import get_logger

logger = get_logger(__name__)

PROFILE_VERSION = "profile-v1"
MAX_INPUT_CHARS = 12000

CONTENT_TYPES = [
    "tutorial", "guide", "reference", "documentation", "article", "opinion", "news",
    "research", "video", "course", "tool", "repository", "discussion", "other",
]
LEVELS = ["beginner", "intermediate", "advanced", "mixed"]

_PROMPT = """You are building a personal knowledge base. Describe this saved item so it can be matched
to what its owner is trying to do later. Be specific to THIS item; do not pad.

Title: {title}
URL: {url}
Owner's note: {notes}
Content (may be truncated):
<<<
{text}
>>>

Return a JSON object with exactly these keys:
- "summary": 2-3 sentences on what this item is and what it covers.
- "teaches_or_solves": 1-5 short phrases, each a concrete thing a reader learns or a problem it helps solve.
- "key_concepts": 3-8 key concepts or topics, most important first.
- "use_when": one sentence describing the situation or goal in which someone would want this item.
- "audience_level": one of {levels}.
- "content_type": one of {types}.
- "technologies": named languages, frameworks, libraries, tools or services actually discussed; [] if none.
If the content is empty or unreadable, base the profile on the title, URL and note, and say so in the summary."""


def build_prompt(title: str, url: str, notes: str, text: str) -> str:
    return _PROMPT.format(
        title=(title or "").strip() or "(none)",
        url=(url or "").strip() or "(none)",
        notes=(notes or "").strip() or "(none)",
        text=(text or "")[:MAX_INPUT_CHARS],
        levels=", ".join(LEVELS),
        types=", ".join(CONTENT_TYPES),
    )


def _str_list(value, max_items: int) -> List[str]:
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip()[:200])
    return out[:max_items]


def parse_profile(raw: Any) -> Optional[Dict[str, Any]]:
    """Validate model output. Returns None unless the essential fields are present."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
    if not isinstance(raw, dict):
        return None

    summary = raw.get("summary")
    use_when = raw.get("use_when")
    concepts = _str_list(raw.get("key_concepts"), 8)
    if not (isinstance(summary, str) and summary.strip() and isinstance(use_when, str) and use_when.strip() and concepts):
        return None

    level = str(raw.get("audience_level", "")).strip().lower()
    ctype = str(raw.get("content_type", "")).strip().lower()
    return {
        "summary": summary.strip()[:1200],
        "teaches_or_solves": _str_list(raw.get("teaches_or_solves"), 5),
        "key_concepts": concepts,
        "use_when": use_when.strip()[:500],
        "audience_level": level if level in LEVELS else "mixed",
        "content_type": ctype if ctype in CONTENT_TYPES else "other",
        "technologies": _str_list(raw.get("technologies"), 15),
    }


def generate_profile(analyzer, title: str, url: str, notes: str, text: str) -> Optional[Dict[str, Any]]:
    raw = analyzer.generate_json(build_prompt(title, url, notes, text))
    profile = parse_profile(raw)
    if profile is None:
        logger.warning("content_profile_invalid_or_missing", extra={"title": (title or "")[:80]})
    return profile


def profile_text(title: str, profile: Dict[str, Any]) -> str:
    """The text that gets embedded for the profile row: what the item is and when it helps."""
    parts = [
        (title or "").strip(),
        profile["summary"],
        f"Useful when: {profile['use_when']}",
    ]
    if profile.get("teaches_or_solves"):
        parts.append("Covers: " + "; ".join(profile["teaches_or_solves"]))
    parts.append("Key concepts: " + ", ".join(profile["key_concepts"]))
    return "\n".join(p for p in parts if p)


def analysis_payload(profile: Dict[str, Any], model_name: Optional[str]) -> Dict[str, Any]:
    """analysis_data JSON. Keeps the legacy keys other readers still use alongside the new ones."""
    return {
        **profile,
        "difficulty": profile["audience_level"],
        "basic_summary": profile["summary"],
        "profile_version": PROFILE_VERSION,
        "model": model_name if isinstance(model_name, str) else None,
    }


def store_profile(session, content, profile: Dict[str, Any], model_name: Optional[str]):
    """Insert or overwrite the content_analysis row for this item."""
    from models import ContentAnalysis

    payload = analysis_payload(profile, model_name)
    row = session.query(ContentAnalysis).filter_by(content_id=content.id).first()
    if row is None:
        row = ContentAnalysis(content_id=content.id, analysis_data=payload)
        session.add(row)
    row.analysis_data = payload
    row.key_concepts = ", ".join(profile["key_concepts"])
    row.content_type = profile["content_type"]
    row.difficulty_level = profile["audience_level"]
    row.technology_tags = ", ".join(profile["technologies"])
    return row


def index_profile_chunk(session, content_id: int, user_id: int, title: str, profile: Dict[str, Any]) -> None:
    """Embed the profile and store it as the item's 'profile' row in content_chunks (Postgres only)."""
    if session.get_bind().dialect.name != "postgresql":
        return
    from sqlalchemy import text
    from services.hybrid_search import _vec_literal
    from utils.embedding_utils import active_embedding_model_name, get_embedding

    body = profile_text(title, profile)
    vec = get_embedding(body)
    session.execute(text("DELETE FROM content_chunks WHERE content_id = :id AND kind = 'profile'"), {"id": content_id})
    session.execute(text(
        "INSERT INTO content_chunks (content_id, user_id, kind, chunk_index, text, embedding, embedding_model) "
        "VALUES (:cid, :uid, 'profile', 0, :text, CAST(:emb AS vector), :model)"
    ), {"cid": content_id, "uid": user_id, "text": body, "emb": _vec_literal(vec),
        "model": active_embedding_model_name()})
