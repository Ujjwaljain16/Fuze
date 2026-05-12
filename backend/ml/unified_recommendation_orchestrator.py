"""
Backward-compatibility shim for ml.unified_recommendation_orchestrator.
The orchestrator was refactored into ml/orchestrator.py + ml/recommendation/.
This module re-exports the public surface so that legacy patch paths and scripts
that reference 'ml.unified_recommendation_orchestrator' continue to work.
"""

# noqa: F401 — all symbols re-exported for backward compatibility
try:
    from ml.orchestrator import get_orchestrator as get_unified_orchestrator  # noqa: F401
    from ml.orchestrator import get_orchestrator  # noqa: F401
except ImportError:
    get_unified_orchestrator = None
    get_orchestrator = None


def clear_gemini_analyzer_cache() -> int:
    """
    Clears cached Gemini analyzer instances.
    Returns the number of entries cleared (0 if no cache is active).
    """
    try:
        from ml.orchestrator import get_orchestrator
        orch = get_orchestrator()
        if orch and hasattr(orch, '_gemini_analyzer'):
            orch._gemini_analyzer = None
            return 1
    except Exception:
        pass
    return 0
