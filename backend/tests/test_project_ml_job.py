import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from jobs.project_ml_job import process_project_ml, is_zero_vector, validate_embedding


def test_is_zero_vector():
    assert is_zero_vector(np.array([0, 0, 0])) is True
    assert is_zero_vector([0.0, 0.0, 0.0]) is True
    assert is_zero_vector(np.array([0, 1, 0])) is False
    assert is_zero_vector([0.1, 0.0]) is False
    assert is_zero_vector(None) is True


def test_validate_embedding():
    assert validate_embedding([0.1] * 384, expected_dim=384) is True
    assert validate_embedding(np.zeros(384), expected_dim=384) is True
    assert validate_embedding([0.1] * 10, expected_dim=384) is False
    assert validate_embedding(None) is False


def test_process_project_ml_success(app):
    with patch('jobs.project_ml_job.UnitOfWork') as mock_uow_cls, \
         patch('jobs.project_ml_job.get_project_embedding') as mock_get_emb, \
         patch('jobs.project_ml_job.analyze_user_intent') as mock_analyze:

        mock_uow = MagicMock()
        mock_uow_cls.return_value.__enter__.return_value = mock_uow

        mock_project = MagicMock()
        mock_project.title = "Test Project"
        mock_project.description = "Test Desc"
        mock_project.technologies = "Python"
        mock_uow.projects.get_by_id.return_value = mock_project

        mock_get_emb.return_value = [0.1] * 384
        mock_intent = MagicMock()
        mock_intent.primary_goal = "Build API"
        mock_intent.project_type = "Web App"
        mock_analyze.return_value = mock_intent

        process_project_ml(project_id=1, user_id=10)

        mock_uow.projects.get_by_id.assert_called_once_with(1, 10)
        mock_uow.projects.update.assert_called_once_with(mock_project)
        mock_analyze.assert_called_once_with(
            user_input="Test Project Test Desc Python",
            project_id=1,
            force_analysis=True
        )
