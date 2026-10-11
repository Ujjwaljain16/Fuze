from unittest.mock import MagicMock, patch

import pytest

from services.content_profile import (
    PROFILE_VERSION, parse_profile, profile_text, generate_profile, store_profile,
)

VALID = {
    "summary": "How to add JWT auth to a Flask API.",
    "teaches_or_solves": ["issuing tokens", "protecting routes"],
    "key_concepts": ["JWT", "Flask", "refresh tokens"],
    "use_when": "When securing a Flask REST API.",
    "audience_level": "intermediate",
    "content_type": "tutorial",
    "technologies": ["Flask", "PyJWT"],
}


def test_valid_profile_passes_and_is_normalized():
    p = parse_profile({**VALID, "audience_level": "Intermediate ", "content_type": "TUTORIAL"})
    assert p["audience_level"] == "intermediate" and p["content_type"] == "tutorial"
    assert p["key_concepts"] == ["JWT", "Flask", "refresh tokens"]


def test_unknown_enum_values_become_neutral_not_guessed():
    p = parse_profile({**VALID, "audience_level": "expert-ish", "content_type": "blogpost"})
    assert p["audience_level"] == "mixed" and p["content_type"] == "other"


@pytest.mark.parametrize("bad", [
    None, "not json", [], {}, {**VALID, "summary": ""}, {**VALID, "use_when": None},
    {**VALID, "key_concepts": []}, {**VALID, "key_concepts": "JWT"},
])
def test_missing_essentials_are_rejected(bad):
    assert parse_profile(bad) is None


def test_json_string_input_is_accepted():
    import json
    assert parse_profile(json.dumps(VALID))["summary"] == VALID["summary"]


def test_profile_text_contains_purpose_and_concepts():
    t = profile_text("Flask JWT guide", parse_profile(VALID))
    assert "Flask JWT guide" in t and "Useful when: When securing" in t and "Key concepts: JWT" in t


def test_generate_profile_returns_none_when_model_fails():
    analyzer = MagicMock()
    analyzer.generate_json.return_value = None
    assert generate_profile(analyzer, "t", "u", "", "body") is None


def test_store_profile_overwrites_existing_row(app):
    from models import db, ContentAnalysis, SavedContent, User
    with app.app_context():
        user = User(username="profile_u", email="profile_u@example.com", password_hash="x")
        db.session.add(user); db.session.commit()
        item = SavedContent(user_id=user.id, url="https://example.com/jwt", title="JWT", extracted_text="body")
        db.session.add(item); db.session.commit()
        db.session.add(ContentAnalysis(content_id=item.id, analysis_data={"summary": "old guess"}))
        db.session.commit()

        store_profile(db.session, item, parse_profile(VALID), "gemini-2.5-flash")
        db.session.commit()

        rows = ContentAnalysis.query.filter_by(content_id=item.id).all()
        assert len(rows) == 1
        assert rows[0].analysis_data["profile_version"] == PROFILE_VERSION
        assert rows[0].analysis_data["summary"] == VALID["summary"]
        assert rows[0].content_type == "tutorial"


def test_content_analysis_failure_returns_none_not_a_guess():
    from utils.gemini_utils import GeminiAnalyzer
    analyzer = GeminiAnalyzer.__new__(GeminiAnalyzer)
    with patch.object(GeminiAnalyzer, "_make_gemini_request", return_value=None):
        assert analyzer.analyze_bookmark_content("Python tips", "", "react docker aws") is None
    with patch.object(GeminiAnalyzer, "_make_gemini_request", side_effect=RuntimeError("quota")):
        assert analyzer.analyze_bookmark_content("Python tips", "", "") is None
