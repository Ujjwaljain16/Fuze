# Logo and Favicon Setup

## Files Created

1. **logo1.svg** - Main logo file with full design (stylized F symbol with gradient, "FUZE" text, and "Intelligence Connected" tagline)
2. **favicon.svg** - Simplified favicon optimized for small sizes (32x32)
3. **logo-icon-only.svg** - Icon-only version of the logo (if needed)

## Current Usage

- **Frontend Favicon**: Uses `favicon.svg` (simplified version for browser tabs)
- **Apple Touch Icon**: Uses `logo1.svg` (full logo for mobile devices)
- **Chrome Extension**: Currently uses PNG files in `BookmarkExtension/icons/`

## Chrome Extension Icons

The Chrome extension requires PNG format icons. To convert `logo1.svg` to PNG formats:

### Option 1: Using Online Tools
1. Use an online SVG to PNG converter (e.g., CloudConvert, Convertio)
2. Generate sizes: 16x16, 48x48, 128x128
3. Replace files in `BookmarkExtension/icons/`

### Option 2: Using ImageMagick (Command Line)
```bash
magick logo1.svg -resize 16x16 icon16.png
magick logo1.svg -resize 48x48 icon48.png
magick logo1.svg -resize 128x128 icon128.png
```

### Option 3: Using Inkscape (Command Line)
```bash
inkscape logo1.svg --export-filename=icon16.png -w 16 -h 16
inkscape logo1.svg --export-filename=icon48.png -w 48 -h 48
inkscape logo1.svg --export-filename=icon128.png -w 128 -h 128
```

## Logo Design

The logo features:
- **Stylized F symbol**: Flowing, continuous line representing fusion/connection
- **Gradient colors**: Blue (#3b82f6) → Cyan (#06b6d4) → Purple (#a855f7)
- **Central node**: White circular node with connection lines
- **Typography**: Bold "FUZE" text with gradient matching the symbol
- **Tagline**: "Intelligence Connected" in lighter weight

## Color Scheme

- Primary Blue: `#3b82f6`
- Cyan: `#06b6d4`
- Purple: `#a855f7`
- White: `#ffffff` (for nodes and text)

