#!/usr/bin/env python3
"""
Test HubSpot Notifications for TraceOne Monitoring System
Tests HubSpot API integration and notification processing functionality
"""

import sys
import os
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

# Add the source directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
from traceone_monitoring.utils.config import ConfigManager
from traceone_monitoring.services.hubspot_notification_handler import HubSpotConfig, create_hubspot_notification_handler
from traceone_monitoring.models.notification import Notification, NotificationType, NotificationElement, Organization
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


def create_test_notifications():
    """Create sample notifications for testing"""
    notifications = []
    
    # Create proper notification elements
    element1 = NotificationElement(
        element="organization.primaryName",
        previous="Old Company Name",
        current="Acme Corporation Ltd",
        timestamp=datetime.utcnow()
    )
    element2 = NotificationElement(
        element="organization.telephone",
        previous="555-0123",
        current="555-0124",
        timestamp=datetime.utcnow()
    )
    
    # Regular UPDATE notification
    notifications.append(Notification(
        type=NotificationType.UPDATE,
        organization=Organization(duns="123456789"),
        delivery_timestamp=datetime.utcnow(),
        deliveryTimeStamp=datetime.utcnow(),
        elements=[element1, element2]
    ))
    
    # Critical DELETE notification
    element3 = NotificationElement(
        element="organization.status",
        previous="active",
        current="deleted",
        timestamp=datetime.utcnow()
    )
    
    notifications.append(Notification(
        type=NotificationType.DELETE,
        organization=Organization(duns="987654321"),
        delivery_timestamp=datetime.utcnow(),
        deliveryTimeStamp=datetime.utcnow(),
        elements=[element3]
    ))
    
    # SEED notification (new organization)
    element4 = NotificationElement(
        element="organization.primaryName",
        previous=None,
        current="New Business Inc",
        timestamp=datetime.utcnow()
    )
    element5 = NotificationElement(
        element="organization.website",
        previous=None,
        current="www.newbusiness.com",
        timestamp=datetime.utcnow()
    )
    
    notifications.append(Notification(
        type=NotificationType.SEED,
        organization=Organization(duns="555666777"),
        delivery_timestamp=datetime.utcnow(),
        deliveryTimeStamp=datetime.utcnow(),
        elements=[element4, element5]
    ))
    
    # TRANSFER notification (critical)
    element6 = NotificationElement(
        element="organization.ownership",
        previous="Company A",
        current="Company B",
        timestamp=datetime.utcnow()
    )
    
    notifications.append(Notification(
        type=NotificationType.TRANSFER,
        organization=Organization(duns="111222333"),
        delivery_timestamp=datetime.utcnow(),
        deliveryTimeStamp=datetime.utcnow(),
        elements=[element6]
    ))
    
    return notifications


async def test_hubspot_notifications():
    """Test HubSpot notification functionality"""
    parser = argparse.ArgumentParser(description="Test TraceOne HubSpot Notifications")
    parser.add_argument("--config", default="config/real-test.yaml", 
                       help="Configuration file path")
    parser.add_argument("--env", default="config/real-test.env",
                       help="Environment file path")
    parser.add_argument("--api-token", required=False,
                       help="HubSpot API token (overrides environment)")
    parser.add_argument("--test-connection", action="store_true",
                       help="Test HubSpot API connection only")
    parser.add_argument("--test-notifications", action="store_true",
                       help="Test with sample notifications")
    parser.add_argument("--enable-hubspot", action="store_true",
                       help="Override config to enable HubSpot for testing")
    parser.add_argument("--duns-property", default="duns_number",
                       help="HubSpot property name for DUNS numbers")
    parser.add_argument("--task-owner", required=False,
                       help="Email of task owner in HubSpot")
    parser.add_argument("--dry-run", action="store_true",
                       help="Don't actually create/update HubSpot objects")
    
    args = parser.parse_args()
    
    print("🎯 TraceOne HubSpot Notification Test")
    print("=" * 50)
    
    # Load environment variables
    if args.env and Path(args.env).exists():
        print(f"📋 Loading environment: {args.env}")
        load_dotenv(args.env)
    else:
        print("⚠️  Environment file not found, using system environment")
        load_dotenv()
    
    try:
        # Get HubSpot API token
        api_token = args.api_token or os.getenv("HUBSPOT_API_TOKEN")
        
        if not api_token:
            print("❌ HubSpot API token not provided")
            print("   Set HUBSPOT_API_TOKEN in your environment file")
            print("   Or use --api-token flag")
            print("\n💡 To get a HubSpot API token:")
            print("   1. Go to HubSpot Settings > Integrations > Private Apps")
            print("   2. Create a new private app")
            print("   3. Grant scopes: crm.objects.companies.read, crm.objects.companies.write,")
            print("      crm.objects.tasks.write, crm.objects.notes.write")
            print("   4. Copy the access token")
            return 1
        
        # Create HubSpot configuration
        hubspot_config = HubSpotConfig(
            enabled=args.enable_hubspot,
            api_token=api_token,
            duns_property_name=args.duns_property,
            task_owner_email=args.task_owner,
            create_missing_companies=True,
            default_company_properties={
                "source": "TraceOne D&B Monitoring",
                "lifecyclestage": "lead"
            }
        )
        
        if not hubspot_config.enabled:
            print("❌ HubSpot integration is disabled")
            print("   Use --enable-hubspot flag for testing")
            return 1
        
        print(f"🎯 HubSpot configuration:")
        print(f"   API URL: {hubspot_config.base_url}")
        print(f"   DUNS Property: {hubspot_config.duns_property_name}")
        print(f"   Task Owner: {hubspot_config.task_owner_email or 'Not set'}")
        print(f"   Create Missing Companies: {hubspot_config.create_missing_companies}")
        
        # Create HubSpot notification handler
        hubspot_handler = create_hubspot_notification_handler(hubspot_config)
        
        # Test HubSpot API connection
        if args.test_connection or not args.test_notifications:
            print("\n🔌 Testing HubSpot API connection...")
            connection_ok = hubspot_handler.test_connection()
            
            if connection_ok:
                print("✅ HubSpot API connection test successful")
            else:
                print("❌ HubSpot API connection test failed")
                print("   Check your API token and network connection")
                return 1
        
        # Test with notifications
        if args.test_notifications:
            print("\n📮 Testing with sample notifications...")
            test_notifications = create_test_notifications()
            
            print(f"   Created {len(test_notifications)} test notifications:")
            for i, notification in enumerate(test_notifications, 1):
                critical_marker = "🔴" if notification.type in hubspot_handler.critical_types else "🟢"
                print(f"   {i}. DUNS {notification.duns} - {notification.type.value} {critical_marker}")
            
            if args.dry_run:
                print("\n🧪 DRY RUN MODE - No actual HubSpot objects will be created")
                # In dry run, just process without making API calls
                for notification in test_notifications:
                    print(f"\n   Would process: {notification.type.value} for DUNS {notification.duns}")
                    actions = hubspot_config.notification_actions.get(notification.type.value, [])
                    for action in actions:
                        print(f"     - {action}")
            else:
                print("\n🚀 Processing notifications in HubSpot...")
                
                # Process notifications
                hubspot_handler.handle_notifications(test_notifications)
                
                print("✅ Sample notifications processed")
            
            # Display statistics
            stats = hubspot_handler.get_status()
            print(f"\n📊 HubSpot Handler Statistics:")
            print(f"   Companies updated: {stats['statistics']['companies_updated']}")
            print(f"   Tasks created: {stats['statistics']['tasks_created']}")
            print(f"   Notes created: {stats['statistics']['notes_created']}")
            print(f"   Notifications processed: {stats['statistics']['notifications_processed']}")
            print(f"   API calls made: {stats['statistics']['api_calls_made']}")
            print(f"   Errors: {stats['statistics']['errors']}")
        
        print("\n🎉 HubSpot notification test completed successfully!")
        print("\n💡 Next Steps:")
        print("   1. Check your HubSpot CRM for new/updated companies")
        print("   2. Look for tasks and notes created for critical alerts") 
        print("   3. Configure custom DUNS property mapping if needed")
        print("   4. Set up task owner for automatic assignment")
        print("   5. Customize notification actions for different alert types")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ HubSpot notification test failed: {e}")
        logger.error("HubSpot test failed", error=str(e))
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(test_hubspot_notifications()))
