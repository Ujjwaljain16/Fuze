from unittest.mock import patch, MagicMock
from jobs.project_ml_job import process_project_ml


def test_process_project_ml_success(app):
    from ml.intent_engine.intent import Intent, IntentContext
    pending = Intent(context=IntentContext(user_id=10, project_id=1), text="Project: Test Project. Test Desc.", hash="h1")
    with patch('jobs.project_ml_job.UnitOfWork') as mock_uow_cls, \
         patch('ml.intent_engine.intent.load_context') as mock_ctx, \
         patch('ml.intent_engine.intent.resolve_intent', return_value=pending) as mock_resolve, \
         patch('ml.intent_engine.intent.compute_intent_job', return_value=True) as mock_compute:

        mock_uow = MagicMock()
        mock_uow_cls.return_value.__enter__.return_value = mock_uow

        mock_project = MagicMock()
        mock_project.title = "Test Project"
        mock_project.description = "Test Desc"
        mock_project.technologies = "Python"
        mock_uow.projects.get_by_id.return_value = mock_project

        process_project_ml(project_id=1, user_id=10)

        mock_uow.projects.get_by_id.assert_called_once_with(1, 10)
        mock_ctx.assert_called_once_with(mock_uow.session, 10, project_id=1)
        assert mock_resolve.call_args.kwargs == {"schedule": False}
        mock_compute.assert_called_once_with("h1", "Project: Test Project. Test Desc.", 10)


def test_gemini_runs_after_the_session_is_closed(app):
    """A transaction held across a multi-second Gemini call pins a pooled connection."""
    from ml.intent_engine.intent import Intent, IntentContext
    pending = Intent(context=IntentContext(user_id=10, project_id=1), text="Project: P.", hash="h1")
    order = []
    with patch('jobs.project_ml_job.UnitOfWork') as mock_uow_cls, \
         patch('ml.intent_engine.intent.load_context'), \
         patch('ml.intent_engine.intent.resolve_intent', return_value=pending), \
         patch('ml.intent_engine.intent.compute_intent_job', side_effect=lambda *a: order.append('gemini') or True):
        mock_uow_cls.return_value.__exit__.side_effect = lambda *a: order.append('session_closed')
        process_project_ml(project_id=1, user_id=10)
    assert order == ['session_closed', 'gemini']


def test_explanation_prompt_is_built_before_gemini_and_without_it(app, test_user):
    from ml.intent_engine import explain
    from models import db, SavedContent
    with app.app_context():
        item = SavedContent(user_id=test_user['id'], url='https://e.com/x', title='JWT refresh guide',
                            extracted_text='Rotate refresh tokens and detect reuse.')
        db.session.add(item)
        db.session.commit()
        with patch('utils.gemini_utils.GeminiAnalyzer') as gemini:
            prompt = explain.build_explain_prompt(db.session, test_user['id'], item.id, query='secure my api')
        gemini.assert_not_called()
    assert prompt and 'Rotate refresh tokens' in prompt
