import pytest
import sentry_sdk

from core import sentry_setup


@pytest.fixture
def fresh(monkeypatch, tmp_path):
    """A process where Sentry was never initialised, with no DSN, SHA or RELEASE file."""
    monkeypatch.setattr(sentry_setup, '_initialized', False)
    monkeypatch.setattr(sentry_setup, 'RELEASE_FILE', str(tmp_path / 'RELEASE'))
    for name in ('SENTRY_DSN', 'GIT_SHA', 'SENTRY_TRACES_SAMPLE_RATE'):
        monkeypatch.delenv(name, raising=False)
    calls = []
    monkeypatch.setattr(sentry_sdk, 'init', lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(sentry_sdk, 'get_global_scope', lambda: sentry_sdk.Scope())  # keep tags out of this process
    return calls


@pytest.mark.unit
def test_not_initialised_without_dsn(fresh):
    assert sentry_setup.init_sentry('web') is False
    assert fresh == []


@pytest.mark.unit
def test_blank_dsn_counts_as_unset(fresh, monkeypatch):
    monkeypatch.setenv('SENTRY_DSN', '   ')
    assert sentry_setup.init_sentry('web') is False
    assert fresh == []


@pytest.mark.unit
def test_app_import_does_not_initialise_sentry():
    # conftest removes SENTRY_DSN, and run_production calls init_sentry at import.
    import run_production  # noqa: F401
    assert not sentry_sdk.get_client().is_active()


@pytest.mark.unit
def test_initialised_with_dsn(fresh, monkeypatch):
    monkeypatch.setenv('SENTRY_DSN', 'https://key@o1.ingest.us.sentry.io/1')
    monkeypatch.setenv('APP_ENV', 'prod')
    monkeypatch.setenv('GIT_SHA', 'abc1234')

    assert sentry_setup.init_sentry('worker') is True

    (options,) = fresh
    assert options['dsn'] == 'https://key@o1.ingest.us.sentry.io/1'
    assert options['environment'] == 'production'  # from app_env(), aliases resolved
    assert options['release'] == 'abc1234'
    assert options['send_default_pii'] is False
    assert options['before_send'] is sentry_setup.scrub_event
    assert options['before_send_transaction'] is sentry_setup.scrub_event
    names = {type(i).__name__ for i in options['integrations']}
    assert names == {'FlaskIntegration', 'RqIntegration', 'SqlalchemyIntegration'}


@pytest.mark.unit
def test_initialises_once_per_process(fresh, monkeypatch):
    monkeypatch.setenv('SENTRY_DSN', 'https://key@o1.ingest.us.sentry.io/1')
    assert sentry_setup.init_sentry('worker') is True
    assert sentry_setup.init_sentry('web') is True
    assert len(fresh) == 1


@pytest.mark.unit
def test_release_falls_back_to_the_deployed_file(fresh):
    assert sentry_setup.release() is None  # neither GIT_SHA nor the file: ignored
    with open(sentry_setup.RELEASE_FILE, 'w', encoding='utf-8') as fh:
        fh.write('0123abc\n')
    assert sentry_setup.release() == '0123abc'


@pytest.mark.unit
def test_git_sha_wins_over_the_file(fresh, monkeypatch):
    with open(sentry_setup.RELEASE_FILE, 'w', encoding='utf-8') as fh:
        fh.write('from-file')
    monkeypatch.setenv('GIT_SHA', 'from-env')
    assert sentry_setup.release() == 'from-env'


@pytest.mark.unit
def test_scrubs_credentials_whatever_the_header_case():
    event = {'request': {
        'headers': {
            'Authorization': 'Bearer secret.jwt',
            'cookie': 'session=abc',
            'X-API-KEY': 'gemini-key',
            'X-Internal-Token': 'internal',
            'Content-Type': 'application/json',
        },
        'cookies': {'session': 'abc'},
    }}

    scrubbed = sentry_setup.scrub_event(event, {})

    headers = scrubbed['request']['headers']
    assert headers['Authorization'] == '[Filtered]'
    assert headers['cookie'] == '[Filtered]'
    assert headers['X-API-KEY'] == '[Filtered]'
    assert headers['X-Internal-Token'] == '[Filtered]'
    assert headers['Content-Type'] == 'application/json'
    assert scrubbed['request']['cookies'] == '[Filtered]'
    assert 'secret.jwt' not in repr(scrubbed)


@pytest.mark.unit
def test_scrubs_headers_sent_as_pairs():
    event = {'request': {'headers': [['Authorization', 'Bearer x'], ['Accept', '*/*']]}}
    headers = sentry_setup.scrub_event(event, {})['request']['headers']
    assert headers == [['Authorization', '[Filtered]'], ['Accept', '*/*']]


@pytest.mark.unit
def test_events_without_request_pass_through():
    event = {'message': 'job failed', 'extra': {'rq-job': {'job_id': '1'}}}
    assert sentry_setup.scrub_event(dict(event), {}) == event


@pytest.mark.unit
def test_scrubbing_runs_in_a_real_client(monkeypatch):
    """End to end through sentry-sdk: what reaches the transport has no credentials."""
    sent = []

    class CaptureTransport(sentry_sdk.transport.Transport):
        def capture_envelope(self, envelope):
            sent.extend(item.payload.json for item in envelope.items if item.payload.json)

    client = sentry_sdk.Client(
        dsn='https://key@o1.ingest.us.sentry.io/1',
        transport=CaptureTransport,
        send_default_pii=False,
        before_send=sentry_setup.scrub_event,
        default_integrations=False,
    )
    with sentry_sdk.new_scope() as scope:
        scope.set_client(client)
        scope.add_event_processor(lambda event, hint: {
            **event, 'request': {'headers': {'Authorization': 'Bearer leaked', 'Cookie': 'sid=1'}},
        })
        sentry_sdk.capture_message('boom')
    client.flush()

    assert sent, 'the event never reached the transport'
    headers = sent[0]['request']['headers']
    assert headers == {'Authorization': '[Filtered]', 'Cookie': '[Filtered]'}
