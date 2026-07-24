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
