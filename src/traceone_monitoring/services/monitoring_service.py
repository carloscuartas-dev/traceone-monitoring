"""
Main DNB Monitoring Service
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
        ):\n            yield notifications\n    \n    def start_background_monitoring(\n        self,\n        registration_reference: str,\n        notification_handler: Callable[[List[Notification]], None],\n        polling_interval: Optional[int] = None\n    ):\n        \"\"\"\n        Start background monitoring task\n        \n        Args:\n            registration_reference: Registration reference\n            notification_handler: Function to handle notifications\n            polling_interval: Polling interval in seconds\n        \"\"\"\n        if registration_reference in self._running_monitors:\n            logger.warning(\"Monitoring already running for registration\",\n                          registration=registration_reference)\n            return\n        \n        async def monitor_task():\n            try:\n                async for notifications in self.monitor_continuously(\n                    registration_reference, polling_interval\n                ):\n                    if notifications:\n                        notification_handler(notifications)\n            except Exception as e:\n                logger.error(\"Background monitoring failed\",\n                            registration=registration_reference,\n                            error=str(e))\n        \n        # Start background task\n        task = asyncio.create_task(monitor_task())\n        self._running_monitors[registration_reference] = task\n        \n        logger.info(\"Background monitoring started\",\n                   registration=registration_reference)\n    \n    def stop_background_monitoring(self, registration_reference: str):\n        \"\"\"\n        Stop background monitoring task\n        \n        Args:\n            registration_reference: Registration reference\n        \"\"\"\n        task = self._running_monitors.get(registration_reference)\n        if task:\n            task.cancel()\n            del self._running_monitors[registration_reference]\n            logger.info(\"Background monitoring stopped\",\n                       registration=registration_reference)\n        else:\n            logger.warning(\"No background monitoring found for registration\",\n                          registration=registration_reference)\n    \n    def stop_all_monitoring(self):\n        \"\"\"Stop all background monitoring tasks\"\"\"\n        for registration_reference in list(self._running_monitors.keys()):\n            self.stop_background_monitoring(registration_reference)\n        \n        logger.info(\"All background monitoring stopped\")\n    \n    async def process_notification(self, notification: Notification) -> bool:\n        \"\"\"\n        Process a single notification\n        \n        Args:\n            notification: Notification to process\n            \n        Returns:\n            True if processing successful\n        \"\"\"\n        logger.info(\"Processing notification\",\n                   duns=notification.duns,\n                   notification_type=notification.type.value,\n                   notification_id=str(notification.id))\n        \n        try:\n            # Call all registered notification handlers\n            for handler in self._notification_handlers:\n                handler([notification])\n            \n            # Mark as processed\n            notification.mark_processed()\n            \n            logger.info(\"Notification processed successfully\",\n                       duns=notification.duns,\n                       notification_id=str(notification.id))\n            \n            return True\n            \n        except Exception as e:\n            logger.error(\"Failed to process notification\",\n                        duns=notification.duns,\n                        notification_id=str(notification.id),\n                        error=str(e))\n            \n            notification.mark_error(str(e))\n            return False\n    \n    async def process_notification_batch(self, batch: NotificationBatch) -> int:\n        \"\"\"\n        Process a batch of notifications\n        \n        Args:\n            batch: Notification batch\n            \n        Returns:\n            Number of successfully processed notifications\n        \"\"\"\n        logger.info(\"Processing notification batch\",\n                   batch_id=str(batch.id),\n                   size=batch.size)\n        \n        successful_count = 0\n        \n        for notification in batch.notifications:\n            success = await self.process_notification(notification)\n            if success:\n                successful_count += 1\n        \n        # Mark batch as processed\n        batch.mark_processed()\n        \n        logger.info(\"Notification batch processed\",\n                   batch_id=str(batch.id),\n                   successful=successful_count,\n                   failed=batch.size - successful_count)\n        \n        return successful_count\n    \n    def add_notification_handler(self, handler: Callable[[List[Notification]], None]):\n        \"\"\"\n        Add a notification handler function\n        \n        Args:\n            handler: Function that takes a list of notifications\n        \"\"\"\n        self._notification_handlers.append(handler)\n        logger.info(\"Notification handler added\",\n                   handler_count=len(self._notification_handlers))\n    \n    def remove_notification_handler(self, handler: Callable[[List[Notification]], None]):\n        \"\"\"\n        Remove a notification handler function\n        \n        Args:\n            handler: Handler function to remove\n        \"\"\"\n        if handler in self._notification_handlers:\n            self._notification_handlers.remove(handler)\n            logger.info(\"Notification handler removed\",\n                       handler_count=len(self._notification_handlers))\n    \n    def get_service_status(self) -> Dict[str, Any]:\n        \"\"\"\n        Get comprehensive service status\n        \n        Returns:\n            Service status information\n        \"\"\"\n        registrations = self.registration_manager.list_registrations()\n        \n        return {\n            \"service\": {\n                \"running\": True,\n                \"environment\": self.config.environment,\n                \"debug_mode\": self.config.debug,\n                \"uptime_seconds\": 0,  # Would track actual uptime\n            },\n            \"authentication\": {\n                \"is_authenticated\": self.authenticator.is_authenticated,\n                \"token_expires_in\": self.authenticator.token_expires_in,\n            },\n            \"api_client\": {\n                \"health_check\": self.api_client.health_check(),\n                \"rate_limit\": self.config.dnb_api.rate_limit,\n            },\n            \"registrations\": {\n                \"total_count\": len(registrations),\n                \"active_count\": len([r for r in registrations if r.status == \"ACTIVE\"]),\n                \"background_monitors\": len(self._running_monitors),\n            },\n            \"notification_handlers\": {\n                \"count\": len(self._notification_handlers),\n            },\n            \"configuration\": {\n                \"polling_interval\": self.config.monitoring.polling_interval,\n                \"max_notifications\": self.config.monitoring.max_notifications,\n                \"batch_size\": self.config.monitoring.notification_batch_size,\n            }\n        }\n    \n    def health_check(self) -> bool:\n        \"\"\"\n        Perform comprehensive health check\n        \n        Returns:\n            True if all components are healthy\n        \"\"\"\n        try:\n            # Check API client\n            api_healthy = self.api_client.health_check()\n            \n            # Check authentication\n            auth_healthy = self.authenticator.is_authenticated\n            \n            logger.info(\"Health check completed\",\n                       api_healthy=api_healthy,\n                       auth_healthy=auth_healthy)\n            \n            return api_healthy and auth_healthy\n            \n        except Exception as e:\n            logger.error(\"Health check failed\", error=str(e))\n            return False\n    \n    async def shutdown(self):\n        \"\"\"\n        Gracefully shutdown the monitoring service\n        \"\"\"\n        logger.info(\"Shutting down monitoring service\")\n        \n        # Stop all background monitoring\n        self.stop_all_monitoring()\n        \n        # Wait for tasks to complete\n        if self._running_monitors:\n            await asyncio.gather(*self._running_monitors.values(), return_exceptions=True)\n        \n        # Close HTTP sessions\n        if hasattr(self.api_client, 'session'):\n            self.api_client.session.close()\n        if hasattr(self.authenticator, 'session'):\n            self.authenticator.session.close()\n        \n        logger.info(\"Monitoring service shutdown complete\")\n    \n    async def __aenter__(self):\n        \"\"\"Async context manager entry\"\"\"\n        return self\n    \n    async def __aexit__(self, exc_type, exc_val, exc_tb):\n        \"\"\"Async context manager exit\"\"\"\n        await self.shutdown()\n\n\n# Convenience functions for common use cases\n\ndef create_standard_monitoring_registration(\n    reference: str,\n    duns_list: List[str],\n    description: Optional[str] = None\n) -> RegistrationConfig:\n    \"\"\"\n    Create a standard monitoring registration configuration\n    \n    Args:\n        reference: Registration reference\n        duns_list: List of DUNS to monitor\n        description: Optional description\n        \n    Returns:\n        Registration configuration\n    \"\"\"\n    return RegistrationConfig(\n        reference=reference,\n        description=description,\n        duns_list=duns_list,\n        data_blocks=[\n            \"companyinfo_L2_v1\",\n            \"principalscontacts_L1_v1\",\n            \"hierarchyconnections_L1_v1\"\n        ],\n        json_path_inclusion=[\n            \"organization.primaryName\",\n            \"organization.registeredAddress\", \n            \"organization.telephone\",\n            \"organization.websiteAddress\",\n            \"organization.primaryIndustryCode\"\n        ]\n    )\n\n\ndef create_financial_monitoring_registration(\n    reference: str,\n    duns_list: List[str],\n    description: Optional[str] = None\n) -> RegistrationConfig:\n    \"\"\"\n    Create a financial monitoring registration configuration\n    \n    Args:\n        reference: Registration reference\n        duns_list: List of DUNS to monitor\n        description: Optional description\n        \n    Returns:\n        Registration configuration\n    \"\"\"\n    return RegistrationConfig(\n        reference=reference,\n        description=description,\n        duns_list=duns_list,\n        data_blocks=[\n            \"companyfinancials_L1_v1\",\n            \"paymentinsights_L1_v1\",\n            \"financialstrengthinsight_L2_v1\"\n        ],\n        json_path_inclusion=[\n            \"organization.financials\",\n            \"organization.paymentExperiences\",\n            \"organization.riskAssessment\"\n        ]\n    )\n\n\n# Example notification handlers\n\ndef log_notification_handler(notifications: List[Notification]):\n    \"\"\"\n    Simple notification handler that logs notifications\n    \n    Args:\n        notifications: List of notifications to handle\n    \"\"\"\n    for notification in notifications:\n        logger.info(\"Notification received\",\n                   duns=notification.duns,\n                   type=notification.type.value,\n                   elements_count=len(notification.elements))\n\n\ndef update_database_handler(notifications: List[Notification]):\n    \"\"\"\n    Notification handler that updates database (placeholder)\n    \n    Args:\n        notifications: List of notifications to handle\n    \"\"\"\n    # This would contain actual database update logic\n    for notification in notifications:\n        logger.info(\"Updating database for notification\",\n                   duns=notification.duns,\n                   type=notification.type.value)\n        # Database update logic here\n\n\ndef alert_notification_handler(notifications: List[Notification]):\n    \"\"\"\n    Notification handler that sends alerts for critical changes\n    \n    Args:\n        notifications: List of notifications to handle\n    \"\"\"\n    critical_types = {\"DELETE\", \"TRANSFER\", \"UNDER_REVIEW\"}\n    \n    for notification in notifications:\n        if notification.type.value in critical_types:\n            logger.warning(\"Critical notification received\",\n                          duns=notification.duns,\n                          type=notification.type.value)\n            # Send alert logic here
