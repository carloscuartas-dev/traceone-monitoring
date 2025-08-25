"""
D&B Pull API client for notification retrieval and processing
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Dict, List, Optional, Tuple, Union
import structlog

from .client import DNBApiClient, NotFoundError
from ..models.notification import (
    Notification, 
    NotificationResponse,
    NotificationBatch, 
    NotificationStats,
)
from ..models.registration import Registration


logger = structlog.get_logger(__name__)


class PullApiClient:
    """
    Client for D&B Pull API to retrieve notifications
    """
    
    def __init__(self, api_client: DNBApiClient):
        """
        Initialize Pull API client
        
        Args:
            api_client: D&B API client
        """
        self.client = api_client
        self.stats = NotificationStats()
    
    def pull_notifications(
        self, 
        registration_reference: str, 
        max_notifications: int = 100
    ) -> NotificationResponse:
        """
        Pull notifications for a registration
        
        Args:
            registration_reference: Registration reference
            max_notifications: Maximum number of notifications to retrieve
            
        Returns:
            NotificationResponse object
            
        Raises:
            NotFoundError: If no notifications are available
            DNBApiError: If API call fails
        """
        endpoint = f"/v1/monitoring/registrations/{registration_reference}/notifications"
        params = {
            "maxNotifications": max_notifications
        }
        
        logger.info("Pulling notifications", 
                   registration=registration_reference,
                   max_notifications=max_notifications)
        
        start_time = time.time()
        try:
            response = self.client.get(endpoint, params=params)
            
            # Parse response
            notification_response = NotificationResponse(**response.json())
            
            # Log results
            notification_count = len(notification_response.notifications)
            logger.info("Notifications retrieved",
                       registration=registration_reference,
                       count=notification_count)
            
            # Update statistics
            self._update_stats(notification_response)
            
            return notification_response
            
        except NotFoundError:
            logger.info("No notifications available",
                       registration=registration_reference)
            raise
        finally:
            elapsed_time = time.time() - start_time
            logger.debug("Pull operation completed",
                        registration=registration_reference,
                        elapsed_seconds=elapsed_time)
    
    def replay_notifications(
        self,
        registration_reference: str,
        start_timestamp: Union[str, datetime],
        max_notifications: int = 100
    ) -> NotificationResponse:
        """
        Replay notifications from a specific timestamp
        
        Args:
            registration_reference: Registration reference
            start_timestamp: Start timestamp for replay (ISO-8601 string or datetime)
            max_notifications: Maximum number of notifications to retrieve
            
        Returns:
            NotificationResponse object
            
        Raises:
            NotFoundError: If no notifications are available
            DNBApiError: If API call fails
        """
        endpoint = f"/v1/monitoring/registrations/{registration_reference}/notifications/replay"
        
        # Convert datetime to ISO-8601 string if needed
        if isinstance(start_timestamp, datetime):
            # Ensure timezone is UTC
            if start_timestamp.tzinfo is None:
                start_timestamp = start_timestamp.replace(tzinfo=timezone.utc)
            timestamp_str = start_timestamp.isoformat()
        else:
            timestamp_str = start_timestamp
        
        params = {
            "replayStartTimestamp": timestamp_str,
            "maxNotifications": max_notifications
        }
        
        logger.info("Replaying notifications",
                   registration=registration_reference,
                   start_timestamp=timestamp_str,
                   max_notifications=max_notifications)
        
        start_time = time.time()
        try:
            response = self.client.get(endpoint, params=params)
            
            # Parse response
            notification_response = NotificationResponse(**response.json())
            
            # Log results
            notification_count = len(notification_response.notifications)
            logger.info("Notifications replayed",
                       registration=registration_reference,
                       count=notification_count)
            
            # Update statistics
            self._update_stats(notification_response)
            
            return notification_response
            
        except NotFoundError:
            logger.info("No notifications available for replay",
                       registration=registration_reference,
                       start_timestamp=timestamp_str)
            raise
        finally:
            elapsed_time = time.time() - start_time
            logger.debug("Replay operation completed",
                        registration=registration_reference,
                        elapsed_seconds=elapsed_time)
    
    def pull_all_notifications(
        self,
        registration_reference: str,
        max_iterations: int = 100,
        max_notifications_per_pull: int = 100,
        batch_size: Optional[int] = None
    ) -> List[NotificationBatch]:
        """
        Pull all available notifications in batches
        
        Args:
            registration_reference: Registration reference
            max_iterations: Maximum number of pull iterations
            max_notifications_per_pull: Maximum notifications per pull request
            batch_size: Maximum notifications per batch (defaults to max_notifications_per_pull)
            
        Returns:
            List of notification batches
        """
        logger.info("Pulling all notifications",
                   registration=registration_reference,
                   max_iterations=max_iterations)
        
        batches = []
        total_notifications = 0
        batch_size = batch_size or max_notifications_per_pull
        
        # Start statistics tracking
        self.stats.processing_start_time = datetime.utcnow()
        
        try:
            for i in range(max_iterations):
                try:
                    # Pull notifications
                    response = self.pull_notifications(
                        registration_reference,
                        max_notifications=max_notifications_per_pull
                    )
                    
                    # Process notifications
                    notifications = response.notifications
                    if not notifications:
                        logger.info("No more notifications available", iteration=i)
                        break
                    
                    # Create batches
                    for j in range(0, len(notifications), batch_size):
                        batch_notifications = notifications[j:j+batch_size]
                        batch = NotificationBatch(
                            registration_id=registration_reference,
                            notifications=batch_notifications
                        )
                        batches.append(batch)
                    
                    total_notifications += len(notifications)
                    logger.info("Pulled batch of notifications",
                               batch=i,
                               count=len(notifications),
                               total=total_notifications)
                    
                except NotFoundError:
                    # No more notifications
                    logger.info("No more notifications available", iteration=i)
                    break
        finally:
            # Finalize statistics
            self.stats.processing_end_time = datetime.utcnow()
            self.stats.unique_duns = len({n.duns for b in batches for n in b.notifications})
            
            logger.info("Completed pulling all notifications",
                       registration=registration_reference,
                       total_batches=len(batches),
                       total_notifications=total_notifications,
                       unique_duns=self.stats.unique_duns)
        
        return batches
    
    async def pull_notifications_continuously(
        self,
        registration: Registration,
        polling_interval: int,
        max_notifications: int = 100,
        replay_on_error: bool = True
    ) -> AsyncGenerator[List[Notification], None]:
        """
        Continuously pull notifications in an async loop
        
        Args:
            registration: Registration object
            polling_interval: Seconds between polling attempts
            max_notifications: Maximum notifications per pull
            replay_on_error: Whether to use replay API on error
            
        Yields:
            Lists of notifications
        """
        logger.info("Starting continuous notification polling",
                   registration=registration.reference,
                   polling_interval=polling_interval)
        
        last_timestamp = registration.last_pull_timestamp
        consecutive_errors = 0
        
        while True:
            try:
                # Use replay API if we have a last timestamp and either:
                # - We're recovering from an error, or
                # - It's been more than polling_interval*2 since last pull
                use_replay = last_timestamp is not None and (
                    replay_on_error and consecutive_errors > 0 or
                    (datetime.utcnow() - last_timestamp).total_seconds() > polling_interval * 2
                )
                
                if use_replay:
                    logger.info("Using replay API",
                               registration=registration.reference,
                               last_timestamp=last_timestamp.isoformat())
                    response = self.replay_notifications(
                        registration.reference,
                        last_timestamp,
                        max_notifications
                    )
                else:
                    response = self.pull_notifications(
                        registration.reference,
                        max_notifications
                    )
                
                # Reset error counter on success
                consecutive_errors = 0
                
                # Update last timestamp
                if response.has_notifications:
                    last_timestamp = response.get_last_timestamp()
                    # Update registration
                    registration.update_pull_timestamp(last_timestamp)
                    
                    # Yield notifications
                    yield response.notifications
                
                # Sleep until next poll
                await asyncio.sleep(polling_interval)
                
            except NotFoundError:
                # No notifications available
                logger.debug("No notifications available",
                            registration=registration.reference)
                await asyncio.sleep(polling_interval)
                
            except Exception as e:
                # Handle other errors
                consecutive_errors += 1
                backoff_time = min(polling_interval * 2 ** consecutive_errors, 3600)
                
                logger.error("Error pulling notifications",
                            registration=registration.reference,
                            error=str(e),
                            consecutive_errors=consecutive_errors,
                            backoff_seconds=backoff_time)
                
                # Record error in registration
                registration.record_error(str(e))
                
                # Backoff before retry
                await asyncio.sleep(backoff_time)
    
    def _update_stats(self, response: NotificationResponse):
        """Update notification statistics"""
        for notification in response.notifications:
            self.stats.add_notification(notification)
            
            # Count unique DUNS
            self.stats.unique_duns = len({n.organization.duns for n in response.notifications})


def create_pull_client(api_client: DNBApiClient) -> PullApiClient:
    """
    Factory function to create Pull API client
    
    Args:
        api_client: D&B API client
        
    Returns:
        Configured Pull API client
    """
    return PullApiClient(api_client)
