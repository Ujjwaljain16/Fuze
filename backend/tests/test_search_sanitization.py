def test_percent_returns_no_results():
    from utils.unified_config import sanitize_sql_like
    res = sanitize_sql_like("%")
    assert res == "\\%"

def test_underscore_is_escaped():
    from utils.unified_config import sanitize_sql_like
    res = sanitize_sql_like("_")
    assert res == "\\_"

def test_empty_query_returns_empty():
    from utils.unified_config import sanitize_sql_like
    res = sanitize_sql_like("")
    assert res == ""
    
def test_long_query_is_truncated():
    from utils.unified_config import sanitize_sql_like
    res = sanitize_sql_like("a" * 300)
    assert len(res) <= 200
