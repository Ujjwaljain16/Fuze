"""One user must never see another user's data through any endpoint."""
import re
import uuid
from unittest.mock import patch
from urllib.parse import quote

import pytest
from flask_jwt_extended import create_access_token


@pytest.fixture
def other_user(app):
    from models import db, User
    from blueprints.auth import hash_password
    with app.app_context():
        tag = uuid.uuid4().hex[:8]
        user = User(username=f'victim_{tag}', email=f'victim_{tag}@example.com', password_hash=hash_password('pw123456'))
        db.session.add(user)
        db.session.commit()
        yield {'id': user.id}
        db.session.delete(user)
        db.session.commit()


def test_feedback_cannot_reference_another_users_project(client, app, test_user, other_user):
    from models import db, Project, SavedContent, UserFeedback
    with app.app_context():
        victim_project = Project(user_id=other_user['id'], title='Secret launch', description='Unreleased plans',
                                 technologies='internal-stack')
        own_bookmark = SavedContent(user_id=test_user['id'], url='https://example.com/a', title='A')
        db.session.add_all([victim_project, own_bookmark])
        db.session.commit()
        project_id, bookmark_id = victim_project.id, own_bookmark.id
        headers = {'Authorization': f"Bearer {create_access_token(identity=str(test_user['id']))}"}

    response = client.post('/api/recommendations/feedback', headers=headers, json={
        'recommendation_id': bookmark_id, 'feedback_type': 'positive',
        'feedback_data': {'project_id': project_id, 'source': 'recommendations_page', 'nested': {'x': 1}},
    })
    assert response.status_code == 200

    with app.app_context():
        stored = db.session.get(UserFeedback, response.json['feedback_id']).context_data
    assert stored == {'source': 'recommendations_page'}

    response = client.get('/api/recommendations/suggested-contexts', headers=headers)
    assert 'Secret launch' not in response.get_data(as_text=True)


def test_suggested_contexts_ignore_foreign_project_ids_already_stored(client, app, test_user, other_user):
    """Rows written before the write-side check must not leak either."""
    from models import db, Project, SavedContent, UserFeedback
    with app.app_context():
        victim_project = Project(user_id=other_user['id'], title='Secret launch')
        own_bookmark = SavedContent(user_id=test_user['id'], url='https://example.com/b', title='B')
        db.session.add_all([victim_project, own_bookmark])
        db.session.commit()
        db.session.add(UserFeedback(user_id=test_user['id'], content_id=own_bookmark.id, feedback_type='helpful',
                                    context_data={'project_id': victim_project.id}))
        db.session.commit()
        headers = {'Authorization': f"Bearer {create_access_token(identity=str(test_user['id']))}"}

    response = client.get('/api/recommendations/suggested-contexts', headers=headers)
    assert response.status_code == 200
    assert 'Secret launch' not in response.get_data(as_text=True)


def test_feedback_keeps_own_project_reference(client, app, test_user):
    from models import db, Project, SavedContent, UserFeedback
    with app.app_context():
        project = Project(user_id=test_user['id'], title='Mine')
        bookmark = SavedContent(user_id=test_user['id'], url='https://example.com/c', title='C')
        db.session.add_all([project, bookmark])
        db.session.commit()
        project_id, bookmark_id = project.id, bookmark.id
        headers = {'Authorization': f"Bearer {create_access_token(identity=str(test_user['id']))}"}

    response = client.post('/api/recommendations/feedback', headers=headers, json={
        'recommendation_id': bookmark_id, 'feedback_type': 'positive', 'feedback_data': {'project_id': project_id}})
    with app.app_context():
        assert db.session.get(UserFeedback, response.json['feedback_id']).context_data == {'project_id': project_id}


# ---------------------------------------------------------------------------------------------------
# Sweep: every route that takes an object id, called by an intruder with the owner's ids.
# ---------------------------------------------------------------------------------------------------

# Which of the owner's objects a route parameter names. A new <int:...> route whose parameter is not
# listed here fails test_every_id_route_is_covered_by_the_sweep: map it (or allowlist it below) so the
# sweep reaches it instead of the route silently escaping the check.
PARAM_TO_OBJECT = {
    'bookmark_id': 'bookmark',
    'content_id': 'bookmark',
    'extraction_id': 'linkedin_extraction',
    'project_id': 'project',
    'task_id': 'task',
    'subtask_id': 'subtask',
    'user_id': 'user',
    'feedback_id': 'feedback',
}

# Int-id routes that are public or not tenant-scoped, as {(rule, method): reason}. Empty today: every
# int-id route belongs to a user.
PUBLIC_INT_ID_ROUTES = {}

# Routes whose path parameter is not an integer id, as {rule: reason or covering test}. Listed so a new
# string- or uuid-keyed route is noticed as well, rather than skipped because it is not <int:...>.
NON_INT_PARAM_ROUTES = {
    '/static/<path:filename>': 'public static files; no tenant data',
    '/api/bookmarks/url/<path:url>': 'covered by test_delete_by_url_cannot_touch_another_users_bookmark',
}

OWNER_PASSWORD = 'owner-pass-123'

# Sent with every POST/PUT/PATCH. Valid enough to get past body validation, so a missing ownership check
# shows up as a 2xx rather than hiding behind a 400. Includes the owner's real password: an unguarded
# password route would accept it.
MUTATION_BODY = {
    'title': 'hijacked', 'description': 'hijacked', 'technologies': 'hijacked', 'completed': True,
    'technology_interests': 'hijacked', 'current_password': OWNER_PASSWORD, 'new_password': 'hijacked-pass-1',
}

_PARAM_RE = re.compile(r'<(?:(\w+)(?:\([^>]*\))?:)?(\w+)>')
_SKIPPED_METHODS = {'OPTIONS', 'HEAD'}


def _routes_with_params(app):
    """[(rule string, method, {param: converter name})] for every route with a path parameter."""
    out = []
    for rule in app.url_map.iter_rules():
        params = {name: conv or 'default' for conv, name in _PARAM_RE.findall(rule.rule)}
        if not params:
            continue
        for method in sorted(rule.methods - _SKIPPED_METHODS):
            out.append((rule.rule, method, params))
    return out


def _int_params(params):
    return [name for name, conv in params.items() if conv == 'int']


def _swept_cases(app):
    cases = []
    for rule, method, params in _routes_with_params(app):
        ints = _int_params(params)
        if ints and len(ints) == len(params) and (rule, method) not in PUBLIC_INT_ID_ROUTES \
                and all(p in PARAM_TO_OBJECT for p in ints):
            cases.append((rule, method, ints))
    return cases


def test_every_id_route_is_covered_by_the_sweep(app):
    problems = []
    seen_rules, seen_pairs = set(), set()
    for rule, method, params in _routes_with_params(app):
        seen_rules.add(rule)
        seen_pairs.add((rule, method))
        ints = _int_params(params)
        if len(ints) != len(params):
            if rule not in NON_INT_PARAM_ROUTES:
                problems.append(f'{method} {rule}: non-integer path parameter; sweep it or add it to '
                                f'NON_INT_PARAM_ROUTES with a reason')
            continue
        if (rule, method) in PUBLIC_INT_ID_ROUTES:
            continue
        unmapped = [p for p in ints if p not in PARAM_TO_OBJECT]
        if unmapped:
            problems.append(f'{method} {rule}: no owner object for {unmapped}; add it to PARAM_TO_OBJECT '
                            f'(and create it in _make_owner) or to PUBLIC_INT_ID_ROUTES with a reason')
    problems += [f'stale NON_INT_PARAM_ROUTES entry: {r}' for r in NON_INT_PARAM_ROUTES if r not in seen_rules]
    problems += [f'stale PUBLIC_INT_ID_ROUTES entry: {k}' for k in PUBLIC_INT_ID_ROUTES if k not in seen_pairs]
    assert not problems, '\n'.join(problems)


def _make_owner(tag):
    """A user with one of every object an id route can name. Every title carries `tag`."""
    from models import db, User, Project, Task, Subtask, SavedContent, Feedback
    from blueprints.auth import hash_password
    user = User(username=f'owner_{tag}', email=f'owner_{tag}@example.com',
                password_hash=hash_password(OWNER_PASSWORD), technology_interests=f'{tag} interests')
    db.session.add(user)
    db.session.flush()
    project = Project(user_id=user.id, title=f'{tag} project', description=f'{tag} plans',
                      technologies=f'{tag} stack')
    bookmark = SavedContent(user_id=user.id, url=f'https://example.com/{tag}/doc', title=f'{tag} bookmark',
                            extracted_text=f'{tag} private text', notes=f'{tag} notes', scrape_status='SUCCESS')
    extraction = SavedContent(user_id=user.id, url=f'https://www.linkedin.com/posts/{tag}', title=f'{tag} post',
                              source='linkedin', category='linkedin', extracted_text=f'{tag} post text',
                              scrape_status='SUCCESS', strategy_used='LINKEDIN')
    db.session.add_all([project, bookmark, extraction])
    db.session.flush()
    task = Task(project_id=project.id, title=f'{tag} task', description=f'{tag} task details')
    db.session.add(task)
    db.session.flush()
    subtask = Subtask(task_id=task.id, title=f'{tag} subtask', description=f'{tag} subtask details')
    feedback = Feedback(user_id=user.id, project_id=project.id, content_id=bookmark.id, feedback_type='like')
    db.session.add_all([subtask, feedback])
    db.session.commit()
    return {'user': user.id, 'project': project.id, 'task': task.id, 'subtask': subtask.id,
            'bookmark': bookmark.id, 'linkedin_extraction': extraction.id, 'feedback': feedback.id}


def _snapshot(ids):
    """Everything an intruder could change or delete, as plain values."""
    from models import db, User, Project, Task, Subtask, SavedContent, Feedback
    db.session.expire_all()

    def row(model, key, *attrs):
        obj = db.session.get(model, ids[key])
        return None if obj is None else tuple(getattr(obj, a) for a in attrs)

    return {
        'user': row(User, 'user', 'username', 'password_hash', 'technology_interests'),
        'project': row(Project, 'project', 'title', 'description', 'technologies'),
        'task': row(Task, 'task', 'title', 'description'),
        'subtask': row(Subtask, 'subtask', 'title', 'description', 'completed'),
        'bookmark': row(SavedContent, 'bookmark', 'title', 'notes', 'extracted_text'),
        'linkedin_extraction': row(SavedContent, 'linkedin_extraction', 'title', 'extracted_text'),
        'feedback': row(Feedback, 'feedback', 'feedback_type'),
    }


def _drop_owner(ids):
    from models import db, User, Feedback
    db.session.rollback()
    db.session.query(Feedback).filter_by(user_id=ids['user']).delete()
    user = db.session.get(User, ids['user'])
    if user is not None:
        db.session.delete(user)
    db.session.commit()


def _bearer(user_id):
    return {'Authorization': f'Bearer {create_access_token(identity=str(user_id))}'}


@pytest.fixture
def sweep_stubs():
    """Keep the owner's control calls away from Gemini, the ML engine and the queue."""
    fake = {'results': [], 'intent': {}, 'cached': False}
    with patch('ml.intent_engine.engine.recommend', return_value=fake), \
            patch('services.background_analysis_service.analyze_content', return_value={'queued': True}), \
            patch('services.task_queue.enqueue_project_ml_job', return_value=None), \
            patch('services.task_queue.is_rq_available', return_value=False):
        yield


def test_intruder_gets_404_on_every_id_route(app, client, test_user, sweep_stubs):
    """Release gate 4: another user's ids behave exactly like ids that do not exist."""
    cases = _swept_cases(app)
    # Guards against a sweep that silently covers nothing (e.g. a broken route parser).
    assert len(cases) >= 15, cases

    failures = []
    for rule, method, params in cases:
        tag = f'zq{uuid.uuid4().hex[:10]}'
        with app.app_context():
            ids = _make_owner(tag)
            before = _snapshot(ids)
            intruder, owner = _bearer(test_user['id']), _bearer(ids['user'])
        try:
            url = _PARAM_RE.sub(lambda m: str(ids[PARAM_TO_OBJECT[m.group(2)]]), rule)
            body = MUTATION_BODY if method in ('POST', 'PUT', 'PATCH') else None

            resp = client.open(url, method=method, json=body, headers=intruder)
            where = f'{method} {url} ({rule})'
            if resp.status_code not in (403, 404):
                failures.append(f'{where}: intruder got {resp.status_code}, expected 403/404')
            if tag in resp.get_data(as_text=True):
                failures.append(f"{where}: response to the intruder contains the owner's data")
            with app.app_context():
                after = _snapshot(ids)
            if after != before:
                changed = sorted(k for k in before if before[k] != after[k])
                failures.append(f"{where}: intruder changed the owner's {changed}")

            # Control: the same call as the owner must reach the object. Otherwise the 404 above only
            # says the id was never resolved (wrong substitution, broken route), not that it is guarded.
            resp = client.open(url, method=method, json=body, headers=owner)
            if not 200 <= resp.status_code < 300:
                failures.append(f'{where}: owner control call got {resp.status_code}; the sweep is not '
                                f'reaching a real object here (fix the mapping or MUTATION_BODY)')
        finally:
            with app.app_context():
                _drop_owner(ids)

    assert not failures, '\n'.join(failures)


def test_delete_by_url_cannot_touch_another_users_bookmark(app, client, test_user, other_user):
    from models import db, SavedContent
    url = f'https://example.com/private/{uuid.uuid4().hex}?id=7'
    with app.app_context():
        bookmark = SavedContent(user_id=other_user['id'], url=url, title='Their bookmark')
        db.session.add(bookmark)
        db.session.commit()
        bookmark_id = bookmark.id
        headers = _bearer(test_user['id'])

        owner_headers = _bearer(other_user['id'])

    path = f'/api/bookmarks/url/{quote(url, safe="")}'
    resp = client.delete(path, headers=headers)
    assert resp.status_code == 404
    assert 'Their bookmark' not in resp.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(SavedContent, bookmark_id) is not None

    # Control: the same path does resolve the bookmark for its owner.
    assert client.delete(path, headers=owner_headers).status_code == 200
