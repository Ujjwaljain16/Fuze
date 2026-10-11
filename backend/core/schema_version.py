"""Compare the database's applied Alembic revision with the newest revision shipped in this build."""

import os
from functools import lru_cache
from typing import Optional

from sqlalchemy import text

_VERSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'alembic')


@lru_cache(maxsize=1)
def expected_head() -> Optional[str]:
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    cfg = Config()
    cfg.set_main_option('script_location', _VERSIONS_DIR)
    return ScriptDirectory.from_config(cfg).get_current_head()


def applied_revision(connection) -> Optional[str]:
    row = connection.execute(text('SELECT version_num FROM alembic_version')).first()
    return row[0] if row else None


def schema_status(connection) -> dict:
    """{'current': ..., 'expected': ..., 'up_to_date': bool} for the readiness probe."""
    current = applied_revision(connection)
    expected = expected_head()
    return {'current': current, 'expected': expected, 'up_to_date': current == expected}
