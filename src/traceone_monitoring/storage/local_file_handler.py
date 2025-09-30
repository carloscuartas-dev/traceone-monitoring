"""
Local File System Storage Handler for D&B Notifications
Handles storing notifications to local filesystem
"""

import json
import csv
import io
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import structlog
from pydantic import BaseModel, Field

from ..models.notification import Notification, NotificationBatch

logger = structlog.get_logger(__name__)


class LocalFileConfig(BaseModel):
    """Local file storage configuration"""
    base_path: str = Field(..., description="Base directory path for storage")
    file_format: str = Field(default="json", description="File format (json, csv, xml)")
    compress_files: bool = Field(default=False, description="Compress files after creation")
    
    # File organization
    organize_by_date: bool = Field(default=True, description="Organize files by date")
    organize_by_registration: bool = Field(default=True, description="Organize files by registration")
    
    # File permissions
    file_permissions: int = Field(default=0o644, description="File permissions (octal)")
    directory_permissions: int = Field(default=0o755, description="Directory permissions (octal)")
    
    # Retention settings
    max_files_per_directory: int = Field(default=1000, description="Maximum files per directory")
    enable_rotation: bool = Field(default=False, description="Enable file rotation")


class LocalFileStorageError(Exception):
    """Local file storage related errors"""
    pass


class LocalFileNotificationStorage:
    """
    Handles storing notifications to local file system
    """
    
    def __init__(self, config: LocalFileConfig):
        """
        Initialize local file storage handler
        
        Args:
            config: Local file storage configuration
        """
        self.config = config
        self.base_path = Path(config.base_path).expanduser().resolve()
        
        # Ensure base directory exists
        self._ensure_directory(self.base_path)
        
        logger.info("Local File Notification Storage initialized",
                   base_path=str(self.base_path),
                   file_format=config.file_format)
    
    def store_notifications(self, notifications: List[Notification], registration_reference: str) -> Dict[str, Any]:
        """
        Store notifications to local file system
        
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
            # Generate file path
            file_path = self._generate_file_path(registration_reference, len(notifications))
            
            # Format notifications
            file_content = self._format_notifications(notifications)
            
            # Write file
            self._write_file(file_path, file_content)
            
            # Compress if enabled
            if self.config.compress_files:
                compressed_path = self._compress_file(file_path)
                final_path = compressed_path
            else:
                final_path = file_path
            
            result = {
                "stored": len(notifications),
                "files": [str(final_path)],
                "registration": registration_reference,
                "timestamp": datetime.utcnow().isoformat(),
                "format": self.config.file_format,
                "base_path": str(self.base_path)
            }
            
            logger.info("Notifications stored to local file system",
                       count=len(notifications),
                       registration=registration_reference,
                       file_path=str(final_path))
            
            return result
            
        except Exception as e:
            logger.error("Failed to store notifications to local file system",
                        error=str(e),
                        registration=registration_reference,
                        count=len(notifications))
            raise LocalFileStorageError(f"Failed to store notifications: {e}")
    
    def store_notification_batch(self, batch: NotificationBatch) -> Dict[str, Any]:
        """
        Store a notification batch to local file system
        
        Args:
            batch: Notification batch to store
            
        Returns:
            Storage result information
        """
        return self.store_notifications(batch.notifications, batch.registration_id)
    
    def list_stored_files(self, registration_reference: Optional[str] = None) -> List[str]:
        """
        List stored notification files
        
        Args:
            registration_reference: Optional registration filter
            
        Returns:
            List of file paths
        """
        try:
            search_path = self.base_path
            
            if registration_reference and self.config.organize_by_registration:
                # Look in registration-specific directories
                search_pattern = f"**/{registration_reference}/**/*"
            else:
                # Look in all directories
                search_pattern = "**/*"
            
            files = []
            for file_path in search_path.glob(search_pattern):
                if file_path.is_file():
                    # Filter by supported extensions
                    if file_path.suffix.lower() in ['.json', '.csv', '.xml', '.gz']:
                        files.append(str(file_path))
            
            return sorted(files)
            
        except Exception as e:
            logger.error("Failed to list stored files", error=str(e))
            raise LocalFileStorageError(f"Failed to list files: {e}")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            total_files = len(self.list_stored_files())
            total_size = 0
            
            for file_path in self.base_path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            
            return {
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "base_path": str(self.base_path),
                "organize_by_date": self.config.organize_by_date,
                "organize_by_registration": self.config.organize_by_registration,
                "file_format": self.config.file_format
            }
            
        except Exception as e:
            logger.error("Failed to get storage stats", error=str(e))
            return {"error": str(e)}
    
    def _generate_file_path(self, registration_reference: str, notification_count: int) -> Path:
        """Generate file path for notifications"""
        timestamp = datetime.utcnow()
        
        # Build path components
        path_parts = []
        
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
        
        # Combine all parts
        if path_parts:
            directory_path = self.base_path / Path(*path_parts)
        else:
            directory_path = self.base_path
            
        file_path = directory_path / filename
        
        # Ensure directory exists
        self._ensure_directory(directory_path)
        
        return file_path
    
    def _format_notifications(self, notifications: List[Notification]) -> str:
        """Format notifications according to configured format"""
        if self.config.file_format.lower() == "json":
            return self._format_as_json(notifications)
        elif self.config.file_format.lower() == "csv":
            return self._format_as_csv(notifications)
        elif self.config.file_format.lower() == "xml":
            return self._format_as_xml(notifications)
        else:
            raise LocalFileStorageError(f"Unsupported file format: {self.config.file_format}")
    
    def _format_as_json(self, notifications: List[Notification]) -> str:
        """Format notifications as JSON"""
        data = {
            "metadata": {
                "export_timestamp": datetime.utcnow().isoformat() + "Z",
                "notification_count": len(notifications),
                "format_version": "1.0",
                "storage_type": "local_file"
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
        xml_lines.append(f'    <storage_type>local_file</storage_type>')
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
        return '\n'.join(xml_lines)
    
    def _write_file(self, file_path: Path, content: str):
        """Write content to file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Set file permissions
            os.chmod(file_path, self.config.file_permissions)
            
            logger.debug("File written successfully",
                        file_path=str(file_path),
                        size_bytes=len(content.encode('utf-8')))
            
        except Exception as e:
            logger.error("Failed to write file",
                        file_path=str(file_path),
                        error=str(e))
            raise LocalFileStorageError(f"Failed to write file {file_path}: {e}")
    
    def _compress_file(self, file_path: Path) -> Path:
        """Compress file using gzip"""
        import gzip
        
        compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
        
        try:
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            # Remove original file
            file_path.unlink()
            
            # Set compressed file permissions
            os.chmod(compressed_path, self.config.file_permissions)
            
            logger.debug("File compressed successfully",
                        original_path=str(file_path),
                        compressed_path=str(compressed_path))
            
            return compressed_path
            
        except Exception as e:
            logger.error("Failed to compress file",
                        file_path=str(file_path),
                        error=str(e))
            # Clean up compressed file if it exists
            if compressed_path.exists():
                compressed_path.unlink()
            raise LocalFileStorageError(f"Failed to compress file {file_path}: {e}")
    
    def _ensure_directory(self, directory_path: Path):
        """Ensure directory exists with proper permissions"""
        try:
            directory_path.mkdir(parents=True, exist_ok=True)
            
            # Set directory permissions
            os.chmod(directory_path, self.config.directory_permissions)
            
        except Exception as e:
            logger.error("Failed to create directory",
                        directory_path=str(directory_path),
                        error=str(e))
            raise LocalFileStorageError(f"Failed to create directory {directory_path}: {e}")


def create_local_file_storage(config: LocalFileConfig) -> LocalFileNotificationStorage:
    """
    Factory function to create local file storage handler
    
    Args:
        config: Local file storage configuration
        
    Returns:
        Configured local file storage handler
    """
    return LocalFileNotificationStorage(config)
