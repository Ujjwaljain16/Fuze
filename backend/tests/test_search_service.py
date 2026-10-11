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
    with patch('services.search_service.embed_query', return_value=[0.1] * 384),          patch('services.hybrid_search.semantic_search', return_value=hits),          patch.object(SearchService, '_document_hits', return_value=[]):
        res = service.supabase_semantic_search(user_id=10, query="secure my api", limit=5)
    assert res['results'][0]['id'] == 1
    assert res['results'][0]['relevance_score'] == 88.1  # sigmoid(2.0)
    assert 'Issue and verify tokens' in res['results'][0]['content_snippet']


def _unit(vec):
    import numpy as np
    v = np.asarray(vec, dtype=np.float32)
    return (v / np.linalg.norm(v)).tolist()


def test_unchunked_bookmarks_stay_searchable_and_other_models_are_excluded(app, test_user):
    """Once a user had any passage chunks, bookmarks without chunks used to vanish from search."""
    from sqlalchemy import text as sql
    from models import db, SavedContent
    from uow.unit_of_work import UnitOfWork
    query = _unit([1.0] + [0.0] * 383)
    near = _unit([0.9, 0.1] + [0.0] * 382)
    far = _unit([0.1, 0.9] + [0.0] * 382)
    with app.app_context():
        chunked = SavedContent(user_id=test_user['id'], url='https://e.com/chunked', title='chunked',
                               embedding=far, embedding_metadata={'model': 'test-model'})
        unchunked = SavedContent(user_id=test_user['id'], url='https://e.com/unchunked', title='unchunked',
                                 embedding=near, embedding_metadata={'model': 'test-model'})
        other_model = SavedContent(user_id=test_user['id'], url='https://e.com/other', title='other',
                                   embedding=query, embedding_metadata={'model': 'some-other-model'})
        db.session.add_all([chunked, unchunked, other_model])
        db.session.commit()
        postgres = db.engine.dialect.name == 'postgresql'
        if postgres:
            from services.hybrid_search import _vec_literal
            db.session.execute(sql(
                "INSERT INTO content_chunks (content_id, user_id, chunk_index, text, embedding, embedding_model) "
                "VALUES (:cid, :uid, 0, 'a passage', CAST(:emb AS vector), 'test-model')"),
                {"cid": chunked.id, "uid": test_user['id'], "emb": _vec_literal(far)})
            db.session.commit()
        ids = {'chunked': chunked.id, 'unchunked': unchunked.id, 'other': other_model.id}

        with patch('services.search_service.embed_query', return_value=query),              patch('services.search_service.active_embedding_model_name', return_value='test-model'),              patch('services.hybrid_search.active_embedding_model_name', return_value='test-model'),              UnitOfWork() as uow:
            res = SearchService(uow).supabase_semantic_search(test_user['id'], 'anything', limit=10)

    found = [r['id'] for r in res['results']]
    assert ids['unchunked'] in found and ids['chunked'] in found
    assert ids['other'] not in found  # a vector from another model is not comparable
    assert found.index(ids['unchunked']) < found.index(ids['chunked'])  # ranked by real similarity
    assert all(r['relevance_score'] < 100 for r in res['results'])


def test_failed_query_embedding_is_an_error_not_a_ranking():
    mock_uow = MagicMock()
    with patch('services.search_service.embed_query', return_value=[0.0] * 384):
        with pytest.raises(RuntimeError):
            SearchService(mock_uow).semantic_search(user_id=1, query='anything')


@pytest.mark.unit
def test_document_vector_search_enables_iterative_hnsw_scan_on_postgres():
    """The per-user filter runs after HNSW; without iterative scan a user can get truncated results."""
    mock_uow = MagicMock()
    session = mock_uow.session
    session.get_bind.return_value.dialect.name = 'postgresql'
    session.execute.return_value.mappings.return_value = []
    with patch('services.search_service.active_embedding_model_name', return_value='test-model'):
        SearchService(mock_uow)._document_hits(7, [0.1] * 384, 5)

    calls = session.execute.call_args_list
    sql = [str(c.args[0]) for c in calls]
    assert "hnsw.iterative_scan" in sql[0] and "relaxed_order" in sql[0]
    assert "hnsw.ef_search" in sql[1] and calls[1].args[1] == {"ef": "40"}
    assert "<=>" in sql[2]  # the ANN query runs after both settings
