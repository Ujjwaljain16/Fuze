import pytest
from models import SavedContent, ContentAnalysis, UserFeedback, db
from repositories.recommendation_repository import RecommendationRepository


@pytest.mark.unit
@pytest.mark.requires_db
def test_recommendation_repository_distinct_and_dict_stats(test_user, app):
    with app.app_context():
        repo = RecommendationRepository(db.session)

        # 1. Add Bookmark
        bookmark = SavedContent(
            user_id=test_user['id'],
            url='https://example.com/ml-guide',
            title='ML Guide',
            tags='python, ml, ai'
        )
        repo.add_bookmark(bookmark)
        db.session.commit()

        # 2. Add Analysis
        analysis = ContentAnalysis(
            content_id=bookmark.id,
            analysis_data={'summary': 'test'},
            content_type='article'
        )
        db.session.add(analysis)
        db.session.commit()

        # 3. Test Distinct Count Analysis Stats
        stats = repo.get_analysis_stats(test_user['id'])
        assert stats['total_content'] >= 1
        assert stats['analyzed_count'] >= 1
        assert stats['pending_count'] == stats['total_content'] - stats['analyzed_count']

        # 4. Add User Feedback (content_id is required)
        fb = UserFeedback(
            user_id=test_user['id'],
            content_id=bookmark.id,
            feedback_type='like'
        )
        repo.add_feedback(fb)
        db.session.commit()

        # 5. Preferences Data with Dict Feedback Stats
        pref = repo.get_user_preferences_data(test_user['id'])
        assert isinstance(pref['feedback_stats'], dict)
        assert pref['feedback_stats'].get('like') == 1

        # 6. Pagination & Ownership Verification
        b_owned = repo.get_bookmark_by_id(bookmark.id, user_id=test_user['id'])
        assert b_owned is not None

        b_unowned = repo.get_bookmark_by_id(bookmark.id, user_id=99999)
        assert b_unowned is None

        paginated_bms = repo.get_user_bookmarks(test_user['id'], limit=10, offset=0)
        assert len(paginated_bms) >= 1
