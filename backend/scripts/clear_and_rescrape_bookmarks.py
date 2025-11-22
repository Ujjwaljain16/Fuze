#!/usr/bin/env python3
"""
Script to clear extraction data and re-scrape all bookmarks with enhanced scraper
This tests the new Scrapling integration and optimized embeddings
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from flask import Flask
from config import DevelopmentConfig
from models import db, SavedContent, ContentAnalysis
from scrapers.scrapling_enhanced_scraper import scrape_url_enhanced
from utils.embedding_utils import get_embedding
import logging
from datetime import datetime
from urllib.parse import urlparse
from collections import defaultdict
import re

# Try to import tqdm for progress bar, fallback if not available
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    # Simple progress bar fallback
    def tqdm(iterable, desc=""):
        return iterable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
db.init_app(app)

def analyze_extraction_quality():
    """Analyze current state of extractions and embeddings"""
    with app.app_context():
        try:
            total = db.session.query(SavedContent).count()
            
            # Empty embeddings (NULL)
            empty_embeddings = db.session.query(SavedContent).filter(
                SavedContent.embedding.is_(None)
            ).count()
            
            # Empty extracted_text
            empty_text = db.session.query(SavedContent).filter(
                db.or_(
                    SavedContent.extracted_text.is_(None),
                    SavedContent.extracted_text == ''
                )
            ).count()
            
            # "Unable to extract" messages
            unable_to_extract = db.session.query(SavedContent).filter(
                SavedContent.extracted_text.like('%Unable to extract%')
            ).count()
            
            # Get actual bookmarks with "Unable to extract"
            unable_to_extract_bookmarks = db.session.query(SavedContent).filter(
                SavedContent.extracted_text.like('%Unable to extract%')
            ).limit(20).all()
            
            # "extraction failed" messages
            extraction_failed = db.session.query(SavedContent).filter(
                SavedContent.extracted_text.like('%extraction failed%')
            ).count()
            
            # Get actual bookmarks with "extraction failed"
            extraction_failed_bookmarks = db.session.query(SavedContent).filter(
                SavedContent.extracted_text.like('%extraction failed%')
            ).limit(20).all()
            
            # Very short content (< 100 chars) but not empty
            short_content = db.session.query(SavedContent).filter(
                db.func.length(SavedContent.extracted_text) < 100,
                SavedContent.extracted_text.isnot(None),
                SavedContent.extracted_text != ''
            ).count()
            
            # Low quality scores (< 5)
            low_quality = db.session.query(SavedContent).filter(
                SavedContent.quality_score < 5,
                SavedContent.quality_score.isnot(None)
            ).count()
            
            # Weird text patterns (CSS/JS-like content)
            weird_text_count = 0
            weird_text_examples = []
            all_content = db.session.query(SavedContent).filter(
                SavedContent.extracted_text.isnot(None),
                SavedContent.extracted_text != ''
            ).limit(1000).all()
            
            for content in all_content:
                text = content.extracted_text
                if not text:
                    continue
                
                # Check for CSS patterns
                css_patterns = [
                    r'\.[a-zA-Z0-9_-]+\s*\{[^}]*\}',  # CSS classes
                    r'#[a-zA-Z0-9_-]+\s*\{[^}]*\}',   # CSS IDs
                    r'@media[^{]*\{[^}]*\}',            # Media queries
                    r'[a-zA-Z-]+\s*:\s*[^;]+;',        # CSS properties
                ]
                
                # Check for high special character ratio (likely CSS/JS)
                special_chars = sum(1 for c in text if c in '{}(),;:[]=+-*/%<>!&|')
                if len(text) > 0:
                    special_ratio = special_chars / len(text)
                    if special_ratio > 0.3:  # More than 30% special chars
                        weird_text_count += 1
                        if len(weird_text_examples) < 5:
                            weird_text_examples.append({
                                'url': content.url,
                                'preview': text[:200] + '...' if len(text) > 200 else text,
                                'special_ratio': f"{special_ratio:.2%}"
                            })
                        continue
                
                # Check for CSS patterns
                for pattern in css_patterns:
                    if re.search(pattern, text[:1000]):  # Check first 1000 chars
                        weird_text_count += 1
                        if len(weird_text_examples) < 5:
                            weird_text_examples.append({
                                'url': content.url,
                                'preview': text[:200] + '...' if len(text) > 200 else text,
                                'pattern': 'CSS pattern detected'
                            })
                        break
            
            # Quality score distribution
            quality_dist = {}
            for score in range(0, 11):
                count = db.session.query(SavedContent).filter(
                    SavedContent.quality_score == score
                ).count()
                if count > 0:
                    quality_dist[score] = count
            
            # Content length distribution
            length_ranges = {
                '0': 0,
                '1-100': 0,
                '101-500': 0,
                '501-2000': 0,
                '2001-10000': 0,
                '10000+': 0
            }
            
            all_with_text = db.session.query(SavedContent).filter(
                SavedContent.extracted_text.isnot(None),
                SavedContent.extracted_text != ''
            ).all()
            
            for content in all_with_text:
                length = len(content.extracted_text)
                if length == 0:
                    length_ranges['0'] += 1
                elif length <= 100:
                    length_ranges['1-100'] += 1
                elif length <= 500:
                    length_ranges['101-500'] += 1
                elif length <= 2000:
                    length_ranges['501-2000'] += 1
                elif length <= 10000:
                    length_ranges['2001-10000'] += 1
                else:
                    length_ranges['10000+'] += 1
            
            # Print summary
            logger.info("")
            logger.info("=" * 80)
            logger.info("EXTRACTION QUALITY ANALYSIS")
            logger.info("=" * 80)
            logger.info(f"Total bookmarks: {total}")
            logger.info("")
            logger.info("ISSUES:")
            logger.info(f"   Empty embeddings: {empty_embeddings} ({empty_embeddings/total*100:.1f}%)")
            logger.info(f"   Empty extracted_text: {empty_text} ({empty_text/total*100:.1f}%)")
            logger.info(f"   'Unable to extract' messages: {unable_to_extract}")
            logger.info(f"   'extraction failed' messages: {extraction_failed}")
            logger.info(f"    Short content (< 100 chars): {short_content}")
            logger.info(f"    Low quality scores (< 5): {low_quality}")
            logger.info(f"    Weird text patterns (CSS/JS): {weird_text_count} (from sample of {len(all_content)})")
            logger.info("")
            logger.info("CONTENT LENGTH DISTRIBUTION:")
            for range_name, count in length_ranges.items():
                if count > 0:
                    logger.info(f"  {range_name} chars: {count} ({count/len(all_with_text)*100:.1f}%)" if len(all_with_text) > 0 else f"  {range_name} chars: {count}")
            logger.info("")
            logger.info("QUALITY SCORE DISTRIBUTION:")
            if quality_dist:
                for score in sorted(quality_dist.keys(), reverse=True):
                    logger.info(f"  Score {score}: {quality_dist[score]} bookmarks ({quality_dist[score]/total*100:.1f}%)")
            else:
                logger.info("  No quality scores set")
            
            if weird_text_examples:
                logger.info("")
                logger.info("WEIRD TEXT EXAMPLES (CSS/JS patterns):")
                for i, example in enumerate(weird_text_examples, 1):
                    logger.info(f"  {i}. {example['url'][:70]}")
                    logger.info(f"     Special chars ratio: {example.get('special_ratio', example.get('pattern', 'N/A'))}")
                    logger.info(f"     Preview: {example['preview'][:100]}...")
            
            # Calculate success rate
            good_content = total - empty_text - unable_to_extract - extraction_failed
            success_rate = (good_content / total * 100) if total > 0 else 0
            
            logger.info("")
            logger.info("SUMMARY:")
            logger.info(f"   Good extractions: {good_content} ({success_rate:.1f}%)")
            logger.info(f"   Failed/Empty: {empty_text + unable_to_extract + extraction_failed} ({(empty_text + unable_to_extract + extraction_failed)/total*100:.1f}%)")
            logger.info("=" * 80)
            logger.info("")
            
            return {
                'total': total,
                'empty_embeddings': empty_embeddings,
                'empty_text': empty_text,
                'unable_to_extract': unable_to_extract,
                'extraction_failed': extraction_failed,
                'short_content': short_content,
                'low_quality': low_quality,
                'weird_text_count': weird_text_count,
                'quality_dist': quality_dist,
                'length_ranges': length_ranges,
                'success_rate': success_rate
            }
            
        except Exception as e:
            logger.error(f"Error analyzing extraction quality: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

def clear_extraction_data():
    """Clear extracted_text, embedding, quality_score, and related analysis data"""
    with app.app_context():
        try:
            logger.info("Clearing extraction data from saved_content table...")
            
            # Count items before clearing
            total_count = db.session.query(SavedContent).count()
            logger.info(f"Total bookmarks: {total_count}")
            
            # Clear extraction-related columns
            # Note: We keep the bookmark itself (id, user_id, url, title, notes, saved_at)
            # We only clear: extracted_text, embedding, quality_score
            
            # Use SQLAlchemy update with proper null handling
            updated = db.session.query(SavedContent).update({
                SavedContent.extracted_text: None,
                SavedContent.quality_score: None
            }, synchronize_session=False)
            
            # Clear embeddings separately (they're Vector type)
            # Set to NULL using raw SQL for pgvector compatibility
            from sqlalchemy import text
            db.session.execute(text("UPDATE saved_content SET embedding = NULL"))
            
            db.session.commit()
            
            logger.info(f" Cleared extraction data from {updated} bookmarks")
            
            # Also clear related ContentAnalysis records (they'll be regenerated)
            analysis_count = db.session.query(ContentAnalysis).count()
            deleted = db.session.query(ContentAnalysis).delete()
            db.session.commit()
            
            logger.info(f" Deleted {deleted} content analysis records (will be regenerated)")
            
            return total_count
            
        except Exception as e:
            logger.error(f"Error clearing extraction data: {e}")
            db.session.rollback()
            raise

def rescrape_bookmarks(batch_size=10, delay=2):
    """
    Re-scrape all bookmarks with enhanced scraper
    
    Args:
        batch_size: Number of bookmarks to process before committing
        delay: Delay between requests (seconds)
    """
    with app.app_context():
        try:
            # Get all bookmarks without extracted_text
            bookmarks = db.session.query(SavedContent).filter(
                db.or_(
                    SavedContent.extracted_text.is_(None),
                    SavedContent.extracted_text == ''
                )
            ).all()
            
            total = len(bookmarks)
            logger.info(f"Found {total} bookmarks to re-scrape")
            
            if total == 0:
                logger.info("No bookmarks to scrape. All bookmarks already have content.")
                return
            
            successful = 0
            failed = 0
            skipped = 0
            
            # Process with progress bar
            progress_iter = tqdm(bookmarks, desc="Re-scraping bookmarks") if HAS_TQDM else bookmarks
            for i, bookmark in enumerate(progress_iter, 1):
                try:
                    # Handle special URL types
                    if bookmark.url.startswith('file://'):
                        # Extract info from local file URL
                        try:
                            from urllib.parse import unquote
                            path = bookmark.url[7:]  # Remove 'file://'
                            filename = os.path.basename(path)
                            dirname = os.path.dirname(path)
                            content = f"Local file: {unquote(filename)}"
                            if dirname:
                                content += f"\nLocated in: {unquote(dirname)}"
                            if bookmark.title:
                                content += f"\nTitle: {bookmark.title}"

                            extracted_text = content
                            quality_score = 7  # Decent quality for local files
                            scraped_title = bookmark.title or unquote(filename)
                            headings = []
                            meta_description = f"Local file: {unquote(filename)}"
                        except Exception as e:
                            logger.debug(f"Failed to parse file URL {bookmark.url}: {e}")
                            skipped += 1
                            continue

                    elif bookmark.url.startswith('javascript:'):
                        # Handle JavaScript bookmarklets
                        content = f"JavaScript bookmarklet: {bookmark.title or 'Unnamed bookmarklet'}"
                        content += "\n\nThis is a JavaScript bookmarklet that runs custom code when clicked."
                        content += "\n\nBookmarklets are small JavaScript programs stored as bookmarks."

                        extracted_text = content
                        quality_score = 6  # Moderate quality for JS bookmarks
                        scraped_title = bookmark.title or "JavaScript Bookmarklet"
                        headings = ["JavaScript", "Bookmarklet"]
                        meta_description = "JavaScript bookmarklet for browser automation"

                    else:
                        # Normal URL scraping
                        if not HAS_TQDM and i % 10 == 0:
                            logger.info(f"[{i}/{total}] Progress: {i}/{total} ({(i/total*100):.1f}%)")
                        logger.info(f"[{i}/{total}] Scraping: {bookmark.url[:80]}...")
                        scraped = scrape_url_enhanced(bookmark.url)

                        if not scraped:
                            logger.warning(f"   No result from scraper")
                            failed += 1
                            continue

                        extracted_text = scraped.get('content', '')
                        quality_score = scraped.get('quality_score', 0)
                        scraped_title = scraped.get('title', '')
                        headings = scraped.get('headings', [])
                        meta_description = scraped.get('meta_description', '')
                    
                    # Update title if scraped title is better
                    if scraped_title and scraped_title != bookmark.title:
                        bookmark.title = scraped_title[:200]  # Ensure it fits in column
                    
                    # Update extracted_text and quality_score
                    bookmark.extracted_text = extracted_text
                    bookmark.quality_score = quality_score
                    
                    # Always generate embedding - even with minimal content
                    # This ensures semantic search works even when scraping fails
                    # Use the same optimized embedding generation as in bookmarks.py
                    embedding_parts = []

                    # Add title (highest priority)
                    if bookmark.title and bookmark.title.strip():
                        embedding_parts.append(bookmark.title.strip())

                    # Add meta description if available
                    if meta_description and meta_description.strip():
                        embedding_parts.append(meta_description.strip())

                    # Add headings if available
                    if headings:
                        embedding_parts.append(' '.join(headings[:10]))

                    # Add user notes if available
                    if bookmark.notes and bookmark.notes.strip():
                        embedding_parts.append(bookmark.notes.strip())

                    # Add extracted text (first 5000 + last 1000 chars)
                    if extracted_text and extracted_text.strip():
                        text_for_embedding = extracted_text[:5000]
                        if len(extracted_text) > 5000:
                            text_for_embedding += " " + extracted_text[-1000:]
                        embedding_parts.append(text_for_embedding)

                    # Always try to generate embedding - even with minimal content
                    # This ensures we have embeddings for semantic search even when scraping fails
                    content_for_embedding = ' '.join(embedding_parts).strip()

                    # If we have no content at all, use URL as absolute minimum
                    if not content_for_embedding:
                        content_for_embedding = bookmark.url or "unknown content"

                    try:
                        embedding = get_embedding(content_for_embedding)
                        bookmark.embedding = embedding
                        logger.info(f"   Generated embedding from {len(content_for_embedding)} chars (title: {len(bookmark.title or '')} chars, text: {len(extracted_text or '')} chars)")
                    except Exception as embed_error:
                        logger.error(f"   Embedding generation failed: {embed_error}")
                        # Don't leave embedding as None - use a fallback
                        try:
                            fallback_content = f"{bookmark.title or 'Unknown'} {bookmark.url or ''}".strip()
                            if fallback_content:
                                embedding = get_embedding(fallback_content)
                                bookmark.embedding = embedding
                                logger.info(f"   Generated fallback embedding from {len(fallback_content)} chars")
                        except Exception as fallback_error:
                            logger.error(f"   Fallback embedding also failed: {fallback_error}")
                    
                    # Commit in batches
                    if i % batch_size == 0:
                        db.session.commit()
                        logger.info(f"  💾 Committed batch ({i}/{total})")
                    
                    successful += 1
                    logger.info(f"   Quality: {quality_score}, Content: {len(extracted_text)} chars")
                    
                    # Rate limiting delay
                    if delay > 0 and i < total:
                        import time
                        time.sleep(delay)
                    
                except Exception as e:
                    logger.error(f"   Error scraping {bookmark.url}: {e}")
                    failed += 1
                    db.session.rollback()
                    continue
            
            # Final commit
            db.session.commit()
            
            # Summary
            logger.info("=" * 80)
            logger.info("RE-SCRAPING SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Total bookmarks: {total}")
            logger.info(f" Successful: {successful}")
            logger.info(f" Failed: {failed}")
            logger.info(f"  Skipped: {skipped}")
            logger.info(f"Success rate: {(successful/total*100):.1f}%")
            
            # Quality statistics
            with_quality = db.session.query(SavedContent).filter(
                SavedContent.quality_score.isnot(None),
                SavedContent.quality_score >= 5
            ).count()
            
            high_quality = db.session.query(SavedContent).filter(
                SavedContent.quality_score.isnot(None),
                SavedContent.quality_score >= 7
            ).count()
            
            with_embeddings = db.session.query(SavedContent).filter(
                SavedContent.embedding.isnot(None)
            ).count()
            
            with_content = db.session.query(SavedContent).filter(
                SavedContent.extracted_text.isnot(None),
                SavedContent.extracted_text != '',
                db.func.length(SavedContent.extracted_text) > 100
            ).count()
            
            logger.info("=" * 80)
            logger.info("QUALITY STATISTICS")
            logger.info("=" * 80)
            logger.info(f"Bookmarks with quality >= 5: {with_quality}/{total} ({(with_quality/total*100):.1f}%)")
            logger.info(f"Bookmarks with quality >= 7: {high_quality}/{total} ({(high_quality/total*100):.1f}%)")
            logger.info(f"Bookmarks with embeddings: {with_embeddings}/{total} ({(with_embeddings/total*100):.1f}%)")
            logger.info(f"Bookmarks with content > 100 chars: {with_content}/{total} ({(with_content/total*100):.1f}%)")
            
            # Quality distribution
            quality_dist = {}
            for score in range(1, 11):
                count = db.session.query(SavedContent).filter(
                    SavedContent.quality_score == score
                ).count()
                if count > 0:
                    quality_dist[score] = count
            
            if quality_dist:
                logger.info("")
                logger.info("Quality Score Distribution:")
                for score in sorted(quality_dist.keys(), reverse=True):
                    logger.info(f"  Score {score}: {quality_dist[score]} bookmarks")
            
        except Exception as e:
            logger.error(f"Error in re-scraping: {e}")
            db.session.rollback()
            raise

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clear and re-scrape bookmarks')
    parser.add_argument('--clear-only', action='store_true', help='Only clear data, do not re-scrape')
    parser.add_argument('--scrape-only', action='store_true', help='Only re-scrape, do not clear data')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze current state, do not clear or scrape')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for commits (default: 10)')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between requests in seconds (default: 2.0)')
    
    args = parser.parse_args()
    
    try:
        # If analyze-only, just run analysis and exit
        if args.analyze_only:
            logger.info("=" * 80)
            logger.info("CURRENT STATE ANALYSIS")
            logger.info("=" * 80)
            analyze_extraction_quality()
            logger.info("")
            logger.info(" Analysis complete!")
            return
        
        # Analyze BEFORE clearing/re-scraping
        if not args.scrape_only:
            logger.info("=" * 80)
            logger.info("BEFORE: CURRENT STATE ANALYSIS")
            logger.info("=" * 80)
            before_stats = analyze_extraction_quality()
        
        if not args.scrape_only:
            logger.info("")
            logger.info("=" * 80)
            logger.info("STEP 1: CLEARING EXTRACTION DATA")
            logger.info("=" * 80)
            total = clear_extraction_data()
            logger.info(f" Cleared extraction data from {total} bookmarks")
        
        if not args.clear_only:
            logger.info("")
            logger.info("=" * 80)
            logger.info("STEP 2: RE-SCRAPING BOOKMARKS")
            logger.info("=" * 80)
            logger.info(f"Using enhanced scraper with Scrapling integration")
            logger.info(f"Batch size: {args.batch_size}, Delay: {args.delay}s")
            logger.info("")
            rescrape_bookmarks(batch_size=args.batch_size, delay=args.delay)
        
        # Analyze AFTER re-scraping
        if not args.clear_only:
            logger.info("")
            logger.info("=" * 80)
            logger.info("AFTER: FINAL STATE ANALYSIS")
            logger.info("=" * 80)
            after_stats = analyze_extraction_quality()
            
            # Compare before and after
            if before_stats and after_stats:
                logger.info("")
                logger.info("=" * 80)
                logger.info("IMPROVEMENT SUMMARY")
                logger.info("=" * 80)
                logger.info(f"Empty embeddings: {before_stats['empty_embeddings']} → {after_stats['empty_embeddings']} (Δ{after_stats['empty_embeddings'] - before_stats['empty_embeddings']:+d})")
                logger.info(f"Empty extracted_text: {before_stats['empty_text']} → {after_stats['empty_text']} (Δ{after_stats['empty_text'] - before_stats['empty_text']:+d})")
                logger.info(f"'Unable to extract': {before_stats['unable_to_extract']} → {after_stats['unable_to_extract']} (Δ{after_stats['unable_to_extract'] - before_stats['unable_to_extract']:+d})")
                logger.info(f"Success rate: {before_stats['success_rate']:.1f}% → {after_stats['success_rate']:.1f}% (Δ{after_stats['success_rate'] - before_stats['success_rate']:+.1f}%)")
                logger.info("=" * 80)
        
        logger.info("")
        logger.info("=" * 80)
        logger.info(" COMPLETE!")
        logger.info("=" * 80)
        logger.info("Next steps:")
        logger.info("1. Background analysis will process the newly extracted content")
        logger.info("2. Check quality scores in database (should be 7-10 for most)")
        logger.info("3. Test semantic search and recommendations")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

