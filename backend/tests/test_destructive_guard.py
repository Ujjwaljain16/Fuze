"""Destructive scripts refuse to run against a remote or production database unless the operator types its host."""
import pytest

from core.destructive_guard import check_target, configured_database_url, database_host, require_safe_target

REMOTE = 'postgresql://postgres:s3cret-pw@db.abcd.supabase.co:6543/postgres?sslmode=require'
LOCAL = 'postgresql://postgres:s3cret-pw@localhost:5432/fuze'


@pytest.fixture
def env(monkeypatch):
    def set_env(value):
        for name in ('APP_ENV', 'ENVIRONMENT', 'FLASK_ENV'):
            monkeypatch.delenv(name, raising=False)
        if value is not None:
            monkeypatch.setenv('APP_ENV', value)
    return set_env


@pytest.mark.parametrize('url', [
    LOCAL,
    'postgresql://postgres:x@127.0.0.1:55432/fz',
    'postgresql://postgres:x@[::1]:5432/fz',
    'postgresql:///fuze',
    'sqlite:///:memory:',
    'sqlite:///instance/dev.db',
])
def test_local_database_in_development_is_allowed(env, url):
    env('development')
    assert require_safe_target(url, argv=[]) is not None


def test_local_database_in_testing_is_allowed(env):
    env('testing')
    assert check_target(LOCAL, [])[0]


def test_remote_host_is_refused(env, capsys):
    env('development')
    with pytest.raises(SystemExit) as exc:
        require_safe_target(REMOTE, argv=[])
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert 'REFUSED' in err
    assert '--i-know=db.abcd.supabase.co' in err
    assert 's3cret-pw' not in err


def test_remote_host_with_correct_confirmation_is_allowed(env, capsys):
    env('development')
    assert require_safe_target(REMOTE, argv=['--limit', '5', '--i-know=db.abcd.supabase.co']) == 'db.abcd.supabase.co'
    assert check_target(REMOTE, ['--i-know', 'DB.ABCD.SUPABASE.CO'])[0]
    assert 's3cret-pw' not in capsys.readouterr().err


@pytest.mark.parametrize('typed', ['localhost', 'db.other.supabase.co', 'supabase.co', ''])
def test_wrong_host_typed_is_refused(env, capsys, typed):
    env('development')
    with pytest.raises(SystemExit) as exc:
        require_safe_target(REMOTE, argv=[f'--i-know={typed}'])
    assert exc.value.code != 0
    assert 's3cret-pw' not in capsys.readouterr().err


def test_production_with_local_url_is_refused_without_confirmation(env):
    env('production')
    with pytest.raises(SystemExit):
        require_safe_target(LOCAL, argv=[])
    assert require_safe_target(LOCAL, argv=['--i-know=localhost']) == 'localhost'


def test_unset_environment_counts_as_production(env):
    env(None)
    assert not check_target('sqlite:///:memory:', [])[0]
    assert check_target('sqlite:///:memory:', ['--i-know=sqlite'])[0]


def test_empty_or_garbage_url_is_refused_even_with_confirmation(env):
    env('development')
    assert not check_target('', ['--i-know=localhost'])[0]
    assert not check_target('not a url', ['--i-know=localhost'])[0]


def test_socket_host_query_parameter_is_respected():
    assert database_host('postgresql:///fuze?host=/var/run/postgresql') == ('localhost', True)
    assert database_host('postgresql:///fuze?host=db.example.com') == ('db.example.com', False)


def test_configured_url_follows_create_app(env, monkeypatch):
    monkeypatch.setenv('DATABASE_URL', REMOTE)
    monkeypatch.setenv('TEST_DATABASE_URL', LOCAL)
    env('development')
    assert configured_database_url() == REMOTE
    env('testing')
    assert configured_database_url() == LOCAL
