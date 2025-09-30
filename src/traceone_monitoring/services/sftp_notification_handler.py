"""
SFTP Notification Handler for TraceOne Monitoring Service
Automatically stores notifications to SFTP server when processed
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
import structlog

from ..storage.sftp_handler import SFTPConfig, SFTPNotificationStorage, SFTPStorageError
from ..models.notification import Notification
from ..utils.config import SFTPStorageConfig

logger = structlog.get_logger(__name__)


class SFTPNotificationHandler:
    """
    Notification handler that automatically stores notifications to SFTP server
    """
    
    def __init__(self, sftp_config: SFTPStorageConfig):
        """
        Initialize SFTP notification handler
        
        Args:
            sftp_config: SFTP storage configuration
        """
        self.config = sftp_config
        self.storage: Optional[SFTPNotificationStorage] = None
        self.enabled = sftp_config.enabled
        
        if self.enabled:
            # Create SFTP storage configuration
            storage_config = self._create_storage_config()
            self.storage = SFTPNotificationStorage(storage_config)
            
            logger.info("SFTP notification handler initialized", 
                       hostname=sftp_config.hostname,
                       enabled=self.enabled)
        else:
            logger.info("SFTP notification handler disabled")
    
    def _create_storage_config(self) -> SFTPConfig:
        """Create SFTP storage configuration from app config"""
        # Expand user path for private key
        private_key_path = self.config.private_key_path
        if private_key_path and private_key_path.startswith('~'):
            private_key_path = str(Path(private_key_path).expanduser())
        
        return SFTPConfig(
            hostname=self.config.hostname,
            port=self.config.port,
            username=self.config.username,
            password=self.config.password,
            private_key_path=private_key_path,
            private_key_passphrase=self.config.private_key_passphrase,
            remote_base_path=self.config.remote_base_path,
            file_format=self.config.file_format,
            compress_files=self.config.compress_files,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries,
            organize_by_date=self.config.organize_by_date,
            organize_by_registration=self.config.organize_by_registration
        )
    
    def handle_notifications(self, notifications: List[Notification]):
        """
        Handle notifications by storing them to SFTP server
        
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
            logger.error("SFTP notification handling failed", 
                        error=str(e),
                        notification_count=len(notifications))
            # Don't re-raise to avoid breaking other handlers
    
    def _group_by_registration(self, notifications: List[Notification]) -> Dict[str, List[Notification]]:
        """Group notifications by registration reference"""
        # For now, we'll extract registration from notification metadata
        # In a real implementation, this would come from the notification context
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
            
            logger.info("Notifications stored to SFTP",
                       registration=registration_ref,
                       stored_count=result['stored'],
                       files=result['files'],
                       format=result['format'])
            
        except SFTPStorageError as e:
            logger.error("Failed to store notifications to SFTP",
                        registration=registration_ref,
                        notification_count=len(notifications),
                        error=str(e))
            
            # Could implement retry logic here
            raise
    
    def test_connection(self) -> bool:
        """Test SFTP connection"""
        if not self.enabled:
            logger.warning("SFTP handler is disabled")
            return False
        
        try:
            self.storage.connect()
            self.storage.disconnect()
            logger.info("SFTP connection test successful")
            return True
            
        except Exception as e:
            logger.error("SFTP connection test failed", error=str(e))
            return False
    
    def get_storage_status(self) -> Dict[str, Any]:
        """Get SFTP storage status information"""
        if not self.enabled:
            return {
                "enabled": False,
                "status": "disabled"
            }
        
        try:
            # Test connection
            connection_ok = self.test_connection()
            
            return {
                "enabled": True,
                "status": "healthy" if connection_ok else "connection_failed",
                "hostname": self.config.hostname,
                "port": self.config.port,
                "username": self.config.username,
                "remote_base_path": self.config.remote_base_path,
                "file_format": self.config.file_format,
                "organize_by_date": self.config.organize_by_date,
                "organize_by_registration": self.config.organize_by_registration
            }
            
        except Exception as e:
            return {
                "enabled": True,
                "status": "error",
                "error": str(e)
            }


def create_sftp_notification_handler(sftp_config: SFTPStorageConfig) -> SFTPNotificationHandler:
    """
    Factory function to create SFTP notification handler
    
    Args:
        sftp_config: SFTP storage configuration
        
    Returns:
        Configured SFTP notification handler
    """
    return SFTPNotificationHandler(sftp_config)


# Pre-configured handler function that can be used directly with monitoring service
def sftp_notification_handler_factory(sftp_config: SFTPStorageConfig):
    """
    Factory that returns a notification handler function
    
    Args:
        sftp_config: SFTP storage configuration
        
    Returns:
        Function that can be used as a notification handler
    """
    handler = create_sftp_notification_handler(sftp_config)
    
    def handle_notifications(notifications: List[Notification]):
        handler.handle_notifications(notifications)
    
    return handle_notifications, handler  # Return both function and handler object
