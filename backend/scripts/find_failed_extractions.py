#!/usr/bin/env python3
"""
Script to find all URLs that failed extraction or have low quality scores
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from models import db, SavedContent
from flask import Flask
from config import DevelopmentConfig
from urllib.parse import urlparse
from collections import defaultdict

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
db.init_app(app)

def find_failed_extractions():
    """Find all URLs with failed or poor extractions"""
    
    with app.app_context():
        # Find content with low quality scores
        low_quality = db.session.query(SavedContent).filter(
            SavedContent.quality_score < 5
        ).all()
        
        # Find content with "Unable to extract" in content
        failed_extractions = db.session.query(SavedContent).filter(
            SavedContent.extracted_text.like('%Unable to extract%')
        ).all()
        
        # Find content with "extraction failed" in content
        failed_extractions2 = db.session.query(SavedContent).filter(
            SavedContent.extracted_text.like('%extraction failed%')
        ).all()
        
        # Find content with very short extracted text (< 100 chars) but not empty
        short_content = db.session.query(SavedContent).filter(
            db.func.length(SavedContent.extracted_text) < 100,
            SavedContent.extracted_text.isnot(None),
            SavedContent.extracted_text != ''
        ).all()
        
        # Find content with empty extracted_text
        empty_content = db.session.query(SavedContent).filter(
            db.or_(
                SavedContent.extracted_text.is_(None),
                SavedContent.extracted_text == ''
            )
        ).all()
        
        # Combine all and deduplicate by URL
        all_failed = {}
        
        for content in low_quality + failed_extractions + failed_extractions2 + short_content + empty_content:
            if content.url not in all_failed:
                all_failed[content.url] = {
                    'id': content.id,
                    'title': content.title,
                    'url': content.url,
                    'quality_score': content.quality_score,
                    'extracted_text_length': len(content.extracted_text) if content.extracted_text else 0,
                    'extracted_text_preview': (content.extracted_text[:200] + '...') if content.extracted_text and len(content.extracted_text) > 200 else (content.extracted_text or ''),
                    'reasons': []
                }
            
            # Add reasons
            if content.quality_score < 5:
                all_failed[content.url]['reasons'].append(f'Low quality score: {content.quality_score}')
            if content.extracted_text and 'Unable to extract' in content.extracted_text:
                all_failed[content.url]['reasons'].append('Contains "Unable to extract"')
            if content.extracted_text and 'extraction failed' in content.extracted_text.lower():
                all_failed[content.url]['reasons'].append('Contains "extraction failed"')
            if content.extracted_text and len(content.extracted_text) < 100:
                all_failed[content.url]['reasons'].append(f'Short content: {len(content.extracted_text)} chars')
            if not content.extracted_text or content.extracted_text == '':
                all_failed[content.url]['reasons'].append('Empty extracted_text')
        
        # Group by domain
        by_domain = defaultdict(list)
        for url, data in all_failed.items():
            try:
                domain = urlparse(url).netloc
                by_domain[domain].append(data)
            except:
                by_domain['unknown'].append(data)
        
        # Print results
        print("=" * 80)
        print(f"FOUND {len(all_failed)} URLs WITH EXTRACTION ISSUES")
        print("=" * 80)
        print()
        
        print("BY DOMAIN:")
        print("-" * 80)
        for domain in sorted(by_domain.keys()):
            print(f"\n{domain} ({len(by_domain[domain])} URLs):")
            for item in by_domain[domain]:
                print(f"  - {item['url']}")
                print(f"    Title: {item['title'][:80]}")
                print(f"    Quality: {item['quality_score']}, Length: {item['extracted_text_length']} chars")
                print(f"    Reasons: {', '.join(item['reasons'])}")
                if item['extracted_text_preview']:
                    print(f"    Preview: {item['extracted_text_preview'][:150]}")
                print()
        
        print("\n" + "=" * 80)
        print("COMPLETE LIST OF FAILED URLs:")
        print("=" * 80)
        for url, data in sorted(all_failed.items()):
            print(f"{url}")
            print(f"  Reasons: {', '.join(data['reasons'])}")
            print()
        
        # Save to file
        output_file = 'failed_extractions.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("FAILED EXTRACTION URLs\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Total: {len(all_failed)} URLs\n\n")
            
            f.write("BY DOMAIN:\n")
            f.write("-" * 80 + "\n")
            for domain in sorted(by_domain.keys()):
                f.write(f"\n{domain} ({len(by_domain[domain])} URLs):\n")
                for item in by_domain[domain]:
                    f.write(f"  - {item['url']}\n")
                    f.write(f"    Title: {item['title']}\n")
                    f.write(f"    Quality: {item['quality_score']}, Length: {item['extracted_text_length']} chars\n")
                    f.write(f"    Reasons: {', '.join(item['reasons'])}\n")
                    if item['extracted_text_preview']:
                        f.write(f"    Preview: {item['extracted_text_preview']}\n")
                    f.write("\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("COMPLETE LIST:\n")
            f.write("=" * 80 + "\n")
            for url, data in sorted(all_failed.items()):
                f.write(f"{url}\n")
                f.write(f"  Reasons: {', '.join(data['reasons'])}\n\n")
        
        print(f"\n✅ Results saved to {output_file}")
        
        return all_failed, by_domain

if __name__ == "__main__":
    find_failed_extractions()


