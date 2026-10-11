"""
Intent: what the user is trying to do right now, built from their own words.

- intent_text: the request composed from the query and the owned project/task/subtask
  context. Always available instantly; no parsing or keyword classification.
- statement + needs: Gemini's reading of that context ("building X; right now needs Y")
  plus 2-4 concrete information needs. Computed in a background job and cached by
  context hash; the request path never waits for it.

Both are turned into query vectors for retrieval.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.logging_config import get_logger

logger = get_logger(__name__)

INTENT_VERSION = "intent-v2"
CACHE_PREFIX = f"{INTENT_VERSION}:"
CACHE_TTL = 7 * 86400
PENDING_TTL = 300
JOB_PATH = "ml.intent_engine.intent.compute_intent_job"
MAX_NEEDS = 4


@dataclass
class IntentContext:
    user_id: int
    query: str = ""
    project_title: str = ""
    project_description: str = ""
    project_technologies: str = ""
    task_title: str = ""
    task_description: str = ""
    subtask_title: str = ""
    subtask_description: str = ""
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    subtask_id: Optional[int] = None


@dataclass
class Intent:
    context: IntentContext
    text: str
    hash: str
    statement: Optional[str] = None
    needs: List[str] = field(default_factory=list)

    def query_texts(self) -> List[str]:
        """Texts to embed as retrieval queries, most direct first."""
        texts = [self.text]
        if self.statement:
            texts.append(self.statement)
        texts.extend(self.needs)
        seen, out = set(), []
        for t in texts:
            if t and t not in seen:
                seen.add(t)
                out.append(t)
        return out

    @property
    def rerank_query(self) -> str:
        return self.statement or self.text


def _task_description(raw: Optional[str]) -> str:
    """AI-generated tasks store a JSON object as the description; use its prose field."""
    if not raw:
        return ""
    stripped = raw.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            if isinstance(data, dict) and isinstance(data.get("description"), str):
                return data["description"]
        except (json.JSONDecodeError, TypeError):
            pass
    return raw


def load_context(session, user_id: int, query: str = "", project_id: Optional[int] = None,
                 task_id: Optional[int] = None, subtask_id: Optional[int] = None) -> IntentContext:
    """Resolve project/task/subtask the user owns; ids that don't belong to the user are ignored."""
    from models import Project, Subtask, Task

    ctx = IntentContext(user_id=user_id, query=(query or "").strip())
    project = session.query(Project).filter_by(id=project_id, user_id=user_id).first() if project_id else None
    task = None
    if task_id:
        task = (session.query(Task).join(Project, Task.project_id == Project.id)
                .filter(Task.id == task_id, Project.user_id == user_id).first())
        if task and not project:
            project = session.query(Project).filter_by(id=task.project_id, user_id=user_id).first()
    subtask = None
    if subtask_id and task:
        subtask = session.query(Subtask).filter_by(id=subtask_id, task_id=task.id).first()

    if project:
        ctx.project_id = project.id
        ctx.project_title = project.title or ""
        ctx.project_description = project.description or ""
        ctx.project_technologies = project.technologies or ""
    if task:
        ctx.task_id = task.id
        ctx.task_title = task.title or ""
        ctx.task_description = _task_description(task.description)
    if subtask:
        ctx.subtask_id = subtask.id
        ctx.subtask_title = subtask.title or ""
        ctx.subtask_description = subtask.description or ""
    return ctx


def compose_intent_text(ctx: IntentContext) -> str:
    """The user's own context as one passage, most specific (what they're doing now) first."""
    parts = []
    if ctx.subtask_title:
        parts.append(f"Current step: {ctx.subtask_title}. {ctx.subtask_description}".strip())
    if ctx.task_title:
        parts.append(f"Current task: {ctx.task_title}. {ctx.task_description}".strip())
    if ctx.query:
        parts.append(f"Looking for: {ctx.query}")
    if ctx.project_title:
        parts.append(f"Project: {ctx.project_title}. {ctx.project_description}".strip())
    if ctx.project_technologies:
        parts.append(f"Using: {ctx.project_technologies}")
    return "\n".join(p.strip(" .") + "." for p in parts if p.strip())


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


_PROMPT = """Someone is using their personal knowledge base. From their own words below, state what
they are trying to do and what information would help them right now. Stay grounded in what they
wrote; do not invent requirements.

<<<
{text}
>>>

Return a JSON object with exactly these keys:
- "statement": 1-2 sentences, in the third person, on what they are working on and what they need next.
- "needs": 2-{max_needs} short phrases, each a specific piece of information or kind of resource that would help now."""


def parse_intent(raw) -> Optional[Dict]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
    if not isinstance(raw, dict):
        return None
    statement = raw.get("statement")
    needs = raw.get("needs")
    if not (isinstance(statement, str) and statement.strip()):
        return None
    needs = [n.strip()[:200] for n in needs if isinstance(n, str) and n.strip()] if isinstance(needs, list) else []
    return {"statement": statement.strip()[:600], "needs": needs[:MAX_NEEDS]}


def compute_intent_job(intent_hash: str, intent_text: str, user_id: Optional[int] = None) -> bool:
    """RQ job: ask Gemini for the intent statement + needs and cache them. Returns success."""
    from utils.gemini_utils import GeminiAnalyzer
    from utils.redis_utils import redis_cache

    try:
        api_key = None
        if user_id:
            try:
                from services.multi_user_api_manager import get_user_api_key
                api_key = get_user_api_key(user_id)
            except Exception:
                api_key = None
        parsed = parse_intent(GeminiAnalyzer(api_key=api_key).generate_json(
            _PROMPT.format(text=intent_text, max_needs=MAX_NEEDS)))
        if parsed is None:
            logger.warning("intent_statement_unavailable", extra={"intent_hash": intent_hash})
            return False
        redis_cache.set_cache(CACHE_PREFIX + intent_hash, parsed, CACHE_TTL)
        return True
    finally:
        try:
            redis_cache.redis_client.delete(CACHE_PREFIX + "pending:" + intent_hash)
        except Exception:
            pass


def schedule_intent(intent_hash: str, intent_text: str, user_id: Optional[int]) -> None:
    """Enqueue compute_intent_job once per context (dedup via a short-lived pending marker)."""
    try:
        from utils.redis_utils import redis_cache
        client = getattr(redis_cache, "redis_client", None)
        if client is None or not client.set(CACHE_PREFIX + "pending:" + intent_hash, 1, nx=True, ex=PENDING_TTL):
            return
        from services.task_queue import get_queue
        queue = get_queue("default")
        if queue is None:
            client.delete(CACHE_PREFIX + "pending:" + intent_hash)
            return
        queue.enqueue(JOB_PATH, intent_hash, intent_text, user_id, job_timeout=120)
    except Exception as e:
        logger.warning("intent_schedule_failed", extra={"error": str(e)})


def resolve_intent(ctx: IntentContext, schedule: bool = True) -> Intent:
    """Intent for this context: cached Gemini statement if ready, else the user's own words."""
    text = compose_intent_text(ctx)
    intent = Intent(context=ctx, text=text, hash=_hash(text))
    if not text:
        return intent
    try:
        from utils.redis_utils import redis_cache
        cached = redis_cache.get_cache(CACHE_PREFIX + intent.hash)
        if isinstance(cached, dict) and cached.get("statement"):
            intent.statement = cached["statement"]
            intent.needs = list(cached.get("needs") or [])
            return intent
    except Exception as e:
        logger.warning("intent_cache_read_failed", extra={"error": str(e)})
    if schedule:
        schedule_intent(intent.hash, text, ctx.user_id)
    return intent
