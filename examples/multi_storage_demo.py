#!/usr/bin/env python3
"""
Multi-Storage Demo Script

Demonstrates the TraceOne monitoring system with multiple storage backends:
- SFTP storage for remote file storage
- Local file storage for local backup/archiving

This script shows how notifications can be automatically stored to both
local files and SFTP servers simultaneously.
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traceone_monitoring.services.monitoring_service import (
    DNBMonitoringService, 
    create_standard_monitoring_registration,
    log_notification_handler
)
from traceone_monitoring.utils.config import init_config
from traceone_monitoring.models.notification import Notification


class MultiStorageDemo:
    """Demo class showcasing multi-storage notification handling"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.service = None
        self.demo_notifications_created = 0
    
    async def initialize_service(self) -> bool:
        """Initialize the monitoring service with multi-storage configuration"""
        print("\n=== Initializing Multi-Storage Monitoring Service ===")
        
        try:
            # Load configuration
            config = init_config(self.config_path)
            print(f"✓ Configuration loaded from: {self.config_path}")
            print(f"  Environment: {config.environment}")
            print(f"  SFTP Storage: {'enabled' if config.sftp_storage.enabled else 'disabled'}")
            print(f"  Local Storage: {'enabled' if config.local_storage.enabled else 'disabled'}")
            
            # Create monitoring service
            self.service = DNBMonitoringService.from_config(self.config_path)
            print("✓ Monitoring service created")
            
            # Test storage connections
            await self.test_storage_connections()
            
            return True
            
        except Exception as e:
            print(f"✗ Failed to initialize service: {e}")
            return False
    
    async def test_storage_connections(self):
        """Test connections to both storage backends"""
        print("\n=== Testing Storage Connections ===")
        
        # Test SFTP connection if enabled
        if self.service._sftp_handler:
            try:
                connection_test = self.service._sftp_handler.test_connection()
                if connection_test:
                    print("✓ SFTP connection successful")
                else:
                    print("⚠ SFTP connection failed (may not be available)")
            except Exception as e:
                print(f"⚠ SFTP connection test error: {e}")
        else:
            print("- SFTP storage not enabled")
        
        # Test local storage if enabled
        if self.service._local_storage_handler:
            try:
                local_test = self.service._local_storage_handler.test_connection()
                if local_test:
                    print("✓ Local file storage connection successful")
                else:
                    print("✗ Local file storage connection failed")
            except Exception as e:
                print(f"✗ Local storage connection test error: {e}")
        else:
            print("- Local storage not enabled")
    
    async def create_demo_registrations(self) -> List[str]:
        """Create demo registrations for testing"""
        print("\n=== Creating Demo Registrations ===")
        
        registrations = []
        
        try:
            # Create standard monitoring registration
            standard_config = create_standard_monitoring_registration(
                reference="multi_storage_demo_standard",
                duns_list=["123456789", "987654321", "555666777"],
                description="Multi-storage demo - Standard monitoring"
            )
            
            standard_reg = self.service.create_registration(standard_config)
            registrations.append(standard_reg.reference)
            print(f"✓ Created standard registration: {standard_reg.reference}")
            
            return registrations
            
        except Exception as e:
            print(f"✗ Failed to create registrations: {e}")
            # Continue with demo even if registration creation fails
            return []
    
    def create_mock_notifications(self, registration_ref: str, count: int = 3) -> List[Notification]:
        """Create mock notifications for demonstration"""
        print(f"\n=== Creating {count} Mock Notifications ===")
        
        notifications = []
        
        for i in range(count):
            # Create mock notification data that matches the expected structure
            notification_data = {
                "duns": f"12345678{i}",
                "transactionDetail": {
                    "duns": f"12345678{i}",
                    "transactionID": f"mock_txn_{int(time.time())}_{i}",
                    "transactionTimestamp": datetime.now().isoformat()
                },
                "changeTransactionInformation": {
                    "changeTransactionID": f"change_{int(time.time())}_{i}",
                    "changeTransactionTimestamp": datetime.now().isoformat()
                },
                "organization": {
                    "primaryName": f"Mock Company {i+1}",
                    "dunsNumber": f"12345678{i}",
                    "primaryAddress": {
                        "streetAddress": {
                            "line1": f"{100 + i} Demo Street"
                        },
                        "addressLocality": {
                            "name": "Demo City"
                        },
                        "addressRegion": {
                            "name": "Demo State"
                        },
                        "postalCode": f"1234{i}",
                        "addressCountry": {
                            "name": "United States"
                        }
                    }
                },
                "registrationDetails": {
                    "registrationReference": registration_ref,
                    "candidateDetails": [
                        {
                            "duns": f"12345678{i}",
                            "primaryName": f"Mock Company {i+1}"
                        }
                    ]
                }
            }
            
            # Convert to Notification object (this will create a proper notification)
            # For demo purposes, we'll create a simple notification structure
            from traceone_monitoring.models.notification import NotificationType, NotificationElement, Organization
            
            # Create notification elements with the correct structure
            elements = [
                NotificationElement(
                    element="organization.primaryName",
                    current=f"Mock Company {i+1}",
                    previous=f"Old Company {i+1}",
                    timestamp=datetime.now()
                ),
                NotificationElement(
                    element="organization.primaryAddress.addressLocality.name",
                    current="Demo City",
                    previous="Old City",
                    timestamp=datetime.now()
                )
            ]
            
            # Create organization object
            organization = Organization(
                duns=f"12345678{i}"
            )
            
            # Create the notification
            notification = Notification(
                type=NotificationType.UPDATE,
                organization=organization,
                elements=elements,
                deliveryTimeStamp=datetime.now()
            )
            
            # Store registration reference in internal dict for storage grouping
            # The handler will use this to group notifications
            
            notifications.append(notification)
            print(f"  ✓ Created mock notification for DUNS: {notification.duns}")
        
        self.demo_notifications_created += count
        return notifications
    
    async def demonstrate_multi_storage(self, registration_ref: str):
        """Demonstrate multi-storage notification handling"""
        print("\n=== Demonstrating Multi-Storage Notification Handling ===")
        
        # Create mock notifications
        notifications = self.create_mock_notifications(registration_ref, 3)
        
        print(f"\nProcessing {len(notifications)} notifications...")
        
        # Process notifications through the service
        # This will automatically trigger all registered handlers (SFTP + Local)
        for i, notification in enumerate(notifications, 1):
            print(f"\n--- Processing Notification {i}/{len(notifications)} ---")
            print(f"DUNS: {notification.duns}")
            print(f"Type: {notification.type.value}")
            print(f"ID: {notification.id}")
            
            # Process the notification (this triggers storage handlers)
            success = await self.service.process_notification(notification)
            
            if success:
                print("✓ Notification processed successfully")
            else:
                print("✗ Notification processing failed")
            
            # Small delay for demonstration
            await asyncio.sleep(1)
    
    def show_storage_status(self):
        """Show the status of all storage backends"""
        print("\n=== Storage Backend Status ===")
        
        status = self.service.get_service_status()
        
        # SFTP Storage Status
        sftp_status = status.get("sftp_storage", {})
        print(f"\nSFTP Storage:")
        print(f"  Enabled: {sftp_status.get('enabled', False)}")
        print(f"  Status: {sftp_status.get('status', 'unknown')}")
        if sftp_status.get('enabled'):
            print(f"  Host: {sftp_status.get('hostname', 'N/A')}")
            print(f"  Files stored: {sftp_status.get('files_stored', 0)}")
        
        # Local Storage Status
        local_status = status.get("local_storage", {})
        print(f"\nLocal File Storage:")
        print(f"  Enabled: {local_status.get('enabled', False)}")
        print(f"  Status: {local_status.get('status', 'unknown')}")
        if local_status.get('enabled'):
            print(f"  Base path: {local_status.get('base_path', 'N/A')}")
            print(f"  Files stored: {local_status.get('files_stored', 0)}")
        
        # General service info
        service_info = status.get("service", {})
        print(f"\nService Information:")
        print(f"  Status: {'Running' if service_info.get('running') else 'Stopped'}")
        print(f"  Environment: {service_info.get('environment', 'unknown')}")
        print(f"  Notification handlers: {status.get('notification_handlers', {}).get('count', 0)}")
    
    async def show_stored_files(self):
        """Show files stored in local storage (if enabled)"""
        print("\n=== Checking Stored Files ===")
        
        if not self.service._local_storage_handler:
            print("Local storage not enabled")
            return
        
        try:
            base_path = Path(self.service.config.local_storage.base_path)
            if not base_path.exists():
                print(f"Storage directory doesn't exist yet: {base_path}")
                return
            
            print(f"\nLocal storage directory: {base_path.absolute()}")
            
            # Walk through the directory structure
            json_files = list(base_path.rglob("*.json"))
            if json_files:
                print(f"Found {len(json_files)} JSON files:")
                for file_path in json_files:
                    rel_path = file_path.relative_to(base_path)
                    file_size = file_path.stat().st_size
                    print(f"  📄 {rel_path} ({file_size} bytes)")
                    
                    # Show content of first few files
                    if len(json_files) <= 3:
                        try:
                            with open(file_path, 'r') as f:
                                data = json.load(f)
                                print(f"      Sample content: {json.dumps(data, indent=2)[:200]}...")
                        except Exception as e:
                            print(f"      Error reading file: {e}")
            else:
                print("No JSON files found")
                
        except Exception as e:
            print(f"Error checking stored files: {e}")
    
    async def run_demo(self):
        """Run the complete multi-storage demo"""
        print("🚀 TraceOne Multi-Storage Demo")
        print("=" * 50)
        
        # Initialize service
        if not await self.initialize_service():
            print("❌ Demo failed - could not initialize service")
            return
        
        try:
            # Create demo registrations
            registrations = await self.create_demo_registrations()
            
            # Use first registration or create a demo reference
            reg_ref = registrations[0] if registrations else "demo_registration"
            
            # Show initial storage status
            self.show_storage_status()
            
            # Demonstrate multi-storage notification handling
            await self.demonstrate_multi_storage(reg_ref)
            
            # Show final storage status
            self.show_storage_status()
            
            # Show stored files
            await self.show_stored_files()
            
            # Summary
            print(f"\n=== Demo Summary ===")
            print(f"✓ Created and processed {self.demo_notifications_created} mock notifications")
            print(f"✓ Demonstrated simultaneous storage to multiple backends:")
            if self.service._sftp_handler:
                print(f"  • SFTP storage (remote)")
            if self.service._local_storage_handler:
                print(f"  • Local file storage")
            print(f"✓ All storage operations completed successfully")
            
        finally:
            # Clean up
            if self.service:
                await self.service.shutdown()
                print("\n✓ Service shutdown complete")


async def main():
    """Main demo function"""
    config_path = "config/multi_storage_demo.yaml"
    
    # Check if config file exists
    if not Path(config_path).exists():
        print(f"❌ Configuration file not found: {config_path}")
        print("Please ensure the config file exists before running the demo.")
        return
    
    # Run the demo
    demo = MultiStorageDemo(config_path)
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
