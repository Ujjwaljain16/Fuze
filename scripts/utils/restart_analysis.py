#!/usr/bin/env python3
"""
Restart Background Analysis Service
Simple script to restart the analysis service with transaction fixes
"""

import sys
import os
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def restart_analysis():
    """Restart the background analysis service"""
    print("🔄 Restarting Background Analysis Service...")
    print("=" * 50)
    
    try:
        from background_analysis_service import start_background_service
        
        # Start the service
        start_background_service()
        
        print("✅ Background analysis service started successfully!")
        print("📊 The service will now analyze all remaining content...")
        print("⏳ Check the logs for progress updates...")
        
        # Keep running
        try:
            while True:
                time.sleep(10)
                print("💤 Service is running... (Press Ctrl+C to stop)")
        except KeyboardInterrupt:
            print("\n🛑 Stopping service...")
            from background_analysis_service import stop_background_service
            stop_background_service()
            print("✅ Service stopped.")
            
    except Exception as e:
        print(f"❌ Error starting service: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    restart_analysis() 