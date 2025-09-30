"""
Local File Storage Notification Handler for TraceOne Monitoring Service
Automatically stores notifications to local file system when processed
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
import structlog

from ..storage.local_file_handler import LocalFileConfig, LocalFileNotificationStorage, LocalFileStorageError
from ..models.notification import Notification

logger = structlog.get_logger(__name__)


class LocalFileStorageConfig(LocalFileConfig):
    """Extended local file storage configuration for the monitoring service"""
    enabled: bool = False


class LocalFileNotificationHandler:
    """
    Notification handler that automatically stores notifications to local file system
    """
    
    def __init__(self, config: LocalFileStorageConfig):
        """
        Initialize local file notification handler
        
        Args:
            config: Local file storage configuration
        """
        self.config = config
        self.storage: Optional[LocalFileNotificationStorage] = None
        self.enabled = config.enabled
        
        if self.enabled:
            # Create local file storage
            self.storage = LocalFileNotificationStorage(config)
            
            logger.info("Local File notification handler initialized", 
                       base_path=config.base_path,
                       enabled=self.enabled)
        else:
            logger.info("Local File notification handler disabled")
    
    def handle_notifications(self, notifications: List[Notification]):
        """
        Handle notifications by storing them to local file system
        
        Args:
            notifications: List of notifications to handle
        """
        if not self.enabled or not notifications:
            return
        
        try:
            # Group notifications by registration
            by_registration = self._group_by_registration(notifications)
            
            for registration_ref, notification_list in by_registration.items():
                self._store_notifications(registration_ref, notification_list)
                
        except Exception as e:
            logger.error("Local file notification handling failed", 
                        error=str(e),
                        notification_count=len(notifications))
            # Don't re-raise to avoid breaking other handlers
    
    def _group_by_registration(self, notifications: List[Notification]) -> Dict[str, List[Notification]]:
        """Group notifications by registration reference"""
        groups = {}
        
        for notification in notifications:
            # Use a default registration reference if not available
            # In production, this should come from the notification processing context
            registration_ref = getattr(notification, 'registration_reference', 'default')
            
            if registration_ref not in groups:
                groups[registration_ref] = []
            groups[registration_ref].append(notification)
        
        return groups
    
    def _store_notifications(self, registration_ref: str, notifications: List[Notification]):
        """Store notifications for a specific registration"""
        try:
            result = self.storage.store_notifications(notifications, registration_ref)
            
            logger.info("Notifications stored to local file system",
                       registration=registration_ref,
                       stored_count=result['stored'],
                       files=result['files'],
                       format=result['format'])
            
        except LocalFileStorageError as e:
            logger.error("Failed to store notifications to local file system",
                        registration=registration_ref,
                        notification_count=len(notifications),
                        error=str(e))
            
            # Could implement retry logic here
            raise
    
    def get_storage_status(self) -> Dict[str, Any]:
        """Get local file storage status information"""
        if not self.enabled:
            return {
                "enabled": False,
                "status": "disabled"
            }
        
        try:
            # Get storage statistics
            stats = self.storage.get_storage_stats()
            
            return {
                "enabled": True,
                "status": "healthy",
                "base_path": self.config.base_path,
                "file_format": self.config.file_format,
                "organize_by_date": self.config.organize_by_date,
                "organize_by_registration": self.config.organize_by_registration,
                "compress_files": self.config.compress_files,
                "statistics": stats
            }
            
        except Exception as e:
            return {
                "enabled": True,
                "status": "error",
                "error": str(e)
            }
    
    def list_stored_files(self, registration_reference: Optional[str] = None) -> List[str]:
        """List stored notification files"""
        if not self.enabled:
            return []
        
        try:
            return self.storage.list_stored_files(registration_reference)
        except Exception as e:
            logger.error("Failed to list stored files", error=str(e))
            return []
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        if not self.enabled:
            return {"enabled": False}
        
        try:
            return self.storage.get_storage_stats()
        except Exception as e:
            logger.error("Failed to get storage stats", error=str(e))
            return {"error": str(e)}
    
    def test_connection(self) -> bool:
        """Test local file storage connection/access"""
        if not self.enabled:
            return False
        
        try:
            # Test if we can create the base directory and write to it
            base_path = Path(self.config.base_path)
            base_path.mkdir(parents=True, exist_ok=True)
            
            # Try to create a test file
            test_file = base_path / ".connection_test"
            test_file.write_text("test")
            test_file.unlink()  # Remove test file
            
            return True
        except Exception as e:
            logger.error("Local file storage connection test failed", error=str(e))
            return False


def create_local_file_notification_handler(config: LocalFileStorageConfig) -> LocalFileNotificationHandler:
    """
    Factory function to create local file notification handler
    
    Args:
        config: Local file storage configuration
        
    Returns:
        Configured local file notification handler
    """
    return LocalFileNotificationHandler(config)


# Pre-configured handler function that can be used directly with monitoring service
def local_file_notification_handler_factory(config: LocalFileStorageConfig):
    """
    Factory that returns a notification handler function
    
    Args:
        config: Local file storage configuration
        
    Returns:
        Function that can be used as a notification handler
    """
    handler = create_local_file_notification_handler(config)
    
    def handle_notifications(notifications: List[Notification]):
        handler.handle_notifications(notifications)
    
    return handle_notifications, handler  # Return both function and handler object
