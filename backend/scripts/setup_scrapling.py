#!/usr/bin/env python3
"""
Setup script to install and configure Scrapling and Camoufox browsers
Run this after installing requirements.txt to set up the scraping dependencies
"""

import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_command(cmd, description):
    """Run a command and handle errors"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Setting up: {description}")
    logger.info(f"Command: {cmd}")
    logger.info(f"{'='*60}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"✅ {description} completed successfully")
        if result.stdout:
            logger.info(f"Output: {result.stdout[:500]}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed")
        logger.error(f"Error: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error during {description}: {e}")
        return False

def main():
    """Main setup function"""
    logger.info("="*60)
    logger.info("Scrapling & Camoufox Setup Script")
    logger.info("="*60)
    logger.info("This script will:")
    logger.info("1. Verify Scrapling and Camoufox are installed")
    logger.info("2. Download Camoufox browser binaries")
    logger.info("3. Verify the setup")
    logger.info("")
    
    # Check if we're in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    if not in_venv:
        logger.warning("⚠️  Not in a virtual environment. Consider using one.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            logger.info("Setup cancelled.")
            return
    
    # Step 1: Verify packages are installed
    logger.info("\n📦 Step 1: Verifying packages...")
    try:
        import scrapling
        import camoufox
        logger.info("✅ Scrapling and Camoufox packages are installed")
    except ImportError as e:
        logger.error(f"❌ Missing packages: {e}")
        logger.error("Please install with: pip install 'scrapling[all]' 'camoufox[geoip]'")
        return False
    
    # Step 2: Download Camoufox browser
    logger.info("\n🌐 Step 2: Downloading Camoufox browser...")
    logger.info("This may take a few minutes...")
    
    # Try camoufox fetch first
    success = run_command(
        "camoufox fetch",
        "Downloading Camoufox browser"
    )
    
    if not success:
        # Try alternative command
        logger.info("\nTrying alternative command...")
        success = run_command(
            "python -m camoufox fetch",
            "Downloading Camoufox browser (alternative)"
        )
    
    if not success:
        logger.warning("⚠️  Could not download Camoufox browser automatically.")
        logger.warning("Please run manually: camoufox fetch")
        logger.warning("Or: python -m camoufox fetch")
        return False
    
    # Step 3: Verify setup
    logger.info("\n✅ Step 3: Verifying setup...")
    try:
        from scrapling.fetchers import StealthyFetcher, DynamicFetcher, Fetcher
        logger.info("✅ Scrapling imports successfully")
        logger.info("✅ Setup complete! Scrapling is ready to use.")
        return True
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        logger.error("Please check the error above and try again.")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        logger.info("\n" + "="*60)
        logger.info("🎉 Setup Complete!")
        logger.info("="*60)
        logger.info("You can now use the enhanced scraper with Scrapling.")
        sys.exit(0)
    else:
        logger.error("\n" + "="*60)
        logger.error("❌ Setup Incomplete")
        logger.error("="*60)
        logger.error("Please fix the errors above and try again.")
        sys.exit(1)


