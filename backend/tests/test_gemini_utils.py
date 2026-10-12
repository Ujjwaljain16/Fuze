import pytest
from unittest.mock import MagicMock, patch
from utils.gemini_utils import GeminiAnalyzer


@pytest.mark.unit
def test_extract_json_from_response_handles_arrays_and_dicts():
    with patch.object(GeminiAnalyzer, '__init__', return_value=None):
        analyzer = GeminiAnalyzer()

        # 1. Test JSON Array extraction
        array_text = '```json\n["reason 1", "reason 2"]\n```'
        res_array = analyzer._extract_json_from_response(array_text)
        assert isinstance(res_array, list)
        assert res_array == ["reason 1", "reason 2"]

        # 2. Test JSON Dict extraction
        dict_text = '{"technologies": ["Python", "Flask"], "relevance_score": 90}'
        res_dict = analyzer._extract_json_from_response(dict_text)
        assert isinstance(res_dict, dict)
        assert res_dict["relevance_score"] == 90


@pytest.mark.unit
def test_filter_bad_recommendations():
    with patch.object(GeminiAnalyzer, '__init__', return_value=None):
        analyzer = GeminiAnalyzer()
        recs = [
            {'title': 'Valid Title', 'reason': 'Great match', 'score': 85},
            {'title': '1 + 1 problem description', 'reason': 'junk', 'score': 10},
            {'title': 'Empty Reason', 'reason': '', 'score': 50}
        ]
        filtered = analyzer.filter_bad_recommendations(recs)
        assert len(filtered) == 1
        assert filtered[0]['title'] == 'Valid Title'


def _fake_client_factory(calls):
    """genai.Client stand-in that records which key served each request."""
    def make(api_key, http_options=None):
        client = MagicMock()

        def generate_content(model, contents, config):
            calls.append((api_key, model))
            return MagicMock(text=f'answer from {api_key}')
        client.models.generate_content.side_effect = generate_content
        return client
    return make


@pytest.mark.unit
def test_each_analyzer_uses_its_own_key_when_interleaved():
    """Regression: the old SDK's genai.configure() made the last configured key win for everyone."""
    calls = []
    with patch('utils.gemini_utils.genai.Client', side_effect=_fake_client_factory(calls)), \
         patch('utils.gemini_utils.gemini_circuit_breaker') as breaker:
        breaker.allow_request.return_value = True
        alice = GeminiAnalyzer(api_key='key-alice')
        bob = GeminiAnalyzer(api_key='key-bob')
        assert alice._make_gemini_request('hi') == 'answer from key-alice'
        assert bob._make_gemini_request('hi') == 'answer from key-bob'
        assert alice._make_gemini_request('again') == 'answer from key-alice'
    assert [key for key, _ in calls] == ['key-alice', 'key-bob', 'key-alice']


@pytest.mark.unit
def test_client_errors_are_not_retried_and_unknown_model_falls_back():
    from google.genai import errors as genai_errors

    def client_error(code):
        return genai_errors.ClientError(code, {'error': {'code': code, 'message': 'x', 'status': 'X'}})

    with patch('utils.gemini_utils.genai.Client') as client_cls, \
         patch('utils.gemini_utils.gemini_circuit_breaker') as breaker, \
         patch('utils.gemini_utils.time.sleep'):
        breaker.allow_request.return_value = True
        generate = client_cls.return_value.models.generate_content

        generate.side_effect = client_error(429)
        analyzer = GeminiAnalyzer(api_key='k')
        assert analyzer._make_gemini_request('hi') is None
        assert generate.call_count == 1

        from core import gemini_quota
        gemini_quota.clear('k')  # the 429 above started a cooldown for this key
        generate.reset_mock()
        generate.side_effect = [client_error(404), MagicMock(text='from fallback')]
        assert analyzer._make_gemini_request('hi') == 'from fallback'
        assert generate.call_args_list[1].kwargs['model'] == analyzer.model_candidates[1]


@pytest.mark.unit
def test_job_timeout_is_not_swallowed_by_retries():
    """RQ raises JobTimeoutException inside the job; catching it hid timeouts until SIGKILL."""
    from core.job_timeout import JobTimeoutException
    with patch('utils.gemini_utils.genai.Client') as client_cls, \
         patch('utils.gemini_utils.gemini_circuit_breaker') as breaker:
        breaker.allow_request.return_value = True
        client_cls.return_value.models.generate_content.side_effect = JobTimeoutException('timeout')
        with pytest.raises(JobTimeoutException):
            GeminiAnalyzer(api_key='k')._make_gemini_request('hi')
