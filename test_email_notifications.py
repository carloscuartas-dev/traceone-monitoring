#!/usr/bin/env python3
"""
Test Email Notifications for TraceOne Monitoring System
Tests both SMTP connection and email notification functionality
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
from traceone_monitoring.services.email_notification_handler import EmailConfig, create_email_notification_handler
from traceone_monitoring.models.notification import Notification, NotificationType
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
    from traceone_monitoring.models.notification import NotificationElement, Organization
    notifications = []
    
    # Create proper notification elements
    element1 = NotificationElement(
        element="organization.primaryName",
        previous="Old Company Name",
        current="Acme Corporation",
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
        deliveryTimeStamp=datetime.utcnow(),  # Required field
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
        deliveryTimeStamp=datetime.utcnow(),  # Required field
        elements=[element3]
    ))
    
    # SEED notification (new organization)
    element4 = NotificationElement(
        element="organization.primaryName",
        previous=None,
        current="New Business Inc",
        timestamp=datetime.utcnow()
    )
    
    notifications.append(Notification(
        type=NotificationType.SEED,
        organization=Organization(duns="555666777"),
        delivery_timestamp=datetime.utcnow(),
        deliveryTimeStamp=datetime.utcnow(),  # Required field
        elements=[element4]
    ))
    
    return notifications


async def test_email_notifications():
    """Test email notification functionality"""
    parser = argparse.ArgumentParser(description="Test TraceOne Email Notifications")
    parser.add_argument("--config", default="config/real-test.yaml", 
                       help="Configuration file path")
    parser.add_argument("--env", default="config/real-test.env",
                       help="Environment file path")
    parser.add_argument("--test-connection", action="store_true",
                       help="Test SMTP connection only")
    parser.add_argument("--test-email", action="store_true", 
                       help="Send test email")
    parser.add_argument("--test-notifications", action="store_true",
                       help="Test with sample notifications")
    parser.add_argument("--enable-emails", action="store_true",
                       help="Override config to enable emails for testing")
    
    args = parser.parse_args()
    
    print("🔔 TraceOne Email Notification Test")
    print("=" * 50)
    
    # Load environment variables
    if args.env and Path(args.env).exists():
        print(f"📋 Loading environment: {args.env}")
        load_dotenv(args.env)
    else:
        print("⚠️  Environment file not found, using system environment")
        load_dotenv()
    
    try:
        # Load configuration
        print(f"📋 Loading configuration: {args.config}")
        config_manager = ConfigManager.from_file(args.config)
        app_config = config_manager.load_config()
        
        # Check if email notifications are configured
        email_config = app_config.email_notifications
        
        # Override to enable for testing if requested
        if args.enable_emails:
            email_config.enabled = True
            print("🔧 Email notifications enabled for testing")
        
        if not email_config.enabled:
            print("❌ Email notifications are disabled in configuration")
            print("   Set 'enabled: true' in the email_notifications section")
            print("   Or use --enable-emails flag for testing")
            return 1
        
        if not email_config.to_emails or not email_config.to_emails[0]:
            print("❌ No recipient email addresses configured")
            print("   Set EMAIL_TO_EMAILS in your environment file")
            return 1
        
        print(f"📧 Email configuration:")
        print(f"   SMTP Server: {email_config.smtp_server}:{email_config.smtp_port}")
        print(f"   From: {email_config.from_email}")
        print(f"   To: {', '.join(email_config.to_emails)}")
        print(f"   TLS: {email_config.use_tls}, SSL: {email_config.use_ssl}")
        
        # Create email notification handler
        handler_config = EmailConfig(
            enabled=email_config.enabled,
            smtp_server=email_config.smtp_server,
            smtp_port=email_config.smtp_port,
            username=email_config.username,
            password=email_config.password,
            from_email=email_config.from_email,
            from_name=email_config.from_name,
            to_emails=email_config.to_emails,
            cc_emails=email_config.cc_emails,
            bcc_emails=email_config.bcc_emails,
            use_tls=email_config.use_tls,
            use_ssl=email_config.use_ssl,
            timeout=email_config.timeout,
            template_dir=email_config.template_dir,
            send_individual_notifications=email_config.send_individual_notifications,
            send_summary_notifications=email_config.send_summary_notifications,
            summary_frequency=email_config.summary_frequency,
            critical_notifications_only=email_config.critical_notifications_only,
            max_notifications_per_email=email_config.max_notifications_per_email,
            subject_prefix=email_config.subject_prefix
        )
        
        email_handler = create_email_notification_handler(handler_config)
        
        # Test SMTP connection
        if args.test_connection or not any([args.test_email, args.test_notifications]):
            print("\\n🔌 Testing SMTP connection...")
            connection_ok = email_handler.test_connection()
            
            if connection_ok:
                print("✅ SMTP connection test successful")
            else:
                print("❌ SMTP connection test failed")
                print("   Check your SMTP settings and credentials")
                return 1
        
        # Send test email
        if args.test_email:
            print("\\n📧 Sending test email...")
            test_sent = email_handler.send_test_email()
            
            if test_sent:
                print("✅ Test email sent successfully")
                print(f"   Check your inbox: {', '.join(email_config.to_emails)}")
            else:
                print("❌ Test email failed to send")
                return 1
        
        # Test with notifications
        if args.test_notifications:
            print("\\n📮 Testing with sample notifications...")
            test_notifications = create_test_notifications()
            
            print(f"   Created {len(test_notifications)} test notifications:")
            for i, notification in enumerate(test_notifications, 1):
                print(f"   {i}. DUNS {notification.duns} - {notification.type.value}")
            
            # Send notifications
            email_handler.handle_notifications(test_notifications)
            
            print("✅ Sample notifications processed")
            print(f"   Check your inbox for notification emails")
            
            # Display statistics
            stats = email_handler.get_status()
            print(f"\\n📊 Email Handler Statistics:")
            print(f"   Emails sent: {stats['statistics']['emails_sent']}")
            print(f"   Notifications processed: {stats['statistics']['notifications_processed']}")
            print(f"   Critical notifications: {stats['statistics']['critical_notifications_sent']}")
            print(f"   Errors: {stats['statistics']['errors']}")
        
        print("\\n🎉 Email notification test completed successfully!")
        print("\\n💡 Next Steps:")
        print("   1. Check your email inbox for test messages")
        print("   2. Set 'enabled: true' in your config to activate in production")
        print("   3. Adjust notification settings as needed")
        print("   4. Run your regular monitoring with email alerts enabled")
        
        return 0
        
    except Exception as e:
        print(f"\\n❌ Email notification test failed: {e}")
        logger.error("Email test failed", error=str(e))
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(test_email_notifications()))
