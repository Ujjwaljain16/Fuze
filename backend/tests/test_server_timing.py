"""X-Server-Timing: 1 returns where a request's time went; ordinary requests see nothing."""
import re
from unittest.mock import patch

import numpy as np

from core.server_timing import header_value


def _durations(header):
    return {name: float(value) for name, value in re.findall(r'(\w+);dur=([\d.]+)', header)}


def test_header_value_format():
    value = header_value({'embed': 640.2, 'db': 1083.5, 'db_statements': 5}, 2154.0)
    assert value == 'total;dur=2154.0, embed;dur=640.2, db;dur=1083.5, dbn;desc="5 statements"'
    assert header_value({}, 3.14159) == 'total;dur=3.1'   # nothing else recorded: just the total


def test_no_header_unless_the_request_asks_for_it(client, auth_headers):
    assert 'Server-Timing' not in client.get('/api/search/text?q=docker', headers=auth_headers).headers
    other = client.get('/api/search/text?q=docker', headers={**auth_headers, 'X-Server-Timing': '0'})
    assert 'Server-Timing' not in other.headers


def test_a_keyword_search_reports_total_and_database_time(client, auth_headers):
    response = client.get('/api/search/text?q=docker', headers={**auth_headers, 'X-Server-Timing': '1'})
    assert response.status_code == 200
    timing = _durations(response.headers['Server-Timing'])
    assert 'db' in timing and timing['total'] >= timing['db'] >= 0   # a local SQLite query can round to 0.0 ms
    assert 'statements' in response.headers['Server-Timing']


def test_a_semantic_search_also_reports_the_embedding_time(client, auth_headers):
    with patch('services.search_service.embed_query', return_value=np.ones(384, dtype=np.float32)):
        response = client.post('/api/search/semantic', json={'query': 'docker containers'},
                               headers={**auth_headers, 'X-Server-Timing': '1'})
    assert response.status_code == 200, response.get_json()
    timing = _durations(response.headers['Server-Timing'])
    assert timing['total'] >= timing['embed'] >= 0
    assert 'embed' in timing and 'db' in timing
