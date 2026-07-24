import pytest
from utils.database_indexes import extract_index_name


@pytest.mark.unit
def test_extract_index_name_regex():
    sql1 = "CREATE INDEX IF NOT EXISTS idx_saved_content_user_id ON saved_content(user_id)"
    assert extract_index_name(sql1) == "idx_saved_content_user_id"

    sql2 = "CREATE INDEX idx_users_username_lower ON users(LOWER(username))"
    assert extract_index_name(sql2) == "idx_users_username_lower"

    sql3 = "CREATE INDEX idx_projects_embedding ON projects USING ivfflat (embedding vector_cosine_ops)"
    assert extract_index_name(sql3) == "idx_projects_embedding"
