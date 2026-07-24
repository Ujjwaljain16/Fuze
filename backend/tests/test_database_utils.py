import pytest
from unittest.mock import MagicMock, patch
from utils.database_utils import (
    get_database_connection,
    with_db_session,
    retry_on_connection_error,
    check_database_tables
)


@pytest.mark.unit
def test_get_database_connection_reuses_engine():
    mock_db = MagicMock()
    mock_conn = MagicMock()
    mock_db.engine.connect.return_value = mock_conn

    with patch.dict('sys.modules', {'models': MagicMock(db=mock_db)}):
        conn = get_database_connection()
        assert conn == mock_conn
        mock_db.engine.connect.assert_called_once()


@pytest.mark.unit
def test_with_db_session_preserves_caller_session():
    mock_caller_session = MagicMock()

    @with_db_session
    def sample_func(session=None):
        return session

    # Should preserve caller session if provided
    result = sample_func(session=mock_caller_session)
    assert result == mock_caller_session


@pytest.mark.unit
def test_retry_on_connection_error_success():
    call_count = 0

    @retry_on_connection_error(max_retries=2, delay=0.01)
    def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            from sqlalchemy.exc import OperationalError
            raise OperationalError("Connection lost", None, None)
        return "success"

    result = flaky_func()
    assert result == "success"
    assert call_count == 2
