import pytest
import socket
import os
from worker import ALLOWED_QUEUES


@pytest.mark.unit
def test_allowed_queues():
    assert 'default' in ALLOWED_QUEUES
    assert 'high' in ALLOWED_QUEUES
    assert 'background_analysis' in ALLOWED_QUEUES
    assert 'invalid_queue' not in ALLOWED_QUEUES


@pytest.mark.unit
def test_worker_unique_name_formatting():
    hostname = socket.gethostname()
    pid = os.getpid()
    queue = 'default'
    worker_index = 1
    worker_name = f"fuze-worker-{queue}-{hostname}-{pid}-{worker_index}"

    assert hostname in worker_name
    assert str(pid) in worker_name
    assert queue in worker_name
