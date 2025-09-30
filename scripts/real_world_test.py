#!/usr/bin/env python3
"""
Real-World Integration Test for TraceOne Monitoring System
Tests local file integration with the complete monitoring pipeline
"""

import asyncio
import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from traceone_monitoring.services.local_file_monitoring_service import (
    LocalFileMonitoringConfig,
    LocalFileMonitoringService,
    create_local_file_monitoring_service
)
from traceone_monitoring.services.local_file_notification_handler import (
    LocalFileStorageConfig,
    LocalFileNotificationHandler
)
from traceone_monitoring.models.notification import Notification


class RealWorldTestResults:
    """Track test results and metrics"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.notifications_processed = 0
        self.files_processed = 0
        self.notifications_stored = 0
        self.errors = []
        self.processing_times = []
        
    def add_processing_time(self, duration: float):
        self.processing_times.append(duration)
        
    def add_error(self, error: str):
        self.errors.append(f"{datetime.now()}: {error}")
        
    def get_summary(self) -> Dict:
        total_time = (datetime.now() - self.start_time).total_seconds()
        avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        
        return {
            "total_test_duration": total_time,
            "notifications_processed": self.notifications_processed,
            "files_processed": self.files_processed,
            "notifications_stored": self.notifications_stored,
            "average_processing_time": avg_processing_time,
            "throughput_notifications_per_second": self.notifications_processed / total_time if total_time > 0 else 0,
            "error_count": len(self.errors),
            "errors": self.errors[:5]  # Show first 5 errors
        }


class TestNotificationHandler:
    """Custom notification handler for testing"""
    
    def __init__(self, test_results: RealWorldTestResults, output_dir: Path):
        self.test_results = test_results
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.notification_log = []
        
    def handle_notifications(self, notifications: List[Notification]):
        """Handle notifications and track results"""
        start_time = time.time()
        
        try:
            # Process notifications
            for notification in notifications:
                self.notification_log.append({
                    "id": str(notification.id),
                    "type": notification.type.value,
                    "duns": notification.duns,
                    "elements_count": len(notification.elements),
                    "timestamp": notification.delivery_timestamp.isoformat() if hasattr(notification, 'delivery_timestamp') else None
                })
            
            # Save notifications to file (simulating storage)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"notifications_{timestamp}.json"
            
            with output_file.open('w') as f:
                json.dump([
                    {
                        "id": str(n.id),
                        "type": n.type.value,
                        "duns": n.duns,
                        "elements_count": len(n.elements),
                        "delivery_timestamp": n.delivery_timestamp.isoformat() if hasattr(n, 'delivery_timestamp') else None,
                        "sample_elements": [
                            {
                                "element": elem.element,
                                "has_current_value": elem.current is not None,
                                "timestamp": elem.timestamp.isoformat()
                            } for elem in n.elements[:3]  # Show first 3 elements
                        ]
                    } for n in notifications
                ], f, indent=2)
            
            # Update test results
            self.test_results.notifications_processed += len(notifications)
            self.test_results.notifications_stored += len(notifications)
            
            processing_time = time.time() - start_time
            self.test_results.add_processing_time(processing_time)
            
            print(f"✅ Processed {len(notifications)} notifications in {processing_time:.2f}s")
            print(f"   Saved to: {output_file}")
            print(f"   Sample DUNS: {[n.duns for n in notifications[:5]]}")
            
        except Exception as e:
            error_msg = f"Failed to handle notifications: {e}"
            self.test_results.add_error(error_msg)
            print(f"❌ {error_msg}")


async def run_real_world_test():
    """Run comprehensive real-world test"""
    print("🚀 TraceOne Real-World Integration Test")
    print("=" * 60)
    
    # Initialize test results
    test_results = RealWorldTestResults()
    
    # Setup output directories
    output_dir = Path("./test_output/real_world_test")
    notifications_dir = output_dir / "notifications"
    logs_dir = output_dir / "logs"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    notifications_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)
    
    print(f"📁 Test output directory: {output_dir.absolute()}")
    
    try:
        # Test 1: File Discovery and Initial Processing
        print("\n=== Test 1: File Discovery ===")
        config = LocalFileMonitoringConfig(
            enabled=True,
            input_directory="~/Library/Mobile Documents/com~apple~CloudDocs/Projects/Traceone/dev/sftp",
            polling_interval=60,
            auto_archive_processed=False,  # Don't move files during testing
            registration_reference="real-world-test"
        )
        
        local_service = create_local_file_monitoring_service(config)
        
        # Add our test notification handler
        test_handler = TestNotificationHandler(test_results, notifications_dir)
        local_service.add_notification_handler(test_handler.handle_notifications)
        
        # Discover files
        discovered_files = local_service.discover_files()
        total_files = sum(len(files) for files in discovered_files.values())
        test_results.files_processed = total_files
        
        print(f"✅ Discovered {total_files} files:")
        for file_type, files in discovered_files.items():
            print(f"   {file_type}: {len(files)} files")
        
        if total_files == 0:
            print("⚠️  No files found. Please ensure files exist in the SFTP directory.")
            return
        
        # Test 2: One-time Processing
        print("\n=== Test 2: One-time File Processing ===")
        start_time = time.time()
        
        notifications = await local_service.process_files_once()
        
        processing_time = time.time() - start_time
        print(f"✅ Processed {len(notifications)} notifications in {processing_time:.2f}s")
        print(f"   Throughput: {len(notifications) / processing_time:.1f} notifications/second")
        
        # Test 3: Verify Output Files
        print("\n=== Test 3: Output Verification ===")
        output_files = list(notifications_dir.glob("*.json"))
        print(f"✅ Generated {len(output_files)} output files")
        
        if output_files:
            # Check first output file
            with output_files[0].open() as f:
                sample_data = json.load(f)
            print(f"   Sample file contains {len(sample_data)} notifications")
            if sample_data:
                print(f"   Sample notification types: {set(n['type'] for n in sample_data)}")
                print(f"   Sample DUNS: {[n['duns'] for n in sample_data[:5]]}")
        
        # Test 4: Test Local File Storage Handler Integration
        print("\n=== Test 4: Storage Handler Integration ===")
        storage_config = LocalFileStorageConfig(
            enabled=True,
            base_path=str(notifications_dir / "storage_handler_output"),
            file_format="json",
            organize_by_date=True,
            organize_by_registration=True
        )
        
        storage_handler = LocalFileNotificationHandler(storage_config)
        
        # Process a small batch through storage handler
        if notifications:
            test_batch = notifications[:10]  # Test with 10 notifications
            storage_handler.handle_notifications(test_batch)
            
            # Check if files were created
            storage_output_dir = Path(storage_config.base_path)
            if storage_output_dir.exists():
                storage_files = list(storage_output_dir.rglob("*.json"))
                print(f"✅ Storage handler created {len(storage_files)} files")
                
                # Show storage organization
                for file_path in storage_files[:3]:  # Show first 3
                    relative_path = file_path.relative_to(storage_output_dir)
                    print(f"   📄 {relative_path}")
        
        # Test 5: Performance Metrics
        print("\n=== Test 5: Performance Analysis ===")
        summary = test_results.get_summary()
        
        print(f"📊 Test Results Summary:")
        print(f"   Total Duration: {summary['total_test_duration']:.2f} seconds")
        print(f"   Files Processed: {summary['files_processed']}")
        print(f"   Notifications Processed: {summary['notifications_processed']}")
        print(f"   Notifications Stored: {summary['notifications_stored']}")
        print(f"   Average Processing Time: {summary['average_processing_time']:.3f} seconds")
        print(f"   Throughput: {summary['throughput_notifications_per_second']:.1f} notifications/second")
        print(f"   Errors: {summary['error_count']}")
        
        if summary['errors']:
            print(f"   Recent Errors:")
            for error in summary['errors']:
                print(f"     - {error}")
        
        # Save detailed results
        results_file = output_dir / "test_results.json"
        with results_file.open('w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📋 Detailed results saved to: {results_file}")
        
        # Test 6: Service Status Check
        print("\n=== Test 6: Service Status ===")
        status = local_service.get_status()
        print("🔍 Service Status:")
        for key, value in status.items():
            print(f"   {key}: {value}")
        
        print("\n🎉 Real-World Test Completed Successfully!")
        print(f"📁 All test outputs saved to: {output_dir.absolute()}")
        
    except Exception as e:
        test_results.add_error(str(e))
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Save final results regardless of success/failure
        final_results_file = output_dir / "final_test_results.json"
        with final_results_file.open('w') as f:
            json.dump(test_results.get_summary(), f, indent=2)


def print_pre_test_info():
    """Print pre-test information and requirements"""
    print("📋 Pre-Test Checklist:")
    print("1. Ensure notification files exist in your SFTP directory")
    print("2. Check that you have read/write permissions to the test output directory")
    print("3. Verify Python environment has all required dependencies")
    print("4. Optionally set environment variables for D&B API (not required for local file test)")
    print()
    
    sftp_dir = Path("~/Library/Mobile Documents/com~apple~CloudDocs/Projects/Traceone/dev/sftp").expanduser()
    if sftp_dir.exists():
        files = list(sftp_dir.glob("*"))
        print(f"✅ SFTP directory found with {len(files)} files")
    else:
        print("⚠️  SFTP directory not found - please verify the path")
    
    print()


if __name__ == "__main__":
    try:
        print_pre_test_info()
        
        response = input("Do you want to proceed with the real-world test? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            asyncio.run(run_real_world_test())
        else:
            print("Test cancelled by user")
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
