#!/usr/bin/env python3
"""
Continuous Monitoring Test Script
Tests the real-time file monitoring functionality
"""

import asyncio
import sys
import signal
from pathlib import Path
from datetime import datetime

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from traceone_monitoring.services.local_file_monitoring_service import (
    LocalFileMonitoringConfig,
    create_local_file_monitoring_service
)


class ContinuousTestHandler:
    """Handler for continuous monitoring test"""
    
    def __init__(self):
        self.notification_count = 0
        self.start_time = datetime.now()
    
    def handle_notifications(self, notifications):
        """Handle incoming notifications"""
        self.notification_count += len(notifications)
        current_time = datetime.now()
        elapsed = (current_time - self.start_time).total_seconds()
        
        print(f"\n📨 {current_time.strftime('%H:%M:%S')} - Received {len(notifications)} notifications")
        print(f"   Total processed: {self.notification_count}")
        print(f"   Average rate: {self.notification_count / elapsed if elapsed > 0 else 0:.1f} notifications/second")
        
        # Show sample notification details
        if notifications:
            sample = notifications[0]
            print(f"   Sample: DUNS {sample.duns}, Type: {sample.type.value}, Elements: {len(sample.elements)}")


async def run_continuous_monitoring_test():
    """Run continuous monitoring test"""
    print("🔄 TraceOne Continuous Monitoring Test")
    print("=" * 50)
    print("This test will run continuously and monitor your SFTP directory for changes.")
    print("Press Ctrl+C to stop the monitoring.\n")
    
    # Create monitoring service
    config = LocalFileMonitoringConfig(
        enabled=True,
        input_directory="~/Library/Mobile Documents/com~apple~CloudDocs/Projects/Traceone/dev/sftp",
        polling_interval=30,  # Check every 30 seconds
        auto_archive_processed=False,  # Keep files for repeated testing
        registration_reference="continuous-test"
    )
    
    local_service = create_local_file_monitoring_service(config)
    
    # Add test handler
    test_handler = ContinuousTestHandler()
    local_service.add_notification_handler(test_handler.handle_notifications)
    
    print(f"🚀 Starting continuous monitoring...")
    print(f"📁 Watching: {config.input_directory}")
    print(f"⏰ Polling interval: {config.polling_interval} seconds")
    print(f"🔄 To test: Add/modify files in the SFTP directory")
    print("\n" + "=" * 50)
    
    try:
        # Start monitoring
        await local_service.start_monitoring()
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        print("\n🛑 Monitoring stopped")
    finally:
        await local_service.stop_monitoring()
        
        # Print final stats
        elapsed = (datetime.now() - test_handler.start_time).total_seconds()
        print(f"\n📊 Final Statistics:")
        print(f"   Duration: {elapsed:.1f} seconds")
        print(f"   Total notifications: {test_handler.notification_count}")
        print(f"   Average rate: {test_handler.notification_count / elapsed if elapsed > 0 else 0:.1f} notifications/second")


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\n🛑 Received interrupt signal, stopping monitoring...")
    raise KeyboardInterrupt


if __name__ == "__main__":
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        asyncio.run(run_continuous_monitoring_test())
    except KeyboardInterrupt:
        print("👋 Monitoring test stopped by user")
    except Exception as e:
        print(f"💥 Error: {e}")
        import traceback
        traceback.print_exc()
