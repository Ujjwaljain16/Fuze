#!/usr/bin/env python3
"""
Script to find bookmarks with bad or missing extractions
Identifies content that needs to be re-scraped
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
from sqlalchemy import func
import logging
from urllib.parse import urlparse
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
db.init_app(app)

def find_bad_extractions():
    """Find all bookmarks with bad or missing extractions"""
    with app.app_context():
        try:
            total = db.session.query(SavedContent).count()
            logger.info(f"Total bookmarks: {total}")
            logger.info("=" * 80)
            
            # 1. Empty extracted_text
            empty_text = db.session.query(SavedContent).filter(
                db.or_(
                    SavedContent.extracted_text.is_(None),
                    SavedContent.extracted_text == ''
                )
            ).all()
            
            logger.info(f"\n1. EMPTY EXTRACTED_TEXT: {len(empty_text)} bookmarks")
            if empty_text:
                logger.info("   Sample URLs:")
                for bm in empty_text[:10]:
                    logger.info(f"   - {bm.url[:80]} (ID: {bm.id}, Title: {bm.title[:50]})")
            
            # 2. "Unable to extract" messages
            unable_to_extract = db.session.query(SavedContent).filter(
                SavedContent.extracted_text.like('%Unable to extract%')
            ).all()
            
            logger.info(f"\n2. 'UNABLE TO EXTRACT' MESSAGES: {len(unable_to_extract)} bookmarks")
            if unable_to_extract:
                logger.info("   Sample URLs:")
                for bm in unable_to_extract[:10]:
                    logger.info(f"   - {bm.url[:80]} (ID: {bm.id}, Title: {bm.title[:50]})")
            
            # 3. "extraction failed" messages
            extraction_failed = db.session.query(SavedContent).filter(
                SavedContent.extracted_text.like('%extraction failed%')
            ).all()
            
            logger.info(f"\n3. 'EXTRACTION FAILED' MESSAGES: {len(extraction_failed)} bookmarks")
            if extraction_failed:
                logger.info("   Sample URLs:")
                for bm in extraction_failed[:10]:
                    logger.info(f"   - {bm.url[:80]} (ID: {bm.id}, Title: {bm.title[:50]})")
            
            # 4. Very short content (< 100 chars) - likely bad extraction
            short_content = db.session.query(SavedContent).filter(
                db.func.length(SavedContent.extracted_text) < 100,
                SavedContent.extracted_text.isnot(None),
                SavedContent.extracted_text != '',
                ~SavedContent.extracted_text.like('%Unable to extract%'),
                ~SavedContent.extracted_text.like('%extraction failed%')
            ).all()
            
            logger.info(f"\n4. VERY SHORT CONTENT (< 100 chars): {len(short_content)} bookmarks")
            if short_content:
                logger.info("   Sample URLs:")
                for bm in short_content[:10]:
                    preview = bm.extracted_text[:60] if bm.extracted_text else ""
                    logger.info(f"   - {bm.url[:80]} (ID: {bm.id}, Length: {len(bm.extracted_text or '')} chars)")
                    logger.info(f"     Preview: {preview}...")
            
            # 5. CSS/JS-like content (high special character ratio)
            all_content = db.session.query(SavedContent).filter(
                SavedContent.extracted_text.isnot(None),
                SavedContent.extracted_text != '',
                ~SavedContent.extracted_text.like('%Unable to extract%'),
                ~SavedContent.extracted_text.like('%extraction failed%')
            ).all()
            
            css_js_content = []
            for content in all_content:
                text = content.extracted_text
                if not text:
                    continue
                
                # Check for high special character ratio (likely CSS/JS)
                special_chars = sum(1 for c in text if c in '{}(),;:[]=+-*/%<>!&|')
                if len(text) > 0:
                    special_ratio = special_chars / len(text)
                    if special_ratio > 0.3:  # More than 30% special chars
                        css_js_content.append((content, special_ratio))
                        continue
                
                # Check for CSS patterns
                css_patterns = [
                    r'\.[a-zA-Z0-9_-]+\s*\{[^}]*\}',  # CSS classes
                    r'#[a-zA-Z0-9_-]+\s*\{[^}]*\}',   # CSS IDs
                    r'@media[^{]*\{[^}]*\}',            # Media queries
                ]
                
                for pattern in css_patterns:
                    if re.search(pattern, text[:1000]):  # Check first 1000 chars
                        css_js_content.append((content, 0.5))  # Mark as CSS
                        break
            
            logger.info(f"\n5. CSS/JS-LIKE CONTENT: {len(css_js_content)} bookmarks")
            if css_js_content:
                logger.info("   Sample URLs:")
                for bm, ratio in css_js_content[:10]:
                    logger.info(f"   - {bm.url[:80]} (ID: {bm.id}, Special chars ratio: {ratio:.2%})")
                    preview = bm.extracted_text[:100] if bm.extracted_text else ""
                    logger.info(f"     Preview: {preview}...")
            
            # 6. Low quality scores (< 5)
            low_quality = db.session.query(SavedContent).filter(
                SavedContent.quality_score.isnot(None),
                SavedContent.quality_score < 5
            ).all()
            
            logger.info(f"\n6. LOW QUALITY SCORES (< 5): {len(low_quality)} bookmarks")
            if low_quality:
                logger.info("   Sample URLs:")
                for bm in low_quality[:10]:
                    logger.info(f"   - {bm.url[:80]} (ID: {bm.id}, Quality: {bm.quality_score})")
            
            # 7. No embeddings
            no_embeddings = db.session.query(SavedContent).filter(
                SavedContent.embedding.is_(None)
            ).all()
            
            logger.info(f"\n7. NO EMBEDDINGS: {len(no_embeddings)} bookmarks")
            if no_embeddings:
                logger.info("   Sample URLs:")
                for bm in no_embeddings[:10]:
                    logger.info(f"   - {bm.url[:80]} (ID: {bm.id}, Title: {bm.title[:50]})")
            
            # Combine all problematic bookmarks
            problematic_ids = set()
            problematic_ids.update(bm.id for bm in empty_text)
            problematic_ids.update(bm.id for bm in unable_to_extract)
            problematic_ids.update(bm.id for bm in extraction_failed)
            problematic_ids.update(bm.id for bm in short_content)
            problematic_ids.update(bm.id for bm, _ in css_js_content)
            problematic_ids.update(bm.id for bm in no_embeddings)
            
            logger.info("\n" + "=" * 80)
            logger.info("SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Total bookmarks: {total}")
            logger.info(f"Empty extracted_text: {len(empty_text)}")
            logger.info(f"'Unable to extract' messages: {len(unable_to_extract)}")
            logger.info(f"'extraction failed' messages: {len(extraction_failed)}")
            logger.info(f"Very short content (< 100 chars): {len(short_content)}")
            logger.info(f"CSS/JS-like content: {len(css_js_content)}")
            logger.info(f"Low quality scores (< 5): {len(low_quality)}")
            logger.info(f"No embeddings: {len(no_embeddings)}")
            logger.info(f"\nTOTAL PROBLEMATIC BOOKMARKS: {len(problematic_ids)} ({len(problematic_ids)/total*100:.1f}%)")
            
            # Group by domain
            logger.info("\n" + "=" * 80)
            logger.info("PROBLEMATIC BOOKMARKS BY DOMAIN")
            logger.info("=" * 80)
            
            domain_counts = {}
            for bm_id in problematic_ids:
                bm = db.session.query(SavedContent).filter_by(id=bm_id).first()
                if bm:
                    try:
                        domain = urlparse(bm.url).netloc.replace('www.', '')
                        domain_counts[domain] = domain_counts.get(domain, 0) + 1
                    except:
                        domain_counts['unknown'] = domain_counts.get('unknown', 0) + 1
            
            for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
                logger.info(f"  {domain}: {count} bookmarks")
            
            # Export list of IDs for re-scraping
            logger.info("\n" + "=" * 80)
            logger.info("EXPORT")
            logger.info("=" * 80)
            logger.info(f"Problematic bookmark IDs (for re-scraping):")
            logger.info(f"{','.join(map(str, sorted(problematic_ids)))}")
            logger.info("")
            logger.info("To re-scrape these bookmarks, run:")
            logger.info(f"  python backend/scripts/rescrape_specific_bookmarks.py --ids \"{','.join(map(str, sorted(problematic_ids)))}\"")
            logger.info("")
            logger.info("Or save IDs to a file and use:")
            logger.info(f"  python backend/scripts/rescrape_specific_bookmarks.py --ids-file bad_extractions_ids.txt")
            
            return {
                'total': total,
                'empty_text': len(empty_text),
                'unable_to_extract': len(unable_to_extract),
                'extraction_failed': len(extraction_failed),
                'short_content': len(short_content),
                'css_js_content': len(css_js_content),
                'low_quality': len(low_quality),
                'no_embeddings': len(no_embeddings),
                'total_problematic': len(problematic_ids),
                'problematic_ids': sorted(list(problematic_ids))
            }
            
        except Exception as e:
            logger.error(f"Error finding bad extractions: {e}")
            import traceback
            traceback.print_exc()
            return None

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Find bookmarks with bad or missing extractions')
    parser.add_argument('--export-ids', action='store_true', help='Export problematic IDs to file')
    parser.add_argument('--output-file', type=str, default='bad_extractions_ids.txt',
                       help='Output file for problematic IDs (default: bad_extractions_ids.txt)')
    
    args = parser.parse_args()
    
    try:
        results = find_bad_extractions()
        
        # Always export IDs to file for convenience
        if results:
            ids_str = ','.join(map(str, results['problematic_ids']))
            output_file = args.output_file if args.export_ids else 'bad_extractions_ids.txt'
            with open(output_file, 'w') as f:
                f.write(ids_str)
            logger.info(f"\n✅ Exported {len(results['problematic_ids'])} problematic IDs to {output_file}")
            logger.info("   You can use these IDs with the re-scrape script to fix them")
            logger.info(f"   Run: python backend/scripts/rescrape_specific_bookmarks.py --ids-file {output_file}")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ ANALYSIS COMPLETE!")
        logger.info("=" * 80)
        logger.info("\nNext steps:")
        logger.info("1. Review the problematic bookmarks above")
        logger.info("2. Run re-scrape script to fix them:")
        logger.info("   python backend/scripts/clear_and_rescrape_bookmarks.py")
        logger.info("3. Or re-scrape specific IDs if you exported them")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

