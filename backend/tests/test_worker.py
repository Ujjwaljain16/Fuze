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


POOL_VARS = ('FUZE_PROCESS_ROLE', 'DB_POOL_SIZE', 'DB_MAX_OVERFLOW', 'DB_WORKER_POOL_SIZE', 'DB_WORKER_MAX_OVERFLOW')


@pytest.fixture
def clean_pool_env(monkeypatch):
    for name in POOL_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.mark.unit
def test_worker_role_gets_the_small_pool(clean_pool_env):
    from utils.unified_config import DatabaseConfig
    clean_pool_env.setenv('FUZE_PROCESS_ROLE', 'worker')
    # The web settings (often set in .env) must not size worker pools.
    clean_pool_env.setenv('DB_POOL_SIZE', '5')
    clean_pool_env.setenv('DB_MAX_OVERFLOW', '10')
    cfg = DatabaseConfig()
    assert (cfg.pool_size, cfg.max_overflow) == (2, 1)

    clean_pool_env.setenv('DB_WORKER_POOL_SIZE', '3')
    clean_pool_env.setenv('DB_WORKER_MAX_OVERFLOW', '0')
    cfg = DatabaseConfig()
    assert (cfg.pool_size, cfg.max_overflow) == (3, 0)


@pytest.mark.unit
@pytest.mark.parametrize('role', [None, 'web', 'something-else'])
def test_web_role_is_the_default_pool(clean_pool_env, role):
    from utils.unified_config import DatabaseConfig
    if role:
        clean_pool_env.setenv('FUZE_PROCESS_ROLE', role)
    cfg = DatabaseConfig()
    assert (cfg.pool_size, cfg.max_overflow) == (5, 5)

    clean_pool_env.setenv('DB_POOL_SIZE', '4')
    clean_pool_env.setenv('DB_MAX_OVERFLOW', '2')
    cfg = DatabaseConfig()
    assert (cfg.pool_size, cfg.max_overflow) == (4, 2)


@pytest.mark.unit
def test_worker_entry_point_marks_the_process_as_a_worker(clean_pool_env):
    """worker.main() must set the role before its first import builds the configuration."""
    from unittest.mock import patch
    import worker
    seen = {}

    def fake_run(args, index):
        from utils.unified_config import process_role
        seen['role'] = process_role()

    with patch.dict(os.environ), patch.object(worker, 'run_single_worker', fake_run), \
            patch('sys.argv', ['worker.py', '--queue', 'default']):
        worker.main()
    assert seen['role'] == 'worker'
    assert 'FUZE_PROCESS_ROLE' not in os.environ  # not leaked into the rest of the suite
