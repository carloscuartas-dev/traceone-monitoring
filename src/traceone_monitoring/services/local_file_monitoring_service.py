"""
Local File Monitoring Service for TraceOne Monitoring System
Monitors local directory for notification files and processes them through the notification pipeline
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
import structlog
from pydantic import Field

from .local_file_input_processor import (
    LocalFileInputProcessor, 
    LocalFileInputConfig,
    create_local_file_input_processor
)
from ..models.notification import Notification, NotificationBatch

logger = structlog.get_logger(__name__)


class LocalFileMonitoringConfig(LocalFileInputConfig):
    """Extended configuration for local file monitoring"""
    enabled: bool = Field(default=False, description="Enable local file monitoring")
    polling_interval: int = Field(default=300, description="Polling interval in seconds")
    max_files_per_batch: int = Field(default=100, description="Maximum files to process per batch")
    registration_reference: str = Field(default="local-files", description="Registration reference for local files")


class LocalFileMonitoringServiceError(Exception):
    """Local file monitoring service errors"""
    pass


class LocalFileMonitoringService:
    """
    Service that monitors local directory for notification files and processes them
    """
    
    def __init__(self, config: LocalFileMonitoringConfig):
        """
        Initialize local file monitoring service
        
        Args:
            config: Local file monitoring configuration
        """
        self.config = config
        self.processor = create_local_file_input_processor(config)
        self._notification_handlers: List[Callable[[List[Notification]], None]] = []
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        logger.info("Local File Monitoring Service initialized",
                   enabled=config.enabled,
                   polling_interval=config.polling_interval,
                   input_directory=config.input_directory)
    
    def add_notification_handler(self, handler: Callable[[List[Notification]], None]):
        """
        Add a notification handler to process discovered notifications
        
        Args:
            handler: Function to handle notifications
        """
        self._notification_handlers.append(handler)
        logger.info("Notification handler added", 
                   handler=handler.__name__ if hasattr(handler, '__name__') else str(handler))
    
    def remove_notification_handler(self, handler: Callable[[List[Notification]], None]):
        """
        Remove a notification handler
        
        Args:
            handler: Handler function to remove
        """
        if handler in self._notification_handlers:
            self._notification_handlers.remove(handler)
            logger.info("Notification handler removed")
    
    async def start_monitoring(self):
        """Start the monitoring service"""
        if not self.config.enabled:
            logger.info("Local file monitoring is disabled")
            return
        
        if self._running:
            logger.warning("Monitoring service is already running")
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("Local file monitoring started",
                   polling_interval=self.config.polling_interval)
    
    async def stop_monitoring(self):
        """Stop the monitoring service"""
        if not self._running:
            return
        
        self._running = False
        
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Local file monitoring stopped")
    
    async def process_files_once(self) -> List[Notification]:
        """
        Process files once and return notifications
        
        Returns:
            List of processed notifications
        """
        try:
            logger.info("Processing local files manually")
            
            # Run processor in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            notifications = await loop.run_in_executor(
                None, 
                self.processor.process_all_files
            )
            
            if notifications:
                # Process notifications through handlers
                await self._handle_notifications(notifications)
            
            logger.info("Manual file processing completed",
                       notification_count=len(notifications))
            
            return notifications
            
        except Exception as e:
            logger.error("Manual file processing failed", error=str(e))
            raise LocalFileMonitoringServiceError(f"File processing failed: {e}")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("Starting monitoring loop")
        
        while self._running:
            try:
                # Process files
                notifications = await self.process_files_once()
                
                if notifications:
                    logger.info("Monitoring cycle processed notifications",
                               count=len(notifications))
                else:
                    logger.debug("No new files found in monitoring cycle")
                
                # Wait for next cycle
                await asyncio.sleep(self.config.polling_interval)
                
            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                logger.error("Error in monitoring loop", error=str(e))
                # Wait before retrying
                await asyncio.sleep(min(60, self.config.polling_interval))
    
    async def _handle_notifications(self, notifications: List[Notification]):
        """
        Handle notifications through registered handlers
        
        Args:
            notifications: List of notifications to handle
        """
        if not self._notification_handlers:
            logger.warning("No notification handlers registered")
            return
        
        # Set registration reference for all notifications
        for notification in notifications:
            # Add registration reference as metadata
            if not hasattr(notification, 'registration_reference'):
                notification.registration_reference = self.config.registration_reference
        
        # Process through each handler
        for handler in self._notification_handlers:
            try:
                logger.debug("Processing notifications through handler",
                           handler=handler.__name__ if hasattr(handler, '__name__') else str(handler),
                           count=len(notifications))
                
                # Run handler in thread pool if it's not async
                if asyncio.iscoroutinefunction(handler):
                    await handler(notifications)
                else:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, handler, notifications)
                
            except Exception as e:
                logger.error("Notification handler failed",
                           handler=handler.__name__ if hasattr(handler, '__name__') else str(handler),
                           error=str(e))
                # Continue with other handlers
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get monitoring service status
        
        Returns:
            Status information
        """
        return {
            "enabled": self.config.enabled,
            "running": self._running,
            "input_directory": self.config.input_directory,
            "polling_interval": self.config.polling_interval,
            "registration_reference": self.config.registration_reference,
            "handlers_count": len(self._notification_handlers),
            "processor_config": {
                "process_json_files": self.config.process_json_files,
                "process_txt_files": self.config.process_txt_files,
                "process_zip_files": self.config.process_zip_files,
                "auto_archive_processed": self.config.auto_archive_processed
            }
        }
    
    def discover_files(self) -> Dict[str, List[Path]]:
        """
        Discover files without processing them
        
        Returns:
            Dictionary mapping file types to paths
        """
        return self.processor.discover_files()
    
    async def test_processing(self, max_files: int = 5) -> Dict[str, Any]:
        """
        Test file processing without archiving files
        
        Args:
            max_files: Maximum files to test
            
        Returns:
            Test results
        """
        try:
            # Temporarily disable archiving for testing
            original_archive = self.config.auto_archive_processed
            self.config.auto_archive_processed = False
            
            # Discover files
            discovered_files = self.processor.discover_files()
            
            # Limit files for testing
            test_files = {}
            total_files = 0
            
            for file_type, files in discovered_files.items():
                if total_files >= max_files:
                    break
                
                remaining = max_files - total_files
                test_files[file_type] = files[:remaining]
                total_files += len(test_files[file_type])
            
            # Process test files
            loop = asyncio.get_event_loop()
            
            # Create a test processor with limited files
            test_notifications = []
            
            for file_type, files in test_files.items():
                for file_path in files:
                    try:
                        if file_type == "seedfile":
                            notifications = await loop.run_in_executor(
                                None,
                                self.processor._process_seedfile,
                                file_path,
                                {}
                            )
                        elif file_type == "exception":
                            notifications = await loop.run_in_executor(
                                None,
                                self.processor._process_exception_file,
                                file_path,
                                {}
                            )
                        elif file_type == "duns_export":
                            notifications = await loop.run_in_executor(
                                None,
                                self.processor._process_duns_export_file,
                                file_path,
                                {}
                            )
                        else:
                            continue
                        
                        test_notifications.extend(notifications[:10])  # Limit per file
                        
                    except Exception as e:
                        logger.warning("Test processing failed for file",
                                     file=str(file_path), error=str(e))
            
            # Restore original config
            self.config.auto_archive_processed = original_archive
            
            return {
                "success": True,
                "discovered_files": {k: len(v) for k, v in discovered_files.items()},
                "test_files": {k: len(v) for k, v in test_files.items()},
                "test_notifications": len(test_notifications),
                "sample_notifications": [
                    {
                        "duns": n.duns,
                        "type": n.type.value,
                        "elements_count": len(n.elements)
                    }
                    for n in test_notifications[:5]
                ]
            }
            
        except Exception as e:
            logger.error("Test processing failed", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }


def create_local_file_monitoring_service(config: LocalFileMonitoringConfig) -> LocalFileMonitoringService:
    """
    Factory function to create local file monitoring service
    
    Args:
        config: Local file monitoring configuration
        
    Returns:
        Configured monitoring service
    """
    return LocalFileMonitoringService(config)


# Integration function for DNBMonitoringService
async def integrate_with_monitoring_service(
    monitoring_service, 
    local_file_config: LocalFileMonitoringConfig
) -> Optional[LocalFileMonitoringService]:
    """
    Integrate local file monitoring with DNBMonitoringService
    
    Args:
        monitoring_service: DNBMonitoringService instance
        local_file_config: Local file monitoring configuration
        
    Returns:
        Local file monitoring service if enabled, None otherwise
    """
    if not local_file_config.enabled:
        logger.info("Local file monitoring integration skipped (disabled)")
        return None
    
    # Create local file monitoring service
    local_service = create_local_file_monitoring_service(local_file_config)
    
    # Copy notification handlers from main monitoring service
    for handler in monitoring_service._notification_handlers:
        local_service.add_notification_handler(handler)
    
    # Start monitoring
    await local_service.start_monitoring()
    
    logger.info("Local file monitoring integrated with DNBMonitoringService")
    return local_service
