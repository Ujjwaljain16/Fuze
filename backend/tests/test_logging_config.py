import pytest
import structlog
from core.logging_config import (
    configure_logging,
    get_logger,
    bind_request_context,
    clear_request_context,
    add_correlation_id,
    add_service_info,
    add_runtime_info,
)


def test_logging_configuration():
    configure_logging(debug=True, force=True)
    logger = get_logger("test_module")
    assert logger is not None


def test_processors():
    event_dict = {}
    
    # Test service info processor
    event_dict = add_service_info(None, "info", event_dict)
    assert "service" in event_dict
    assert "environment" in event_dict

    # Test runtime info processor
    event_dict = add_runtime_info(None, "info", event_dict)
    assert "pid" in event_dict
    assert "hostname" in event_dict

    # Test correlation ID processor
    cid = bind_request_context(correlation_id="test-corr-123", path="/api/test")
    assert cid == "test-corr-123"

    event_dict = add_correlation_id(None, "info", event_dict)
    assert event_dict.get("correlation_id") == "test-corr-123"

    clear_request_context()
