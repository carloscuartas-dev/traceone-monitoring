#!/usr/bin/env python3
"""
Real-time Testing Script for TraceOne Monitoring Service

This script demonstrates how to work with real D&B data using your dev registration entity.
It includes various testing scenarios for real-time monitoring capabilities.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import structlog
import click

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traceone_monitoring import DNBMonitoringService
from traceone_monitoring.models.registration import RegistrationConfig
from traceone_monitoring.services.monitoring_service import (
    create_standard_monitoring_registration,
    create_financial_monitoring_registration,
    log_notification_handler
)
from traceone_monitoring.utils.config import init_config


logger = structlog.get_logger(__name__)


class RealTimeTestRunner:
    """
    Real-time test runner for TraceOne monitoring service
    """
    
    def __init__(self, config_path: str = "config/dev.yaml"):
        """Initialize the test runner with configuration"""
        self.config_path = config_path
        self.service = None
        self.active_registrations = {}
    
    async def setup(self):
        """Setup the monitoring service"""
        try:
            # Initialize the service
            self.service = DNBMonitoringService.from_config(self.config_path)
            
            # Add logging handler for notifications
            self.service.add_notification_handler(log_notification_handler)
            
            logger.info("Real-time test runner initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize test runner", error=str(e))
            return False
    
    async def test_authentication(self):
        """Test D&B API authentication"""
        logger.info("🔐 Testing D&B API authentication...")
        
        try:
            # Perform health check which includes authentication test
            health_status = self.service.health_check()
            
            if health_status:
                logger.info("✅ Authentication successful - Ready for real-time testing")
                
                # Get detailed status
                status_info = self.service.get_service_status()
                logger.info("Authentication details",
                           authenticated=status_info['authentication']['is_authenticated'],
                           token_expires_in=f"{status_info['authentication']['token_expires_in']} seconds",
                           api_health=status_info['api_client']['health_check'])
                return True
            else:
                logger.error("❌ Authentication failed - Check your credentials")
                return False
                
        except Exception as e:
            logger.error("❌ Authentication test failed", error=str(e))
            return False
    
    async def create_test_registration(
        self, 
        name: str,
        duns_list: List[str],
        monitoring_type: str = "standard"
    ) -> str:
        """Create a test registration with real DUNS numbers"""
        
        logger.info("📝 Creating test registration",
                   name=name,
                   duns_count=len(duns_list),
                   type=monitoring_type)
        
        try:
            # Create registration configuration
            reference = f"TraceOne_Test_{name.replace(' ', '_')}"
            
            if monitoring_type == "financial":
                config = create_financial_monitoring_registration(
                    reference=reference,
                    duns_list=duns_list,
                    description=f"Real-time test registration: {name}"
                )
            else:
                config = create_standard_monitoring_registration(
                    reference=reference,
                    duns_list=duns_list,
                    description=f"Real-time test registration: {name}"
                )
            
            # Create the registration
            registration = self.service.create_registration(config)
            
            # Store for tracking
            self.active_registrations[reference] = {
                'registration': registration,
                'created_at': datetime.utcnow(),
                'duns_list': duns_list,
                'type': monitoring_type
            }
            
            logger.info("✅ Test registration created",
                       reference=reference,
                       registration_id=str(registration.id),
                       status=registration.status.value)
            
            return reference
            
        except Exception as e:
            logger.error("❌ Failed to create test registration", error=str(e))
            raise
    
    async def activate_and_monitor(
        self,
        registration_ref: str,
        duration_minutes: int = 5,
        polling_interval: int = 30
    ):
        """Activate monitoring and run for specified duration"""
        
        logger.info("🚀 Activating real-time monitoring",
                   registration=registration_ref,
                   duration_minutes=duration_minutes,
                   polling_interval=polling_interval)
        
        try:
            # Activate monitoring
            success = await self.service.activate_monitoring(registration_ref)
            
            if not success:
                raise RuntimeError(f"Failed to activate monitoring for {registration_ref}")
            
            logger.info("✅ Monitoring activated successfully")
            
            # Start monitoring for specified duration
            end_time = datetime.now() + timedelta(minutes=duration_minutes)
            notification_count = 0
            
            logger.info("📡 Starting real-time monitoring session",
                       end_time=end_time.strftime("%H:%M:%S"))
            
            async for notifications in self.service.monitor_continuously(
                registration_ref, 
                polling_interval=polling_interval,
                max_notifications=50
            ):
                # Check if we should stop
                if datetime.now() > end_time:
                    logger.info("⏰ Monitoring session completed")
                    break
                
                if notifications:
                    notification_count += len(notifications)
                    logger.info("📬 Notifications received",
                               count=len(notifications),
                               total=notification_count)
                    
                    # Process each notification
                    for notification in notifications:
                        await self.process_test_notification(notification)
                        await self.service.process_notification(notification)
                else:
                    logger.info("🔍 Polling completed - No new notifications",
                               time=datetime.now().strftime("%H:%M:%S"))
            
            return notification_count
            
        except Exception as e:
            logger.error("❌ Monitoring session failed", error=str(e))
            raise
    
    async def process_test_notification(self, notification):
        """Process a notification for testing purposes"""
        
        logger.info("🔔 Processing notification",
                   duns=notification.duns,
                   type=notification.type.value,
                   elements_count=len(notification.elements),
                   delivery_time=notification.delivery_timestamp)
        
        # Log details of what changed
        for element in notification.elements:
            logger.info("📊 Data element change",
                       element=element.element,
                       previous_value=element.previous_value,
                       new_value=element.new_value,
                       change_type=element.change_indicator)
    
    async def test_pull_notifications(self, registration_ref: str, max_notifications: int = 20):
        """Test pulling notifications on-demand"""
        
        logger.info("📥 Testing notification pull",
                   registration=registration_ref,
                   max_notifications=max_notifications)
        
        try:
            notifications = await self.service.pull_notifications(
                registration_ref, 
                max_notifications
            )
            
            logger.info("✅ Notifications pulled successfully",
                       count=len(notifications))
            
            if notifications:
                for i, notification in enumerate(notifications, 1):
                    logger.info(f"📋 Notification {i}",
                               duns=notification.duns,
                               type=notification.type.value,
                               elements=len(notification.elements),
                               timestamp=notification.delivery_timestamp)
                    
                    # Process each notification
                    await self.process_test_notification(notification)
            else:
                logger.info("ℹ️  No notifications available at this time")
            
            return notifications
            
        except Exception as e:
            logger.error("❌ Failed to pull notifications", error=str(e))
            raise
    
    async def test_replay_functionality(self, registration_ref: str):
        """Test notification replay functionality"""
        
        logger.info("🔄 Testing notification replay functionality")
        
        try:
            # Replay notifications from 24 hours ago
            start_time = (datetime.utcnow() - timedelta(hours=24)).isoformat() + "Z"
            
            replayed_notifications = await self.service.replay_notifications(
                registration_ref,
                start_time
            )
            
            logger.info("✅ Notification replay completed",
                       replayed_count=len(replayed_notifications))
            
            for notification in replayed_notifications:
                logger.info("🔄 Replayed notification",
                           duns=notification.duns,
                           type=notification.type.value,
                           original_time=notification.delivery_timestamp)
            
            return replayed_notifications
            
        except Exception as e:
            logger.error("❌ Replay functionality test failed", error=str(e))
            raise
    
    async def cleanup(self):
        """Cleanup test resources"""
        logger.info("🧹 Cleaning up test resources")
        
        try:
            # Note: In a real scenario, you might want to keep registrations
            # for ongoing monitoring, so we'll just log them here
            for ref, info in self.active_registrations.items():
                logger.info("📝 Active test registration",
                           reference=ref,
                           created=info['created_at'],
                           duns_count=len(info['duns_list']))
            
            if self.service:
                await self.service.shutdown()
                logger.info("✅ Service shutdown completed")
                
        except Exception as e:
            logger.error("❌ Cleanup failed", error=str(e))


async def run_comprehensive_test():
    """Run a comprehensive real-time testing scenario"""
    
    # Setup logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    logger.info("🚀 Starting comprehensive real-time testing")
    
    # Initialize test runner
    test_runner = RealTimeTestRunner()
    
    try:
        # Setup
        if not await test_runner.setup():
            logger.error("Failed to setup test runner")
            return False
        
        # Test authentication
        if not await test_runner.test_authentication():
            logger.error("Authentication test failed")
            return False
        
        # REPLACE THESE WITH ACTUAL DUNS NUMBERS FROM YOUR DEV REGISTRATION
        test_duns = [
            "123456789",  # Replace with real DUNS
            "987654321",  # Replace with real DUNS
            "555666777"   # Replace with real DUNS
        ]
        
        logger.warning("⚠️  IMPORTANT: Replace test DUNS numbers with real ones from your dev registration")
        logger.info("📋 Test DUNS numbers", duns_list=test_duns)
        
        # Create test registration
        registration_ref = await test_runner.create_test_registration(
            name="Real Time Test",
            duns_list=test_duns,
            monitoring_type="standard"
        )
        
        # Test notification pull
        await test_runner.test_pull_notifications(registration_ref, max_notifications=10)
        
        # Test replay functionality
        await test_runner.test_replay_functionality(registration_ref)
        
        # Run real-time monitoring for 3 minutes
        notification_count = await test_runner.activate_and_monitor(
            registration_ref,
            duration_minutes=3,
            polling_interval=30
        )
        
        logger.info("🎉 Comprehensive testing completed successfully",
                   total_notifications=notification_count)
        
        return True
        
    except Exception as e:
        logger.error("❌ Comprehensive test failed", error=str(e))
        return False
        
    finally:
        await test_runner.cleanup()


@click.command()
@click.option('--duns', '-d', multiple=True, help='DUNS numbers to test with (from your dev registration)')
@click.option('--duns-file', '-f', help='CSV file containing DUNS numbers')
@click.option('--duns-column', '-c', default='duns', help='Column name for DUNS in CSV file')
@click.option('--monitoring-type', '-t', default='standard', 
              type=click.Choice(['standard', 'financial']), help='Type of monitoring')
@click.option('--duration', '-dur', default=5, help='Monitoring duration in minutes')
@click.option('--polling-interval', '-p', default=30, help='Polling interval in seconds')
@click.option('--max-duns', default=20, help='Maximum DUNS to process from CSV file')
def run_real_time_test(duns, duns_file, duns_column, monitoring_type, duration, polling_interval, max_duns):
    """Run real-time monitoring test with your dev registration entity"""
    
    # Load DUNS from various sources
    duns_list = list(duns) if duns else []
    
    # Load from CSV file if provided
    if duns_file:
        try:
            from duns_csv_loader import DunsCSVLoader
            loader = DunsCSVLoader()
            csv_duns = loader.load_from_csv(duns_file, duns_column)
            
            # Limit number of DUNS if requested
            if len(csv_duns) > max_duns:
                click.echo(f"⚠️  CSV contains {len(csv_duns)} DUNS, limiting to first {max_duns}")
                csv_duns = csv_duns[:max_duns]
            
            duns_list.extend(csv_duns)
            click.echo(f"✅ Loaded {len(csv_duns)} DUNS numbers from CSV: {duns_file}")
            
        except Exception as e:
            click.echo(f"❌ Error loading CSV file: {e}", err=True)
            return
    
    if not duns_list:
        click.echo("❌ Please provide DUNS numbers using one of these methods:")
        click.echo("  • Individual DUNS: -d 123456789 -d 987654321")
        click.echo("  • CSV file: -f your_duns.csv")
        click.echo("  • Both: -d 123456789 -f additional_duns.csv")
        return
    
    click.echo(f"📋 Testing with {len(duns_list)} DUNS numbers")
    for i, duns_num in enumerate(duns_list, 1):
        click.echo(f"  {i:2d}. {duns_num}")
    
    async def test_with_params():
        test_runner = RealTimeTestRunner()
        
        try:
            # Setup and authenticate
            if not await test_runner.setup():
                return False
            
            if not await test_runner.test_authentication():
                return False
            
            # Create registration with provided DUNS
            registration_ref = await test_runner.create_test_registration(
                name="Custom Real Time Test",
                duns_list=duns_list,
                monitoring_type=monitoring_type
            )
            
            # Run monitoring
            notification_count = await test_runner.activate_and_monitor(
                registration_ref,
                duration_minutes=duration,
                polling_interval=polling_interval
            )
            
            click.echo(f"✅ Test completed! Processed {notification_count} notifications")
            return True
            
        except Exception as e:
            click.echo(f"❌ Test failed: {e}")
            return False
        finally:
            await test_runner.cleanup()
    
    success = asyncio.run(test_with_params())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # If run with command line arguments, use click
    if len(sys.argv) > 1:
        run_real_time_test()
    else:
        # Run comprehensive test
        success = asyncio.run(run_comprehensive_test())
        sys.exit(0 if success else 1)
