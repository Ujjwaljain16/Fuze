#!/usr/bin/env python3
"""
Content Analysis Script for User Recommendations
Analyzes saved bookmarks content to generate personalized recommendations
Supports multi-user architecture - analyzes content per user
"""

import sys
import os
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter
import statistics

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from models import db, SavedContent, ContentAnalysis, User
from utils.gemini_utils import GeminiAnalyzer
from utils.redis_utils import redis_cache
from services.multi_user_api_manager import get_user_api_key
import flask

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ContentAnalysisEngine:
    """Engine for analyzing user content and generating recommendations"""

    def __init__(self, user_id: int, use_user_api_key: bool = True, delay_between_requests: float = 3.0):
        """
        Initialize analysis engine for a specific user

        Args:
            user_id: User ID to analyze content for
            use_user_api_key: Whether to use user's own API key if available
            delay_between_requests: Delay between API requests in seconds
        """
        self.user_id = user_id
        self.use_user_api_key = use_user_api_key
        self.delay_between_requests = delay_between_requests
        self.user_api_key = None
        self.analyzer = None  # Initialize later when Flask context is available

        # Analysis results
        self.content_analyses = []
        self.skill_profile = {}
        self.learning_path = {}
        self.recommendations = {}

    def analyze_user_content(self, force_refresh: bool = False) -> Dict:
        """
        Analyze all saved content for the user

        Args:
            force_refresh: If True, re-analyze content that was already analyzed

        Returns:
            Dict containing analysis results and recommendations
        """
        logger.info(f"Starting content analysis for user {self.user_id}")

        # Initialize analyzer with user API key (now that Flask context is available)
        if self.use_user_api_key and self.analyzer is None:
            try:
                from services.multi_user_api_manager import get_user_api_key
                self.user_api_key = get_user_api_key(self.user_id)
                if self.user_api_key:
                    logger.info(f"Using user's API key for analysis")
                else:
                    logger.info(f"No user API key found, using default")
            except Exception as e:
                logger.warning(f"Could not get user API key: {e}")

        # Initialize analyzer
        if self.analyzer is None:
            self.analyzer = GeminiAnalyzer(api_key=self.user_api_key)

        # Get all user's saved content
        total_bookmarks = SavedContent.query.filter_by(user_id=self.user_id).count()
        logger.info(f"Total bookmarks for user {self.user_id}: {total_bookmarks}")

        query = SavedContent.query.filter_by(user_id=self.user_id)

        # Filter out already analyzed content unless force refresh
        if not force_refresh:
            # Get analyzed content IDs for THIS user only (join through SavedContent)
            analyzed_content_ids = db.session.query(ContentAnalysis.content_id).join(
                SavedContent, ContentAnalysis.content_id == SavedContent.id
            ).filter(SavedContent.user_id == self.user_id).all()
            analyzed_ids = {row[0] for row in analyzed_content_ids}
            already_analyzed = len(analyzed_ids)
            logger.info(f"Already analyzed: {already_analyzed} bookmarks")
            query = query.filter(~SavedContent.id.in_(analyzed_ids))
        else:
            already_analyzed = ContentAnalysis.query.join(
                SavedContent, ContentAnalysis.content_id == SavedContent.id
            ).filter(SavedContent.user_id == self.user_id).count()
            logger.info(f"Force refresh mode: Will re-analyze {already_analyzed} existing analyses")

        saved_content = query.all()
        logger.info(f"Found {len(saved_content)} bookmarks to analyze")

        if not saved_content:
            logger.info("No new content to analyze")
            return self._generate_empty_analysis()

        # Analyze content in batches
        analyzed_count = 0
        skipped_count = 0
        rate_limited_count = 0
        failed_count = 0

        for content in saved_content:
            try:
                # Check rate limit before processing
                if self.use_user_api_key:
                    try:
                        from services.multi_user_api_manager import check_user_rate_limit
                        rate_limit_status = check_user_rate_limit(self.user_id)
                        if not rate_limit_status['can_make_request']:
                            wait_time = rate_limit_status['wait_time_seconds']
                            logger.warning(f"Rate limit exceeded. Waiting {wait_time} seconds...")
                            rate_limited_count += 1
                            import time
                            time.sleep(min(wait_time, 60))  # Wait up to 60 seconds
                            continue  # Skip this item and try again later
                    except Exception as rate_limit_error:
                        logger.warning(f"Could not check rate limit: {rate_limit_error}")

                # Analyze all content regardless of quality or emptiness
                # Use fallback content if extracted_text is empty
                if not content.extracted_text or not content.extracted_text.strip():
                    # Use minimal fallback content for analysis (same as background_analysis_service)
                    content.extracted_text = content.title or content.url or "Untitled content"
                    logger.debug(f"Using fallback content for analysis: {content.title}")

                # Analyze content (no quality score filtering - analyze everything)
                analysis_result = self._analyze_single_content(content)

                if analysis_result:
                    self.content_analyses.append(analysis_result)
                    analyzed_count += 1

                    # Record API usage for rate limiting
                    if self.use_user_api_key:
                        try:
                            from services.multi_user_api_manager import record_user_request
                            record_user_request(self.user_id)
                        except Exception as record_error:
                            logger.warning(f"Could not record API usage: {record_error}")

                    # Log progress
                    if analyzed_count % 5 == 0:  # Log more frequently
                        logger.info(f"Analyzed {analyzed_count}/{len(saved_content)} bookmarks")

                    # Add delay between requests to avoid rate limiting (gradual processing)
                    import time
                    time.sleep(self.delay_between_requests)

                else:
                    # Analysis failed
                    failed_count += 1
                    logger.debug(f"Analysis failed for content: {content.title}")

                    # Still add small delay for failed analyses
                    import time
                    time.sleep(self.delay_between_requests * 0.2)  # Shorter delay for failures

            except Exception as e:
                logger.error(f"Error analyzing content {content.id}: {e}")
                continue

        logger.info(f"Analysis complete: {analyzed_count} analyzed, {skipped_count} skipped, {rate_limited_count} rate limited, {failed_count} failed")

        # Generate comprehensive analysis
        analysis_results = self._generate_comprehensive_analysis()

        # Save analysis results to database
        self._save_analysis_results(analysis_results)

        return analysis_results

    def _analyze_single_content(self, content: SavedContent) -> Optional[Dict]:
        """
        Analyze a single piece of content

        Args:
            content: SavedContent object to analyze

        Returns:
            Dict with analysis results or None if analysis failed
        """
        try:
            # Prepare content for analysis
            title = content.title or "Untitled"
            description = content.notes or ""
            extracted_text = content.extracted_text or ""

            # Log content length for debugging (analyze all content regardless of length)
            content_length = len(extracted_text.strip())
            logger.debug(f"Analyzing content '{title[:50]}...' with {content_length} characters")

            # Analyze with Gemini
            analysis = self.analyzer.analyze_bookmark_content(
                title=title,
                description=description,
                content=extracted_text,
                url=content.url
            )

            if not analysis:
                logger.warning(f"Analysis failed for content {content.id}")
                return None

            # Add content metadata
            analysis.update({
                'content_id': content.id,
                'title': title,
                'url': content.url,
                'analyzed_at': datetime.utcnow().isoformat(),
                'quality_score': content.quality_score
            })

            # Save analysis result immediately to database
            self._save_single_analysis(content.id, analysis)
            logger.debug(f"Saved analysis for content {content.id} to database")

            return analysis

        except Exception as e:
            logger.error(f"Error in single content analysis: {e}")
            return None

    def _save_single_analysis(self, content_id: int, analysis_result: Dict):
        """Save a single analysis result to database immediately"""
        try:
            # Check if analysis already exists (avoid duplicates/race conditions)
            existing_analysis = ContentAnalysis.query.filter_by(content_id=content_id).first()
            if existing_analysis:
                # If force_refresh is False, we shouldn't hit this (query filters them out)
                # But handle race conditions gracefully
                logger.debug(f"Analysis already exists for content {content_id}, updating instead of skipping")
                # Update existing analysis instead of skipping
                existing_analysis.analysis_data = analysis_result
                existing_analysis.key_concepts = ','.join(analysis_result.get('key_concepts', [])) if isinstance(analysis_result.get('key_concepts', []), list) else str(analysis_result.get('key_concepts', ''))
                existing_analysis.content_type = analysis_result.get('content_type', 'article')
                existing_analysis.difficulty_level = analysis_result.get('difficulty', 'intermediate')
                existing_analysis.technology_tags = ','.join(analysis_result.get('technologies', [])) if isinstance(analysis_result.get('technologies', []), list) else str(analysis_result.get('technologies', ''))
                existing_analysis.relevance_score = analysis_result.get('relevance_score', 50)
                existing_analysis.updated_at = datetime.now()
                db.session.commit()
                return

            # Extract key information from analysis
            key_concepts = analysis_result.get('key_concepts', [])
            content_type = analysis_result.get('content_type', 'article')
            difficulty_level = analysis_result.get('difficulty', 'intermediate')
            technology_tags = analysis_result.get('technologies', [])
            relevance_score = analysis_result.get('relevance_score', 50)

            # Create analysis record
            analysis_record = ContentAnalysis(
                content_id=content_id,
                analysis_data=analysis_result,
                key_concepts=','.join(key_concepts) if isinstance(key_concepts, list) else str(key_concepts),
                content_type=content_type,
                difficulty_level=difficulty_level,
                technology_tags=','.join(technology_tags) if isinstance(technology_tags, list) else str(technology_tags),
                relevance_score=relevance_score
            )

            # Save to database immediately
            db.session.add(analysis_record)
            db.session.commit()

            logger.debug(f"Successfully saved analysis for content {content_id}")

        except Exception as e:
            logger.error(f"Error saving single analysis for content {content_id}: {e}")
            db.session.rollback()

    def _generate_comprehensive_analysis(self) -> Dict:
        """
        Generate comprehensive analysis from all content analyses

        Returns:
            Dict with comprehensive analysis and recommendations
        """
        if not self.content_analyses:
            return self._generate_empty_analysis()

        # Aggregate technologies
        all_technologies = []
        content_types = Counter()
        difficulties = Counter()
        intents = Counter()
        all_key_concepts = []
        skill_levels = Counter()

        for analysis in self.content_analyses:
            # Technologies
            technologies = analysis.get('technologies', [])
            if isinstance(technologies, list):
                all_technologies.extend(technologies)

            # Content types
            content_type = analysis.get('content_type', 'unknown')
            content_types[content_type] += 1

            # Difficulties
            difficulty = analysis.get('difficulty', 'unknown')
            difficulties[difficulty] += 1

            # Learning intents
            intent = analysis.get('intent', 'unknown')
            intents[intent] += 1

            # Key concepts
            key_concepts = analysis.get('key_concepts', [])
            if isinstance(key_concepts, list):
                all_key_concepts.extend(key_concepts)

            # Target audience (skill level)
            target_audience = analysis.get('target_audience', 'unknown')
            skill_levels[target_audience] += 1

        # Calculate technology expertise
        tech_counter = Counter(all_technologies)
        top_technologies = tech_counter.most_common(20)

        # Calculate concept expertise
        concept_counter = Counter(all_key_concepts)
        top_concepts = concept_counter.most_common(20)

        # Determine user's skill level
        primary_skill_level = difficulties.most_common(1)[0][0] if difficulties else 'intermediate'
        audience_level = skill_levels.most_common(1)[0][0] if skill_levels else 'intermediate'

        # Generate learning path insights
        learning_path = self._generate_learning_path(content_types, difficulties, intents)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            top_technologies, top_concepts, primary_skill_level, audience_level
        )

        # Calculate engagement metrics
        engagement_metrics = self._calculate_engagement_metrics()

        return {
            'user_id': self.user_id,
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'total_content_analyzed': len(self.content_analyses),

            # Content overview
            'content_breakdown': {
                'content_types': dict(content_types.most_common(10)),
                'difficulties': dict(difficulties.most_common()),
                'learning_intents': dict(intents.most_common()),
                'skill_levels': dict(skill_levels.most_common())
            },

            # Technology expertise
            'technology_expertise': {
                'top_technologies': top_technologies,
                'technology_count': len(set(all_technologies)),
                'primary_technologies': [tech for tech, _ in top_technologies[:5]]
            },

            # Learning insights
            'learning_profile': {
                'primary_skill_level': primary_skill_level,
                'target_audience_level': audience_level,
                'learning_path': learning_path
            },

            # Key concepts
            'concept_expertise': {
                'top_concepts': top_concepts,
                'concept_count': len(set(all_key_concepts)),
                'core_concepts': [concept for concept, _ in top_concepts[:10]]
            },

            # Recommendations
            'recommendations': recommendations,

            # Engagement metrics
            'engagement_metrics': engagement_metrics,

            # Raw analyses (for detailed inspection)
            'content_analyses': self.content_analyses[:50]  # Limit to first 50 for size
        }

    def _generate_learning_path(self, content_types: Counter, difficulties: Counter, intents: Counter) -> Dict:
        """Generate learning path insights"""
        learning_path = {
            'current_focus': intents.most_common(1)[0][0] if intents else 'general',
            'difficulty_distribution': dict(difficulties),
            'content_type_distribution': dict(content_types),
            'learning_trajectory': []
        }

        # Determine learning trajectory
        if difficulties['beginner'] > difficulties['intermediate'] > difficulties['advanced']:
            learning_path['learning_trajectory'] = ['beginner', 'intermediate', 'advanced']
        elif difficulties['intermediate'] > difficulties['beginner']:
            learning_path['learning_trajectory'] = ['intermediate', 'advanced']
        else:
            learning_path['learning_trajectory'] = ['general']

        return learning_path

    def _generate_recommendations(self, top_technologies, top_concepts, skill_level, audience_level) -> Dict:
        """Generate personalized recommendations"""
        recommendations = {
            'skill_gaps': [],
            'next_steps': [],
            'content_suggestions': [],
            'project_ideas': [],
            'learning_resources': []
        }

        # Technology recommendations
        primary_tech = [tech for tech, _ in top_technologies[:3]]
        recommendations['skill_gaps'] = [
            f"Deepen expertise in {tech}" for tech in primary_tech
        ]

        # Learning recommendations based on skill level
        if skill_level == 'beginner':
            recommendations['next_steps'] = [
                "Focus on fundamental concepts and basic implementations",
                "Practice with simple projects and tutorials",
                "Build a strong foundation before advancing"
            ]
        elif skill_level == 'intermediate':
            recommendations['next_steps'] = [
                "Work on real-world projects and complex implementations",
                "Explore advanced patterns and best practices",
                "Contribute to open source or collaborate on projects"
            ]
        else:  # advanced
            recommendations['next_steps'] = [
                "Focus on architecture design and system optimization",
                "Mentor others and contribute to the community",
                "Explore cutting-edge technologies and research"
            ]

        # Content type recommendations
        recommendations['content_suggestions'] = [
            "More hands-on tutorials and practical examples",
            "Case studies and real-world implementations",
            "Advanced topics in your primary technologies"
        ]

        # Project ideas based on technologies
        if primary_tech:
            recommendations['project_ideas'] = [
                f"Build a full-stack application using {primary_tech[0]}",
                f"Create a library or tool for {primary_tech[0]} developers",
                f"Develop a portfolio project showcasing {', '.join(primary_tech[:2])}"
            ]

        # Learning resources
        recommendations['learning_resources'] = [
            "Official documentation and API references",
            "Online courses and certifications",
            "Community forums and discussion groups",
            "Technical blogs and newsletters"
        ]

        return recommendations

    def _calculate_engagement_metrics(self) -> Dict:
        """Calculate engagement and learning metrics"""
        if not self.content_analyses:
            return {}

        # Calculate average quality scores
        quality_scores = [analysis.get('quality_indicators', {}).get('completeness', 0)
                         for analysis in self.content_analyses]
        avg_quality = statistics.mean(quality_scores) if quality_scores else 0

        # Calculate learning diversity
        technologies = set()
        concepts = set()
        for analysis in self.content_analyses:
            technologies.update(analysis.get('technologies', []))
            concepts.update(analysis.get('key_concepts', []))

        return {
            'total_technologies_covered': len(technologies),
            'total_concepts_covered': len(concepts),
            'average_content_quality': round(avg_quality, 1),
            'content_diversity_score': min(len(technologies) + len(concepts), 100),
            'learning_breadth': len(set(analysis.get('content_type', '')
                                      for analysis in self.content_analyses))
        }

    def _generate_empty_analysis(self) -> Dict:
        """Generate empty analysis structure"""
        return {
            'user_id': self.user_id,
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'total_content_analyzed': 0,
            'message': 'No content available for analysis',
            'recommendations': {
                'next_steps': ['Save some bookmarks to get personalized recommendations!']
            }
        }

    def _save_analysis_results(self, analysis_results: Dict):
        """Save analysis summary/cache data (individual analyses are saved immediately)"""
        try:
            # All individual content analyses have already been saved during analysis
            # Just save the user-level analysis summary/cache data
            cache_key = f"user_analysis:{self.user_id}"
            redis_cache.set_cache(cache_key, analysis_results, ttl=86400*7)  # 7 days

            # Log completion
            analyzed_count = len(self.content_analyses)
            logger.info(f"Analysis complete: {analyzed_count} content analyses saved to database for user {self.user_id}")

        except Exception as e:
            logger.error(f"Error saving analysis summary: {e}")
            # Don't rollback since individual analyses are already committed

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='Analyze user content for recommendations')
    parser.add_argument('--user-id', type=int, required=True,
                       help='User ID to analyze content for')
    parser.add_argument('--force-refresh', action='store_true',
                       help='Re-analyze content that was already analyzed')
    parser.add_argument('--output-file', type=str,
                       help='Save results to JSON file')
    parser.add_argument('--no-user-api-key', action='store_true',
                       help='Use default API key instead of user-specific key')
    parser.add_argument('--delay', type=float, default=3.0,
                       help='Delay between API requests in seconds (default: 3.0)')

    args = parser.parse_args()

    # Setup Flask app context for database access
    app = flask.Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://localhost/fuze')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        # Create analysis engine
        engine = ContentAnalysisEngine(
            user_id=args.user_id,
            use_user_api_key=not args.no_user_api_key,
            delay_between_requests=args.delay
        )

        # Run analysis
        logger.info(f"Starting content analysis for user {args.user_id}")
        results = engine.analyze_user_content(force_refresh=args.force_refresh)

        # Output results
        if args.output_file:
            with open(args.output_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {args.output_file}")
        else:
            # Print summary
            print("\n" + "="*80)
            print(f"CONTENT ANALYSIS RESULTS - User {args.user_id}")
            print("="*80)

            print(f"\n📊 Total Content Analyzed: {results.get('total_content_analyzed', 0)}")

            if results.get('total_content_analyzed', 0) > 0:
                print(f"\n🛠️  Technology Expertise:")
                tech_expertise = results.get('technology_expertise', {})
                for tech, count in tech_expertise.get('top_technologies', [])[:5]:
                    print(f"  • {tech}: {count} bookmarks")

                print(f"\n📚 Learning Profile:")
                learning = results.get('learning_profile', {})
                print(f"  • Primary Skill Level: {learning.get('primary_skill_level', 'unknown')}")
                print(f"  • Target Audience: {learning.get('target_audience_level', 'unknown')}")

                print(f"\n🎯 Recommendations:")
                recs = results.get('recommendations', {})
                for step in recs.get('next_steps', [])[:3]:
                    print(f"  • {step}")

                print(f"\n📈 Engagement Metrics:")
                metrics = results.get('engagement_metrics', {})
                print(f"  • Technologies Covered: {metrics.get('total_technologies_covered', 0)}")
                print(f"  • Concepts Covered: {metrics.get('total_concepts_covered', 0)}")
                print(f"  • Average Quality: {metrics.get('average_content_quality', 0)}%")
            else:
                print("\n📝 No content analyzed yet.")
                print("💡 Save some bookmarks to get personalized recommendations!")

            print("\n" + "="*80)

if __name__ == '__main__':
    main()
