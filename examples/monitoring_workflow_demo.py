#!/usr/bin/env python3
"""
TraceOne Monitoring Workflow Demo with SFTP Integration

This script demonstrates the complete monitoring workflow including:
1. Service initialization with SFTP storage
2. Registration creation
3. Notification monitoring 
4. Automatic SFTP storage of notifications
5. Status monitoring and health checks

Usage:
    python monitoring_workflow_demo.py
"""

import sys
import asyncio
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List

# Add src to path  
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traceone_monitoring.services.monitoring_service import DNBMonitoringService, create_standard_monitoring_registration
from traceone_monitoring.models.notification import Notification, NotificationType
from traceone_monitoring.utils.config import init_config
import structlog

# Setup logging
logger = structlog.get_logger(__name__)


class MonitoringWorkflowDemo:
    """Complete monitoring workflow demonstration"""
    
    def __init__(self, config_path: str = None):
        """Initialize the demo"""
        self.config_path = config_path
        self.service: DNBMonitoringService = None
        self.registration_ref = "TraceOne_Demo_Monitoring"
        
    async def initialize_service(self):
        """Initialize the monitoring service"""
        print("🚀 Initializing TraceOne Monitoring Service")
        print("=" * 50)
        
        # Load configuration
        try:
            if self.config_path:
                config = init_config(self.config_path)
                print(f"   ✅ Configuration loaded from: {self.config_path}")
            else:
                config = init_config()
                print("   ✅ Configuration loaded from environment")
                
        except Exception as e:
            print(f"   ❌ Configuration loading failed: {e}")
            return False
        
        # Create monitoring service
        try:
            self.service = DNBMonitoringService(config)
            print("   ✅ Monitoring service initialized")
            
            # Display configuration status
            print(f"   📋 Environment: {config.environment}")
            print(f"   📋 Debug Mode: {config.debug}")
            print(f"   📋 SFTP Storage: {'Enabled' if config.sftp_storage.enabled else 'Disabled'}")
            
            if config.sftp_storage.enabled:
                print(f"   📋 SFTP Server: {config.sftp_storage.hostname}:{config.sftp_storage.port}")
                print(f"   📋 SFTP Format: {config.sftp_storage.file_format}")
                print(f"   📋 SFTP Path: {config.sftp_storage.remote_base_path}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Service initialization failed: {e}")
            return False
    
    def create_monitoring_registration(self):
        """Create a monitoring registration"""
        print(f"\n📝 Creating Monitoring Registration")
        print("=" * 40)
        
        try:
            # Sample DUNS numbers for demo (these are fake)
            demo_duns = [
                "123456789",  # Demo company 1
                "987654321",  # Demo company 2 
                "555666777",  # Demo company 3
            ]
            
            # Create registration configuration
            reg_config = create_standard_monitoring_registration(
                reference=self.registration_ref,
                duns_list=demo_duns,
                description="TraceOne monitoring workflow demonstration"
            )
            
            print(f"   📋 Registration Reference: {self.registration_ref}")
            print(f"   📋 DUNS Count: {len(demo_duns)}")
            print(f"   📋 Data Blocks: {', '.join(reg_config.data_blocks)}")
            
            # Create the registration
            registration = self.service.create_registration(reg_config)
            print(f"   ✅ Registration created successfully")
            print(f"   📋 Registration ID: {registration.id}")
            print(f"   📋 Status: {registration.status}")
            
            return registration
            
        except Exception as e:
            print(f"   ❌ Registration creation failed: {e}")
            return None
    
    async def activate_monitoring(self):
        """Activate monitoring for the registration"""
        print(f"\n🔄 Activating Monitoring")
        print("=" * 30)
        
        try:
            success = await self.service.activate_monitoring(self.registration_ref)
            if success:
                print("   ✅ Monitoring activated successfully")
            else:
                print("   ❌ Monitoring activation failed")
            return success
            
        except Exception as e:
            print(f"   ❌ Monitoring activation error: {e}")
            return False
    
    def setup_notification_handlers(self):
        """Setup additional notification handlers"""
        print(f"\n🔧 Setting up Notification Handlers")
        print("=" * 40)
        
        # Log handler (built-in)
        from traceone_monitoring.services.monitoring_service import log_notification_handler
        self.service.add_notification_handler(log_notification_handler)
        print("   ✅ Log notification handler added")
        
        # Custom demo handler
        def demo_handler(notifications: List[Notification]):
            print(f"   📨 Demo Handler: Processing {len(notifications)} notifications")
            for notification in notifications:
                print(f"      - DUNS: {notification.duns}, Type: {notification.type.value}")
        
        self.service.add_notification_handler(demo_handler)
        print("   ✅ Demo notification handler added")
        
        # SFTP handler is automatically added if enabled in config
        if self.service._sftp_handler:
            print("   ✅ SFTP notification handler already registered")
        else:
            print("   ℹ️  SFTP storage disabled in configuration")
    
    async def demonstrate_notification_polling(self):
        """Demonstrate notification polling"""
        print(f"\n📡 Demonstrating Notification Polling")
        print("=" * 40)
        
        try:
            print("   📥 Pulling notifications...")
            notifications = await self.service.pull_notifications(
                self.registration_ref, 
                max_notifications=10
            )
            
            print(f"   📊 Retrieved {len(notifications)} notifications")
            
            if notifications:
                print("   📋 Notification Details:")
                for i, notification in enumerate(notifications, 1):
                    print(f"      {i}. DUNS: {notification.duns}")
                    print(f"         Type: {notification.type.value}")
                    print(f"         Timestamp: {notification.delivery_timestamp}")
                    print(f"         Elements: {len(notification.elements)}")
            else:
                print("   ℹ️  No new notifications available")
                
                # For demo purposes, create fake notifications
                print("   🎭 Creating demo notifications for testing...")
                demo_notifications = self.create_demo_notifications()
                
                # Process them manually to trigger handlers
                for notification in demo_notifications:
                    await self.service.process_notification(notification)
                    
                print(f"   ✅ Processed {len(demo_notifications)} demo notifications")
            
        except Exception as e:
            print(f"   ❌ Notification polling failed: {e}")
    
    def create_demo_notifications(self) -> List[Notification]:
        """Create demo notifications for testing"""
        notifications = []
        
        demo_data = [
            ("123456789", NotificationType.UPDATE),
            ("987654321", NotificationType.UPDATE),
            ("555666777", NotificationType.UPDATE),
        ]
        
        for duns, notification_type in demo_data:
            notification = Notification(
                type=notification_type,
                organization={"duns": duns},
                delivery_timestamp=datetime.utcnow(),
                elements=[]
            )
            # Set registration reference for SFTP storage
            notification.registration_reference = self.registration_ref
            notifications.append(notification)
            
        return notifications
    
    def display_service_status(self):
        """Display comprehensive service status"""
        print(f"\n📊 Service Status")
        print("=" * 25)
        
        try:
            status = self.service.get_service_status()
            
            print(f"   🚦 Service Status:")
            print(f"      Running: {status['service']['running']}")
            print(f"      Environment: {status['service']['environment']}")
            print(f"      Debug Mode: {status['service']['debug_mode']}")
            
            print(f"\n   🔐 Authentication:")
            print(f"      Authenticated: {status['authentication']['is_authenticated']}")
            print(f"      Token Expires In: {status['authentication']['token_expires_in']}s")
            
            print(f"\n   📡 API Client:")
            print(f"      Health Check: {status['api_client']['health_check']}")
            print(f"      Rate Limit: {status['api_client']['rate_limit']} req/s")
            
            print(f"\n   📋 Registrations:")
            print(f"      Total Count: {status['registrations']['total_count']}")
            print(f"      Active Count: {status['registrations']['active_count']}")
            print(f"      Background Monitors: {status['registrations']['background_monitors']}")
            
            print(f"\n   🔔 Notification Handlers:")
            print(f"      Handler Count: {status['notification_handlers']['count']}")
            
            print(f"\n   💾 SFTP Storage:")
            sftp_status = status['sftp_storage']
            print(f"      Enabled: {sftp_status['enabled']}")
            print(f"      Status: {sftp_status['status']}")
            if sftp_status['enabled']:
                print(f"      Hostname: {sftp_status.get('hostname', 'N/A')}")
                print(f"      Format: {sftp_status.get('file_format', 'N/A')}")
                print(f"      Organize by Date: {sftp_status.get('organize_by_date', 'N/A')}")
            
        except Exception as e:
            print(f"   ❌ Status retrieval failed: {e}")
    
    async def test_sftp_connection(self):
        """Test SFTP connection if enabled"""
        print(f"\n🔌 Testing SFTP Connection")
        print("=" * 30)
        
        if self.service._sftp_handler:
            try:
                connection_ok = self.service._sftp_handler.test_connection()
                if connection_ok:
                    print("   ✅ SFTP connection test successful")
                else:
                    print("   ❌ SFTP connection test failed")
                return connection_ok
            except Exception as e:
                print(f"   ❌ SFTP connection test error: {e}")
                return False
        else:
            print("   ℹ️  SFTP storage is disabled")
            return True
    
    async def demonstrate_background_monitoring(self):
        """Demonstrate background monitoring"""
        print(f"\n🔄 Demonstrating Background Monitoring")
        print("=" * 40)
        
        def background_handler(notifications: List[Notification]):
            if notifications:
                print(f"   🔔 Background Monitor: {len(notifications)} new notifications!")
                for notification in notifications:
                    print(f"      - {notification.duns}: {notification.type.value}")
        
        try:
            # Start background monitoring
            print("   🚀 Starting background monitoring...")
            self.service.start_background_monitoring(
                self.registration_ref,
                background_handler,
                polling_interval=60  # Check every minute
            )
            print("   ✅ Background monitoring started")
            
            # Let it run for a short time
            print("   ⏳ Monitoring for 30 seconds...")
            await asyncio.sleep(30)
            
            # Stop background monitoring
            print("   🛑 Stopping background monitoring...")
            self.service.stop_background_monitoring(self.registration_ref)
            print("   ✅ Background monitoring stopped")
            
        except Exception as e:
            print(f"   ❌ Background monitoring demo failed: {e}")
    
    async def run_complete_demo(self):
        """Run the complete monitoring workflow demo"""
        print("🎯 TraceOne Monitoring Workflow Demo")
        print("=" * 50)
        print("This demo shows the complete monitoring workflow including SFTP integration\n")
        
        try:
            # 1. Initialize service
            if not await self.initialize_service():
                print("❌ Demo failed during service initialization")
                return
            
            # 2. Test SFTP connection first
            if not await self.test_sftp_connection():
                print("⚠️  SFTP connection failed - continuing with demo")
            
            # 3. Create registration
            registration = self.create_monitoring_registration()
            if not registration:
                print("❌ Demo failed during registration creation")
                return
            
            # 4. Activate monitoring
            if not await self.activate_monitoring():
                print("⚠️  Monitoring activation failed - continuing with demo")
            
            # 5. Setup handlers
            self.setup_notification_handlers()
            
            # 6. Demonstrate notification polling
            await self.demonstrate_notification_polling()
            
            # 7. Show service status
            self.display_service_status()
            
            # 8. Demonstrate background monitoring (optional)
            # await self.demonstrate_background_monitoring()
            
            print(f"\n🎉 Monitoring Workflow Demo Complete!")
            print("✨ Key Features Demonstrated:")
            print("   • Service initialization with configuration")
            print("   • Monitoring registration creation")
            print("   • SFTP storage integration")
            print("   • Notification processing and handling")
            print("   • Service status monitoring")
            print("   • Health checks and error handling")
            
        except Exception as e:
            print(f"❌ Demo failed with error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Cleanup
            if self.service:
                await self.service.shutdown()
                print("\n🧹 Service shutdown complete")


async def main():
    """Main demo runner"""
    # Check for config file argument
    config_path = None
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
        print(f"Using configuration file: {config_path}")
    else:
        print("Using environment configuration (set SFTP_ENABLED=true to test SFTP)")
    
    # Run the demo
    demo = MonitoringWorkflowDemo(config_path)
    await demo.run_complete_demo()


if __name__ == "__main__":
    # Run the demo
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        sys.exit(1)
