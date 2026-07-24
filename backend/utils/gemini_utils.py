import os
import json
import re
import time
from typing import Dict, List, Optional, Any, Union
import google.generativeai as genai
from core.logging_config import get_logger

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
    """

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or os.environ.get('GEMINI_API_KEY')
        if not key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        genai.configure(api_key=key)

        model_candidates = ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-pro']
        self.model = None

        for model_name in model_candidates:
            try:
                self.model = genai.GenerativeModel(model_name)
                logger.info("gemini_model_initialized", extra={"model_name": model_name})
                break
            except Exception:
                continue

        if not self.model:
            raise ValueError("Failed to initialize Gemini AI with candidate models")

        self.generation_config = {
            'temperature': 0.3,
            'top_p': 0.8,
            'top_k': 40,
            'max_output_tokens': 2048,
        }

        self.max_retries = 3
        self.retry_delay = 1.0

    def _make_gemini_request(self, prompt: str) -> Optional[str]:
        """Make an iterative request to Gemini with backoff and error handling."""
        if not prompt or not isinstance(prompt, str):
            return None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=self.generation_config
                )

                if not response or not hasattr(response, 'text') or not response.text:
                    if attempt < self.max_retries:
                        time.sleep(self.retry_delay * (attempt + 1))
                        continue
                    return None

                cleaned = response.text.strip()
                if cleaned:
                    return cleaned
            except Exception as e:
                logger.warning("gemini_request_failed_attempt", extra={"attempt": attempt + 1, "error": str(e)})
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue

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

    def analyze_bookmark_content(self, title: str, description: str, content: str, url: str = "") -> Dict:
        """Analyze bookmark content using Gemini AI with fallback handling."""
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

            return self._get_fallback_analysis(title, description, content)
        except Exception as e:
            logger.error("analyze_bookmark_content_failed", extra={"title": title, "error": str(e)})
            return self._get_fallback_analysis(title, description, content)

    def _get_fallback_analysis(self, title: str, description: str, content: str) -> Dict:
        """Deterministic fallback analysis when AI is unavailable."""
        text = f"{title or ''} {description or ''} {content or ''}".lower()
        common_techs = ['python', 'javascript', 'typescript', 'react', 'node', 'sql', 'docker', 'aws']
        detected = [t.capitalize() for t in common_techs if t in text]

        return {
            "technologies": detected or ["General"],
            "content_type": "article",
            "difficulty": "intermediate",
            "intent": "learning",
            "key_concepts": [title[:30]] if title else ["Content Analysis"],
            "relevance_score": 75,
            "summary": description[:150] if description else (title[:150] if title else "Content summary")
        }

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

            return [f"Relevant based on matching content topics and technologies." for _ in recommendations]
        except Exception as e:
            logger.error("batch_reasoning_failed", extra={"error": str(e)})
            return [f"Relevant content recommendation." for _ in batch_context.get('recommendations', [])]