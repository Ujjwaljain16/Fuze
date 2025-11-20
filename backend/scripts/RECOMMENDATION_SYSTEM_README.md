# Content Analysis & Recommendation Integration

AI-powered content analysis system that integrates with the existing Unified Recommendation Orchestrator for personalized bookmark recommendations.

## Architecture Overview

The system integrates with your existing recommendation infrastructure:

1. **Content Analysis Engine** (`content_analysis_script.py`)
   - Analyzes saved bookmarks using Gemini AI
   - Extracts technologies, concepts, and learning insights
   - Generates comprehensive user profiles for the Unified Recommendation Orchestrator

2. **Unified Recommendation Orchestrator** (existing)
   - Your existing `unified_recommendation_orchestrator.py`
   - Uses content analysis results for personalized recommendations
   - Processes analysis data through Fast Semantic and Context-Aware engines

3. **Multi-User Architecture**
   - Complete user isolation maintained
   - API key management per user
   - Secure data separation

## Quick Start

### 1. Analyze User Content
```bash
# Analyze content for user ID 123
python scripts/content_analysis_script.py --user-id 123
```

### 2. Use with Existing Recommendation Orchestrator
```python
from scripts.content_analysis_script import ContentAnalysisEngine
from ml.unified_recommendation_orchestrator import UnifiedRecommendationOrchestrator, UnifiedRecommendationRequest

# Analyze user content
analysis_engine = ContentAnalysisEngine(user_id=123)
analysis_results = analysis_engine.analyze_user_content()

# Use analysis results to enhance recommendations
orchestrator = UnifiedRecommendationOrchestrator()

# Create request enriched with user analysis
request = UnifiedRecommendationRequest(
    user_id=123,
    title="Python development",
    technologies=",".join(analysis_results.get('technology_expertise', {}).get('primary_technologies', [])),
    user_interests=f"Skill level: {analysis_results.get('learning_profile', {}).get('primary_skill_level', 'intermediate')}"
)

recommendations = orchestrator.get_recommendations(request)
```

### 3. Background Processing
```bash
# Run analysis for multiple users
python scripts/content_analysis_script.py --user-id 123 --force-refresh
python scripts/content_analysis_script.py --user-id 456 --force-refresh
```

## Detailed Usage

### Content Analysis Script

**Command:**
```bash
python scripts/content_analysis_script.py [OPTIONS]
```

**Options:**
- `--user-id INT` (required): User ID to analyze
- `--force-refresh`: Re-analyze already analyzed content
- `--output-file PATH`: Save detailed results to JSON
- `--no-user-api-key`: Use default API key instead of user's

**Example Output:**
```
================================================================================
CONTENT ANALYSIS RESULTS - User 123
================================================================================

📊 Total Content Analyzed: 45

🛠️  Technology Expertise:
  • JavaScript: 25 bookmarks
  • React: 20 bookmarks
  • Python: 15 bookmarks

📚 Learning Profile:
  • Primary Skill Level: intermediate
  • Target Audience: intermediate

🎯 Recommendations:
  • Work on real-world projects and complex implementations
  • Explore advanced patterns and best practices
  • Contribute to open source or collaborate on projects

📈 Engagement Metrics:
  • Technologies Covered: 12
  • Concepts Covered: 45
  • Average Quality: 82.5%
================================================================================
```

### Integration with Unified Recommendation Orchestrator

The content analysis results integrate seamlessly with your existing `UnifiedRecommendationOrchestrator`:

**Key Integration Points:**

1. **Technology Enrichment**
   ```python
   # Analysis provides user's primary technologies
   primary_tech = analysis_results['technology_expertise']['primary_technologies']
   request.technologies = ",".join(primary_tech)
   ```

2. **Skill Level Context**
   ```python
   # Analysis provides user's skill level for better recommendations
   skill_level = analysis_results['learning_profile']['primary_skill_level']
   request.user_interests = f"Skill level: {skill_level}"
   ```

3. **Concept-Based Filtering**
   ```python
   # Analysis provides key concepts user has mastered
   key_concepts = analysis_results['concept_expertise']['core_concepts']
   # Used by orchestrator for relevance scoring
   ```

**Recommendation Types (via your existing orchestrator):**

1. **Semantic Content Matching**
   - Uses user's technology profile for similarity matching
   - Considers skill level for difficulty appropriateness
   - Leverages learned concepts for relevance scoring

2. **Context-Aware Suggestions**
   - Considers user's learning trajectory
   - Adapts to current skill development stage
   - Provides progression-appropriate recommendations

3. **Diverse Content Sources**
   - Matches against your existing content database
   - Uses analysis insights for personalized filtering
   - Maintains quality thresholds based on user profile

## Integration with Existing System

### Background Analysis Service
The content analysis integrates with your existing background analysis service:

```python
from scripts.content_analysis_script import ContentAnalysisEngine

# In your background analysis service
def analyze_user_content_background(user_id):
    engine = ContentAnalysisEngine(user_id)
    results = engine.analyze_user_content()

    # Results are automatically cached in Redis with key: user_analysis:{user_id}
    # Your UnifiedRecommendationOrchestrator can access this cached data
    return results
```

### Enhanced Recommendation API
Your existing recommendation endpoints can now use the analysis data:

```python
from ml.unified_recommendation_orchestrator import UnifiedRecommendationOrchestrator, UnifiedRecommendationRequest
from scripts.content_analysis_script import ContentAnalysisEngine

@recommendations_bp.route('/analyze/<int:user_id>')
def analyze_user(user_id):
    """Trigger content analysis for user (background processing)"""
    engine = ContentAnalysisEngine(user_id)
    results = engine.analyze_user_content()
    return jsonify({
        'status': 'analysis_started',
        'message': f'Analysis initiated for user {user_id}',
        'estimated_completion': '5-15 minutes depending on content volume'
    })

@recommendations_bp.route('/recommendations/<int:user_id>')
def get_enhanced_recommendations(user_id):
    """Get AI-enhanced recommendations using content analysis"""

    # Try to get cached analysis results
    from utils.redis_utils import redis_cache
    analysis_cache_key = f"user_analysis:{user_id}"
    analysis_results = redis_cache.get_cached_data(analysis_cache_key)

    # Create enhanced request using analysis data
    request = UnifiedRecommendationRequest(
        user_id=user_id,
        title="Personalized recommendations",
        technologies=",".join(analysis_results.get('technology_expertise', {}).get('primary_technologies', [])) if analysis_results else "",
        user_interests=f"Skill level: {analysis_results.get('learning_profile', {}).get('primary_skill_level', 'intermediate')}" if analysis_results else "",
        max_recommendations=15,
        diversity_weight=0.4,
        quality_threshold=7
    )

    # Get recommendations using your existing orchestrator
    orchestrator = UnifiedRecommendationOrchestrator()
    recommendations = orchestrator.get_recommendations(request)

    return jsonify({
        'recommendations': [asdict(rec) for rec in recommendations],
        'analysis_available': analysis_results is not None,
        'user_profile': analysis_results.get('learning_profile') if analysis_results else None,
        'technology_focus': analysis_results.get('technology_expertise', {}).get('primary_technologies') if analysis_results else []
    })
```

### Database Schema
The system uses existing tables:
- `saved_content`: User bookmarks
- `content_analysis`: AI analysis results (auto-populated)

Results are cached in Redis for performance:
- `user_analysis:{user_id}`: Analysis results (7-day TTL)
- `user_recommendations:{user_id}`: Generated recommendations (24-hour TTL)

## Analysis Output Structure

### Content Analysis Results
```json
{
  "user_id": 123,
  "total_content_analyzed": 45,
  "technology_expertise": {
    "primary_technologies": ["JavaScript", "React", "Python"],
    "top_technologies": [["JavaScript", 25], ["React", 20]]
  },
  "learning_profile": {
    "primary_skill_level": "intermediate",
    "learning_path": {
      "current_focus": "learning",
      "learning_trajectory": ["intermediate", "advanced"]
    }
  },
  "recommendations": {
    "next_steps": ["Work on real-world projects", "Explore advanced patterns"],
    "skill_gaps": ["Deepen JavaScript expertise"]
  },
  "engagement_metrics": {
    "total_technologies_covered": 12,
    "average_content_quality": 82.5
  }
}
```

### Enhanced Recommendation Results
Your existing `UnifiedRecommendationOrchestrator` returns results in this format, now enhanced with content analysis:

```json
{
  "recommendations": [
    {
      "id": 456,
      "title": "Advanced React Patterns",
      "url": "https://example.com/react-patterns",
      "score": 0.92,
      "reason": "Matches your intermediate JavaScript expertise and React focus",
      "content_type": "tutorial",
      "difficulty": "intermediate",
      "technologies": ["React", "JavaScript"],
      "key_concepts": ["hooks", "context", "performance"],
      "quality_score": 8.5,
      "engine_used": "context",
      "confidence": 0.89,
      "metadata": {...},
      "basic_summary": "Advanced React patterns tutorial",
      "context_summary": "Perfect match for your current learning trajectory"
    }
  ],
  "analysis_available": true,
  "user_profile": {
    "primary_skill_level": "intermediate",
    "target_audience_level": "intermediate",
    "learning_path": {
      "current_focus": "implementation",
      "learning_trajectory": ["intermediate", "advanced"]
    }
  },
  "technology_focus": ["JavaScript", "React", "Python"]
}
```

## Performance & Scaling

### Rate Limiting
- Respects Gemini API limits (10 req/min default)
- Configurable batch sizes and delays
- Automatic backoff on API errors

### Caching Strategy
- Analysis results cached for 7 days
- Recommendations cached for 24 hours
- Redis-based for high performance

### Multi-User Isolation
- Complete data separation between users
- User-specific API keys supported
- Secure database queries with user_id filters

## Error Handling

### Content Analysis Errors
- Skips malformed content gracefully
- Continues processing on individual analysis failures
- Logs errors without stopping batch processing

### API Failures
- Falls back to default API key if user key fails
- Continues with partial results
- Comprehensive error logging

### Data Validation
- Validates analysis results before saving
- Handles missing or corrupted data
- Maintains data integrity across failures

## Monitoring & Debugging

### Logging
- Comprehensive logging at all levels
- Progress tracking for long-running analyses
- Error details for troubleshooting

### Health Checks
```python
# Check if analysis system is working
from scripts.content_analysis_script import ContentAnalysisEngine

def health_check():
    try:
        engine = ContentAnalysisEngine(user_id=1)
        # Test with minimal analysis
        return engine.analyzer.analyze_bookmark_content(
            "Test", "Test content", "Test content", "https://example.com"
        ) is not None
    except Exception as e:
        logger.error(f"Analysis health check failed: {e}")
        return False
```

### Performance Metrics
- Analysis completion times
- Success/failure rates
- Content quality distributions
- User engagement metrics

## Example Workflow

1. **User saves bookmarks** via browser extension
2. **Background analysis** processes new content (existing system)
3. **Content analysis script** runs periodically to build user profiles:
   ```bash
   python scripts/content_analysis_script.py --user-id 123
   ```
4. **Your Unified Recommendation Orchestrator** uses analysis data for enhanced recommendations:
   ```python
   # Analysis results automatically cached and used by orchestrator
   recommendations = orchestrator.get_recommendations(request)
   ```
5. **API serves enhanced recommendations** to frontend with user profile insights
6. **User sees AI-powered, personalized content** in their dashboard

## Production Deployment

### Cron Job Setup
```bash
# Daily analysis for active users
0 2 * * * /path/to/venv/bin/python /path/to/backend/scripts/content_analysis_script.py --user-id $(get_active_users.sh)
```

### Background Service Integration
```python
# In your background service
from scripts.content_analysis_script import ContentAnalysisEngine

def scheduled_content_analysis():
    """Run analysis for users with new content"""
    users_with_new_content = get_users_with_new_bookmarks()

    for user_id in users_with_new_content:
        try:
            engine = ContentAnalysisEngine(user_id)
            results = engine.analyze_user_content()
            logger.info(f"Analysis completed for user {user_id}")
        except Exception as e:
            logger.error(f"Analysis failed for user {user_id}: {e}")
```

### Monitoring Dashboard
Track system health:
- Analysis success rates
- Processing times
- User satisfaction metrics
- Content quality trends

This system provides a complete, production-ready recommendation engine that learns from user behavior and provides personalized, AI-powered learning suggestions.
