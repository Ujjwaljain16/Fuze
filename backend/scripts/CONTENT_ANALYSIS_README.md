# Content Analysis Script

This script analyzes saved bookmarks content to generate personalized recommendations and learning insights for users.

## Overview

The `content_analysis_script.py` performs comprehensive analysis of a user's saved bookmarks using Gemini AI to:

- Extract technologies, concepts, and learning objectives
- Assess content difficulty and quality
- Generate personalized recommendations
- Build learning path insights
- Calculate engagement metrics

## Features

### Multi-User Architecture
- **User Isolation**: Each analysis is scoped to a specific user ID
- **API Key Support**: Uses user's own Gemini API key if available
- **Secure Data**: No cross-user content mixing

### Comprehensive Analysis
- **Technology Detection**: Identifies all technologies mentioned in content
- **Content Classification**: Categorizes content type, difficulty, and learning intent
- **Concept Extraction**: Extracts key concepts for learning tracking
- **Quality Assessment**: Evaluates content completeness, clarity, and practical value

### Personalized Recommendations
- **Skill Gap Analysis**: Identifies areas for improvement
- **Learning Path**: Suggests optimal learning progression
- **Content Suggestions**: Recommends types of content to explore
- **Project Ideas**: Suggests projects based on technology expertise

## Usage

### Basic Analysis
```bash
python scripts/content_analysis_script.py --user-id 123
```

### Force Refresh Analysis
Re-analyze content that was already analyzed:
```bash
python scripts/content_analysis_script.py --user-id 123 --force-refresh
```

### Save Results to File
```bash
python scripts/content_analysis_script.py --user-id 123 --output-file analysis_results.json
```

### Use Default API Key
Skip user-specific API key and use default:
```bash
python scripts/content_analysis_script.py --user-id 123 --no-user-api-key
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--user-id` | **Required**: User ID to analyze content for |
| `--force-refresh` | Re-analyze content that was already analyzed |
| `--output-file` | Save detailed results to JSON file |
| `--no-user-api-key` | Use default API key instead of user's key |

## Output Structure

The analysis generates a comprehensive JSON structure:

```json
{
  "user_id": 123,
  "analysis_timestamp": "2024-01-15T10:30:00",
  "total_content_analyzed": 45,

  "content_breakdown": {
    "content_types": {"tutorial": 20, "documentation": 15, "article": 10},
    "difficulties": {"intermediate": 25, "beginner": 15, "advanced": 5},
    "learning_intents": {"learning": 30, "implementation": 10, "reference": 5},
    "skill_levels": {"intermediate": 28, "beginner": 12, "advanced": 5}
  },

  "technology_expertise": {
    "top_technologies": [["JavaScript", 25], ["React", 20], ["Python", 15]],
    "technology_count": 12,
    "primary_technologies": ["JavaScript", "React", "Python"]
  },

  "learning_profile": {
    "primary_skill_level": "intermediate",
    "target_audience_level": "intermediate",
    "learning_path": {
      "current_focus": "learning",
      "difficulty_distribution": {...},
      "learning_trajectory": ["intermediate", "advanced"]
    }
  },

  "concept_expertise": {
    "top_concepts": [["asynchronous programming", 15], ["state management", 12]],
    "concept_count": 45,
    "core_concepts": ["asynchronous programming", "state management", ...]
  },

  "recommendations": {
    "skill_gaps": ["Deepen expertise in JavaScript", "Learn advanced React patterns"],
    "next_steps": ["Work on real-world projects", "Explore advanced patterns"],
    "content_suggestions": ["More hands-on tutorials", "Case studies"],
    "project_ideas": ["Build a full-stack application using JavaScript", ...],
    "learning_resources": ["Official documentation", "Online courses", ...]
  },

  "engagement_metrics": {
    "total_technologies_covered": 12,
    "total_concepts_covered": 45,
    "average_content_quality": 82.5,
    "content_diversity_score": 57,
    "learning_breadth": 8
  }
}
```

## How It Works

### 1. Content Filtering
- Analyzes only content with quality score ≥ 5
- Skips empty or very short content
- Processes content in batches for efficiency

### 2. Gemini AI Analysis
- Uses comprehensive prompts to analyze full content
- Extracts technologies, concepts, and learning objectives
- Assesses difficulty, content type, and practical value

### 3. Data Aggregation
- Aggregates technologies and concepts across all content
- Calculates skill levels and learning patterns
- Generates statistical insights

### 4. Recommendation Engine
- Identifies skill gaps and learning opportunities
- Suggests next steps based on current expertise
- Recommends projects and resources

### 5. Database Storage
- Saves individual content analyses to `content_analysis` table
- Caches user-level insights in Redis for 7 days
- Maintains data isolation between users

## Integration Points

### Background Service
The script can be integrated into the background analysis service:

```python
from scripts.content_analysis_script import ContentAnalysisEngine

# Analyze user content
engine = ContentAnalysisEngine(user_id=user_id)
results = engine.analyze_user_content()
```

### API Endpoints
Can be called from Flask routes for real-time analysis:

```python
@analysis_bp.route('/analyze/<int:user_id>')
def analyze_user(user_id):
    engine = ContentAnalysisEngine(user_id)
    results = engine.analyze_user_content()
    return jsonify(results)
```

### Recommendation Engine
Results feed into the recommendation system:

```python
# Get user's technology expertise
tech_expertise = results['technology_expertise']['primary_technologies']

# Generate content recommendations
recommendations = generate_recommendations(tech_expertise, user_id)
```

## Performance Considerations

- **Rate Limiting**: Respects Gemini API limits (free tier: ~10 req/min)
- **Batch Processing**: Processes content in manageable batches
- **Caching**: Results cached in Redis to avoid redundant analysis
- **Content Limits**: Restricts analysis to 100K characters per bookmark

## Error Handling

- **API Failures**: Falls back to basic analysis if Gemini unavailable
- **Content Issues**: Skips malformed or empty content gracefully
- **User Isolation**: Ensures no cross-user data contamination
- **Logging**: Comprehensive logging for debugging and monitoring

## Example Output

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

