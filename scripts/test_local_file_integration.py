#!/usr/bin/env python3
"""
Test script to demonstrate local file processing integration
Tests the local file input processor with your actual SFTP files
"""

import asyncio
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from traceone_monitoring.services.local_file_input_processor import (
    LocalFileInputConfig,
    LocalFileInputProcessor,
    create_local_file_input_processor
)
from traceone_monitoring.services.local_file_monitoring_service import (
    LocalFileMonitoringConfig,
    LocalFileMonitoringService,
    create_local_file_monitoring_service
)


async def test_file_discovery():
    """Test file discovery without processing"""
    print("=== Testing File Discovery ===")
    
    # Configure processor for your local SFTP directory
    config = LocalFileInputConfig(
        input_directory="~/Library/Mobile Documents/com~apple~CloudDocs/Projects/Traceone/dev/sftp",
        auto_archive_processed=False  # Don't move files during testing
    )
    
    try:
        processor = create_local_file_input_processor(config)
        
        # Discover files
        discovered_files = processor.discover_files()
        
        print(f"Input directory: {processor.input_path}")
        print("\nDiscovered files by type:")
        
        total_files = 0
        for file_type, files in discovered_files.items():
            print(f"  {file_type}: {len(files)} files")
            total_files += len(files)
            
            # Show first few files of each type
            if files:
                print(f"    Examples:")
                for file_path in files[:3]:  # Show first 3
                    print(f"      - {file_path.name}")
                if len(files) > 3:
                    print(f"      ... and {len(files) - 3} more")
        
        print(f"\nTotal files discovered: {total_files}")
        return discovered_files
        
    except Exception as e:
        print(f"File discovery failed: {e}")
        return {}


async def test_single_file_processing(discovered_files):
    """Test processing a single file of each type"""
    print("\n=== Testing Single File Processing ===")
    
    config = LocalFileInputConfig(
        input_directory="~/Library/Mobile Documents/com~apple~CloudDocs/Projects/Traceone/dev/sftp",
        auto_archive_processed=False  # Don't move files during testing
    )
    
    processor = create_local_file_input_processor(config)
    
    # Test one file of each type
    for file_type, files in discovered_files.items():
        if not files:
            continue
            
        print(f"\nTesting {file_type} processing:")
        test_file = files[0]  # Use first file
        print(f"  File: {test_file.name}")
        
        try:
            if file_type == "header":
                # Test header parsing
                header_data = processor._parse_header_file(test_file)
                print(f"  ✓ Header parsed successfully")
                print(f"    Header type: {header_data.get('headerType', 'Unknown')}")
                print(f"    Reference: {header_data.get('reference', 'Unknown')}")
                
            elif file_type == "seedfile":
                # Test seedfile processing (limit to first 5 records)
                notifications = processor._process_seedfile(test_file, {})
                print(f"  ✓ Seedfile processed: {len(notifications)} notifications")
                
                if notifications:
                    sample = notifications[0]
                    print(f"    Sample DUNS: {sample.duns}")
                    print(f"    Notification type: {sample.type.value}")
                    print(f"    Elements: {len(sample.elements)}")
                
            elif file_type == "exception":
                # Test exception file processing
                notifications = processor._process_exception_file(test_file, {})
                print(f"  ✓ Exception file processed: {len(notifications)} notifications")
                
                if notifications:
                    sample = notifications[0]
                    print(f"    Sample DUNS: {sample.duns}")
                    print(f"    Exception type: {sample.elements[0].current.get('exception_type', 'Unknown')}")
                
            elif file_type == "duns_export":
                # Test DUNS export processing
                notifications = processor._process_duns_export_file(test_file, {})
                print(f"  ✓ DUNS export processed: {len(notifications)} notifications")
                
                if notifications:
                    sample = notifications[0]
                    print(f"    Sample DUNS: {sample.duns}")
            
        except Exception as e:
            print(f"  ✗ Processing failed: {e}")


async def test_monitoring_service():
    """Test the monitoring service integration"""
    print("\n=== Testing Monitoring Service ===")
    
    # Configure monitoring service
    config = LocalFileMonitoringConfig(
        enabled=True,
        input_directory="~/Library/Mobile Documents/com~apple~CloudDocs/Projects/Traceone/dev/sftp",
        polling_interval=60,  # 1 minute for testing
        auto_archive_processed=False,  # Don't move files during testing
        registration_reference="test-local-files"
    )
    
    try:
        # Create monitoring service
        monitoring_service = create_local_file_monitoring_service(config)
        
        # Add a simple notification handler for testing
        def test_handler(notifications):
            print(f"Handler received {len(notifications)} notifications")
            for notification in notifications[:3]:  # Show first 3
                print(f"  - DUNS: {notification.duns}, Type: {notification.type.value}")
        
        monitoring_service.add_notification_handler(test_handler)
        
        # Get status
        status = monitoring_service.get_status()
        print("Service status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
        
        # Test file processing once
        print("\nProcessing files once...")
        notifications = await monitoring_service.process_files_once()
        
        print(f"Processed {len(notifications)} total notifications")
        
        # Test processing with limits
        print("\nTesting limited processing...")
        test_results = await monitoring_service.test_processing(max_files=2)
        
        if test_results["success"]:
            print("Test processing results:")
            print(f"  Discovered files: {test_results['discovered_files']}")
            print(f"  Test files processed: {test_results['test_files']}")
            print(f"  Test notifications: {test_results['test_notifications']}")
            
            if test_results.get("sample_notifications"):
                print("  Sample notifications:")
                for sample in test_results["sample_notifications"]:
                    print(f"    - DUNS: {sample['duns']}, Type: {sample['type']}, Elements: {sample['elements_count']}")
        else:
            print(f"Test processing failed: {test_results.get('error')}")
            
    except Exception as e:
        print(f"Monitoring service test failed: {e}")


async def main():
    """Main test function"""
    print("TraceOne Local File Integration Test")
    print("=" * 50)
    
    # Test 1: File Discovery
    discovered_files = await test_file_discovery()
    
    if not discovered_files or not any(discovered_files.values()):
        print("\nNo files discovered. Please ensure files exist in the SFTP directory.")
        return
    
    # Test 2: Single File Processing
    await test_single_file_processing(discovered_files)
    
    # Test 3: Monitoring Service Integration
    await test_monitoring_service()
    
    print("\n=== Test Completed ===")
    print("\nNext steps:")
    print("1. Review the test output above")
    print("2. Check if notifications were processed correctly")
    print("3. If everything looks good, you can enable auto-archiving")
    print("4. Integrate with your main monitoring service configuration")


if __name__ == "__main__":
    # Run the test
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
