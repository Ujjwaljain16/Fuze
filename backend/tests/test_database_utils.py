import pytest
from utils.database_utils import retry_on_connection_error


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
