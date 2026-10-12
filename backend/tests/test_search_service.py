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
    assert "hnsw.ef_search" in sql[0] and calls[0].args[1] == {"ef": "40"}  # both settings, one statement
    assert "<=>" in sql[1]  # the ANN query runs right after them


@pytest.mark.unit
def test_ann_settings_are_one_statement_and_sent_once_per_transaction():
    """Each statement is a network round trip: the settings used to be two statements, repeated per query."""
    from services.hybrid_search import configure_filtered_ann
    session = MagicMock()
    session.info = {}
    transaction = object()
    session.get_transaction.return_value = transaction

    configure_filtered_ann(session, 60)
    assert session.execute.call_count == 1
    sql = str(session.execute.call_args.args[0])
    assert "hnsw.iterative_scan" in sql and "hnsw.ef_search" in sql  # both settings in the one statement

    configure_filtered_ann(session, 60)   # same transaction, same ef: nothing sent
    configure_filtered_ann(session, 10)   # a smaller ef is covered by the larger one already set
    assert session.execute.call_count == 1

    configure_filtered_ann(session, 100)  # a larger ef needs the setting raised
    assert session.execute.call_count == 2

    session.get_transaction.return_value = object()  # a new transaction has forgotten the settings
    configure_filtered_ann(session, 60)
    assert session.execute.call_count == 3


@pytest.mark.unit
def test_passage_search_makes_no_second_query_when_retrieval_returned_the_details():
    from services import hybrid_search
    session = MagicMock()
    candidates = [{"content_id": 1, "passage": "p", "similarity": 0.9, "id": 1, "title": "T", "url": "https://e.com",
                   "notes": "", "saved_at": None}]
    with patch.object(hybrid_search, 'retrieve', return_value=candidates):
        results = hybrid_search.semantic_search(session, 7, "q", limit=5, rerank=False, query_vector=[0.1] * 384)
    assert results[0]["title"] == "T"
    session.execute.assert_not_called()


@pytest.mark.unit
def test_passage_search_still_fetches_details_for_candidates_that_lack_them():
    from services import hybrid_search
    session = MagicMock()
    session.execute.return_value.mappings.return_value = [{"id": 1, "title": "From the table", "url": "u", "notes": "", "saved_at": None}]
    with patch.object(hybrid_search, 'retrieve', return_value=[{"content_id": 1, "passage": "p", "similarity": 0.9}]):
        results = hybrid_search.semantic_search(session, 7, "q", limit=5, rerank=False, query_vector=[0.1] * 384)
    assert results[0]["title"] == "From the table"
    assert session.execute.call_count == 1


def test_ann_settings_work_with_the_scoped_session_the_app_really_uses(tmp_path):
    """uow.session is a scoped_session, which has no get_transaction(): a MagicMock session hid that."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import scoped_session, sessionmaker
    from services.hybrid_search import _real_session
    engine = create_engine(f"sqlite:///{tmp_path / 's.db'}")
    session = scoped_session(sessionmaker(bind=engine))
    try:
        real = _real_session(session)
        assert real.get_transaction() is None            # nothing begun yet
        session.execute(__import__('sqlalchemy').text("SELECT 1"))
        first = real.get_transaction()
        assert first is not None and real.get_transaction() is first   # one transaction, a stable identity
        session.commit()
        session.execute(__import__('sqlalchemy').text("SELECT 1"))
        assert real.get_transaction() is not first         # a new transaction after commit
        real.info["ann_config"] = (first, 60)              # settings remembered for the old transaction ...
        from services.hybrid_search import configure_filtered_ann
        with patch.object(session, 'execute') as run:      # ... do not count for the new one
            configure_filtered_ann(session, 60)
        assert run.call_count == 1
    finally:
        session.remove()
        engine.dispose()
