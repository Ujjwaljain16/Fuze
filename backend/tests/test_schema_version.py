"""Readiness must fail when the database schema is behind the code."""
import pytest
from sqlalchemy import create_engine, text

from core.schema_version import expected_head, schema_status


def test_expected_head_is_the_newest_revision():
    import os
    versions = os.listdir(os.path.join(os.path.dirname(__file__), '..', 'alembic', 'versions'))
    newest = max(f.split('_')[0] for f in versions if f[:4].isdigit())
    assert expected_head() == newest


@pytest.mark.parametrize('applied,up_to_date', [(None, False), ('0001', False), ('HEAD', True)])
def test_schema_status(applied, up_to_date):
    engine = create_engine('sqlite://')
    with engine.connect() as conn:
        conn.execute(text('CREATE TABLE alembic_version (version_num VARCHAR(32))'))
        if applied:
            conn.execute(text('INSERT INTO alembic_version VALUES (:v)'), {'v': expected_head() if applied == 'HEAD' else applied})
        assert schema_status(conn)['up_to_date'] is up_to_date


def test_readiness_reports_outdated_schema(client, app):
    from models import db
    with app.app_context():
        with db.engine.begin() as conn:
            conn.execute(text('CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32))'))
            conn.execute(text('DELETE FROM alembic_version'))
            conn.execute(text("INSERT INTO alembic_version VALUES ('0001')"))
    response = client.get('/health/readiness')
    assert response.status_code == 503
    assert response.json['schema'] == 'outdated'

    with app.app_context():
        with db.engine.begin() as conn:
            conn.execute(text('UPDATE alembic_version SET version_num = :v'), {'v': expected_head()})
    response = client.get('/health/readiness')
    assert response.json['schema'] == 'current'


def test_readiness_reports_round_trip_times_only_when_asked(client, app, patch_redis_for_tests):
    """?timing=1 lets a deployment report how far it is from its database (a region mismatch shows up here)."""
    from models import db
    with app.app_context():
        with db.engine.begin() as conn:
            conn.execute(text('CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32))'))
            conn.execute(text('DELETE FROM alembic_version'))
            conn.execute(text('INSERT INTO alembic_version VALUES (:v)'), {'v': expected_head()})
    plain = client.get('/health/readiness')
    assert 'timing' not in plain.json  # probes are unchanged

    timed = client.get('/health/readiness?timing=1')
    assert timed.status_code == plain.status_code
    assert timed.json['timing']['database_round_trip_ms'] >= 0
    assert set(timed.json['timing']) <= {'database_round_trip_ms', 'redis_round_trip_ms'}
