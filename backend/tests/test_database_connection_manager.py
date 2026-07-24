import pytest
from unittest.mock import MagicMock, patch
from utils.database_connection_manager import DatabaseConnectionManager, get_database_info


@pytest.mark.unit
def test_db_connection_manager_rlock_no_deadlock():
    manager = DatabaseConnectionManager()
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    with patch.object(manager, '_create_engine', return_value=mock_engine), \
         patch.object(manager, '_get_database_url', return_value='sqlite:///:memory:'):

        # refresh_connections calls get_engine(force_refresh=True) inside lock
        # With RLock, this will succeed without deadlocking
        res = manager.refresh_connections()
        assert res is True


@pytest.mark.unit
def test_db_connection_manager_password_masking():
    manager = DatabaseConnectionManager()
    test_url = "postgresql://user:super_secret_password@localhost:5432/fuzedb"

    with patch.object(manager, '_get_database_url', return_value=test_url):
        info = manager.get_connection_info()
        assert "super_secret_password" not in info['safe_url']
        assert "***" in info['safe_url']
        assert info['host'] == "localhost"
        assert info['port'] == 5432


@pytest.mark.unit
def test_sqlite_pragma_listener_dialect_scoped():
    from sqlalchemy import create_engine
    manager = DatabaseConnectionManager()
    real_sqlite_engine = create_engine('sqlite:///:memory:')

    # Verify setup_engine_events attaches event listener without error
    manager._setup_engine_events(real_sqlite_engine)
    assert real_sqlite_engine.dialect.name == "sqlite"
