#!/bin/bash
# Bash script to package Fuze Web Clipper extension for distribution
# This creates a zip file ready for manual installation

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EXTENSION_DIR="$PROJECT_ROOT/BookmarkExtension"
OUTPUT_DIR="$PROJECT_ROOT/dist"
ZIP_FILE="$OUTPUT_DIR/fuze-web-clipper.zip"

echo "📦 Packaging Fuze Web Clipper Extension..."

# Check if extension directory exists
if [ ! -d "$EXTENSION_DIR" ]; then
    echo "❌ Extension directory not found: $EXTENSION_DIR"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"
echo "✅ Created output directory: $OUTPUT_DIR"

# Remove old zip if exists
if [ -f "$ZIP_FILE" ]; then
    rm "$ZIP_FILE"
    echo "🗑️  Removed old zip file"
fi

# Verify manifest exists
if [ ! -f "$EXTENSION_DIR/MANIFEST.JSON" ]; then
    echo "❌ MANIFEST.JSON not found in extension directory"
    exit 1
fi

# Create zip file
echo "📦 Creating zip archive..."
cd "$EXTENSION_DIR"
zip -r "$ZIP_FILE" . -x "*.git*" "*.DS_Store" "*.md" > /dev/null

ZIP_SIZE=$(du -h "$ZIP_FILE" | cut -f1)
echo "✅ Zip file created: $ZIP_FILE ($ZIP_SIZE)"

echo ""
echo "🎉 Extension packaged successfully!"
echo "📁 Location: $ZIP_FILE"
echo ""
echo "📝 Next steps:"
echo "   1. Upload the zip file to your hosting/CDN"
echo "   2. Update ExtensionDownload.jsx with the download URL"
echo "   3. Users can download and extract the zip"
echo "   4. Load unpacked extension in Chrome"

