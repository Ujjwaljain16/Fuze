"""Text search: ranking, user scoping, special characters, empty queries.

Runs on both lanes. On SQLite it exercises the substring fallback; with TEST_DATABASE_URL
pointing at Postgres it exercises the indexed search (search_vector + title trigrams), and the
postgres-only tests check stemming, websearch syntax and ts_rank_cd ordering.
"""
import uuid
from datetime import datetime, timedelta

import pytest

from services.search_service import SearchService


@pytest.fixture
def other_user(app):
    from models import User, db
    with app.app_context():
        tag = uuid.uuid4().hex[:8]
        user = User(username=f'other_{tag}', email=f'other_{tag}@example.com', password_hash='x')
        db.session.add(user)
        db.session.commit()
        yield {'id': user.id}
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def postgres_only(app):
    from models import db
    with app.app_context():
        if db.engine.dialect.name != 'postgresql':
            pytest.skip('needs Postgres full-text search (set TEST_DATABASE_URL)')


def _save(user_id, title, body='', notes=None, age_days=0):
    from models import SavedContent, db
    item = SavedContent(user_id=user_id, url=f'https://example.com/{uuid.uuid4().hex}', title=title,
                        extracted_text=body or None, notes=notes,
                        saved_at=datetime(2026, 10, 1) - timedelta(days=age_days))
    db.session.add(item)
    db.session.commit()
    return item.id


def _search(query, user_id, limit=10):
    from uow.unit_of_work import UnitOfWork
    with UnitOfWork() as uow:
        return SearchService(uow).text_search(user_id, query, limit)


def _ids(results):
    return [r['id'] for r in results]


def test_title_match_outranks_newer_body_only_match(app, test_user):
    with app.app_context():
        uid = test_user['id']
        body_only = _save(uid, 'Weekly notes', body='We tried kubernetes autoscaling last week.', age_days=0)
        in_title = _save(uid, 'Kubernetes autoscaling guide', body='How the HPA scales pods.', age_days=30)
        _save(uid, 'Unrelated', body='Sourdough starter feeding schedule.')

        results = _search('kubernetes autoscaling', uid)

        assert _ids(results) == [in_title, body_only]
        assert results[0]['title'] == 'Kubernetes autoscaling guide'
        assert results[0]['has_content'] is True


def test_results_never_include_another_users_bookmarks(app, test_user, other_user):
    with app.app_context():
        mine = _save(test_user['id'], 'Postgres GIN indexes', body='GIN indexes for full text search.')
        theirs = _save(other_user['id'], 'Postgres GIN indexes', body='GIN indexes for full text search.')

        assert _ids(_search('GIN indexes', test_user['id'])) == [mine]
        assert _ids(_search('GIN indexes', other_user['id'])) == [theirs]


def test_notes_are_searched(app, test_user):
    with app.app_context():
        item = _save(test_user['id'], 'Untitled page', notes='read before the pgvector migration')
        assert _ids(_search('pgvector', test_user['id'])) == [item]


@pytest.mark.parametrize('query', ['', '   ', None])
def test_empty_query_returns_nothing(app, test_user, query):
    with app.app_context():
        _save(test_user['id'], 'Anything at all', body='some text')
        assert _search(query, test_user['id']) == []


@pytest.mark.parametrize('query', [
    '100%', 'snake_case', '\\', "'; DROP TABLE saved_content; --", '"unterminated phrase',
    'a & b | !c :*', '(((', 'OR', '-', '<->', '%_%',
])
def test_special_characters_never_error_or_act_as_wildcards(app, test_user, query):
    with app.app_context():
        _save(test_user['id'], 'Plain article', body='nothing special here')
        results = _search(query, test_user['id'])
        # None of these appear in the bookmark, and LIKE wildcards are escaped.
        assert results == []


def test_like_wildcards_match_literally(app, test_user):
    with app.app_context():
        uid = test_user['id']
        literal = _save(uid, 'Reach 100% test coverage', body='coverage tips')
        _save(uid, 'Reach 1000 users', body='growth tips')
        assert _ids(_search('100%', uid)) == [literal]


def test_symbol_queries_match_titles(app, test_user):
    with app.app_context():
        uid = test_user['id']
        item = _save(uid, 'Modern C++ move semantics', body='rvalue references explained')
        _save(uid, 'C programming basics', body='pointers and arrays')
        assert _search('C++', uid)[0]['id'] == item


def test_limit_is_respected(app, test_user):
    with app.app_context():
        for i in range(5):
            _save(test_user['id'], f'Redis note {i}', body='redis streams', age_days=i)
        assert len(_search('redis', test_user['id'], limit=3)) == 3


# --------------------------------------------------------------------------- Postgres only

def test_words_match_by_stem_in_any_order(app, test_user, postgres_only):
    with app.app_context():
        uid = test_user['id']
        item = _save(uid, 'Benchmarks', body='The indexes were rebuilt while queries kept running.')
        assert _ids(_search('run query index', uid)) == [item]


def test_partial_title_words_match_through_trigrams(app, test_user, postgres_only):
    with app.app_context():
        uid = test_user['id']
        item = _save(uid, 'Kubernetes networking deep dive', body='CNI plugins')
        assert _ids(_search('kubern', uid)) == [item]


def test_websearch_syntax_phrase_and_exclusion(app, test_user, postgres_only):
    with app.app_context():
        uid = test_user['id']
        phrase = _save(uid, 'Notes A', body='Use connection pooling for Postgres.')
        scattered = _save(uid, 'Notes B', body='Pooling of threads. A new connection per request.')
        assert _ids(_search('"connection pooling"', uid)) == [phrase]
        assert _ids(_search('pooling -threads', uid)) == [phrase]
        assert set(_ids(_search('pooling', uid))) == {phrase, scattered}


def test_rank_prefers_documents_where_terms_appear_together(app, test_user, postgres_only):
    with app.app_context():
        uid = test_user['id']
        filler = ' '.join(['lorem ipsum dolor'] * 60)
        far_apart = _save(uid, 'Doc one', body=f'vector {filler} quantization', age_days=0)
        together = _save(uid, 'Doc two', body=f'{filler} vector quantization reduces memory. '
                                              f'Product vector quantization {filler}', age_days=10)
        assert _ids(_search('vector quantization', uid)) == [together, far_apart]


def test_stop_word_only_query_does_not_error(app, test_user, postgres_only):
    with app.app_context():
        uid = test_user['id']
        _save(uid, 'Something', body='content')
        assert _search('the of', uid) == []
        # Too short for title substrings, but still a word match.
        item = _save(uid, 'Go generics', body='type parameters')
        assert _ids(_search('go', uid)) == [item]
