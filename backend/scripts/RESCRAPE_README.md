# Re-scrape Bookmarks Script

## Overview

This script clears extraction data and re-scrapes all existing bookmarks using the new enhanced scraper with Scrapling integration. This allows you to test the improved extraction quality and embeddings without re-importing.

## Prerequisites

- Python 3.11+
- Flask application configured
- Database with existing bookmarks
- **Scrapling & Camoufox setup** (recommended for best results):
  ```bash
  # Install packages (already in requirements.txt)
  pip install -r requirements.txt
  
  # Setup browsers
  cd backend
  python scripts/setup_scrapling.py
  ```
  
  Or manually:
  ```bash
  camoufox fetch
  ```
  
  > **Note**: If Scrapling/Camoufox is not set up, the script will use the standard scraper as fallback.

## Usage

### Basic Usage (Clear + Re-scrape)
```bash
cd backend
python scripts/clear_and_rescrape_bookmarks.py
```

### Options

```bash
# Only clear data (don't re-scrape)
python scripts/clear_and_rescrape_bookmarks.py --clear-only

# Only re-scrape (don't clear data first)
python scripts/clear_and_rescrape_bookmarks.py --scrape-only

# Custom batch size and delay
python scripts/clear_and_rescrape_bookmarks.py --batch-size 5 --delay 3.0
```

## What It Does

### Step 1: Clear Extraction Data
- Clears `extracted_text` column
- Clears `embedding` column  
- Clears `quality_score` column
- Deletes `ContentAnalysis` records (will be regenerated)
- **Keeps**: id, user_id, url, title, notes, saved_at (bookmark data preserved)

### Step 2: Re-scrape All Bookmarks
- Uses enhanced scraper with Scrapling integration
- Extracts content with improved quality
- Generates optimized embeddings (priority-based)
- Updates quality scores
- Commits in batches for safety

## Features

- ✅ **Safe**: Only clears extraction data, preserves bookmarks
- ✅ **Progress tracking**: Shows progress bar (if tqdm installed)
- ✅ **Batch commits**: Commits in batches to prevent data loss
- ✅ **Rate limiting**: Configurable delay between requests
- ✅ **Error handling**: Continues on errors, logs failures
- ✅ **Statistics**: Shows success rate and quality metrics

## Expected Results

### Before
- Many bookmarks with quality_score = 3
- Empty or short extracted_text
- Missing embeddings
- Failed extractions (94 URLs)

### After
- Quality scores 7-10 for most bookmarks
- Full content extracted (500+ chars)
- Comprehensive embeddings generated
- Better extraction from GitHub, LeetCode, JS-heavy sites

## Output

The script provides:
- Progress updates for each bookmark
- Success/failure counts
- Quality statistics
- Summary report

## Example Output

```
================================================================================
STEP 1: CLEARING EXTRACTION DATA
================================================================================
Total bookmarks: 194
✅ Cleared extraction data from 194 bookmarks
✅ Deleted 30 content analysis records

================================================================================
STEP 2: RE-SCRAPING BOOKMARKS
================================================================================
Found 194 bookmarks to re-scrape
Re-scraping bookmarks: 100%|████████████| 194/194 [15:23<00:00, 4.76s/it]

[1/194] Scraping: https://github.com/mrinal1224/SST-dev-2-Assignments...
  ✅ Quality: 8, Content: 5234 chars
  ✅ Generated embedding from 6234 chars

...

================================================================================
RE-SCRAPING SUMMARY
================================================================================
Total bookmarks: 194
✅ Successful: 180
❌ Failed: 10
⏭️  Skipped: 4
Success rate: 92.8%

================================================================================
QUALITY STATISTICS
================================================================================
Bookmarks with quality >= 5: 175
Bookmarks with quality >= 7: 162
High quality rate: 83.5%
```

## Notes

- **Scrapling not installed**: Script works with existing scraper (no errors)
- **Rate limiting**: Default 2s delay to avoid overwhelming servers
- **Batch commits**: Default batch size 10 for safety
- **Background analysis**: Will automatically process newly extracted content

## Next Steps

After running the script:
1. Background analysis will process the new content
2. Check quality scores in database
3. Test semantic search and recommendations
4. Verify embeddings are working correctly

