#!/usr/bin/env python3
"""
Real-world DUNS testing script with actual D&B API integration.

This script demonstrates how to:
1. Set up real D&B API authentication
2. Create registrations with your actual DUNS numbers
3. Pull real notifications from D&B
4. Store results in database and files

Usage:
    python3 real_duns_test.py --config config/real-test.yaml --env config/real-test.env
"""

import sys
import os
import asyncio
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add the source directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
from traceone_monitoring.utils.config import ConfigManager
from traceone_monitoring.services.monitoring_service import DNBMonitoringService
from traceone_monitoring.models.registration import RegistrationConfig
from traceone_monitoring.auth.authenticator import DNBAuthenticator
from traceone_monitoring.api.client import DNBApiClient
from traceone_monitoring.api.pull_client import PullApiClient
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


class RealWorldDUNSTest:
    """Real-world DUNS testing with actual D&B API"""
    
    def __init__(self, config_file: str, env_file: str = None):
        """Initialize with configuration files"""
        if env_file:
            load_dotenv(env_file)
        
        self.config_manager = ConfigManager.from_file(config_file)
        self.app_config = self.config_manager.load_config()
        self.monitoring_service = None
        
        # Results tracking
        self.test_results = {
            "start_time": datetime.utcnow().isoformat(),
            "tests_run": [],
            "errors": [],
            "registrations_created": [],
            "notifications_received": [],
            "files_stored": []
        }
        
        logger.info("Real-world DUNS test initialized", 
                   config=config_file, 
                   env=env_file,
                   storage_enabled=self.app_config.local_storage.enabled)
    
    async def setup(self):
        """Set up monitoring service and test infrastructure"""
        logger.info("Setting up monitoring service...")
        
        try:
            # Initialize monitoring service directly with config
            self.monitoring_service = DNBMonitoringService(self.app_config)
            
            # Test API authentication
            auth_test = await self.test_authentication()
            self.test_results["tests_run"].append({
                "name": "authentication_test",
                "success": auth_test,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            if not auth_test:
                raise Exception("Authentication test failed")
            
            logger.info("Monitoring service setup completed")
            return True
            
        except Exception as e:
            logger.error("Setup failed", error=str(e))
            self.test_results["errors"].append({
                "stage": "setup",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            return False
    
    async def test_authentication(self) -> bool:
        """Test D&B API authentication"""
        logger.info("Testing D&B API authentication...")
        
        try:
            # Create authenticator directly to test
            authenticator = DNBAuthenticator(self.app_config.dnb_api)
            
            # Try to get a token
            token = await asyncio.get_event_loop().run_in_executor(
                None, authenticator.get_token
            )
            
            if token:
                logger.info("Authentication successful", token_length=len(token))
                return True
            else:
                logger.error("Authentication failed - no token received")
                return False
                
        except Exception as e:
            logger.error("Authentication test failed", error=str(e))
            return False
    
    async def create_test_registration(self, duns_list: List[str], registration_name: str) -> bool:
        """Create a test registration with real DUNS numbers"""
        logger.info("Creating test registration", 
                   name=registration_name, 
                   duns_count=len(duns_list))
        
        try:
            # Create registration configuration
            config = RegistrationConfig(
                reference=registration_name,
                description=f"Real-world test registration created {datetime.utcnow().isoformat()}",
                duns_list=duns_list,
                dataBlocks=[
                    "companyinfo_L2_v1",      # Basic company information
                    "principalscontacts_L1_v1", # Key contacts
                    "financialstrength_L1_v1"   # Financial indicators
                ],
                jsonPathInclusion=[
                    "organization.primaryName",
                    "organization.registeredAddress", 
                    "organization.telephone",
                    "organization.numberOfEmployees",
                    "organization.annualSalesRevenue",
                    "organization.operatingStatus"
                ]
            )
            
            # Create registration via monitoring service
            loop = asyncio.get_event_loop()
            registration = await loop.run_in_executor(
                None, 
                self.monitoring_service.create_registration,
                config
            )
            
            if registration:
                logger.info("Registration created successfully", 
                           registration_id=str(registration.id),
                           reference=registration.reference)
                
                self.test_results["registrations_created"].append({
                    "id": str(registration.id),
                    "reference": registration.reference,
                    "duns_count": len(duns_list),
                    "created_at": datetime.utcnow().isoformat(),
                    "duns_list": duns_list
                })
                
                return True
            else:
                logger.error("Registration creation failed")
                return False
                
        except Exception as e:
            logger.error("Registration creation failed", 
                        error=str(e),
                        registration_name=registration_name)
            self.test_results["errors"].append({
                "stage": "registration_creation",
                "registration_name": registration_name,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            return False
    
    async def test_pull_notifications(self, registration_reference: str) -> bool:
        """Test pulling notifications for a registration"""
        logger.info("Testing notification pull", registration=registration_reference)
        
        try:
            # Pull notifications
            notifications = await self.monitoring_service.pull_notifications(
                registration_reference, 
                max_notifications=50
            )
            
            logger.info("Notifications pulled successfully", 
                       count=len(notifications),
                       registration=registration_reference)
            
            # Store notification info
            notification_data = []
            for notification in notifications:
                notification_data.append({
                    "id": str(notification.id),
                    "type": notification.type.value,
                    "duns": notification.organization.duns,
                    "delivery_timestamp": notification.deliveryTimeStamp.isoformat(),
                    "elements_count": len(notification.elements)
                })
            
            self.test_results["notifications_received"].append({
                "registration": registration_reference,
                "count": len(notifications),
                "timestamp": datetime.utcnow().isoformat(),
                "notifications": notification_data
            })
            
            return True
            
        except Exception as e:
            logger.error("Notification pull failed",
                        error=str(e),
                        registration=registration_reference)
            self.test_results["errors"].append({
                "stage": "notification_pull",
                "registration": registration_reference,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            return False
    
    async def test_continuous_monitoring(self, registration_reference: str, duration_minutes: int = 5) -> bool:
        """Test continuous monitoring for a short period"""
        logger.info("Starting continuous monitoring test", 
                   registration=registration_reference,
                   duration_minutes=duration_minutes)
        
        try:
            end_time = datetime.utcnow() + timedelta(minutes=duration_minutes)
            total_notifications = 0
            
            async for notification_batch in self.monitoring_service.monitor_continuously(
                registration_reference
            ):
                if datetime.utcnow() > end_time:
                    break
                
                total_notifications += len(notification_batch)
                logger.info("Received notification batch",
                           count=len(notification_batch),
                           total=total_notifications)
                
                # Process each notification
                for notification in notification_batch:
                    # This would typically trigger your notification handlers
                    logger.debug("Processing notification",
                                notification_id=str(notification.id),
                                duns=notification.organization.duns,
                                type=notification.type.value)
            
            logger.info("Continuous monitoring test completed",
                       duration_minutes=duration_minutes,
                       total_notifications=total_notifications)
            
            return True
            
        except Exception as e:
            logger.error("Continuous monitoring test failed",
                        error=str(e),
                        registration=registration_reference)
            self.test_results["errors"].append({
                "stage": "continuous_monitoring",
                "registration": registration_reference,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            return False
    
    def check_storage_results(self):
        """Check where results are stored"""
        logger.info("Checking storage locations...")
        
        storage_info = {
            "local_storage": {
                "enabled": self.app_config.local_storage.enabled,
                "path": self.app_config.local_storage.base_path,
                "format": self.app_config.local_storage.file_format
            },
            "sftp_storage": {
                "enabled": self.app_config.sftp_storage.enabled
            },
            "database": {
                "url": self.app_config.database.url
            }
        }
        
        # Check local storage
        if self.app_config.local_storage.enabled:
            local_path = Path(self.app_config.local_storage.base_path)
            if local_path.exists():
                files = list(local_path.rglob("*"))
                storage_info["local_storage"]["files_found"] = len([f for f in files if f.is_file()])
                storage_info["local_storage"]["directories"] = len([f for f in files if f.is_dir()])
                
                # List some example files
                example_files = []
                for file_path in local_path.rglob("*.json"):
                    example_files.append(str(file_path))
                    if len(example_files) >= 5:  # Limit to first 5
                        break
                storage_info["local_storage"]["example_files"] = example_files
        
        self.test_results["storage_info"] = storage_info
        logger.info("Storage check completed", storage=storage_info)
        
        return storage_info
    
    def save_test_results(self):
        """Save test results to file"""
        self.test_results["end_time"] = datetime.utcnow().isoformat()
        self.test_results["duration_seconds"] = (
            datetime.fromisoformat(self.test_results["end_time"].replace('Z', '')) - 
            datetime.fromisoformat(self.test_results["start_time"].replace('Z', ''))
        ).total_seconds()
        
        # Save to JSON file
        import json
        results_file = Path("./real_test_results.json")
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        logger.info("Test results saved", file=str(results_file))
        return results_file
    
    async def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up...")
        
        if self.monitoring_service:
            try:
                await self.monitoring_service.shutdown()
            except Exception as e:
                logger.warning("Error during cleanup", error=str(e))
        
        logger.info("Cleanup completed")


async def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description="Real-world DUNS testing")
    parser.add_argument("--config", default="config/real-test.yaml", 
                       help="Configuration file path")
    parser.add_argument("--env", default="config/real-test.env",
                       help="Environment file path")
    parser.add_argument("--duns", nargs="+", 
                       help="DUNS numbers to test (space-separated)")
    parser.add_argument("--registration-name", default="RealWorldTest",
                       help="Registration name")
    parser.add_argument("--continuous-minutes", type=int, default=0,
                       help="Minutes to run continuous monitoring (0 to skip)")
    
    args = parser.parse_args()
    
    # Default DUNS if none provided (replace with your actual DUNS)
    test_duns = args.duns or [
        "804735132",  # Example - replace with your actual DUNS
        "069032677",  # Example - replace with your actual DUNS
        "006273905"   # Example - replace with your actual DUNS
    ]
    
    print("🚀 Starting Real-World DUNS Testing")
    print(f"📋 Configuration: {args.config}")
    print(f"🔑 Environment: {args.env}")
    print(f"📊 DUNS to test: {test_duns}")
    print(f"📝 Registration: {args.registration_name}")
    print("=" * 60)
    
    # Initialize test
    test = RealWorldDUNSTest(args.config, args.env)
    
    try:
        # Setup
        print("\n1️⃣ Setting up monitoring service...")
        if not await test.setup():
            print("❌ Setup failed. Check your configuration and credentials.")
            return 1
        
        print("✅ Setup completed successfully")
        
        # Create registration
        print(f"\n2️⃣ Creating registration '{args.registration_name}'...")
        if not await test.create_test_registration(test_duns, args.registration_name):
            print("❌ Registration creation failed")
            return 1
        
        print("✅ Registration created successfully")
        
        # Pull notifications
        print(f"\n3️⃣ Pulling notifications for '{args.registration_name}'...")
        await test.test_pull_notifications(args.registration_name)
        
        # Continuous monitoring (optional)
        if args.continuous_minutes > 0:
            print(f"\n4️⃣ Running continuous monitoring for {args.continuous_minutes} minutes...")
            await test.test_continuous_monitoring(args.registration_name, args.continuous_minutes)
        
        # Check storage
        print("\n5️⃣ Checking storage locations...")
        storage_info = test.check_storage_results()
        
        print("\n📁 Storage Information:")
        if storage_info["local_storage"]["enabled"]:
            print(f"   Local Storage: {storage_info['local_storage']['path']}")
            print(f"   Format: {storage_info['local_storage']['format']}")
            if "files_found" in storage_info["local_storage"]:
                print(f"   Files: {storage_info['local_storage']['files_found']}")
        
        if storage_info["database"]["url"]:
            print(f"   Database: {storage_info['database']['url']}")
        
        # Save results
        print("\n6️⃣ Saving test results...")
        results_file = test.save_test_results()
        print(f"✅ Results saved to: {results_file}")
        
        print("\n🎉 Real-world testing completed successfully!")
        print("\n📋 Next Steps:")
        print("   1. Check the local storage directory for notification files")
        print("   2. Review the database for stored registration data")  
        print("   3. Check the log files for detailed execution logs")
        print("   4. Review real_test_results.json for comprehensive results")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        logger.error("Test failed", error=str(e))
        return 1
        
    finally:
        await test.cleanup()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
