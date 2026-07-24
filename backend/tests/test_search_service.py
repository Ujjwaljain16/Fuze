import pytest
from unittest.mock import MagicMock, patch
from services.search_service import SearchService, MAX_QUERY_LENGTH


@pytest.mark.unit
def test_search_service_query_validation():
    mock_uow = MagicMock()
    service = SearchService(mock_uow)

    assert service._validate_query("") is None
    assert service._validate_query("   ") is None

    long_query = "A" * (MAX_QUERY_LENGTH + 500)
    validated = service._validate_query(long_query)
    assert len(validated) == MAX_QUERY_LENGTH


@pytest.mark.unit
def test_text_search_empty_query():
    mock_uow = MagicMock()
    service = SearchService(mock_uow)

    assert service.text_search(user_id=1, query="") == []
    assert service.text_search(user_id=1, query="   ") == []


@pytest.mark.unit
def test_supabase_semantic_search_with_injected_client():
    mock_uow = MagicMock()
    mock_supabase = MagicMock()
    mock_supabase.rpc.side_effect = Exception("RPC disabled in test")

    mock_response = MagicMock()
    mock_response.data = [
        {
            'id': 1,
            'user_id': 10,
            'url': 'https://example.com',
            'title': 'Test Title',
            'extracted_text': 'Text content',
            'embedding': [0.1] * 384
        }
    ]
    mock_supabase.table.return_value.select.return_value.eq.return_value.not_.is_.return_value.limit.return_value.execute.return_value = mock_response

    service = SearchService(mock_uow, client=mock_supabase)

    with patch('services.search_service.get_embedding', return_value=[0.1] * 384):
        res = service.supabase_semantic_search(user_id=10, query="python dev", limit=5)
        assert res['source'] in ('supabase', 'supabase_rpc')
        assert len(res['results']) == 1
        assert res['results'][0]['id'] == 1
