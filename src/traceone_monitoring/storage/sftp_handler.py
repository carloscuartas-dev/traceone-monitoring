"""
SFTP Storage Handler for D&B Notifications
Handles uploading notifications to SFTP servers
"""

import json
import csv
import io
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import paramiko
import structlog
from pydantic import BaseModel, Field

from ..models.notification import Notification, NotificationBatch

logger = structlog.get_logger(__name__)


class SFTPConfig(BaseModel):
    """SFTP server configuration"""
    hostname: str = Field(..., description="SFTP server hostname")
    port: int = Field(default=22, description="SFTP server port")
    username: str = Field(..., description="SFTP username")
    password: Optional[str] = Field(default=None, description="SFTP password")
    private_key_path: Optional[str] = Field(default=None, description="Path to private key file")
    private_key_passphrase: Optional[str] = Field(default=None, description="Private key passphrase")
    
    # Remote paths
    remote_base_path: str = Field(default="/notifications", description="Base path on SFTP server")
    
    # File format options
    file_format: str = Field(default="json", description="File format (json, csv, xml)")
    compress_files: bool = Field(default=False, description="Compress files before upload")
    
    # Connection settings
    timeout: int = Field(default=30, description="Connection timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    
    # File organization
    organize_by_date: bool = Field(default=True, description="Organize files by date")
    organize_by_registration: bool = Field(default=True, description="Organize files by registration")


class SFTPStorageError(Exception):
    """SFTP storage related errors"""
    pass


class SFTPNotificationStorage:
    """
    Handles storing notifications on SFTP servers
    """
    
    def __init__(self, config: SFTPConfig):
        """
        Initialize SFTP storage handler
        
        Args:
            config: SFTP configuration
        """
        self.config = config
        self.client = None
        self.sftp = None
        
        logger.info("SFTP Notification Storage initialized",
                   hostname=config.hostname,
                   port=config.port,
                   username=config.username)
    
    def connect(self):
        """Establish SFTP connection"""
        if self.client and self.sftp:
            return  # Already connected
        
        try:
            logger.info("Connecting to SFTP server", 
                       hostname=self.config.hostname,
                       port=self.config.port)
            
            # Create SSH client
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Determine authentication method
            if self.config.private_key_path:
                # Use private key authentication with auto-detection
                private_key = self._load_private_key(
                    self.config.private_key_path,
                    self.config.private_key_passphrase
                )
                self.client.connect(
                    hostname=self.config.hostname,
                    port=self.config.port,
                    username=self.config.username,
                    pkey=private_key,
                    timeout=self.config.timeout,
                    look_for_keys=False,  # Only use provided key
                    allow_agent=False     # Don't use SSH agent
                )
            else:
                # Use password authentication
                self.client.connect(
                    hostname=self.config.hostname,
                    port=self.config.port,
                    username=self.config.username,
                    password=self.config.password,
                    timeout=self.config.timeout
                )
            
            # Open SFTP session
            self.sftp = self.client.open_sftp()
            
            # Ensure base directory exists
            self._ensure_remote_directory(self.config.remote_base_path)
            
            logger.info("SFTP connection established successfully")
            
        except Exception as e:
            logger.error("Failed to connect to SFTP server", error=str(e))
            self.disconnect()
            raise SFTPStorageError(f"SFTP connection failed: {e}")
    
    def disconnect(self):
        """Close SFTP connection"""
        try:
            if self.sftp:
                self.sftp.close()
                self.sftp = None
            
            if self.client:
                self.client.close()
                self.client = None
                
            logger.info("SFTP connection closed")
            
        except Exception as e:
            logger.warning("Error during SFTP disconnect", error=str(e))
    
    def _load_private_key(self, private_key_path: str, passphrase: Optional[str] = None):
        """Load private key with automatic type detection"""
        
        # Validate key file exists
        key_path = Path(private_key_path)
        if not key_path.exists():
            raise SFTPStorageError(f"Private key file not found: {private_key_path}")
        
        logger.debug("Loading private key", path=private_key_path)
        
        # Try different key types in order of preference
        key_loaders = [
            ("RSA", paramiko.RSAKey.from_private_key_file),
            ("Ed25519", paramiko.Ed25519Key.from_private_key_file),
            ("ECDSA", paramiko.ECDSAKey.from_private_key_file),
        ]
        
        last_error = None
        for key_type, loader in key_loaders:
            try:
                logger.debug(f"Attempting to load key as {key_type}")
                key = loader(private_key_path, password=passphrase)
                logger.info(f"Successfully loaded {key_type} private key", path=private_key_path)
                return key
            except Exception as e:
                logger.debug(f"Failed to load key as {key_type}: {e}")
                last_error = e
                continue
        
        # If we get here, all loaders failed
        raise SFTPStorageError(
            f"Failed to load private key {private_key_path} with any supported format. "
            f"Last error: {last_error}"
        )
    
    def store_notifications(self, notifications: List[Notification], registration_reference: str) -> Dict[str, Any]:
        """
        Store notifications on SFTP server
        
        Args:
            notifications: List of notifications to store
            registration_reference: Registration reference
            
        Returns:
            Storage result information
        """
        if not notifications:
            logger.warning("No notifications to store")
            return {"stored": 0, "files": []}
        
        try:
            self.connect()
            
            # Generate remote file path
            remote_file_path = self._generate_remote_path(
                registration_reference, 
                len(notifications)
            )
            
            # Format notifications
            file_content = self._format_notifications(notifications)
            
            # Upload file
            self._upload_file(remote_file_path, file_content)
            
            result = {
                "stored": len(notifications),
                "files": [remote_file_path],
                "registration": registration_reference,
                "timestamp": datetime.utcnow().isoformat(),
                "format": self.config.file_format
            }
            
            logger.info("Notifications stored successfully",
                       count=len(notifications),
                       registration=registration_reference,
                       file_path=remote_file_path)
            
            return result
            
        except Exception as e:
            logger.error("Failed to store notifications via SFTP",
                        error=str(e),
                        registration=registration_reference,
                        count=len(notifications))
            raise SFTPStorageError(f"Failed to store notifications: {e}")
    
    def store_notification_batch(self, batch: NotificationBatch) -> Dict[str, Any]:
        """
        Store a notification batch on SFTP server
        
        Args:
            batch: Notification batch to store
            
        Returns:
            Storage result information
        """
        return self.store_notifications(batch.notifications, batch.registration_id)
    
    def _generate_remote_path(self, registration_reference: str, notification_count: int) -> str:
        """Generate remote file path"""
        timestamp = datetime.utcnow()
        
        # Build path components
        path_parts = [self.config.remote_base_path.strip("/")]
        
        if self.config.organize_by_date:
            path_parts.extend([
                f"{timestamp.year:04d}",
                f"{timestamp.month:02d}",
                f"{timestamp.day:02d}"
            ])
        
        if self.config.organize_by_registration:
            path_parts.append(registration_reference)
        
        # Generate filename
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        filename = f"notifications_{timestamp_str}_{notification_count}.{self.config.file_format}"
        
        path_parts.append(filename)
        
        return "/" + "/".join(path_parts)
    
    def _format_notifications(self, notifications: List[Notification]) -> str:
        """Format notifications according to configured format"""
        if self.config.file_format.lower() == "json":
            return self._format_as_json(notifications)
        elif self.config.file_format.lower() == "csv":
            return self._format_as_csv(notifications)
        elif self.config.file_format.lower() == "xml":
            return self._format_as_xml(notifications)
        else:
            raise SFTPStorageError(f"Unsupported file format: {self.config.file_format}")
    
    def _format_as_json(self, notifications: List[Notification]) -> str:
        """Format notifications as JSON"""
        data = {
            "metadata": {
                "export_timestamp": datetime.utcnow().isoformat() + "Z",
                "notification_count": len(notifications),
                "format_version": "1.0"
            },
            "notifications": [n.dict() for n in notifications]
        }
        return json.dumps(data, indent=2, default=str)
    
    def _format_as_csv(self, notifications: List[Notification]) -> str:
        """Format notifications as CSV"""
        output = io.StringIO()
        
        if not notifications:
            return ""
        
        # Define CSV columns
        columns = [
            "id", "type", "duns", "delivery_timestamp", 
            "processed", "processing_timestamp", "error_count"
        ]
        
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        
        for notification in notifications:
            row = {
                "id": str(notification.id),
                "type": notification.type.value,
                "duns": notification.duns,
                "delivery_timestamp": notification.delivery_timestamp.isoformat(),
                "processed": notification.processed,
                "processing_timestamp": notification.processing_timestamp.isoformat() if notification.processing_timestamp else "",
                "error_count": notification.error_count
            }
            writer.writerow(row)
        
        return output.getvalue()
    
    def _format_as_xml(self, notifications: List[Notification]) -> str:
        """Format notifications as XML"""
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append('<notifications>')
        xml_lines.append(f'  <metadata>')
        xml_lines.append(f'    <export_timestamp>{datetime.utcnow().isoformat()}Z</export_timestamp>')
        xml_lines.append(f'    <notification_count>{len(notifications)}</notification_count>')
        xml_lines.append(f'  </metadata>')
        
        for notification in notifications:
            xml_lines.append('  <notification>')
            xml_lines.append(f'    <id>{notification.id}</id>')
            xml_lines.append(f'    <type>{notification.type.value}</type>')
            xml_lines.append(f'    <duns>{notification.duns}</duns>')
            xml_lines.append(f'    <delivery_timestamp>{notification.delivery_timestamp.isoformat()}</delivery_timestamp>')
            xml_lines.append(f'    <processed>{notification.processed}</processed>')
            xml_lines.append(f'    <error_count>{notification.error_count}</error_count>')
            xml_lines.append('  </notification>')
        
        xml_lines.append('</notifications>')
        return '\\n'.join(xml_lines)
    
    def _upload_file(self, remote_path: str, content: str):
        """Upload file content to SFTP server"""
        # Ensure remote directory exists
        remote_dir = str(Path(remote_path).parent)
        self._ensure_remote_directory(remote_dir)
        
        # Upload file
        file_like = io.StringIO(content)
        
        # Convert to bytes for SFTP
        content_bytes = content.encode('utf-8')
        bytes_io = io.BytesIO(content_bytes)
        
        logger.debug("Uploading file to SFTP",
                    remote_path=remote_path,
                    size=len(content_bytes))
        
        self.sftp.putfo(bytes_io, remote_path)
        
        logger.debug("File uploaded successfully", remote_path=remote_path)
    
    def _ensure_remote_directory(self, remote_path: str):
        """Ensure remote directory exists"""
        if not remote_path or remote_path == "/":
            return
        
        try:
            # Check if directory exists
            self.sftp.stat(remote_path)
            return  # Directory exists
        except FileNotFoundError:
            pass  # Directory doesn't exist, create it
        
        # Create parent directories first
        parent_path = str(Path(remote_path).parent)
        if parent_path != remote_path and parent_path != "/":
            self._ensure_remote_directory(parent_path)
        
        # Create this directory
        try:
            self.sftp.mkdir(remote_path)
            logger.debug("Created remote directory", path=remote_path)
        except Exception as e:
            # Ignore if directory already exists (race condition)
            if "file already exists" not in str(e).lower():
                logger.warning("Failed to create remote directory",
                             path=remote_path, error=str(e))
    
    def list_remote_files(self, registration_reference: Optional[str] = None) -> List[str]:
        """List files on SFTP server"""
        try:
            self.connect()
            
            search_path = self.config.remote_base_path
            if registration_reference and self.config.organize_by_registration:
                search_path = f"{search_path.rstrip('/')}/{registration_reference}"
            
            files = []
            self._list_files_recursive(search_path, files)
            
            return files
            
        except Exception as e:
            logger.error("Failed to list remote files", error=str(e))
            raise SFTPStorageError(f"Failed to list files: {e}")
    
    def _list_files_recursive(self, path: str, files: List[str]):
        """Recursively list files in directory"""
        try:
            for item in self.sftp.listdir_attr(path):
                full_path = f"{path}/{item.filename}"
                if item.st_mode & 0o040000:  # Directory
                    self._list_files_recursive(full_path, files)
                else:  # File
                    files.append(full_path)
        except FileNotFoundError:
            # Directory doesn't exist
            pass
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


def create_sftp_storage(config: SFTPConfig) -> SFTPNotificationStorage:
    """
    Factory function to create SFTP storage handler
    
    Args:
        config: SFTP configuration
        
    Returns:
        Configured SFTP storage handler
    """
    return SFTPNotificationStorage(config)
