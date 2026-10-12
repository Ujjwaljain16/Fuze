"""An OpenAI-compatible chat provider (CloseRouter, OpenRouter, a local server...) for Fuze's LLM calls.

Off by default: Fuze talks to Gemini. Set LLM_PROVIDER=openai_compat together with LLM_BASE_URL,
LLM_API_KEY and LLM_MODEL and every LLM call in the deployment (page analysis, Ask, intents,
explanations) goes through it instead; users then need no Gemini key of their own. The secret
lives in the environment only: it is never stored, logged or sent anywhere but the base URL.
"""

from typing import Optional
from urllib.parse import urlparse

import requests

from core.logging_config import get_logger

logger = get_logger(__name__)

PROVIDER_NAME = 'openai_compat'
_LOCAL_HOSTS = ('localhost', '127.0.0.1', '::1')


class ProviderClientError(Exception):
    """The provider refused the request in a way a retry will not fix (bad key, no balance, quota)."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


class ProviderServerError(Exception):
    """The provider failed or was unreachable; worth retrying."""


def settings():
    from utils.unified_config import get_config
    return get_config().ai


def is_active() -> bool:
    """Whether LLM calls are routed to the external provider (and it is fully configured)."""
    ai = settings()
    return (ai.llm_provider == PROVIDER_NAME and bool(ai.llm_base_url and ai.llm_api_key and ai.llm_model))


def active_key() -> Optional[str]:
    """The provider key when the external provider is on, else None. Used where code asks
    "is there any usable LLM key for this user?": with a provider configured, there is."""
    return settings().llm_api_key if is_active() else None


def config_problems(ai) -> list:
    """What is wrong with the LLM settings, for startup validation (empty when fine)."""
    if ai.llm_provider in ('', 'gemini'):
        return []
    if ai.llm_provider != PROVIDER_NAME:
        return [f"LLM_PROVIDER must be 'gemini' or '{PROVIDER_NAME}', got {ai.llm_provider!r}"]
    problems = [f"{name} is not set" for name, value in
                (('LLM_BASE_URL', ai.llm_base_url), ('LLM_API_KEY', ai.llm_api_key), ('LLM_MODEL', ai.llm_model))
                if not value]
    if ai.llm_base_url:
        url = urlparse(ai.llm_base_url)
        if url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in _LOCAL_HOSTS):
            problems.append('LLM_BASE_URL must use https:// (http:// only for localhost)')
        if url.username or url.password:
            problems.append('LLM_BASE_URL must not contain credentials; use LLM_API_KEY')
    return problems


class OpenAICompatClient:
    """POST {base_url}/chat/completions with a Bearer key. One instance per analyzer."""

    def __init__(self, base_url: str, api_key: str, timeout: float, json_mode: bool = False):
        self.url = base_url.rstrip('/') + '/chat/completions'
        self._api_key = api_key
        self.timeout = timeout
        self.json_mode = json_mode

    def chat(self, model: str, prompt: str, *, max_tokens: int, temperature: float,
             json_mode: bool = False) -> Optional[str]:
        body = {
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens,
            'temperature': temperature,
        }
        if json_mode and self.json_mode:
            body['response_format'] = {'type': 'json_object'}
        try:
            response = requests.post(
                self.url, json=body, timeout=self.timeout,
                headers={'Authorization': f'Bearer {self._api_key}', 'Content-Type': 'application/json'})
        except requests.RequestException as e:
            raise ProviderServerError(f'request failed: {type(e).__name__}') from e

        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After', '')
            hint = f'Please retry in {int(float(retry_after))}s' if retry_after.replace('.', '', 1).isdigit() else ''
            raise ProviderClientError(429, f'rate limited. {hint}'.strip())
        if response.status_code == 402:
            raise ProviderClientError(402, 'insufficient balance on the LLM provider account')
        if 400 <= response.status_code < 500:
            raise ProviderClientError(response.status_code, self._error_message(response))
        if response.status_code >= 500:
            raise ProviderServerError(f'HTTP {response.status_code}: {self._error_message(response)}')
        try:
            choice = response.json()['choices'][0]
            text = choice['message']['content']
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise ProviderServerError('unexpected response shape') from e
        if choice.get('finish_reason') == 'length':
            # The model ran out of output budget (hidden reasoning counts): the reply is cut off.
            logger.warning("llm_reply_truncated", extra={"model": model, "max_tokens": max_tokens})
        return (text or '').strip() or None

    @staticmethod
    def _error_message(response) -> str:
        """The provider's error code and message; never the request, so no prompt text is logged."""
        try:
            error = response.json().get('error') or {}
            return f"{error.get('code', response.status_code)}: {str(error.get('message', ''))[:200]}"
        except (ValueError, AttributeError):
            return f'HTTP {response.status_code}'
