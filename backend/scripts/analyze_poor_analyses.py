#!/usr/bin/env python3
"""
Analyze and re-analyze bookmarks with poor or empty content analysis
Identifies bookmarks with:
- Empty or missing analysis
- Poor quality analysis (empty technologies, key_concepts, summary)
- Generic/fallback analysis results
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from run_production import app
from models import db, SavedContent, ContentAnalysis, User
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_poor_analyses(user_id=None):
    """Find bookmarks with poor or empty analyses"""
    with app.app_context():
        try:
            # Query all content analyses
            query = db.session.query(ContentAnalysis).join(
                SavedContent, ContentAnalysis.content_id == SavedContent.id
            )
            
            if user_id:
                query = query.filter(SavedContent.user_id == user_id)
            
            all_analyses = query.all()
            logger.info(f"Total analyses found: {len(all_analyses)}")
            
            poor_analyses = []
            
            for analysis in all_analyses:
                content = analysis.content
                analysis_data = analysis.analysis_data or {}
                
                # Check for poor analysis indicators
                issues = []
                
                # 1. Empty or missing technologies
                technologies = analysis_data.get('technologies', [])
                if not technologies or len(technologies) == 0:
                    issues.append("empty_technologies")
                
                # 2. Empty or missing key_concepts
                key_concepts = analysis_data.get('key_concepts', [])
                if not key_concepts or len(key_concepts) == 0:
                    issues.append("empty_key_concepts")
                
                # 3. Generic/fallback summary
                summary = analysis_data.get('summary', '')
                basic_summary = analysis_data.get('basic_summary', '')
                if (not summary or 
                    summary.lower() in ['content about general topics', 'content about', ''] or
                    basic_summary.lower() in ['content about general topics', 'content about', '']):
                    issues.append("generic_summary")
                
                # 4. Very low relevance score
                relevance_score = analysis_data.get('relevance_score', 0)
                if relevance_score < 50:
                    issues.append("low_relevance")
                
                # 5. Missing or empty analysis_data
                if not analysis_data or len(analysis_data) == 0:
                    issues.append("empty_analysis_data")
                
                # 6. Check if technologies are generic fallbacks
                if technologies and len(technologies) == 1:
                    generic_techs = ['Web Development', 'Mobile Development', 'Data Science', 'General Programming']
                    if technologies[0] in generic_techs:
                        issues.append("generic_technologies")
                
                # 7. Check if key_concepts are generic
                if key_concepts and len(key_concepts) == 1:
                    if key_concepts[0].lower() in ['general content', 'untitled', 'unknown']:
                        issues.append("generic_key_concepts")
                
                if issues:
                    poor_analyses.append({
                        'content_id': content.id,
                        'content_title': content.title,
                        'content_url': content.url,
                        'user_id': content.user_id,
                        'analysis_id': analysis.id,
                        'issues': issues,
                        'technologies': technologies,
                        'key_concepts': key_concepts,
                        'summary': summary,
                        'relevance_score': relevance_score
                    })
            
            return poor_analyses
            
        except Exception as e:
            logger.error(f"Error finding poor analyses: {e}")
            import traceback
            traceback.print_exc()
            return []

def re_analyze_poor_content(poor_analyses, user_id=None):
    """Re-analyze bookmarks with poor analyses"""
    # Import ContentAnalysisEngine
    from scripts.content_analysis_script import ContentAnalysisEngine
    
    if not poor_analyses:
        logger.info("No poor analyses found to re-analyze")
        return
    
    logger.info(f"Found {len(poor_analyses)} bookmarks with poor analyses")
    logger.info("=" * 80)
    
    # Group by user_id
    analyses_by_user = {}
    for analysis_info in poor_analyses:
        uid = analysis_info['user_id']
        if uid not in analyses_by_user:
            analyses_by_user[uid] = []
        analyses_by_user[uid].append(analysis_info)
    
    total_reanalyzed = 0
    total_failed = 0
    
    for uid, analyses in analyses_by_user.items():
        logger.info(f"\nProcessing user {uid}: {len(analyses)} bookmarks to re-analyze")
        
        try:
            # Create analysis engine for this user
            engine = ContentAnalysisEngine(user_id=uid, use_user_api_key=True, delay_between_requests=3.0)
            
            # Initialize analyzer (similar to analyze_user_content method)
            # This must be done before calling _analyze_single_content
            if engine.use_user_api_key and engine.analyzer is None:
                try:
                    from services.multi_user_api_manager import get_user_api_key
                    engine.user_api_key = get_user_api_key(uid)
                    if engine.user_api_key:
                        logger.info(f"Using user {uid}'s API key for analysis")
                    else:
                        logger.warning(f"No user API key found for user {uid}, using default")
                except Exception as e:
                    logger.warning(f"Could not get user API key: {e}")
            
            # Initialize analyzer - CRITICAL: must be done before _analyze_single_content
            if engine.analyzer is None:
                from utils.gemini_utils import GeminiAnalyzer
                engine.analyzer = GeminiAnalyzer(api_key=engine.user_api_key)
                logger.info(f"Initialized GeminiAnalyzer for user {uid}")
            
            # Verify analyzer is initialized
            if engine.analyzer is None:
                logger.error(f"Failed to initialize analyzer for user {uid}")
                total_failed += len(analyses)
                continue
            
            # Re-analyze each bookmark
            for analysis_info in analyses:
                content_id = analysis_info['content_id']
                content_title = analysis_info['content_title']
                issues = analysis_info['issues']
                
                logger.info(f"\nRe-analyzing: {content_title[:60]}...")
                logger.info(f"  Issues: {', '.join(issues)}")
                logger.info(f"  Current tech: {analysis_info['technologies']}")
                logger.info(f"  Current concepts: {analysis_info['key_concepts']}")
                
                try:
                    # Get the content
                    content = SavedContent.query.filter_by(id=content_id).first()
                    if not content:
                        logger.warning(f"  Content {content_id} not found, skipping")
                        total_failed += 1
                        continue
                    
                    # Delete old analysis
                    old_analysis = ContentAnalysis.query.filter_by(content_id=content_id).first()
                    if old_analysis:
                        db.session.delete(old_analysis)
                        db.session.commit()
                    
                    # Re-analyze
                    analysis_result = engine._analyze_single_content(content)
                    
                    if analysis_result:
                        new_tech = analysis_result.get('technologies', [])
                        new_concepts = analysis_result.get('key_concepts', [])
                        new_summary = analysis_result.get('summary', '')
                        
                        logger.info(f"  ✅ Re-analyzed successfully")
                        logger.info(f"  New tech: {new_tech}")
                        logger.info(f"  New concepts: {new_concepts}")
                        logger.info(f"  New summary: {new_summary[:80]}...")
                        
                        total_reanalyzed += 1
                    else:
                        logger.warning(f"  ⚠️  Analysis returned None")
                        total_failed += 1
                    
                    # Add delay between requests
                    import time
                    time.sleep(3.0)
                    
                except Exception as e:
                    logger.error(f"  ❌ Error re-analyzing content {content_id}: {e}")
                    total_failed += 1
                    continue
            
        except Exception as e:
            logger.error(f"Error processing user {uid}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    logger.info("\n" + "=" * 80)
    logger.info(f"Re-analysis complete:")
    logger.info(f"  ✅ Successfully re-analyzed: {total_reanalyzed}")
    logger.info(f"  ❌ Failed: {total_failed}")
    logger.info(f"  📊 Total processed: {len(poor_analyses)}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Find and re-analyze bookmarks with poor analyses')
    parser.add_argument('--user-id', type=int, help='User ID to analyze (optional, analyzes all users if not specified)')
    parser.add_argument('--dry-run', action='store_true', help='Only show poor analyses without re-analyzing')
    parser.add_argument('--export', type=str, help='Export poor analysis IDs to file')
    
    args = parser.parse_args()
    
    with app.app_context():
        logger.info("=" * 80)
        logger.info("Finding bookmarks with poor or empty analyses...")
        logger.info("=" * 80)
        
        poor_analyses = find_poor_analyses(user_id=args.user_id)
        
        if not poor_analyses:
            logger.info("✅ No poor analyses found! All analyses look good.")
            return
        
        # Show summary
        logger.info(f"\n📊 Found {len(poor_analyses)} bookmarks with poor analyses:")
        logger.info("=" * 80)
        
        # Count by issue type
        issue_counts = {}
        for analysis in poor_analyses:
            for issue in analysis['issues']:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        logger.info("\nIssues breakdown:")
        for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {issue}: {count} bookmarks")
        
        # Show sample
        logger.info("\nSample poor analyses:")
        for i, analysis in enumerate(poor_analyses[:10], 1):
            logger.info(f"\n{i}. {analysis['content_title'][:60]}...")
            logger.info(f"   URL: {analysis['content_url'][:80]}")
            logger.info(f"   Issues: {', '.join(analysis['issues'])}")
            logger.info(f"   Tech: {analysis['technologies']}")
            logger.info(f"   Concepts: {analysis['key_concepts']}")
            logger.info(f"   Summary: {analysis['summary'][:60]}...")
        
        if len(poor_analyses) > 10:
            logger.info(f"\n... and {len(poor_analyses) - 10} more")
        
        # Export if requested
        if args.export:
            content_ids = [a['content_id'] for a in poor_analyses]
            with open(args.export, 'w') as f:
                f.write(','.join(map(str, content_ids)))
            logger.info(f"\n✅ Exported {len(content_ids)} content IDs to {args.export}")
        
        # Re-analyze if not dry run
        if not args.dry_run:
            logger.info("\n" + "=" * 80)
            logger.info("Starting re-analysis...")
            logger.info("=" * 80)
            re_analyze_poor_content(poor_analyses, user_id=args.user_id)
        else:
            logger.info("\n🔍 DRY RUN - No re-analysis performed")
            logger.info("Run without --dry-run to re-analyze these bookmarks")

if __name__ == '__main__':
    main()

