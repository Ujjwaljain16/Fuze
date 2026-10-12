import json
import re
import time
from typing import Any, Dict, List, Optional, Union
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from core.logging_config import get_logger

from core.circuit_breaker import gemini_circuit_breaker
from core.job_timeout import JobTimeoutException

logger = get_logger(__name__)


def get_gemini_response(prompt: str, temperature: float = 0.3, user_id: Optional[int] = None) -> Optional[str]:
    """
    Wrapper function for acquiring single Gemini API responses.
    """
    try:
        api_key = None
        if user_id:
            try:
                from services.multi_user_api_manager import get_user_api_key
                api_key = get_user_api_key(user_id)
            except Exception as e:
                logger.warning("user_api_key_lookup_failed", extra={"user_id": user_id, "error": str(e)})

        analyzer = GeminiAnalyzer(api_key=api_key)
        return analyzer._make_gemini_request(prompt)
    except Exception as e:
        logger.error("get_gemini_response_failed", extra={"error": str(e)})
        return None


class GeminiAnalyzer:
    """
    Gemini AI-powered content analyzer for recommendation engine enrichment.

    Every analyzer owns its own client bound to one API key. The old SDK kept the key in
    process-global state (genai.configure), so under gevent a request could run on whichever
    user's key was configured last: one user's saved content billed to another user's key.
    """

    def __init__(self, api_key: Optional[str] = None):
        from utils.unified_config import get_config
        config = get_config()

        self.client: Any = None
        self.model = None  # kept for callers that test truthiness; the model name when ready
        self.active_model_name = None
        self.max_retries = 2
        self.retry_delay = 1.0

        # None means "the caller has no opinion": use the system key. An empty string means no key
        # is allowed for this user (e.g. their daily share of the system key is used up).
        key = config.ai.gemini_api_key if api_key is None else api_key
        if not key:
            logger.info("gemini_disabled_no_api_key_configured")
            return

        try:
            self.client = genai.Client(
                api_key=key,
                http_options=genai_types.HttpOptions(timeout=config.ai.gemini_timeout * 1000),
            )
        except Exception as client_err:
            logger.warning("gemini_client_init_failed", extra={"error": str(client_err)})
            return

        self.model_candidates = [m for m in (config.ai.gemini_model, config.ai.gemini_fallback_model) if m]
        if not self.model_candidates:
            self.client = None
            return
        self.model = self.active_model_name = self.model_candidates[0]
        self.generation_config = {
            'temperature': config.ai.gemini_temperature,
            'top_p': 0.8,
            'top_k': 40,
            'max_output_tokens': config.ai.gemini_max_tokens,
        }

    def generate_json(self, prompt: str) -> Optional[Union[Dict, List]]:
        """Request a JSON response (Gemini JSON mode) and parse it; None on any failure."""
        raw = self._make_gemini_request(prompt, json_mode=True)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return self._extract_json_from_response(raw)

    def validate_key(self) -> bool:
        """One cheap call with no retries: does this key work at all?"""
        if not self.client or not self.active_model_name:
            return False
        try:
            response = self.client.models.generate_content(
                model=self.active_model_name, contents='Reply with OK.',
                config=genai_types.GenerateContentConfig(max_output_tokens=5),
            )
            return bool(response and response.text)
        except Exception as e:
            logger.info("gemini_key_validation_failed", extra={"error": str(e)})
            return False

    def _generate(self, model_name: str, prompt: str, json_mode: bool) -> Optional[str]:
        config = dict(self.generation_config)
        if json_mode:
            config['response_mime_type'] = 'application/json'
        response = self.client.models.generate_content(
            model=model_name, contents=prompt, config=genai_types.GenerateContentConfig(**config))
        text = (response.text or '').strip() if response else ''
        return text or None

    def _make_gemini_request(self, prompt: str, json_mode: bool = False) -> Optional[str]:
        """Make a request with backoff and circuit breaker isolation; None on failure."""
        from core.metrics import gemini_calls_total

        def count(status):
            try:
                gemini_calls_total.labels(model=self.active_model_name, status=status).inc()
            except Exception:
                pass

        if not self.client or not prompt or not isinstance(prompt, str):
            return None

        if not gemini_circuit_breaker.allow_request():
            logger.warning("gemini_request_blocked_by_circuit_breaker")
            count("circuit_breaker_blocked")
            return None

        for model_name in self.model_candidates:
            for attempt in range(self.max_retries + 1):
                try:
                    text = self._generate(model_name, prompt, json_mode)
                except JobTimeoutException:
                    raise
                except genai_errors.ClientError as e:
                    # 4xx (bad key, quota, unknown model) will not succeed on retry. An unknown
                    # model moves on to the fallback model; anything else ends the request.
                    logger.warning("gemini_client_error", extra={"model": model_name, "code": e.code, "error": str(e)})
                    if e.code == 404:
                        break
                    count("client_error")
                    return None
                except Exception as e:
                    logger.warning("gemini_request_failed_attempt",
                                   extra={"model": model_name, "attempt": attempt + 1, "error": str(e)})
                    text = None
                if text:
                    self.active_model_name = model_name
                    gemini_circuit_breaker.record_success()
                    count("success")
                    return text
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))

        gemini_circuit_breaker.record_failure()
        count("failed")
        return None

    def _extract_json_from_response(self, response_text: str) -> Optional[Union[Dict, List]]:
        """Extract JSON dict or array from Gemini response text safely."""
        if not response_text or not isinstance(response_text, str):
            return None

        json_patterns = [
            r'```json\s*([\s\S]*?)```',
            r'```\s*([\s\S]*?)```',
            r'\{[\s\S]*?\}',
            r'\[[\s\S]*?\]'
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, response_text, re.DOTALL)
            for match in matches:
                try:
                    cleaned = match.strip()
                    if (cleaned.startswith('{') and cleaned.endswith('}')) or (cleaned.startswith('[') and cleaned.endswith(']')):
                        return json.loads(cleaned)
                except Exception:
                    continue

        try:
            cleaned_response = re.sub(r'^```.*?\n', '', response_text, flags=re.MULTILINE)
            cleaned_response = re.sub(r'\n```$', '', cleaned_response, flags=re.MULTILINE).strip()
            if (cleaned_response.startswith('{') and cleaned_response.endswith('}')) or (cleaned_response.startswith('[') and cleaned_response.endswith(']')):
                return json.loads(cleaned_response)
        except Exception:
            pass

        logger.warning("json_extraction_from_gemini_response_failed")
        return None

    def filter_bad_recommendations(self, recommendations: list) -> list:
        """Filter out recommendations with empty/junk titles or invalid scores."""
        filtered = []
        for rec in recommendations:
            if not isinstance(rec, dict):
                continue
            title = str(rec.get('title', '')).strip()
            reason = str(rec.get('reason', '')).strip()
            score = rec.get('score', 0)

            if not title or title.lower().startswith('1 +') or 'problem description' in title.lower():
                continue
            if not reason or reason.lower() in {'n/a', 'none', 'junk', 'irrelevant'}:
                continue
            if not (0 <= score <= 100):
                continue
            filtered.append(rec)
        return filtered

    def analyze_bookmark_content(self, title: str, description: str, content: str, url: str = "") -> Optional[Dict]:
        """Analyze bookmark content with Gemini. Returns None on failure so the caller records a
        failed (retryable) analysis instead of storing a guess as if it came from the model."""
        try:
            content_preview = (content or "")[:3000]
            prompt = f"""
            Analyze technical content and provide structured insights.
            Title: {title}
            Description: {description}
            URL: {url}
            Content Preview: {content_preview}

            Respond ONLY with valid JSON:
            {{
                "technologies": ["tech1", "tech2"],
                "content_type": "article",
                "difficulty": "intermediate",
                "intent": "learning",
                "key_concepts": ["concept1"],
                "relevance_score": 85,
                "summary": "Summary here"
            }}
            """
            response_text = self._make_gemini_request(prompt)
            if response_text:
                result = self._extract_json_from_response(response_text)
                if isinstance(result, dict):
                    return result
            return None
        except Exception as e:
            logger.error("analyze_bookmark_content_failed", extra={"title": title, "error": str(e)})
            return None


    def generate_batch_recommendation_reasoning(self, batch_context: Dict) -> List[str]:
        """Generate recommendation reasoning for multiple items, supporting JSON arrays."""
        try:
            recommendations = batch_context.get('recommendations', [])
            if not recommendations:
                return []

            prompt = f"Generate JSON array of {len(recommendations)} short reasons for recommendations: {json.dumps(recommendations)[:1500]}"
            response_text = self._make_gemini_request(prompt)
            if response_text:
                res = self._extract_json_from_response(response_text)
                if isinstance(res, list):
                    return [str(r) for r in res]

            return ["Relevant based on matching content topics and technologies." for _ in recommendations]
        except Exception as e:
            logger.error("batch_reasoning_failed", extra={"error": str(e)})
            return ["Relevant content recommendation." for _ in batch_context.get('recommendations', [])]