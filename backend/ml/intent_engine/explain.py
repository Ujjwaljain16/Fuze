"""On-demand, Gemini-written explanation of how one saved item helps with the user's current intent."""

from typing import Optional

from core.logging_config import get_logger
from ml.intent_engine.intent import load_context, resolve_intent

logger = get_logger(__name__)

_PROMPT = """You are helping someone use their own saved knowledge.

What they are doing:
<<<
{intent}
>>>

An item they saved:
Title: {title}
Summary: {summary}
Useful when: {use_when}
Key concepts: {concepts}
Excerpt:
<<<
{excerpt}
>>>

In 2-3 sentences, tell them specifically how this item helps with what they are doing now and what
to take from it. If it only partly applies, say which part. Do not restate the title. Plain text only."""


def explain_item(session, user_id: int, content_id: int, query: str = "", project_id: Optional[int] = None,
                 task_id: Optional[int] = None, subtask_id: Optional[int] = None,
                 api_key: Optional[str] = None) -> Optional[str]:
    """Return the explanation, or None if the item isn't the user's or the model gave nothing usable."""
    from models import ContentAnalysis, SavedContent
    from utils.gemini_utils import GeminiAnalyzer

    item = session.query(SavedContent).filter_by(id=content_id, user_id=user_id).first()
    if item is None:
        return None
    analysis = session.query(ContentAnalysis).filter_by(content_id=item.id).first()
    profile = (analysis.analysis_data if analysis else None) or {}
    if not profile.get("profile_version"):
        profile = {}

    intent = resolve_intent(load_context(session, user_id, query, project_id, task_id, subtask_id))
    if not intent.text:
        return None

    prompt = _PROMPT.format(
        intent=intent.statement or intent.text,
        title=item.title or item.url,
        summary=profile.get("summary") or "(not analyzed yet)",
        use_when=profile.get("use_when") or "(unknown)",
        concepts=", ".join(profile.get("key_concepts") or []) or "(unknown)",
        excerpt=(item.extracted_text or item.notes or "")[:1500],
    )
    text = GeminiAnalyzer(api_key=api_key)._make_gemini_request(prompt)
    if not text or len(text.strip()) < 20:
        logger.warning("explain_item_no_output", extra={"content_id": content_id})
        return None
    return text.strip()
