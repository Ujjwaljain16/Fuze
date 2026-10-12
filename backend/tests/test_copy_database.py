"""scripts/copy_database.py moves a whole database exactly: rows, vectors, counters. Postgres lane only."""
import importlib.util
import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

SCRIPT = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'copy_database.py')
# COPY's text format treats these specially: a tab, a newline and a backslash must survive the trip.
TRICKY_NOTE = 'a note with a tab' + chr(9) + 'and a newline' + chr(10) + 'and a backslash ' + chr(92) + ' done'


@pytest.fixture(autouse=True)
def postgres_only(app):
    from models import db
    with app.app_context():
        if db.engine.dialect.name != 'postgresql':
            pytest.skip('needs Postgres (run with TEST_DATABASE_URL=postgresql://...localhost...)')


@pytest.fixture
def copy_script():
    spec = importlib.util.spec_from_file_location('copy_database', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def target_url(app):
    """A second, empty database on the same server, with the schema built the way the app builds it."""
    from models import db
    source_url = make_url(os.environ['DATABASE_URL'])
    name = f"copy_target_{uuid.uuid4().hex[:8]}"
    admin = create_engine(source_url.set(database='postgres'), isolation_level='AUTOCOMMIT')
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    url = source_url.set(database=name)
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS pg_trgm'))
    db.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)'))
        conn.execute(text('DELETE FROM alembic_version'))
        conn.execute(text("INSERT INTO alembic_version VALUES ('copytest')"))
    engine.dispose()
    yield url.render_as_string(hide_password=False)
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    admin.dispose()


def _seed(app, user_id):
    from models import db, SavedContent
    from services.hybrid_search import _vec_literal
    vector = [0.01 * (i % 7) for i in range(384)]
    with app.app_context():
        db.session.execute(text('CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)'))
        db.session.execute(text('DELETE FROM alembic_version'))
        db.session.execute(text("INSERT INTO alembic_version VALUES ('copytest')"))
        rows = [SavedContent(user_id=user_id, url=f'https://copy.example/{i}', title=f'Copy {i} café',
                             notes=TRICKY_NOTE, extracted_text=f'body {i} ' * 20,
                             embedding=vector, embedding_metadata={'model': 'copy-test'}) for i in range(5)]
        db.session.add_all(rows)
        db.session.commit()
        ids = [r.id for r in rows]
        db.session.execute(text(
            "INSERT INTO content_chunks (content_id, user_id, chunk_index, text, embedding, embedding_model) "
            "VALUES (:cid, :uid, 0, 'a passage', CAST(:emb AS vector), 'copy-test')"),
            {'cid': ids[0], 'uid': user_id, 'emb': _vec_literal(vector)})
        db.session.commit()
    return ids


def test_a_database_is_copied_exactly_and_counters_continue_after_it(app, test_user, copy_script, target_url, monkeypatch):
    ids = _seed(app, test_user['id'])
    source_url = os.environ['DATABASE_URL']
    monkeypatch.setattr('sys.argv', ['copy_database.py', '--source', source_url, '--target', target_url])
    copy_script.main()   # exits non-zero (SystemExit) on any mismatch

    src, dst = create_engine(source_url), create_engine(target_url)
    with src.connect() as a, dst.connect() as b:
        for table in ('users', 'saved_content', 'content_chunks'):
            assert b.execute(text(f'SELECT count(*) FROM {table}')).scalar() == a.execute(text(f'SELECT count(*) FROM {table}')).scalar()
        query = ("SELECT title, notes, embedding::text, embedding_metadata::text FROM saved_content "
                 "WHERE id = :i")
        assert b.execute(text(query), {'i': ids[0]}).first() == a.execute(text(query), {'i': ids[0]}).first()  # vectors, JSON, tabs, accents
        chunk = "SELECT text, embedding::text, kind FROM content_chunks WHERE content_id = :i"
        assert b.execute(text(chunk), {'i': ids[0]}).first() == a.execute(text(chunk), {'i': ids[0]}).first()
        # the generated search column was rebuilt by the target, not copied
        assert b.execute(text("SELECT count(*) FROM saved_content WHERE search_vector IS NOT NULL")).scalar() > 0
    with dst.begin() as conn:  # the id counter continues after the copied rows instead of colliding with them
        new_id = conn.execute(text(
            "INSERT INTO saved_content (user_id, url, title) VALUES (:u, 'https://copy.example/new', 'New') RETURNING id"),
            {'u': test_user['id']}).scalar()
    assert new_id > max(ids)
    src.dispose(); dst.dispose()


def test_it_refuses_a_target_that_already_has_data_and_a_different_schema_revision(app, test_user, copy_script, target_url, monkeypatch):
    _seed(app, test_user['id'])
    source_url = os.environ['DATABASE_URL']
    monkeypatch.setattr('sys.argv', ['copy_database.py', '--source', source_url, '--target', target_url])
    copy_script.main()
    with pytest.raises(SystemExit, match='not empty'):   # second run: the target now holds the data
        copy_script.main()
    engine = create_engine(target_url)
    with engine.begin() as conn:
        conn.execute(text("UPDATE alembic_version SET version_num = 'different'"))
    engine.dispose()
    with pytest.raises(SystemExit, match='revisions differ'):
        copy_script.main()


def test_a_dry_run_changes_nothing(app, test_user, copy_script, target_url, monkeypatch, capsys):
    _seed(app, test_user['id'])
    monkeypatch.setattr('sys.argv', ['copy_database.py', '--source', os.environ['DATABASE_URL'], '--target', target_url, '--dry-run'])
    copy_script.main()
    assert 'Dry run' in capsys.readouterr().out
    engine = create_engine(target_url)
    with engine.connect() as conn:
        assert conn.execute(text('SELECT count(*) FROM saved_content')).scalar() == 0
    engine.dispose()
