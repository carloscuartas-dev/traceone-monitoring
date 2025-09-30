#!/usr/bin/env python3
"""
Automated DUNS Notification Monitoring with File Input
Reads DUNS numbers from a text file and monitors existing D&B registration.
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
import re

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


class DUNSFileReader:
    """Utility class for reading and validating DUNS from text files"""
    
    @staticmethod
    def read_duns_from_file(file_path: str) -> List[str]:
        """
        Read DUNS numbers from a text file
        
        Args:
            file_path: Path to the text file containing DUNS numbers
            
        Returns:
            List of valid DUNS numbers
        """
        duns_list = []
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            raise FileNotFoundError(f"DUNS file not found: {file_path}")
        
        logger.info("Reading DUNS from file", file_path=file_path)
        
        try:
            with open(file_path_obj, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                # Remove whitespace and comments
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Extract DUNS (should be 9 digits)
                duns_match = re.match(r'^(\d{9})(?:\s|$)', line)
                if duns_match:
                    duns = duns_match.group(1)
                    duns_list.append(duns)
                    logger.debug("Found valid DUNS", duns=duns, line_number=line_num)
                else:
                    logger.warning("Invalid DUNS format", line=line, line_number=line_num)
            
            logger.info("DUNS file parsed successfully", 
                       file_path=file_path,
                       total_duns=len(duns_list))
            
            return duns_list
            
        except Exception as e:
            logger.error("Error reading DUNS file", file_path=file_path, error=str(e))
            raise
    
    @staticmethod
    def validate_duns(duns_list: List[str]) -> List[str]:
        """Validate DUNS numbers format"""
        valid_duns = []
        
        for duns in duns_list:
            if re.match(r'^\d{9}$', duns):
                valid_duns.append(duns)
            else:
                logger.warning("Invalid DUNS format", duns=duns)
        
        return valid_duns
    
    @staticmethod
    def create_example_file(file_path: str):
        """Create an example DUNS file"""
        example_content = """# DUNS Numbers for Monitoring
# One DUNS per line - comments and empty lines are ignored
# Format: 9-digit DUNS number

001017545
001211952
001316439
001344381
001389360

# You can add more DUNS numbers here:
# 123456789
# 987654321

# Example companies for testing:
# 006273905
# 804735132
# 069032677
"""
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(example_content)
        
        logger.info("Example DUNS file created", file_path=file_path)


class FileBasedAutomatedMonitoring:
    """Automated monitoring that reads DUNS from file"""
    
    def __init__(self, config_file: str, env_file: str = None, duns_file: str = None):
        """Initialize monitoring service"""
        if env_file:
            load_dotenv(env_file)
        
        self.config_manager = ConfigManager.from_file(config_file)
        self.app_config = self.config_manager.load_config()
        self.monitoring_service = None
        self.running = False
        self.duns_file = duns_file or "./duns_list.txt"
        self.duns_list = []
        
        # Statistics tracking
        self.stats = {
            "start_time": datetime.utcnow().isoformat(),
            "duns_file": self.duns_file,
            "total_duns": 0,
            "total_polls": 0,
            "total_notifications": 0,
            "last_notification_time": None,
            "errors": 0,
            "registrations_monitored": set()
        }
        
        logger.info("File-based automated monitoring initialized", 
                   config=config_file, 
                   env=env_file,
                   duns_file=self.duns_file)
    
    def load_duns_from_file(self) -> bool:
        """Load DUNS numbers from file"""
        try:
            logger.info("Loading DUNS from file", file=self.duns_file)
            
            # Check if file exists, create example if not
            if not Path(self.duns_file).exists():
                logger.warning("DUNS file not found, creating example file", file=self.duns_file)
                DUNSFileReader.create_example_file(self.duns_file)
                print(f"📝 Created example DUNS file: {self.duns_file}")
                print("   Please edit this file with your DUNS numbers and run again.")
                return False
            
            # Read DUNS from file
            self.duns_list = DUNSFileReader.read_duns_from_file(self.duns_file)
            
            if not self.duns_list:
                logger.error("No valid DUNS found in file", file=self.duns_file)
                print(f"❌ No valid DUNS numbers found in {self.duns_file}")
                print("   Please check the file format and try again.")
                return False
            
            # Validate DUNS
            valid_duns = DUNSFileReader.validate_duns(self.duns_list)
            if len(valid_duns) != len(self.duns_list):
                logger.warning("Some DUNS were invalid", 
                              total=len(self.duns_list), 
                              valid=len(valid_duns))
            
            self.duns_list = valid_duns
            self.stats["total_duns"] = len(self.duns_list)
            
            logger.info("DUNS loaded successfully", 
                       file=self.duns_file,
                       total_duns=len(self.duns_list))
            
            return True
            
        except Exception as e:
            logger.error("Error loading DUNS from file", file=self.duns_file, error=str(e))
            return False
    
    async def setup(self) -> bool:
        """Set up monitoring service"""
        try:
            logger.info("Setting up file-based automated monitoring service...")
            
            # Load DUNS from file
            if not self.load_duns_from_file():
                return False
            
            # Initialize monitoring service (does not create registrations)
            self.monitoring_service = DNBMonitoringService(self.app_config)
            
            # Test authentication
            auth_test = await asyncio.get_event_loop().run_in_executor(
                None, self.monitoring_service.authenticator.get_token
            )
            
            if not auth_test:
                logger.error("Authentication failed")
                return False
            
            logger.info("File-based automated monitoring service setup completed",
                       total_duns=len(self.duns_list))
            return True
            
        except Exception as e:
            logger.error("Setup failed", error=str(e))
            return False
    
    async def monitor_registration(self, registration_name: str) -> int:
        """Monitor notifications for a specific existing registration"""
        logger.info("Monitoring registration for notifications", 
                   registration=registration_name,
                   duns_count=len(self.duns_list))
        
        try:
            # Pull notifications from existing registration
            notifications = await self.monitoring_service.pull_notifications(
                registration_name, 
                max_notifications=100
            )
            
            notification_count = len(notifications)
            self.stats["total_notifications"] += notification_count
            self.stats["registrations_monitored"].add(registration_name)
            
            if notification_count > 0:
                self.stats["last_notification_time"] = datetime.utcnow().isoformat()
                logger.info("Notifications received", 
                           registration=registration_name,
                           count=notification_count,
                           duns_monitored=len(self.duns_list))
                
                # Log summary of notifications for DUNS in our file
                our_duns_set = set(self.duns_list)
                matching_notifications = 0
                
                for notification in notifications[:10]:  # Log first 10
                    try:
                        notification_duns = getattr(notification.organization, 'duns', None) if hasattr(notification, 'organization') else None
                        
                        if notification_duns in our_duns_set:
                            matching_notifications += 1
                            logger.info("Notification for monitored DUNS",
                                       registration=registration_name,
                                       notification_id=str(notification.id),
                                       notification_type=notification.type.value if hasattr(notification.type, 'value') else str(notification.type),
                                       duns=notification_duns)
                        
                    except Exception as e:
                        logger.debug("Error logging notification details", error=str(e))
                
                logger.info("Notification summary",
                           registration=registration_name,
                           total_notifications=notification_count,
                           matching_our_duns=matching_notifications)
            else:
                logger.info("No new notifications", 
                           registration=registration_name,
                           duns_monitored=len(self.duns_list))
            
            return notification_count
            
        except Exception as e:
            logger.error("Error monitoring registration",
                        registration=registration_name,
                        error=str(e))
            self.stats["errors"] += 1
            return 0
    
    def save_monitoring_stats(self):
        """Save monitoring statistics"""
        try:
            self.stats["current_time"] = datetime.utcnow().isoformat()
            self.stats["registrations_monitored"] = list(self.stats["registrations_monitored"])
            self.stats["duns_list"] = self.duns_list
            
            stats_file = Path("./monitoring_stats_file.json")
            with open(stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2, default=str)
                
        except Exception as e:
            logger.error("Error saving monitoring stats", error=str(e))
    
    async def single_poll(self, registration_name: str):
        """Perform a single poll for notifications"""
        logger.info("Performing single notification poll", 
                   registration=registration_name,
                   duns_file=self.duns_file,
                   duns_count=len(self.duns_list))
        
        notification_count = await self.monitor_registration(registration_name)
        self.stats["total_polls"] = 1
        
        # Save stats
        self.save_monitoring_stats()
        
        logger.info("Single poll completed",
                   notifications_received=notification_count,
                   duns_monitored=len(self.duns_list))
        
        return notification_count
    
    async def monitor_continuously(self, registration_name: str, poll_interval_minutes: int = 5, duration_hours: Optional[int] = None):
        """Run continuous monitoring"""
        
        logger.info("Starting continuous monitoring",
                   registration=registration_name,
                   poll_interval_minutes=poll_interval_minutes,
                   duration_hours=duration_hours or "unlimited",
                   duns_file=self.duns_file,
                   duns_count=len(self.duns_list))
        
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
                
                # Reload DUNS from file (in case it was updated)
                old_count = len(self.duns_list)
                if self.load_duns_from_file():
                    new_count = len(self.duns_list)
                    if new_count != old_count:
                        logger.info("DUNS file updated", 
                                   old_count=old_count,
                                   new_count=new_count)
                
                # Monitor for notifications
                logger.info("Polling for notifications...", 
                           poll_number=self.stats["total_polls"] + 1,
                           duns_count=len(self.duns_list))
                
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
                       total_duns=len(self.duns_list),
                       duration_hours=((datetime.utcnow() - start_time).total_seconds() / 3600))
    
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
    parser = argparse.ArgumentParser(description="File-based Automated DUNS Notification Monitoring")
    parser.add_argument("--config", default="config/real-test.yaml", 
                       help="Configuration file path")
    parser.add_argument("--env", default="config/real-test.env",
                       help="Environment file path")
    parser.add_argument("--duns-file", default="./duns_list.txt",
                       help="Text file containing DUNS numbers (one per line)")
    parser.add_argument("--registration-name", default="TRACE_Company_info_dev",
                       help="Registration name to monitor")
    parser.add_argument("--mode", choices=["single", "continuous"], default="single",
                       help="Monitoring mode: single poll or continuous")
    parser.add_argument("--poll-interval", type=int, default=5,
                       help="Poll interval in minutes (for continuous mode)")
    parser.add_argument("--duration", type=int, default=None,
                       help="Duration to run in hours (for continuous mode, unlimited if not specified)")
    parser.add_argument("--create-example", action="store_true",
                       help="Create example DUNS file and exit")
    
    args = parser.parse_args()
    
    # Create example file if requested
    if args.create_example:
        DUNSFileReader.create_example_file(args.duns_file)
        print(f"📝 Created example DUNS file: {args.duns_file}")
        print("   Edit this file with your DUNS numbers and run the monitoring script.")
        return 0
    
    print("🔍 Starting File-based Automated DUNS Notification Monitoring")
    print(f"📋 Configuration: {args.config}")
    print(f"🔑 Environment: {args.env}")
    print(f"📄 DUNS File: {args.duns_file}")
    print(f"📝 Registration: {args.registration_name}")
    print(f"⚙️  Mode: {args.mode}")
    if args.mode == "continuous":
        print(f"⏱️  Poll Interval: {args.poll_interval} minutes")
        print(f"⏳ Duration: {args.duration or 'unlimited'} hours")
    print("=" * 60)
    
    # Initialize monitoring
    monitor = FileBasedAutomatedMonitoring(args.config, args.env, args.duns_file)
    
    try:
        # Setup
        print("\n🔧 Setting up monitoring service...")
        if not await monitor.setup():
            print("❌ Setup failed. Check your configuration, credentials, and DUNS file.")
            return 1
        
        print(f"✅ Setup completed successfully")
        print(f"📊 DUNS loaded from file: {len(monitor.duns_list)}")
        
        if args.mode == "single":
            # Single poll
            print(f"\n🔍 Performing single poll for '{args.registration_name}'...")
            notification_count = await monitor.single_poll(args.registration_name)
            
            print(f"\n📊 Results:")
            print(f"   DUNS monitored: {len(monitor.duns_list)}")
            print(f"   Notifications received: {notification_count}")
            print(f"   Results saved to: monitoring_stats_file.json")
            
        else:
            # Continuous monitoring
            print(f"\n🔄 Starting continuous monitoring for '{args.registration_name}'...")
            print("   Press Ctrl+C to stop monitoring gracefully")
            print(f"   DUNS file will be re-read every poll cycle")
            
            await monitor.monitor_continuously(
                args.registration_name, 
                args.poll_interval, 
                args.duration
            )
        
        print("\n🎉 Monitoring completed successfully!")
        print("\n📋 Check Results:")
        print("   • monitoring_stats_file.json - Monitoring statistics with DUNS list")
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
