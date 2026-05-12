from unittest.mock import patch
from utils.gemini_utils import GeminiAnalyzer

def test_circuit_breaker_trips_after_failures():
    """Verify that the circuit breaker opens after repeated failures"""
    from utils.gemini_utils import gemini_breaker
    
    # Reset breaker state
    gemini_breaker.close()
    
    # Mock generation to raise a RETRYABLE error
    with patch('google.generativeai.GenerativeModel.generate_content') as mock_gen:
        # Use a retryable error message (e.g., 429)
        mock_gen.side_effect = Exception("429 Too Many Requests")
        
        analyzer = GeminiAnalyzer(api_key="test-key")
        
        # We need to fail enough times to trip it (fail_max=3)
        for _ in range(5):
            try:
                analyzer._make_gemini_request("test prompt")
            except Exception:
                pass
        
        # The breaker should now be open
        assert gemini_breaker.current_state == 'open'
        
        # Wrapped call should return None when breaker is open
        result = analyzer._make_gemini_request("test prompt")
        assert result is None
    
    # Clean up
    gemini_breaker.close()

def test_400_does_not_trip_breaker():
    """Verify that non-retryable errors are excluded from the breaker count"""
    from utils.gemini_utils import gemini_breaker, GeminiNonRetryableError
    gemini_breaker.close()
    
    analyzer = GeminiAnalyzer(api_key="test-key")
    
    with patch('google.generativeai.GenerativeModel.generate_content') as mock_gen:
        # This error is in the 'exclude' list
        mock_gen.side_effect = GeminiNonRetryableError("Bad Request")
        
        for _ in range(5):
            try:
                analyzer._make_gemini_request("test prompt")
            except GeminiNonRetryableError:
                pass
        
        # Breaker should still be CLOSED because of the exclude list
        assert gemini_breaker.current_state == 'closed'
