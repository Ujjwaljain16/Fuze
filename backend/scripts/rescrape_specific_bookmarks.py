#!/usr/bin/env python3
"""
Script to re-scrape specific bookmarks by ID
Uses the enhanced scraper with intelligent content extraction
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from flask import Flask
from config import DevelopmentConfig
from models import db, SavedContent
from scrapers.scrapling_enhanced_scraper import scrape_url_enhanced
from utils.embedding_utils import get_embedding
import logging
from datetime import datetime
from urllib.parse import urlparse
import re

# Try to import tqdm for progress bar, fallback if not available
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    def tqdm(iterable, desc=""):
        return iterable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
db.init_app(app)

def rescrape_bookmarks_by_ids(bookmark_ids, batch_size=10, delay=2):
    """
    Re-scrape specific bookmarks by their IDs
    
    Args:
        bookmark_ids: List of bookmark IDs to re-scrape
        batch_size: Number of bookmarks to process before committing
        delay: Delay between requests (seconds)
    """
    with app.app_context():
        try:
            # Get bookmarks by IDs
            bookmarks = db.session.query(SavedContent).filter(
                SavedContent.id.in_(bookmark_ids)
            ).all()
            
            total = len(bookmarks)
            logger.info(f"Found {total} bookmarks to re-scrape")
            
            if total == 0:
                logger.info("No bookmarks found with the provided IDs")
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
                        # Normal URL scraping with enhanced scraper
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
                SavedContent.id.in_(bookmark_ids),
                SavedContent.quality_score.isnot(None),
                SavedContent.quality_score >= 5
            ).count()
            
            high_quality = db.session.query(SavedContent).filter(
                SavedContent.id.in_(bookmark_ids),
                SavedContent.quality_score.isnot(None),
                SavedContent.quality_score >= 7
            ).count()
            
            with_embeddings = db.session.query(SavedContent).filter(
                SavedContent.id.in_(bookmark_ids),
                SavedContent.embedding.isnot(None)
            ).count()
            
            with_content = db.session.query(SavedContent).filter(
                SavedContent.id.in_(bookmark_ids),
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
            
        except Exception as e:
            logger.error(f"Error in re-scraping: {e}")
            db.session.rollback()
            raise

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Re-scrape specific bookmarks by ID')
    parser.add_argument('--ids', type=str, help='Comma-separated list of bookmark IDs (e.g., 528,529,530)')
    parser.add_argument('--ids-file', type=str, help='File containing comma-separated bookmark IDs (one line)')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for commits (default: 10)')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between requests in seconds (default: 2.0)')
    
    args = parser.parse_args()
    
    # Get bookmark IDs
    bookmark_ids = []
    
    if args.ids:
        bookmark_ids = [int(id.strip()) for id in args.ids.split(',') if id.strip().isdigit()]
    elif args.ids_file:
        try:
            with open(args.ids_file, 'r') as f:
                content = f.read().strip()
                bookmark_ids = [int(id.strip()) for id in content.split(',') if id.strip().isdigit()]
        except FileNotFoundError:
            logger.error(f"File not found: {args.ids_file}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error reading IDs file: {e}")
            sys.exit(1)
    else:
        logger.error("Either --ids or --ids-file must be provided")
        parser.print_help()
        sys.exit(1)
    
    if not bookmark_ids:
        logger.error("No valid bookmark IDs provided")
        sys.exit(1)
    
    logger.info(f"Will re-scrape {len(bookmark_ids)} bookmarks")
    logger.info(f"Batch size: {args.batch_size}, Delay: {args.delay}s")
    logger.info("")
    
    try:
        rescrape_bookmarks_by_ids(bookmark_ids, batch_size=args.batch_size, delay=args.delay)
        
        logger.info("")
        logger.info("=" * 80)
        logger.info(" COMPLETE!")
        logger.info("=" * 80)
        logger.info("Next steps:")
        logger.info("1. Background analysis will process the newly extracted content")
        logger.info("2. Check quality scores in database (should be improved)")
        logger.info("3. Test semantic search and recommendations")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

