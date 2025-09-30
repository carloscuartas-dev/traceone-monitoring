"""
Email Notification Handler for TraceOne Monitoring Service
Sends email notifications when D&B notifications are received
"""

import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any, Set
from pathlib import Path
import structlog
from jinja2 import Template, Environment, FileSystemLoader

from ..models.notification import Notification, NotificationType

logger = structlog.get_logger(__name__)


class EmailConfig:
    """Email notification configuration"""
    
    def __init__(
        self,
        enabled: bool = False,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
        username: str = "",
        password: str = "",
        from_email: str = "",
        from_name: str = "TraceOne Monitoring",
        to_emails: List[str] = None,
        cc_emails: List[str] = None,
        bcc_emails: List[str] = None,
        use_tls: bool = True,
        use_ssl: bool = False,
        timeout: int = 30,
        template_dir: Optional[str] = None,
        send_individual_notifications: bool = False,
        send_summary_notifications: bool = True,
        summary_frequency: str = "immediate",  # immediate, hourly, daily
        critical_notifications_only: bool = False,
        max_notifications_per_email: int = 100,
        subject_prefix: str = "[TraceOne Alert]",
    ):
        self.enabled = enabled
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email or username
        self.from_name = from_name
        self.to_emails = to_emails or []
        self.cc_emails = cc_emails or []
        self.bcc_emails = bcc_emails or []
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.timeout = timeout
        self.template_dir = template_dir
        self.send_individual_notifications = send_individual_notifications
        self.send_summary_notifications = send_summary_notifications
        self.summary_frequency = summary_frequency
        self.critical_notifications_only = critical_notifications_only
        self.max_notifications_per_email = max_notifications_per_email
        self.subject_prefix = subject_prefix


class EmailNotificationHandler:
    """
    Notification handler that sends email alerts for D&B notifications
    """
    
    def __init__(self, config: EmailConfig):
        """
        Initialize email notification handler
        
        Args:
            config: Email configuration
        """
        self.config = config
        self.enabled = config.enabled
        self.critical_types = {
            NotificationType.DELETE,
            NotificationType.TRANSFER,
            NotificationType.UNDER_REVIEW
        }
        
        # Setup Jinja2 environment for templates
        if config.template_dir and Path(config.template_dir).exists():
            self.jinja_env = Environment(loader=FileSystemLoader(config.template_dir))
        else:
            self.jinja_env = None
        
        # Statistics
        self.stats = {
            "emails_sent": 0,
            "notifications_processed": 0,
            "errors": 0,
            "last_email_time": None,
            "critical_notifications_sent": 0
        }
        
        if self.enabled:
            logger.info("Email notification handler initialized",
                       smtp_server=config.smtp_server,
                       from_email=config.from_email,
                       to_emails=len(config.to_emails))
        else:
            logger.info("Email notification handler disabled")
    
    def handle_notifications(self, notifications: List[Notification]):
        """
        Handle notifications by sending email alerts
        
        Args:
            notifications: List of notifications to handle
        """
        if not self.enabled or not notifications:
            return
        
        try:
            # Filter notifications based on configuration
            filtered_notifications = self._filter_notifications(notifications)
            
            if not filtered_notifications:
                logger.debug("No notifications match email criteria")
                return
            
            self.stats["notifications_processed"] += len(filtered_notifications)
            
            # Send notifications based on configuration
            if self.config.send_individual_notifications:
                self._send_individual_notifications(filtered_notifications)
            
            if self.config.send_summary_notifications:
                self._send_summary_notification(filtered_notifications)
                
        except Exception as e:
            logger.error("Email notification handling failed",
                        error=str(e),
                        notification_count=len(notifications))
            self.stats["errors"] += 1
            # Don't re-raise to avoid breaking other handlers
    
    def _filter_notifications(self, notifications: List[Notification]) -> List[Notification]:
        """Filter notifications based on configuration rules"""
        if self.config.critical_notifications_only:
            return [n for n in notifications if n.type in self.critical_types]
        return notifications
    
    def _send_individual_notifications(self, notifications: List[Notification]):
        """Send individual email for each notification"""
        for notification in notifications:
            try:
                self._send_notification_email([notification], individual=True)
            except Exception as e:
                logger.error("Failed to send individual notification email",
                           duns=notification.duns,
                           type=notification.type.value,
                           error=str(e))
    
    def _send_summary_notification(self, notifications: List[Notification]):
        """Send summary email with all notifications"""
        try:
            # Group notifications by type and priority
            critical_notifications = [n for n in notifications if n.type in self.critical_types]
            regular_notifications = [n for n in notifications if n.type not in self.critical_types]
            
            # Send critical notifications immediately if any
            if critical_notifications:
                self._send_notification_email(critical_notifications, critical=True)
                self.stats["critical_notifications_sent"] += len(critical_notifications)
            
            # Send regular notifications summary
            if regular_notifications and not self.config.critical_notifications_only:
                self._send_notification_email(regular_notifications, critical=False)
                
        except Exception as e:
            logger.error("Failed to send summary notification email",
                        notification_count=len(notifications),
                        error=str(e))
    
    def _send_notification_email(
        self, 
        notifications: List[Notification], 
        individual: bool = False,
        critical: bool = False
    ):
        """Send email notification"""
        
        # Create email message
        msg = MIMEMultipart('alternative')
        
        # Set email headers
        subject = self._generate_subject(notifications, individual, critical)
        msg['Subject'] = subject
        msg['From'] = f"{self.config.from_name} <{self.config.from_email}>"
        msg['To'] = ", ".join(self.config.to_emails)
        
        if self.config.cc_emails:
            msg['Cc'] = ", ".join(self.config.cc_emails)
        
        # Generate email content
        text_content = self._generate_text_content(notifications, individual, critical)
        html_content = self._generate_html_content(notifications, individual, critical)
        
        # Attach text and HTML versions
        text_part = MIMEText(text_content, 'plain', 'utf-8')
        html_part = MIMEText(html_content, 'html', 'utf-8')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Send email
        self._send_email(msg)
        
        logger.info("Notification email sent",
                   subject=subject,
                   notification_count=len(notifications),
                   critical=critical,
                   recipients=len(self.config.to_emails))
    
    def _generate_subject(
        self, 
        notifications: List[Notification], 
        individual: bool, 
        critical: bool
    ) -> str:
        """Generate email subject line"""
        prefix = self.config.subject_prefix
        
        if individual:
            notification = notifications[0]
            return f"{prefix} {notification.type.value} Alert - DUNS {notification.duns}"
        
        count = len(notifications)
        if critical:
            critical_types = {n.type.value for n in notifications}
            types_str = ", ".join(sorted(critical_types))
            return f"{prefix} CRITICAL - {count} {types_str} Alert{'s' if count > 1 else ''}"
        else:
            return f"{prefix} {count} D&B Notification{'s' if count > 1 else ''} Received"
    
    def _generate_text_content(
        self, 
        notifications: List[Notification], 
        individual: bool, 
        critical: bool
    ) -> str:
        """Generate plain text email content"""
        
        lines = []
        lines.append("TraceOne D&B Monitoring Alert")
        lines.append("=" * 40)
        lines.append(f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        lines.append(f"Notifications: {len(notifications)}")
        
        if critical:
            lines.append("⚠️  CRITICAL NOTIFICATIONS DETECTED")
        
        lines.append("")
        
        # Group notifications by type
        by_type = {}
        for notification in notifications:
            type_key = notification.type.value
            if type_key not in by_type:
                by_type[type_key] = []
            by_type[type_key].append(notification)
        
        # Add summary by type
        lines.append("Summary by Type:")
        for notification_type, type_notifications in by_type.items():
            lines.append(f"  • {notification_type}: {len(type_notifications)} notification(s)")
        
        lines.append("")
        
        # Add detailed notifications (limited)
        lines.append("Notification Details:")
        for i, notification in enumerate(notifications[:20], 1):  # Limit to first 20
            lines.append(f"{i}. DUNS: {notification.duns}")
            lines.append(f"   Type: {notification.type.value}")
            lines.append(f"   Time: {notification.delivery_timestamp}")
            if hasattr(notification, 'organization') and notification.organization:
                if hasattr(notification.organization, 'primaryName'):
                    lines.append(f"   Company: {notification.organization.primaryName}")
            lines.append(f"   Elements Changed: {len(notification.elements)}")
            lines.append("")
        
        if len(notifications) > 20:
            lines.append(f"... and {len(notifications) - 20} more notifications")
            lines.append("")
        
        lines.append("This is an automated message from TraceOne Monitoring System.")
        lines.append("Please do not reply to this email.")
        
        return "\n".join(lines)
    
    def _generate_html_content(
        self, 
        notifications: List[Notification], 
        individual: bool, 
        critical: bool
    ) -> str:
        """Generate HTML email content"""
        
        # Try to use custom template if available
        if self.jinja_env:
            try:
                template_name = "critical_notification.html" if critical else "notification_summary.html"
                template = self.jinja_env.get_template(template_name)
                return template.render(
                    notifications=notifications,
                    individual=individual,
                    critical=critical,
                    timestamp=datetime.utcnow(),
                    stats=self.stats
                )
            except Exception as e:
                logger.warning("Failed to use custom email template, using default",
                              template_name=template_name,
                              error=str(e))
        
        # Use built-in HTML template
        return self._generate_default_html_content(notifications, individual, critical)
    
    def _generate_default_html_content(
        self, 
        notifications: List[Notification], 
        individual: bool, 
        critical: bool
    ) -> str:
        """Generate default HTML email content"""
        
        # Group notifications by type for summary
        by_type = {}
        for notification in notifications:
            type_key = notification.type.value
            if type_key not in by_type:
                by_type[type_key] = []
            by_type[type_key].append(notification)
        
        # Critical notification styling
        alert_style = """
        background-color: #fff3cd; 
        border: 1px solid #ffeaa7; 
        border-left: 4px solid #f39c12;
        padding: 15px; 
        margin: 10px 0;
        """ if not critical else """
        background-color: #f8d7da; 
        border: 1px solid #f5c6cb; 
        border-left: 4px solid #dc3545;
        padding: 15px; 
        margin: 10px 0;
        """
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
                .alert {{ {alert_style} }}
                .summary {{ background-color: #f8f9fa; padding: 15px; margin: 10px 0; }}
                .notification {{ border: 1px solid #dee2e6; margin: 10px 0; padding: 15px; }}
                .critical {{ border-left: 4px solid #dc3545; }}
                .regular {{ border-left: 4px solid #28a745; }}
                .meta {{ color: #666; font-size: 0.9em; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔔 TraceOne D&B Monitoring Alert</h1>
                <p>Real-time notification from your DUNS monitoring system</p>
            </div>
            
            <div class="alert">
                <h2>{'⚠️ CRITICAL ALERT' if critical else '📋 Notification Summary'}</h2>
                <p><strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                <p><strong>Notifications:</strong> {len(notifications)}</p>
                {'<p><strong>⚠️ Critical notifications detected - immediate attention required!</strong></p>' if critical else ''}
            </div>
            
            <div class="summary">
                <h3>📊 Summary by Type</h3>
                <table>
                    <tr><th>Notification Type</th><th>Count</th><th>Status</th></tr>
        """
        
        for notification_type, type_notifications in by_type.items():
            is_critical = any(n.type in self.critical_types for n in type_notifications)
            status = "🔴 Critical" if is_critical else "🟢 Regular"
            html += f"""
                    <tr>
                        <td><strong>{notification_type}</strong></td>
                        <td>{len(type_notifications)}</td>
                        <td>{status}</td>
                    </tr>
            """
        
        html += """
                </table>
            </div>
            
            <div>
                <h3>📋 Notification Details</h3>
        """
        
        # Show detailed notifications (limited to first 20)
        for i, notification in enumerate(notifications[:20], 1):
            is_critical_type = notification.type in self.critical_types
            css_class = "critical" if is_critical_type else "regular"
            
            company_name = "Unknown Company"
            if hasattr(notification, 'organization') and notification.organization:
                # Organization is a Pydantic model, not a dict
                company_name = getattr(notification.organization, 'primaryName', company_name)
            
            html += f"""
                <div class="notification {css_class}">
                    <h4>{i}. DUNS {notification.duns} - {company_name}</h4>
                    <div class="meta">
                        <p><strong>Type:</strong> {notification.type.value} {'🔴' if is_critical_type else '🟢'}</p>
                        <p><strong>Time:</strong> {notification.delivery_timestamp}</p>
                        <p><strong>Elements Changed:</strong> {len(notification.elements)}</p>
                    </div>
                </div>
            """
        
        if len(notifications) > 20:
            html += f"""
                <div class="alert">
                    <p><strong>... and {len(notifications) - 20} more notifications</strong></p>
                    <p>Check your monitoring system for complete details.</p>
                </div>
            """
        
        html += f"""
            </div>
            
            <div style="margin-top: 30px; padding: 20px; background-color: #f8f9fa; border-top: 1px solid #dee2e6;">
                <p><strong>📈 System Statistics:</strong></p>
                <ul>
                    <li>Total emails sent today: {self.stats['emails_sent']}</li>
                    <li>Total notifications processed: {self.stats['notifications_processed']}</li>
                    <li>Critical notifications sent: {self.stats['critical_notifications_sent']}</li>
                </ul>
                
                <hr style="margin: 20px 0;">
                <p style="color: #666; font-size: 0.9em;">
                    This is an automated message from TraceOne Monitoring System.<br>
                    Please do not reply to this email.<br>
                    Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
                </p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _send_email(self, msg: MIMEMultipart):
        """Send email via SMTP"""
        try:
            # All recipients
            recipients = (
                self.config.to_emails + 
                self.config.cc_emails + 
                self.config.bcc_emails
            )
            
            if not recipients:
                logger.warning("No email recipients configured")
                return
            
            # Create SMTP connection
            if self.config.use_ssl:
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(
                    self.config.smtp_server, 
                    self.config.smtp_port,
                    timeout=self.config.timeout,
                    context=context
                )
            else:
                server = smtplib.SMTP(
                    self.config.smtp_server, 
                    self.config.smtp_port,
                    timeout=self.config.timeout
                )
                
                if self.config.use_tls:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
            
            # Login if credentials provided
            if self.config.username and self.config.password:
                server.login(self.config.username, self.config.password)
            
            # Send email
            text = msg.as_string()
            server.sendmail(self.config.from_email, recipients, text)
            server.quit()
            
            # Update statistics
            self.stats["emails_sent"] += 1
            self.stats["last_email_time"] = datetime.utcnow().isoformat()
            
            logger.info("Email sent successfully",
                       recipients=len(recipients),
                       smtp_server=self.config.smtp_server)
            
        except Exception as e:
            logger.error("Failed to send email",
                        smtp_server=self.config.smtp_server,
                        error=str(e))
            self.stats["errors"] += 1
            raise
    
    def test_connection(self) -> bool:
        """Test SMTP connection and authentication"""
        if not self.enabled:
            logger.warning("Email handler is disabled")
            return False
        
        try:
            logger.info("Testing SMTP connection",
                       server=self.config.smtp_server,
                       port=self.config.smtp_port)
            
            # Create connection
            if self.config.use_ssl:
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(
                    self.config.smtp_server,
                    self.config.smtp_port,
                    timeout=self.config.timeout,
                    context=context
                )
            else:
                server = smtplib.SMTP(
                    self.config.smtp_server,
                    self.config.smtp_port,
                    timeout=self.config.timeout
                )
                
                if self.config.use_tls:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
            
            # Test authentication if credentials provided
            if self.config.username and self.config.password:
                server.login(self.config.username, self.config.password)
                logger.info("SMTP authentication successful")
            
            server.quit()
            logger.info("SMTP connection test successful")
            return True
            
        except Exception as e:
            logger.error("SMTP connection test failed", error=str(e))
            return False
    
    def send_test_email(self) -> bool:
        """Send a test email to verify configuration"""
        if not self.enabled:
            logger.warning("Email handler is disabled")
            return False
        
        try:
            # Create test notification
            from ..models.notification import NotificationElement, Organization
            test_element = NotificationElement(
                element="organization.primaryName",
                previous="Old Company Name",
                current="Test Company",
                timestamp=datetime.utcnow()
            )
            test_notification = Notification(
                type=NotificationType.UPDATE,
                organization=Organization(duns="123456789"),
                delivery_timestamp=datetime.utcnow(),
                deliveryTimeStamp=datetime.utcnow(),  # Add required field
                elements=[test_element]
            )
            
            # Create test email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"{self.config.subject_prefix} Test Email"
            msg['From'] = f"{self.config.from_name} <{self.config.from_email}>"
            msg['To'] = ", ".join(self.config.to_emails)
            
            text_content = """
TraceOne Email Notification Test

This is a test email to verify your email notification configuration.

If you received this message, your email notifications are working correctly!

Configuration Details:
- SMTP Server: {}
- From: {}
- Recipients: {}

This is an automated test message.
            """.format(
                self.config.smtp_server,
                self.config.from_email,
                ", ".join(self.config.to_emails)
            )
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; margin: 20px;">
                <div style="background-color: #2c3e50; color: white; padding: 20px; text-align: center;">
                    <h1>✅ TraceOne Email Test</h1>
                </div>
                
                <div style="background-color: #d4edda; border: 1px solid #c3e6cb; padding: 15px; margin: 20px 0;">
                    <h2>🎉 Email Notifications Working!</h2>
                    <p>This is a test email to verify your email notification configuration.</p>
                    <p>If you received this message, your email notifications are working correctly!</p>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 15px; margin: 10px 0;">
                    <h3>📋 Configuration Details</h3>
                    <ul>
                        <li><strong>SMTP Server:</strong> {self.config.smtp_server}:{self.config.smtp_port}</li>
                        <li><strong>From:</strong> {self.config.from_email}</li>
                        <li><strong>Recipients:</strong> {', '.join(self.config.to_emails)}</li>
                        <li><strong>TLS:</strong> {'Enabled' if self.config.use_tls else 'Disabled'}</li>
                        <li><strong>SSL:</strong> {'Enabled' if self.config.use_ssl else 'Disabled'}</li>
                    </ul>
                </div>
                
                <p style="color: #666; font-size: 0.9em; margin-top: 30px;">
                    This is an automated test message from TraceOne Monitoring System.<br>
                    Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
                </p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            self._send_email(msg)
            logger.info("Test email sent successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to send test email", error=str(e))
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get email handler status"""
        return {
            "enabled": self.enabled,
            "smtp_server": self.config.smtp_server,
            "smtp_port": self.config.smtp_port,
            "from_email": self.config.from_email,
            "recipients": len(self.config.to_emails),
            "statistics": self.stats.copy()
        }


def create_email_notification_handler(config: EmailConfig) -> EmailNotificationHandler:
    """
    Factory function to create email notification handler
    
    Args:
        config: Email configuration
        
    Returns:
        Configured email notification handler
    """
    return EmailNotificationHandler(config)


# Pre-configured handler function
def email_notification_handler_factory(config: EmailConfig):
    """
    Factory that returns a notification handler function
    
    Args:
        config: Email configuration
        
    Returns:
        Function that can be used as a notification handler
    """
    handler = create_email_notification_handler(config)
    
    def handle_notifications(notifications: List[Notification]):
        handler.handle_notifications(notifications)
    
    return handle_notifications, handler  # Return both function and handler object
