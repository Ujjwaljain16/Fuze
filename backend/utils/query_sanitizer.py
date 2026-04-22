def sanitize_like_query(query: str, max_length: int = 200) -> str:
    """
    Escapes PostgreSQL LIKE special characters in user input.
    Prevents pattern injection and query explosion.
    % \u2192 literal percent
    _ \u2192 literal underscore  
    \ \u2192 literal backslash (escape character itself)
    Also strips leading/trailing whitespace and enforces max length.
    
    Order of replacement is critical: \\ must be escaped FIRST to 
    prevent double-escaping later replacements.
    """
    if not query:
        return ""
        
    # 1. Strip and truncate
    safe_query = query.strip()[:max_length]
    
    # 2. Escape backslashes first (\ -> \\)
    safe_query = safe_query.replace('\\', '\\\\')
    
    # 3. Escape percent signs (% -> \%)
    safe_query = safe_query.replace('%', '\\%')
    
    # 4. Escape underscores (_ -> \_)
    safe_query = safe_query.replace('_', '\\_')
    
    return safe_query
