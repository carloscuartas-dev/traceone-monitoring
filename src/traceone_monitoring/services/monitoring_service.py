"""
Main TraceOne Monitoring Service
Orchestrates all monitoring components and provides high-level API
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import AsyncGenerator, List, Optional, Dict, Any, Callable
import structlog

from ..utils.config import AppConfig, ConfigManager
from ..auth.authenticator import DNBAuthenticator, create_authenticator
from ..api.client import DNBApiClient, create_api_client
from ..api.pull_client import PullApiClient, create_pull_client
from ..services.registration_service import RegistrationManager, create_registration_manager
from ..models.registration import Registration, RegistrationConfig
from ..models.notification import Notification, NotificationBatch
from .sftp_notification_handler import create_sftp_notification_handler, SFTPNotificationHandler
from .email_notification_handler import EmailConfig, create_email_notification_handler, EmailNotificationHandler


logger = structlog.get_logger(__name__)


class MonitoringServiceError(Exception):
    """Monitoring service errors"""
    pass


class DNBMonitoringService:
    """
    Main D&B monitoring service that provides high-level API for monitoring operations
    """
    
    def __init__(
        self,
        config: AppConfig,
        authenticator: Optional[DNBAuthenticator] = None,
        api_client: Optional[DNBApiClient] = None,
        pull_client: Optional[PullApiClient] = None,
        registration_manager: Optional[RegistrationManager] = None
    ):
        """
        Initialize monitoring service
        
        Args:
            config: Application configuration
            authenticator: Optional DNB authenticator (will create if not provided)
            api_client: Optional API client (will create if not provided)
            pull_client: Optional pull client (will create if not provided)
            registration_manager: Optional registration manager (will create if not provided)
        """
        self.config = config
        
        # Initialize components
        self.authenticator = authenticator or create_authenticator(config.dnb_api)
        self.api_client = api_client or create_api_client(config.dnb_api, self.authenticator)
        self.pull_client = pull_client or create_pull_client(self.api_client)
        self.registration_manager = registration_manager or create_registration_manager(self.api_client)
        
        # State tracking
        self._running_monitors: Dict[str, asyncio.Task] = {}
        self._notification_handlers: List[Callable[[List[Notification]], None]] = []
        
        # Initialize SFTP handler if enabled
        self._sftp_handler: Optional[SFTPNotificationHandler] = None
        if config.sftp_storage.enabled:
            self._sftp_handler = create_sftp_notification_handler(config.sftp_storage)
            # Auto-register SFTP handler
            self.add_notification_handler(self._sftp_handler.handle_notifications)
            logger.info("SFTP notification handler registered automatically")
        
        # Initialize local file storage handler if enabled
        self._local_storage_handler = None
        if config.local_storage.enabled:
            from .local_file_notification_handler import LocalFileNotificationHandler
            self._local_storage_handler = LocalFileNotificationHandler(
                config.local_storage
            )
            # Auto-register local storage handler
            self.add_notification_handler(self._local_storage_handler.handle_notifications)
            logger.info("Local file storage notification handler registered automatically")
        
        # Initialize email notification handler if enabled
        self._email_handler: Optional[EmailNotificationHandler] = None
        if config.email_notifications.enabled:
            # Convert config to EmailConfig
            email_config = EmailConfig(
                enabled=config.email_notifications.enabled,
                smtp_server=config.email_notifications.smtp_server,
                smtp_port=config.email_notifications.smtp_port,
                username=config.email_notifications.username,
                password=config.email_notifications.password,
                from_email=config.email_notifications.from_email,
                from_name=config.email_notifications.from_name,
                to_emails=config.email_notifications.to_emails,
                cc_emails=config.email_notifications.cc_emails,
                bcc_emails=config.email_notifications.bcc_emails,
                use_tls=config.email_notifications.use_tls,
                use_ssl=config.email_notifications.use_ssl,
                timeout=config.email_notifications.timeout,
                template_dir=config.email_notifications.template_dir,
                send_individual_notifications=config.email_notifications.send_individual_notifications,
                send_summary_notifications=config.email_notifications.send_summary_notifications,
                summary_frequency=config.email_notifications.summary_frequency,
                critical_notifications_only=config.email_notifications.critical_notifications_only,
                max_notifications_per_email=config.email_notifications.max_notifications_per_email,
                subject_prefix=config.email_notifications.subject_prefix
            )
            self._email_handler = create_email_notification_handler(email_config)
            # Auto-register email handler
            self.add_notification_handler(self._email_handler.handle_notifications)
            logger.info("Email notification handler registered automatically")
        
        logger.info("DNB Monitoring Service initialized",
                   environment=config.environment,
                   polling_interval=config.monitoring.polling_interval)
    
    @classmethod
    def from_config(cls, config_path: Optional[str] = None) -> "DNBMonitoringService":
        """
        Create monitoring service from configuration file or environment
        
        Args:
            config_path: Optional path to configuration file
            
        Returns:
            Configured monitoring service
        """
        if config_path:
            config_manager = ConfigManager.from_file(config_path)
        else:
            config_manager = ConfigManager.from_env()
        
        config = config_manager.load_config()
        return cls(config)
    
    def create_registration(self, config: RegistrationConfig) -> Registration:
        """
        Create a new monitoring registration
        
        Args:
            config: Registration configuration
            
        Returns:
            Created registration
        """
        return self.registration_manager.create_registration_from_config(config)
    
    def create_registration_from_file(self, config_file_path: str) -> Registration:
        """
        Create registration from YAML configuration file
        
        Args:
            config_file_path: Path to YAML configuration file
            
        Returns:
            Created registration
        """
        return self.registration_manager.create_registration_from_file(config_file_path)
    
    async def add_duns_to_monitoring(
        self, 
        registration_reference: str, 
        duns_list: List[str],
        batch_mode: bool = True
    ):
        """
        Add DUNS to monitoring asynchronously
        
        Args:
            registration_reference: Registration reference
            duns_list: List of DUNS to add
            batch_mode: Whether to add in batch mode
        """
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.registration_manager.add_duns_to_monitoring,
            registration_reference,
            duns_list,
            batch_mode
        )
    
    async def remove_duns_from_monitoring(
        self,
        registration_reference: str,
        duns_list: List[str],
        batch_mode: bool = True
    ):
        """
        Remove DUNS from monitoring asynchronously
        
        Args:
            registration_reference: Registration reference
            duns_list: List of DUNS to remove
            batch_mode: Whether to remove in batch mode
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.registration_manager.remove_duns_from_monitoring,
            registration_reference,
            duns_list,
            batch_mode
        )
    
    async def activate_monitoring(self, registration_reference: str) -> bool:
        """
        Activate monitoring for a registration
        
        Args:
            registration_reference: Registration reference
            
        Returns:
            True if activation successful
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.registration_manager.activate_monitoring,
            registration_reference
        )
    
    async def pull_notifications(
        self, 
        registration_reference: str,
        max_notifications: Optional[int] = None
    ) -> List[Notification]:
        """
        Pull notifications for a registration
        
        Args:
            registration_reference: Registration reference
            max_notifications: Maximum notifications to retrieve
            
        Returns:
            List of notifications
        """
        max_notifications = max_notifications or self.config.monitoring.max_notifications
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            self.pull_client.pull_notifications,
            registration_reference,
            max_notifications
        )
        
        return response.notifications
    
    async def replay_notifications(
        self,
        registration_reference: str,
        start_timestamp: datetime,
        max_notifications: Optional[int] = None
    ) -> List[Notification]:
        """
        Replay notifications from a specific timestamp
        
        Args:
            registration_reference: Registration reference
            start_timestamp: Start timestamp for replay
            max_notifications: Maximum notifications to retrieve
            
        Returns:
            List of notifications
        """
        max_notifications = max_notifications or self.config.monitoring.max_notifications
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            self.pull_client.replay_notifications,
            registration_reference,
            start_timestamp,
            max_notifications
        )
        
        return response.notifications
    
    async def monitor_continuously(
        self,
        registration_reference: str,
        polling_interval: Optional[int] = None,
        max_notifications: Optional[int] = None
    ) -> AsyncGenerator[List[Notification], None]:
        """
        Continuously monitor a registration for notifications
        
        Args:
            registration_reference: Registration reference
            polling_interval: Polling interval in seconds
            max_notifications: Maximum notifications per pull
            
        Yields:
            Lists of notifications
        """
        registration = self.registration_manager.get_registration(registration_reference)
        if not registration:
            raise MonitoringServiceError(f"Registration not found: {registration_reference}")
        
        polling_interval = polling_interval or self.config.monitoring.polling_interval
        max_notifications = max_notifications or self.config.monitoring.max_notifications
        
        logger.info("Starting continuous monitoring",
                   registration=registration_reference,
                   polling_interval=polling_interval)
        
        async for notifications in self.pull_client.pull_notifications_continuously(
            registration, polling_interval, max_notifications
        ):
            yield notifications
    
    def start_background_monitoring(
        self,
        registration_reference: str,
        notification_handler: Callable[[List[Notification]], None],
        polling_interval: Optional[int] = None
    ):
        """
        Start background monitoring task
        
        Args:
            registration_reference: Registration reference
            notification_handler: Function to handle notifications
            polling_interval: Polling interval in seconds
        """
        if registration_reference in self._running_monitors:
            logger.warning("Monitoring already running for registration",
                          registration=registration_reference)
            return
        
        async def monitor_task():
            try:
                async for notifications in self.monitor_continuously(
                    registration_reference, polling_interval
                ):
                    if notifications:
                        notification_handler(notifications)
            except Exception as e:
                logger.error("Background monitoring failed",
                            registration=registration_reference,
                            error=str(e))
        
        # Start background task
        task = asyncio.create_task(monitor_task())
        self._running_monitors[registration_reference] = task
        
        logger.info("Background monitoring started",
                   registration=registration_reference)
    
    def stop_background_monitoring(self, registration_reference: str):
        """
        Stop background monitoring task
        
        Args:
            registration_reference: Registration reference
        """
        task = self._running_monitors.get(registration_reference)
        if task:
            task.cancel()
            del self._running_monitors[registration_reference]
            logger.info("Background monitoring stopped",
                       registration=registration_reference)
        else:
            logger.warning("No background monitoring found for registration",
                          registration=registration_reference)
    
    def stop_all_monitoring(self):
        """Stop all background monitoring tasks"""
        for registration_reference in list(self._running_monitors.keys()):
            self.stop_background_monitoring(registration_reference)
        
        logger.info("All background monitoring stopped")
    
    async def process_notification(self, notification: Notification) -> bool:
        """
        Process a single notification
        
        Args:
            notification: Notification to process
            
        Returns:
            True if processing successful
        """
        logger.info("Processing notification",
                   duns=notification.duns,
                   notification_type=notification.type.value,
                   notification_id=str(notification.id))
        
        try:
            # Call all registered notification handlers
            for handler in self._notification_handlers:
                handler([notification])
            
            # Mark as processed
            notification.mark_processed()
            
            logger.info("Notification processed successfully",
                       duns=notification.duns,
                       notification_id=str(notification.id))
            
            return True
            
        except Exception as e:
            logger.error("Failed to process notification",
                        duns=notification.duns,
                        notification_id=str(notification.id),
                        error=str(e))
            
            notification.mark_error(str(e))
            return False
    
    async def process_notification_batch(self, batch: NotificationBatch) -> int:
        """
        Process a batch of notifications
        
        Args:
            batch: Notification batch
            
        Returns:
            Number of successfully processed notifications
        """
        logger.info("Processing notification batch",
                   batch_id=str(batch.id),
                   size=batch.size)
        
        successful_count = 0
        
        for notification in batch.notifications:
            success = await self.process_notification(notification)
            if success:
                successful_count += 1
        
        # Mark batch as processed
        batch.mark_processed()
        
        logger.info("Notification batch processed",
                   batch_id=str(batch.id),
                   successful=successful_count,
                   failed=batch.size - successful_count)
        
        return successful_count
    
    def add_notification_handler(self, handler: Callable[[List[Notification]], None]):
        """
        Add a notification handler function
        
        Args:
            handler: Function that takes a list of notifications
        """
        self._notification_handlers.append(handler)
        logger.info("Notification handler added",
                   handler_count=len(self._notification_handlers))
    
    def remove_notification_handler(self, handler: Callable[[List[Notification]], None]):
        """
        Remove a notification handler function
        
        Args:
            handler: Handler function to remove
        """
        if handler in self._notification_handlers:
            self._notification_handlers.remove(handler)
            logger.info("Notification handler removed",
                       handler_count=len(self._notification_handlers))
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get comprehensive service status
        
        Returns:
            Service status information
        """
        registrations = self.registration_manager.list_registrations()
        
        return {
            "service": {
                "running": True,
                "environment": self.config.environment,
                "debug_mode": self.config.debug,
                "uptime_seconds": 0,  # Would track actual uptime
            },
            "authentication": {
                "is_authenticated": self.authenticator.is_authenticated,
                "token_expires_in": self.authenticator.token_expires_in,
            },
            "api_client": {
                "health_check": self.api_client.health_check(),
                "rate_limit": self.config.dnb_api.rate_limit,
            },
            "registrations": {
                "total_count": len(registrations),
                "active_count": len([r for r in registrations if r.status == "ACTIVE"]),
                "background_monitors": len(self._running_monitors),
            },
            "notification_handlers": {
                "count": len(self._notification_handlers),
            },
            "sftp_storage": (
                self._sftp_handler.get_storage_status() if self._sftp_handler 
                else {"enabled": False, "status": "disabled"}
            ),
            "local_storage": (
                self._local_storage_handler.get_storage_status() if self._local_storage_handler 
                else {"enabled": False, "status": "disabled"}
            ),
            "email_notifications": (
                self._email_handler.get_status() if self._email_handler 
                else {"enabled": False, "status": "disabled"}
            ),
            "configuration": {
                "polling_interval": self.config.monitoring.polling_interval,
                "max_notifications": self.config.monitoring.max_notifications,
                "batch_size": self.config.monitoring.notification_batch_size,
            }
        }
    
    def health_check(self) -> bool:
        """
        Perform comprehensive health check
        
        Returns:
            True if all components are healthy
        """
        try:
            # Check API client
            api_healthy = self.api_client.health_check()
            
            # Check authentication
            auth_healthy = self.authenticator.is_authenticated
            
            logger.info("Health check completed",
                       api_healthy=api_healthy,
                       auth_healthy=auth_healthy)
            
            return api_healthy and auth_healthy
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return False
    
    async def shutdown(self):
        """
        Gracefully shutdown the monitoring service
        """
        logger.info("Shutting down monitoring service")
        
        # Stop all background monitoring
        self.stop_all_monitoring()
        
        # Wait for tasks to complete
        if self._running_monitors:
            await asyncio.gather(*self._running_monitors.values(), return_exceptions=True)
        
        # Close HTTP sessions
        if hasattr(self.api_client, 'session'):
            self.api_client.session.close()
        if hasattr(self.authenticator, 'session'):
            self.authenticator.session.close()
        
        logger.info("Monitoring service shutdown complete")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.shutdown()


# Convenience functions for common use cases

def create_standard_monitoring_registration(
    reference: str,
    duns_list: List[str],
    description: Optional[str] = None
) -> RegistrationConfig:
    """
    Create a standard monitoring registration configuration
    
    Args:
        reference: Registration reference
        duns_list: List of DUNS to monitor
        description: Optional description
        
    Returns:
        Registration configuration
    """
    return RegistrationConfig(
        reference=reference,
        description=description,
        duns_list=duns_list,
        dataBlocks=[
            "companyinfo_L2_v1",
            "principalscontacts_L1_v1",
            "hierarchyconnections_L1_v1"
        ],
        jsonPathInclusion=[
            "organization.primaryName",
            "organization.registeredAddress", 
            "organization.telephone",
            "organization.websiteAddress",
            "organization.primaryIndustryCode"
        ]
    )


def create_financial_monitoring_registration(
    reference: str,
    duns_list: List[str],
    description: Optional[str] = None
) -> RegistrationConfig:
    """
    Create a financial monitoring registration configuration
    
    Args:
        reference: Registration reference
        duns_list: List of DUNS to monitor
        description: Optional description
        
    Returns:
        Registration configuration
    """
    return RegistrationConfig(
        reference=reference,
        description=description,
        duns_list=duns_list,
        dataBlocks=[
            "companyfinancials_L1_v1",
            "paymentinsights_L1_v1",
            "financialstrengthinsight_L2_v1"
        ],
        jsonPathInclusion=[
            "organization.financials",
            "organization.paymentExperiences",
            "organization.riskAssessment"
        ]
    )


# Example notification handlers

def log_notification_handler(notifications: List[Notification]):
    """
    Simple notification handler that logs notifications
    
    Args:
        notifications: List of notifications to handle
    """
    for notification in notifications:
        logger.info("Notification received",
                   duns=notification.duns,
                   type=notification.type.value,
                   elements_count=len(notification.elements))


def update_database_handler(notifications: List[Notification]):
    """
    Notification handler that updates database (placeholder)
    
    Args:
        notifications: List of notifications to handle
    """
    # This would contain actual database update logic
    for notification in notifications:
        logger.info("Updating database for notification",
                   duns=notification.duns,
                   type=notification.type.value)
        # Database update logic here


def alert_notification_handler(notifications: List[Notification]):
    """
    Notification handler that sends alerts for critical changes
    
    Args:
        notifications: List of notifications to handle
    """
    critical_types = {"DELETE", "TRANSFER", "UNDER_REVIEW"}
    
    for notification in notifications:
        if notification.type.value in critical_types:
            logger.warning("Critical notification received",
                          duns=notification.duns,
                          type=notification.type.value)
            # Send alert logic here
