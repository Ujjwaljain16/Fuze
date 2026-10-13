"""Fewer database round trips per search, without ever changing what a search returns."""
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from services import hybrid_search
from services.hybrid_search import configure_filtered_ann, retrieve_with_unchunked


def _session(defaults):
    """A session whose connection reports `defaults` as what the database gave it at connect time."""
    session = MagicMock()
    session.info = {}
    session.get_transaction.return_value = object()
    session.connection.return_value.connection.info = {"ann_defaults": defaults}
    return session


@pytest.mark.unit
@pytest.mark.parametrize("defaults, k, sends", [
    (("relaxed_order", 60), 60, False),    # the database defaults already cover it: no round trip
    (("relaxed_order", 60), 10, False),    # a smaller ef_search is covered too
    (("relaxed_order", 60), 100, True),    # a bigger one is not: set it for this transaction
    (("strict_order", 60), 60, True),      # the wrong scan mode: set it
    (("off", 60), 60, True),
    (None, 60, True),                      # a database without the migration, or a failed check
])
def test_the_settings_statement_is_skipped_only_when_the_connection_already_has_them(defaults, k, sends):
    session = _session(defaults)
    configure_filtered_ann(session, k)
    assert (session.execute.call_count == 1) is sends


@pytest.mark.unit
def test_anything_unexpected_about_the_connection_falls_back_to_sending_the_settings():
    session = MagicMock()                  # a bare mock: .info.get() would return a truthy MagicMock
    session.info = {}
    session.get_transaction.return_value = object()
    configure_filtered_ann(session, 60)
    assert session.execute.call_count == 1

    broken = _session(("relaxed_order", 60))
    broken.connection.side_effect = RuntimeError("no connection")
    configure_filtered_ann(broken, 60)
    assert broken.execute.call_count == 1  # never wrong, only slower


def _row(src, id, similarity, **extra):
    base = {"src": src, "id": id, "passage": None if src == "d" else f"passage {id}", "similarity": similarity,
            "title": f"T{id}", "url": f"https://e.com/{id}", "notes": "", "saved_at": None, "has_content": True}
    return {**base, **extra}


@pytest.mark.unit
def test_one_statement_returns_passages_and_unchunked_documents_in_the_shapes_callers_expect():
    session = _session(("relaxed_order", 60))
    session.execute.return_value.mappings.return_value = [
        _row("p", 1, 0.70), _row("p", 1, 0.90, passage="the better passage"),   # two passages of one bookmark
        _row("p", 2, 0.80), _row("d", 9, 0.40), _row("d", 8, 0.60)]
    with patch.object(hybrid_search, "active_embedding_model_name", return_value="m"):
        passages, documents = retrieve_with_unchunked(session, 7, np.ones(384, dtype=np.float32), doc_limit=10)
    assert session.execute.call_count == 1                       # the whole search retrieval: one statement
    assert [p["content_id"] for p in passages] == [1, 2]          # one entry per bookmark, best first
    assert passages[0]["passage"] == "the better passage" and passages[0]["title"] == "T1"
    assert [d["id"] for d in documents] == [8, 9]                 # unchunked documents, best first
    assert set(documents[0]) == {"id", "title", "url", "notes", "saved_at", "has_content", "similarity"}


@pytest.mark.unit
def test_the_combined_statement_keeps_each_branch_hnsw_friendly_and_tenant_scoped():
    sql = hybrid_search._COMBINED_SQL
    assert sql.count("ORDER BY c.embedding <=>") == 1 and sql.count("ORDER BY s.embedding <=>") == 1
    assert sql.count("LIMIT :k") == 1 and sql.count("LIMIT :doc_limit") == 1   # each branch is LIMITed
    assert sql.count("user_id = :uid") == 3    # passages, their bookmark join, and the unchunked branch
    assert "NOT EXISTS" in sql                  # only bookmarks without chunks come back from the document branch


@pytest.mark.unit
def test_a_search_makes_one_retrieval_statement_unless_reranking():
    from services.search_service import SearchService
    uow = MagicMock()
    uow.session.get_bind.return_value.dialect.name = "postgresql"
    service = SearchService(uow)
    candidates = [{"content_id": 1, "passage": "p", "similarity": 0.9, "id": 1, "title": "T", "url": "u",
                   "notes": "", "saved_at": None}]
    with patch("services.search_service.embed_query", return_value=np.ones(384, dtype=np.float32)), \
         patch("services.hybrid_search.rerank_enabled", return_value=False), \
         patch("services.hybrid_search.retrieve_with_unchunked", return_value=(candidates, [])) as combined, \
         patch.object(SearchService, "_document_hits") as separate:
        result = service.supabase_semantic_search(7, "docker", limit=5)
    assert combined.call_count == 1
    separate.assert_not_called()          # the second statement is gone
    assert result["results"][0]["id"] == 1

    with patch("services.search_service.embed_query", return_value=np.ones(384, dtype=np.float32)), \
         patch("services.hybrid_search.rerank_enabled", return_value=True), \
         patch("services.hybrid_search.retrieve_with_unchunked") as combined, \
         patch("services.hybrid_search.semantic_search", return_value=[]), \
         patch.object(SearchService, "_document_hits", return_value=[]) as separate:
        service.supabase_semantic_search(7, "docker", limit=5)
    combined.assert_not_called()          # reranking keeps the original two-step path
    separate.assert_called_once()


@pytest.fixture
def postgres_only(app):
    from models import db
    with app.app_context():
        if db.engine.dialect.name != 'postgresql':
            pytest.skip('needs Postgres (run with TEST_DATABASE_URL=postgresql://...localhost...)')


def _statements_of_one_search(app, user_id):
    """The SQL a real semantic search sends, counted at the driver."""
    from sqlalchemy import event
    from models import db
    from uow.unit_of_work import UnitOfWork
    from services.search_service import SearchService
    sent = []

    def record(conn, cursor, statement, parameters, context, executemany):
        sent.append(' '.join(statement.split()))
    with app.app_context():
        event.listen(db.engine, 'before_cursor_execute', record)
        try:
            with patch('services.search_service.embed_query', return_value=np.ones(384, dtype=np.float32)), \
                 patch('services.search_service.active_embedding_model_name', return_value='m'), \
                 patch('services.hybrid_search.active_embedding_model_name', return_value='m'), \
                 patch('services.hybrid_search.rerank_enabled', return_value=False), \
                 UnitOfWork() as uow:
                SearchService(uow).supabase_semantic_search(user_id, 'anything', limit=10)
        finally:
            event.remove(db.engine, 'before_cursor_execute', record)
    return sent


def _set_database_defaults(app, enabled):
    from sqlalchemy import text
    from models import db
    with app.app_context():
        name = db.session.execute(text('SELECT current_database()')).scalar()
        db.session.commit()
        with db.engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
            if enabled:
                conn.execute(text(f'ALTER DATABASE "{name}" SET hnsw.iterative_scan = \'relaxed_order\''))
                conn.execute(text(f'ALTER DATABASE "{name}" SET hnsw.ef_search = \'60\''))
            else:
                conn.execute(text(f'ALTER DATABASE "{name}" RESET hnsw.iterative_scan'))
                conn.execute(text(f'ALTER DATABASE "{name}" RESET hnsw.ef_search'))
        db.engine.dispose()   # new connections pick the defaults up (and record them) at connect time


def test_a_real_search_sends_one_statement_when_the_database_has_the_defaults(app, test_user, postgres_only):
    _set_database_defaults(app, True)
    try:
        sent = _statements_of_one_search(app, test_user['id'])
    finally:
        _set_database_defaults(app, False)
    assert len(sent) == 1 and sent[0].startswith("SELECT 'p' AS src"), sent   # was 3 statements, then 2


def test_without_the_defaults_a_real_search_still_works_with_one_extra_statement(app, test_user, postgres_only):
    _set_database_defaults(app, False)
    sent = _statements_of_one_search(app, test_user['id'])
    assert len(sent) == 2 and 'set_config' in sent[0] and sent[1].startswith("SELECT 'p' AS src"), sent
