"""Page content captured by the browser extension and sent with the save."""
import uuid
from unittest.mock import patch

import pytest

from services.captured_content import (
    MAX_CAPTURED_HTML_BYTES, MAX_CAPTURED_TEXT_BYTES, CaptureRejected, CapturedPage,
    build_captured_document, clean_captured_text, parse_captured,
)

ARTICLE_WORDS = ' '.join(f'word{i}' for i in range(300))


def _url():
    return f'https://example.com/members/{uuid.uuid4().hex}'


# --- validation and sanitizing ---------------------------------------------------------------

def test_absent_capture_is_none():
    assert parse_captured(None) is None


@pytest.mark.parametrize('raw', ['text', ['text'], {'text': 5}, {'text': 'x', 'html': 7}])
def test_malformed_capture_is_a_400(raw):
    with pytest.raises(CaptureRejected) as err:
        parse_captured(raw)
    assert err.value.status == 400


def test_empty_capture_is_a_400():
    with pytest.raises(CaptureRejected) as err:
        parse_captured({'text': '  \n\t '})
    assert err.value.status == 400


def test_oversized_text_is_a_413():
    with pytest.raises(CaptureRejected) as err:
        parse_captured({'text': 'a' * (MAX_CAPTURED_TEXT_BYTES + 1)})
    assert err.value.status == 413


def test_text_limit_counts_bytes_not_characters():
    # 3 bytes per character in UTF-8: under the limit in characters, over it in bytes.
    with pytest.raises(CaptureRejected) as err:
        parse_captured({'text': '€' * (MAX_CAPTURED_TEXT_BYTES // 3 + 1)})
    assert err.value.status == 413


def test_oversized_html_is_a_413():
    with pytest.raises(CaptureRejected) as err:
        parse_captured({'text': 'ok', 'html': '<p>' + 'a' * MAX_CAPTURED_HTML_BYTES + '</p>'})
    assert err.value.status == 413


def test_text_is_stripped_of_control_characters_and_tidied():
    raw = 'Title\r\n\r\n\r\n\r\nFirst\x00 line\x07 with   spaces\t\tand tabs ​\nSecond line  '
    assert clean_captured_text(raw) == 'Title\n\nFirst line with spaces and tabs\nSecond line'


def test_canonical_url_and_lang_are_validated():
    page = parse_captured({'text': 'hello', 'canonical_url': 'javascript:alert(1)', 'lang': 'en"><script>'})
    assert page.canonical_url is None and page.lang is None

    page = parse_captured({'text': 'hello', 'canonical_url': 'https://example.com/a?b=C', 'lang': 'pt_BR'})
    assert page.canonical_url == 'https://example.com/a?b=C'
    assert page.lang == 'pt-BR'

    assert parse_captured({'text': 'hello', 'lang': 'zh-Hans-CN-x-private'}).lang == 'zh'


# --- building the document without the network -----------------------------------------------

def test_text_only_capture_becomes_the_document_body():
    doc = build_captured_document('https://example.com/a', CapturedPage(text=ARTICLE_WORDS, lang='en'), 'A title')
    assert doc.markdown_content == ARTICLE_WORDS
    assert doc.fetch_metadata.strategy == 'EXTENSION'
    assert doc.metadata.title == 'A title'
    assert doc.metadata.language == 'en'
    assert doc.provider_raw_payload['capture']['source'] == 'extension'


def test_html_capture_runs_the_extractor_and_drops_scripts():
    paragraphs = [f'Paragraph {i} {ARTICLE_WORDS[:200]}' for i in range(5)]
    html = ('<html><head><title>Members post</title><script>steal()</script></head><body><article><h1>Members post</h1>'
            + ''.join(f'<p>{p}</p>' for p in paragraphs)
            + '</article><script>alert("x")</script></body></html>')
    text = 'Members post\n' + '\n'.join(paragraphs)
    doc = build_captured_document('https://example.com/a', CapturedPage(text=text, html=html), '')
    assert 'Paragraph 3' in doc.markdown_content
    assert 'steal()' not in doc.markdown_content and 'alert(' not in doc.markdown_content
    assert doc.metadata.title == 'Members post'


def test_html_that_lost_the_text_falls_back_to_the_rendered_text():
    # A script-built page: the HTML shell has almost nothing, the rendered text has the article.
    doc = build_captured_document('https://example.com/app', CapturedPage(text=ARTICLE_WORDS, html='<div id="root"></div>'), 'App')
    assert doc.markdown_content == ARTICLE_WORDS


# --- the save routes ---------------------------------------------------------------------------

@pytest.fixture
def no_queue():
    with patch('blueprints.bookmarks.process_bookmark_content_async') as fetch, \
         patch('services.pipeline_orchestrator.PipelineOrchestrator.request_embedding', return_value=True) as embed:
        yield fetch, embed


def _bookmark(app, bookmark_id):
    from models import db, SavedContent
    with app.app_context():
        bm = db.session.get(SavedContent, bookmark_id)
        db.session.expunge(bm)
        return bm


@pytest.mark.parametrize('route', ['/api/bookmarks', '/api/bookmarks/quick-save'])
def test_save_with_captured_text_skips_the_fetch_and_embeds(app, client, auth_headers, no_queue, route):
    from scrapers.models import compute_content_hash
    fetch, embed = no_queue
    text = 'DROP TABLE users; -- is how the tutorial starts.\n' + ARTICLE_WORDS
    resp = client.post(route, headers=auth_headers, json={
        'url': _url(), 'title': 'Paywalled article',
        'captured': {'text': text, 'canonical_url': 'https://example.com/canonical', 'lang': 'en'},
    })
    assert resp.status_code == 201, resp.get_json()
    assert resp.json['contentCaptured'] is True

    bm = _bookmark(app, resp.json['bookmark']['id'])
    assert bm.extracted_text == text
    assert bm.scrape_status == 'SUCCESS'
    assert bm.strategy_used == 'EXTENSION'
    assert bm.content_hash == compute_content_hash(text)
    assert bm.language == 'en'
    fetch.assert_not_called()
    embed.assert_called_once_with(bm.id, bm.user_id)


def test_save_with_captured_html_stores_sanitized_text(app, client, auth_headers, no_queue):
    html = ('<html><body><article><h1>Inside</h1>'
            + ''.join(f'<p onclick="x()">Para {i} {ARTICLE_WORDS[:300]}</p>' for i in range(4))
            + '<script>document.cookie</script></article></body></html>')
    resp = client.post('/api/bookmarks', headers=auth_headers, json={
        'url': _url(), 'title': 'Inside', 'captured': {'text': 'Inside ' + ARTICLE_WORDS[:1200], 'html': html},
    })
    assert resp.status_code == 201, resp.get_json()
    bm = _bookmark(app, resp.json['bookmark']['id'])
    assert 'Para 2' in bm.extracted_text
    assert 'document.cookie' not in bm.extracted_text and '<script' not in bm.extracted_text
    assert 'onclick' not in bm.extracted_text


@pytest.mark.parametrize('route', ['/api/bookmarks', '/api/bookmarks/quick-save'])
def test_oversized_capture_is_refused_and_nothing_is_saved(app, client, auth_headers, no_queue, route):
    from models import SavedContent
    url = _url()
    resp = client.post(route, headers=auth_headers, json={
        'url': url, 'title': 'Big', 'captured': {'text': 'a' * (MAX_CAPTURED_TEXT_BYTES + 10)},
    })
    assert resp.status_code == 413
    assert resp.json['error'] == 'invalid_capture'
    with app.app_context():
        assert SavedContent.query.filter_by(url=url).first() is None


def test_malformed_capture_is_a_400_on_the_route(client, auth_headers, no_queue):
    resp = client.post('/api/bookmarks', headers=auth_headers, json={'url': _url(), 'captured': 'not an object'})
    assert resp.status_code == 400


def test_save_without_capture_still_queues_the_fetch(app, client, auth_headers, no_queue):
    fetch, embed = no_queue
    resp = client.post('/api/bookmarks', headers=auth_headers, json={'url': _url(), 'title': 'Plain'})
    assert resp.status_code == 201
    assert resp.json['contentCaptured'] is False
    fetch.assert_called_once()
    embed.assert_not_called()


def test_recapture_does_not_replace_clearly_better_stored_text(app, client, auth_headers, test_user, no_queue):
    from models import db, SavedContent
    url = _url()
    long_text = ' '.join(['server'] * 1000)
    with app.app_context():
        bm = SavedContent(user_id=test_user['id'], url=url, title='Saved', extracted_text=long_text,
                          strategy_used='HTTP', scrape_status='SUCCESS')
        db.session.add(bm)
        db.session.commit()
        bookmark_id = bm.id

    resp = client.post('/api/bookmarks', headers=auth_headers, json={
        'url': url, 'title': 'Saved', 'captured': {'text': 'Just a teaser paragraph before the login wall.'},
    })
    assert resp.status_code == 200
    assert resp.json['contentCaptured'] is False
    assert _bookmark(app, bookmark_id).extracted_text == long_text
