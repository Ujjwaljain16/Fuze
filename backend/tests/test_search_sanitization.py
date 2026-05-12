from utils.query_sanitizer import sanitize_like_query

def test_percent_escaped():
    """query = '%' should be escaped to '\%'"""
    assert sanitize_like_query('%') == '\\%'

def test_underscore_escaped():
    """query = '_' should be escaped to '\_'"""
    assert sanitize_like_query('_') == '\\_'

def test_backslash_escaped():
    """query = '\' should be escaped to '\\'"""
    assert sanitize_like_query('\\') == '\\\\'

def test_injection_pattern():
    """query = 'test%injection' should be 'test\%injection'"""
    assert sanitize_like_query('test%injection') == 'test\\%injection'

def test_empty_query():
    """Empty queries should return empty strings"""
    assert sanitize_like_query('') == ''
    assert sanitize_like_query('   ') == ''

def test_truncation():
    """Long queries should be truncated to max_length (default 200)"""
    long_query = 'a' * 300
    sanitized = sanitize_like_query(long_query)
    assert len(sanitized) == 200
    assert sanitized == 'a' * 200

if __name__ == "__main__":
    # Manual run if needed
    print(f"Testing %: {sanitize_like_query('%')}")
    print(f"Testing _: {sanitize_like_query('_')}")
    print(f"Testing injection: {sanitize_like_query('test%injection')}")
    print(f"Testing long: {len(sanitize_like_query('a'*300))}")
