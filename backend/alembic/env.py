import logging
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import text

from alembic import context

logger = logging.getLogger(__name__)

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from models import db

target_metadata = db.metadata

def get_url():
    """Retrieve database URL from application config"""
    from utils.unified_config import get_config
    app_config = get_config()
    return app_config.database.url

# Set dynamic URL
config.set_main_option("sqlalchemy.url", get_url())

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def include_object(object, name, type_, reflected, compare_to):
    """Ignore raw PostgreSQL HNSW vector indexes during autogenerate and drift check."""
    if type_ == "index" and name and "hnsw" in name:
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Run the whole migration chain on an AUTOCOMMIT connection (every
        # statement commits immediately, rather than one transaction wrapping
        # each migration file).
        #
        # Why: migration 0003 uses op.get_context().autocommit_block() for
        # CREATE INDEX CONCURRENTLY (which Postgres refuses to run inside a
        # transaction block). Discovered by actually running this chain
        # against a fresh Postgres instance for the first time this session:
        # under Alembic's default transactional mode (and even with
        # transaction_per_migration=True, which docs suggest but which hit a
        # separate `assert self._transaction is not None` failure inside
        # autocommit_block() with this Alembic/SQLAlchemy version combo),
        # autocommit_block()'s internal transaction bookkeeping doesn't line
        # up. Existing production databases were never affected only because
        # they already applied 0003 years ago -- but any NEW environment
        # (disaster recovery, a fresh clone, CI) would hit this AssertionError
        # and fail to migrate past 0003.
        #
        # This is safe here specifically because every migration in this
        # chain is already written to be idempotent (IF NOT EXISTS / additive
        # ALTER TABLE), so losing cross-statement atomicity within a single
        # migration file isn't a new risk -- it's what these migrations were
        # already designed to tolerate.
        connection = connection.execution_options(isolation_level="AUTOCOMMIT")

        # Prevent catalog reflection statement timeouts on remote PostgreSQL instances.
        # (Previously used the undefined name `sa` here -- raised NameError on every
        # single migration run, silently swallowed by the bare except below, so this
        # protection had never actually applied. Also harmless-but-expected to fail
        # on non-Postgres dialects, e.g. SQLite in tests -- hence still catching and
        # logging rather than letting it abort the migration.)
        try:
            connection.execute(text("SET statement_timeout = 0;"))
            # SQLAlchemy 2.0 "autobegin": the execute() above silently starts
            # a logical transaction on this Connection (tracked by SQLAlchemy
            # itself, independent of the AUTOCOMMIT isolation level set
            # above). Alembic's autocommit_block() (used by migration 0003)
            # checks connection.in_transaction() and, seeing True with no
            # transaction object of ITS OWN on record, raises
            # `AssertionError: assert self._transaction is not None`. Closing
            # this out resets in_transaction() to False before Alembic's own
            # machinery takes over.
            connection.commit()
        except Exception as e:
            logger.warning(f"Could not disable statement_timeout for migration: {e}")

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
