#!/usr/bin/env python3
"""
Automated DUNS Notification Monitoring
Only monitors notifications from existing D&B registration - does NOT create new registrations.
"""

import sys
import os
import asyncio
import argparse
import signal
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json

# Add the source directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
from traceone_monitoring.utils.config import ConfigManager
from traceone_monitoring.services.monitoring_service import DNBMonitoringService
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class AutomatedMonitoring:
    """Automated monitoring for existing D&B registrations"""
    
    def __init__(self, config_file: str, env_file: str = None):
        """Initialize monitoring service"""
        if env_file:
            load_dotenv(env_file)
        
        self.config_manager = ConfigManager.from_file(config_file)
        self.app_config = self.config_manager.load_config()
        self.monitoring_service = None
        self.running = False
        
        # Statistics tracking
        self.stats = {
            "start_time": datetime.utcnow().isoformat(),
            "total_polls": 0,
            "total_notifications": 0,
            "last_notification_time": None,
            "errors": 0,
            "registrations_monitored": set()
        }
        
        logger.info("Automated monitoring initialized", 
                   config=config_file, 
                   env=env_file)
    
    async def setup(self) -> bool:
        """Set up monitoring service"""
        try:
            logger.info("Setting up automated monitoring service...")
            
            # Initialize monitoring service (does not create registrations)
            self.monitoring_service = DNBMonitoringService(self.app_config)
            
            # Test authentication
            auth_test = await asyncio.get_event_loop().run_in_executor(
                None, self.monitoring_service.authenticator.get_token
            )
            
            if not auth_test:
                logger.error("Authentication failed")
                return False
            
            logger.info("Automated monitoring service setup completed")
            return True
            
        except Exception as e:
            logger.error("Setup failed", error=str(e))
            return False
    
    async def monitor_registration(self, registration_name: str) -> int:
        """Monitor notifications for a specific existing registration"""
        logger.info("Monitoring registration for notifications", 
                   registration=registration_name)
        
        try:
            # Pull notifications from existing registration
            notifications = await self.monitoring_service.pull_notifications(
                registration_name, 
                max_notifications=50
            )
            
            notification_count = len(notifications)
            self.stats["total_notifications"] += notification_count
            self.stats["registrations_monitored"].add(registration_name)
            
            if notification_count > 0:
                self.stats["last_notification_time"] = datetime.utcnow().isoformat()
                logger.info("Notifications received", 
                           registration=registration_name,
                           count=notification_count)
                
                # Log summary of notifications
                for notification in notifications[:5]:  # Log first 5
                    try:
                        logger.info("Notification summary",
                                   registration=registration_name,
                                   notification_id=str(notification.id),
                                   notification_type=notification.type.value if hasattr(notification.type, 'value') else str(notification.type),
                                   duns=getattr(notification.organization, 'duns', 'Unknown') if hasattr(notification, 'organization') else 'Unknown')
                    except Exception as e:
                        logger.debug("Error logging notification details", error=str(e))
            else:
                logger.info("No new notifications", 
                           registration=registration_name)
            
            return notification_count
            
        except Exception as e:
            logger.error("Error monitoring registration",
                        registration=registration_name,
                        error=str(e))
            self.stats["errors"] += 1
            return 0
    
    async def monitor_continuously(self, registration_name: str, poll_interval_minutes: int = 5, duration_hours: Optional[int] = None):
        """Run continuous monitoring"""
        
        logger.info("Starting continuous monitoring",
                   registration=registration_name,
                   poll_interval_minutes=poll_interval_minutes,
                   duration_hours=duration_hours or "unlimited")
        
        self.running = True
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=duration_hours) if duration_hours else None
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal", signal=signum)
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            while self.running:
                current_time = datetime.utcnow()
                
                # Check if we should stop (duration limit)
                if end_time and current_time > end_time:
                    logger.info("Duration limit reached, stopping monitoring")
                    break
                
                # Monitor for notifications
                logger.info("Polling for notifications...", 
                           poll_number=self.stats["total_polls"] + 1)
                
                notification_count = await self.monitor_registration(registration_name)
                self.stats["total_polls"] += 1
                
                # Save current stats
                self.save_monitoring_stats()
                
                if not self.running:
                    break
                
                # Wait for next poll
                logger.info("Waiting for next poll",
                           next_poll_in_minutes=poll_interval_minutes,
                           total_notifications_so_far=self.stats["total_notifications"])
                
                for _ in range(poll_interval_minutes * 60):  # Convert to seconds
                    if not self.running:
                        break
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error("Error in continuous monitoring", error=str(e))
        
        finally:
            self.running = False
            logger.info("Monitoring stopped",
                       total_polls=self.stats["total_polls"],
                       total_notifications=self.stats["total_notifications"],
                       duration_hours=((datetime.utcnow() - start_time).total_seconds() / 3600))
    
    def save_monitoring_stats(self):
        """Save monitoring statistics"""
        try:
            self.stats["current_time"] = datetime.utcnow().isoformat()
            self.stats["registrations_monitored"] = list(self.stats["registrations_monitored"])
            
            stats_file = Path("./monitoring_stats.json")
            with open(stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2, default=str)
                
        except Exception as e:
            logger.error("Error saving monitoring stats", error=str(e))
    
    async def single_poll(self, registration_name: str):
        """Perform a single poll for notifications"""
        logger.info("Performing single notification poll", registration=registration_name)
        
        notification_count = await self.monitor_registration(registration_name)
        self.stats["total_polls"] = 1
        
        # Save stats
        self.save_monitoring_stats()
        
        logger.info("Single poll completed",
                   notifications_received=notification_count)
        
        return notification_count
    
    async def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up monitoring service...")
        self.running = False
        
        if self.monitoring_service:
            try:
                await self.monitoring_service.shutdown()
            except Exception as e:
                logger.warning("Error during cleanup", error=str(e))
        
        logger.info("Cleanup completed")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Automated DUNS Notification Monitoring")
    parser.add_argument("--config", default="config/real-test.yaml", 
                       help="Configuration file path")
    parser.add_argument("--env", default="config/real-test.env",
                       help="Environment file path")
    parser.add_argument("--registration-name", default="TRACE_Company_info_dev",
                       help="Registration name to monitor")
    parser.add_argument("--mode", choices=["single", "continuous"], default="single",
                       help="Monitoring mode: single poll or continuous")
    parser.add_argument("--poll-interval", type=int, default=5,
                       help="Poll interval in minutes (for continuous mode)")
    parser.add_argument("--duration", type=int, default=None,
                       help="Duration to run in hours (for continuous mode, unlimited if not specified)")
    
    args = parser.parse_args()
    
    print("🔍 Starting Automated DUNS Notification Monitoring")
    print(f"📋 Configuration: {args.config}")
    print(f"🔑 Environment: {args.env}")
    print(f"📝 Registration: {args.registration_name}")
    print(f"⚙️  Mode: {args.mode}")
    if args.mode == "continuous":
        print(f"⏱️  Poll Interval: {args.poll_interval} minutes")
        print(f"⏳ Duration: {args.duration or 'unlimited'} hours")
    print("=" * 60)
    
    # Initialize monitoring
    monitor = AutomatedMonitoring(args.config, args.env)
    
    try:
        # Setup
        print("\n🔧 Setting up monitoring service...")
        if not await monitor.setup():
            print("❌ Setup failed. Check your configuration and credentials.")
            return 1
        
        print("✅ Setup completed successfully")
        
        if args.mode == "single":
            # Single poll
            print(f"\n🔍 Performing single poll for '{args.registration_name}'...")
            notification_count = await monitor.single_poll(args.registration_name)
            
            print(f"\n📊 Results:")
            print(f"   Notifications received: {notification_count}")
            print(f"   Results saved to: monitoring_stats.json")
            
        else:
            # Continuous monitoring
            print(f"\n🔄 Starting continuous monitoring for '{args.registration_name}'...")
            print("   Press Ctrl+C to stop monitoring gracefully")
            
            await monitor.monitor_continuously(
                args.registration_name, 
                args.poll_interval, 
                args.duration
            )
        
        print("\n🎉 Monitoring completed successfully!")
        print("\n📋 Check Results:")
        print("   • monitoring_stats.json - Monitoring statistics")
        print("   • ./test_results/ - Notification files (if any received)")
        print("   • ./logs/ - Detailed monitoring logs")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Monitoring failed with error: {e}")
        logger.error("Monitoring failed", error=str(e))
        return 1
        
    finally:
        await monitor.cleanup()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
