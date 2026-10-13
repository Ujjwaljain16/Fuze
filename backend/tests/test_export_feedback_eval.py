"""scripts/export_feedback_eval.py turns per-project feedback into a BEIR-format evaluation set."""
import importlib.util
import json
import os
import uuid

import pytest

SCRIPT = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'export_feedback_eval.py')


@pytest.fixture
def exporter():
    spec = importlib.util.spec_from_file_location('export_feedback_eval', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def stranger(app):
    from models import db, User
    from blueprints.auth import hash_password
    with app.app_context():
        tag = uuid.uuid4().hex[:8]
        user = User(username=f'exp_{tag}', email=f'exp_{tag}@example.com', password_hash=hash_password('pw123456'))
        db.session.add(user)
        db.session.commit()
        yield {'id': user.id}
        db.session.delete(user)
        db.session.commit()


def _seed(app, user_id, stranger_id):
    from models import db, Project, SavedContent, UserFeedback
    vector = [0.1] * 384
    with app.app_context():
        tag = uuid.uuid4().hex[:6]
        mine = [SavedContent(user_id=user_id, url=f'https://e.com/{tag}/{i}', title=f'Doc {i}',
                             extracted_text=f'text of document {i} ' * 50, embedding=vector) for i in range(4)]
        unembedded = SavedContent(user_id=user_id, url=f'https://e.com/{tag}/none', title='No vector', extracted_text='x')
        alien = SavedContent(user_id=stranger_id, url=f'https://e.com/{tag}/alien', title='Not mine', extracted_text='y',
                             embedding=vector)
        rust = Project(user_id=user_id, title='Learn Rust', description='async and ownership', technologies='rust')
        web = Project(user_id=user_id, title='Portfolio site', description='', technologies='react')
        theirs = Project(user_id=stranger_id, title='Secret launch', description='private plans', technologies='go')
        db.session.add_all([*mine, unembedded, alien, rust, web, theirs])
        db.session.commit()
        d0, d1, d2, d3 = (m.id for m in mine)

        def fb(project, content, kind, **context):
            return UserFeedback(user_id=user_id, content_id=content, project_id=project.id if project else None,
                                feedback_type=kind, context_data=context or {})
        db.session.add_all([
            fb(rust, d0, 'helpful', position=1, score=91.5),
            fb(rust, d1, 'not_relevant', position=2, score=80),
            fb(rust, d2, 'dislike', position=3),
            fb(rust, d2, 'like', position=3),             # re-judged: the latest judgment wins
            fb(rust, d3, 'clicked', position=4),          # a bare click is not a judgment
            fb(web, d0, 'not_relevant', position=1),      # the same bookmark, the opposite call for another project
            fb(None, d1, 'helpful'),                      # no project: cannot be used per project
            UserFeedback(user_id=user_id, content_id=d1, project_id=theirs.id, feedback_type='helpful', context_data={}),
        ])
        db.session.commit()
        return {'d': (d0, d1, d2, d3), 'rust': rust.id, 'web': web.id, 'theirs': theirs.id, 'alien': alien.id,
                'unembedded': unembedded.id}


def _tsv(path):
    with open(path, encoding='utf-8') as f:
        next(f)
        return {tuple(line.rstrip('\n').split('\t')[:2]): int(line.rstrip('\n').split('\t')[2]) for line in f}


def _jsonl(path):
    with open(path, encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def test_the_export_is_per_project_and_uses_the_latest_judgment(app, test_user, stranger, exporter, tmp_path):
    from models import db
    ids = _seed(app, test_user['id'], stranger['id'])
    d0, d1, d2, d3 = ids['d']
    with app.app_context():
        summary = exporter.export(db.session.connection(), test_user['id'], str(tmp_path))

    qrels = _tsv(tmp_path / 'qrels' / 'test.tsv')
    rust, web = f"p{ids['rust']}", f"p{ids['web']}"
    assert qrels == {
        (rust, f'b{d0}'): 1,       # helpful
        (rust, f'b{d1}'): 0,       # not relevant
        (rust, f'b{d2}'): 1,       # disliked, then liked: the later call wins
        (web, f'b{d0}'): 0,        # the same bookmark is judged separately for the other project
    }
    assert summary['judgments'] == 4 and summary['useful'] == 2 and summary['not_useful'] == 2
    assert summary['projects'] == 2

    queries = {q['_id']: q['text'] for q in _jsonl(tmp_path / 'queries.jsonl')}
    assert queries == {rust: 'Learn Rust. async and ownership. rust', web: 'Portfolio site. react'}
    assert f"p{ids['theirs']}" not in queries            # another user's project never appears

    corpus = {c['_id']: c for c in _jsonl(tmp_path / 'corpus.jsonl')}
    assert set(corpus) == {f'b{x}' for x in ids['d']}    # only this user's bookmarks that have an embedding
    assert corpus[f'b{d0}']['text'].startswith('text of document 0')

    judgments = {(j['query'], j['doc']): j for j in _jsonl(tmp_path / 'judgments.jsonl')}
    assert judgments[(rust, f'b{d0}')]['position'] == 1 and judgments[(rust, f'b{d0}')]['score'] == 91.5
    assert 'Not mine' not in (tmp_path / 'corpus.jsonl').read_text(encoding='utf-8')
    assert 'Secret launch' not in (tmp_path / 'queries.jsonl').read_text(encoding='utf-8')
    assert 'position bias' in (tmp_path / 'SUMMARY.txt').read_text(encoding='utf-8').lower() or 'favour' in (tmp_path / 'SUMMARY.txt').read_text(encoding='utf-8')


def test_no_text_exports_ids_and_titles_only(app, test_user, stranger, exporter, tmp_path):
    from models import db
    _seed(app, test_user['id'], stranger['id'])
    with app.app_context():
        exporter.export(db.session.connection(), test_user['id'], str(tmp_path), include_text=False)
    assert all(c['text'] == '' for c in _jsonl(tmp_path / 'corpus.jsonl'))
    assert any(c['title'].startswith('Doc') for c in _jsonl(tmp_path / 'corpus.jsonl'))


def test_the_output_is_readable_by_the_evaluation_harness(app, test_user, stranger, exporter, tmp_path):
    """qrels/test.tsv must load with eval_recommendations._read_qrels (BEIR format, header line first)."""
    from models import db
    ids = _seed(app, test_user['id'], stranger['id'])
    with app.app_context():
        exporter.export(db.session.connection(), test_user['id'], str(tmp_path))
    spec = importlib.util.spec_from_file_location('eval_recommendations', os.path.join(os.path.dirname(SCRIPT), 'eval_recommendations.py'))
    try:
        harness = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(harness)
    except Exception as e:   # the harness needs heavy optional dependencies on some machines
        pytest.skip(f'harness not importable here: {e}')
    qrels = harness._read_qrels(str(tmp_path / 'qrels' / 'test.tsv'))
    assert qrels[f"p{ids['rust']}"] == {f"b{ids['d'][0]}": 1, f"b{ids['d'][2]}": 1}   # negatives are not "relevant"
