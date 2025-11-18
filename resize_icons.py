#!/usr/bin/env python3
"""
High-quality PNG icon resizer for Fuze Chrome Extension
Creates crisp 16x16 and 48x48 icons from the 128x128 source image
"""

import os
from PIL import Image

def resize_icon(input_path, output_path, size):
    """Resize image with high quality settings"""
    try:
        # Open image
        img = Image.open(input_path)

        # Convert to RGBA if not already (for transparency support)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Resize with high-quality Lanczos filter
        resized = img.resize((size, size), Image.LANCZOS)

        # Save with high quality
        resized.save(output_path, 'PNG', optimize=True)

        print(f"✅ Created {size}x{size} icon: {output_path}")
        return True

    except Exception as e:
        print(f"❌ Error resizing to {size}x{size}: {e}")
        return False

def main():
    # Paths
    icons_dir = r"C:\Users\ujjwa\OneDrive\Desktop\fuze\BookmarkExtension\icons"
    source_file = os.path.join(icons_dir, "icon128.png")
    icon16_path = os.path.join(icons_dir, "icon16.png")
    icon48_path = os.path.join(icons_dir, "icon48.png")

    # Check if source exists
    if not os.path.exists(source_file):
        print(f"❌ Source file not found: {source_file}")
        return

    print("🔄 Creating high-quality extension icons...")

    # Create 48x48 icon
    success_48 = resize_icon(source_file, icon48_path, 48)

    # Create 16x16 icon
    success_16 = resize_icon(source_file, icon16_path, 16)

    if success_48 and success_16:
        print("\n🎉 All icons created successfully!")
        print("📁 Check your BookmarkExtension/icons directory")
        print("🔍 Quality tips:")
        print("   - Used Lanczos resampling for crisp results")
        print("   - Maintained aspect ratio and transparency")
        print("   - Optimized PNG output")
    else:
        print("\n❌ Some icons failed to create")

if __name__ == "__main__":
    main()