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
def test_semantic_endpoint_uses_passage_search_when_indexed():
    mock_uow = MagicMock()
    mock_uow.session.get_bind.return_value.dialect.name = 'postgresql'
    hits = [{"content_id": 1, "passage": "Flask JWT guide\nIssue and verify tokens", "similarity": 0.62,
             "rerank_score": 2.0, "title": "Flask JWT guide", "url": "https://example.com"}]
    service = SearchService(mock_uow)
    with patch('services.hybrid_search.user_has_chunks', return_value=True), \
         patch('services.hybrid_search.semantic_search', return_value=hits):
        res = service.supabase_semantic_search(user_id=10, query="secure my api", limit=5)
    assert res['source'] == 'passages'
    assert res['results'][0]['id'] == 1
    assert res['results'][0]['relevance_score'] == 88.1  # sigmoid(2.0)
    assert 'Issue and verify tokens' in res['results'][0]['content_snippet']


@pytest.mark.unit
def test_semantic_endpoint_falls_back_to_documents_without_passages():
    mock_uow = MagicMock()
    mock_uow.session.get_bind.return_value.dialect.name = 'postgresql'
    service = SearchService(mock_uow)
    with patch('services.hybrid_search.user_has_chunks', return_value=False), \
         patch.object(SearchService, 'semantic_search', return_value=[
             {'id': 3, 'title': 't', 'url': 'u', 'description': 'd', 'saved_at': None, 'has_content': True}]):
        res = service.supabase_semantic_search(user_id=10, query="secure my api", limit=5)
    assert res['source'] == 'fallback'
    assert res['results'][0]['id'] == 3
