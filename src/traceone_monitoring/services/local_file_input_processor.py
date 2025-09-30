"""
Local File Input Processor for TraceOne Monitoring Service
Reads and processes notification files from local SFTP directory
"""

import json
import csv
import zipfile
import gzip
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Generator, Union
import structlog
from pydantic import BaseModel, Field

from ..models.notification import (
    Notification, 
    NotificationElement, 
    NotificationType, 
    Organization
)

logger = structlog.get_logger(__name__)


class LocalFileInputConfig(BaseModel):
    """Local file input processor configuration"""
    input_directory: str = Field(..., description="Directory containing notification files")
    process_json_files: bool = Field(default=True, description="Process JSON seedfiles")
    process_txt_files: bool = Field(default=True, description="Process text exception files")
    process_zip_files: bool = Field(default=True, description="Process ZIP archives")
    process_header_files: bool = Field(default=True, description="Process header metadata files")
    auto_archive_processed: bool = Field(default=True, description="Archive processed files")
    archive_directory: Optional[str] = Field(default=None, description="Archive directory")
    file_patterns: Dict[str, str] = Field(
        default_factory=lambda: {
            "seedfile": "*SEEDFILE*.txt",
            "header": "*HEADER*.json",
            "exception": "*exception*.txt", 
            "duns_export": "*DunsExport*.txt",
            "zip_archive": "*.zip"
        },
        description="File patterns to match"
    )


class LocalFileInputProcessorError(Exception):
    """Local file input processor errors"""
    pass


class LocalFileInputProcessor:
    """
    Processes notification files from local directory and converts them to Notification models
    """
    
    def __init__(self, config: LocalFileInputConfig):
        """
        Initialize local file input processor
        
        Args:
            config: Local file input configuration
        """
        self.config = config
        self.input_path = Path(config.input_directory).expanduser().resolve()
        
        if not self.input_path.exists():
            raise LocalFileInputProcessorError(f"Input directory does not exist: {self.input_path}")
        
        # Set up archive directory
        self.archive_path = None
        if config.auto_archive_processed and config.archive_directory:
            self.archive_path = Path(config.archive_directory).expanduser().resolve()
            self.archive_path.mkdir(parents=True, exist_ok=True)
        elif config.auto_archive_processed:
            self.archive_path = self.input_path / "processed"
            self.archive_path.mkdir(exist_ok=True)
        
        logger.info("Local File Input Processor initialized",
                   input_path=str(self.input_path),
                   archive_path=str(self.archive_path) if self.archive_path else None)
    
    def discover_files(self) -> Dict[str, List[Path]]:
        """
        Discover files in input directory by type
        
        Returns:
            Dictionary mapping file types to file paths
        """
        discovered_files = {}
        
        try:
            for file_type, pattern in self.config.file_patterns.items():
                matching_files = list(self.input_path.glob(pattern))
                discovered_files[file_type] = matching_files
                
                logger.debug(f"Discovered {file_type} files",
                           count=len(matching_files),
                           pattern=pattern)
            
            total_files = sum(len(files) for files in discovered_files.values())
            logger.info("File discovery completed", 
                       total_files=total_files,
                       by_type={k: len(v) for k, v in discovered_files.items()})
            
            return discovered_files
            
        except Exception as e:
            logger.error("File discovery failed", error=str(e))
            raise LocalFileInputProcessorError(f"File discovery failed: {e}")
    
    def process_all_files(self) -> List[Notification]:
        """
        Process all files in input directory
        
        Returns:
            List of parsed notifications
        """
        discovered_files = self.discover_files()
        all_notifications = []
        processed_files = []
        
        # Process header files first to get metadata
        headers_by_file = {}
        if self.config.process_header_files and discovered_files.get("header"):
            for header_file in discovered_files["header"]:
                try:
                    header_data = self._parse_header_file(header_file)
                    headers_by_file[header_file.stem] = header_data
                    processed_files.append(header_file)
                except Exception as e:
                    logger.error("Failed to process header file",
                               file=str(header_file), error=str(e))
        
        # Process JSON seedfiles
        if self.config.process_json_files and discovered_files.get("seedfile"):
            for seedfile in discovered_files["seedfile"]:
                try:
                    notifications = self._process_seedfile(seedfile, headers_by_file)
                    all_notifications.extend(notifications)
                    processed_files.append(seedfile)
                    logger.info("Processed seedfile",
                               file=str(seedfile),
                               notification_count=len(notifications))
                except Exception as e:
                    logger.error("Failed to process seedfile",
                               file=str(seedfile), error=str(e))
        
        # Process text exception files
        if self.config.process_txt_files and discovered_files.get("exception"):
            for exception_file in discovered_files["exception"]:
                try:
                    notifications = self._process_exception_file(exception_file, headers_by_file)
                    all_notifications.extend(notifications)
                    processed_files.append(exception_file)
                    logger.info("Processed exception file",
                               file=str(exception_file),
                               notification_count=len(notifications))
                except Exception as e:
                    logger.error("Failed to process exception file",
                               file=str(exception_file), error=str(e))
        
        # Process DUNS export files  
        if self.config.process_txt_files and discovered_files.get("duns_export"):
            for export_file in discovered_files["duns_export"]:
                try:
                    notifications = self._process_duns_export_file(export_file, headers_by_file)
                    all_notifications.extend(notifications)
                    processed_files.append(export_file)
                    logger.info("Processed DUNS export file",
                               file=str(export_file),
                               notification_count=len(notifications))
                except Exception as e:
                    logger.error("Failed to process DUNS export file",
                               file=str(export_file), error=str(e))
        
        # Process ZIP archives
        if self.config.process_zip_files and discovered_files.get("zip_archive"):
            for zip_file in discovered_files["zip_archive"]:
                try:
                    notifications = self._process_zip_archive(zip_file, headers_by_file)
                    all_notifications.extend(notifications)
                    processed_files.append(zip_file)
                    logger.info("Processed ZIP archive",
                               file=str(zip_file),
                               notification_count=len(notifications))
                except Exception as e:
                    logger.error("Failed to process ZIP archive",
                               file=str(zip_file), error=str(e))
        
        # Archive processed files
        if self.config.auto_archive_processed and self.archive_path:
            self._archive_files(processed_files)
        
        logger.info("File processing completed",
                   total_notifications=len(all_notifications),
                   processed_files_count=len(processed_files))
        
        return all_notifications
    
    def _parse_header_file(self, header_file: Path) -> Dict[str, Any]:
        """Parse header JSON file"""
        try:
            with header_file.open('r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to parse header file", file=str(header_file), error=str(e))
            raise
    
    def _process_seedfile(self, seedfile: Path, headers: Dict[str, Any]) -> List[Notification]:
        """
        Process a seedfile containing JSON organization data
        
        Args:
            seedfile: Path to seedfile
            headers: Header metadata by filename
            
        Returns:
            List of notifications
        """
        notifications = []
        
        try:
            with seedfile.open('r', encoding='utf-8') as f:
                # Each line is a JSON object with organization data
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        org_data = json.loads(line)
                        notification = self._create_notification_from_org_data(
                            org_data, seedfile, headers, line_num
                        )
                        if notification:
                            notifications.append(notification)
                    except json.JSONDecodeError as e:
                        logger.warning("Invalid JSON in seedfile",
                                     file=str(seedfile),
                                     line=line_num,
                                     error=str(e))
                    except Exception as e:
                        logger.error("Failed to process organization data",
                                   file=str(seedfile),
                                   line=line_num,
                                   error=str(e))
        
        except Exception as e:
            logger.error("Failed to process seedfile", file=str(seedfile), error=str(e))
            raise
        
        return notifications
    
    def _create_notification_from_org_data(
        self, 
        org_data: Dict[str, Any], 
        source_file: Path,
        headers: Dict[str, Any],
        line_num: int
    ) -> Optional[Notification]:
        """
        Create notification from organization data
        
        Args:
            org_data: Organization data from JSON
            source_file: Source file path
            headers: Header metadata
            line_num: Line number in file
            
        Returns:
            Notification object or None if invalid
        """
        try:
            # Extract DUNS number
            organization_info = org_data.get('organization', {})
            duns = organization_info.get('duns')
            
            if not duns or len(duns) != 9 or not duns.isdigit():
                logger.warning("Invalid or missing DUNS number",
                             file=str(source_file),
                             line=line_num,
                             duns=duns)
                return None
            
            # Create organization
            organization = Organization(duns=duns)
            
            # Create notification elements from organization data
            elements = self._extract_notification_elements(organization_info)
            
            # Get header info for this file
            header_key = source_file.stem
            header_info = headers.get(header_key, {})
            
            # Determine notification type based on file content
            notification_type = self._determine_notification_type(header_info, source_file)
            
            # Create notification
            notification = Notification(
                type=notification_type,
                organization=organization,
                elements=elements,
                deliveryTimeStamp=datetime.utcnow()
            )
            
            return notification
            
        except Exception as e:
            logger.error("Failed to create notification from org data",
                       file=str(source_file),
                       line=line_num,
                       error=str(e))
            return None
    
    def _extract_notification_elements(self, org_data: Dict[str, Any]) -> List[NotificationElement]:
        """
        Extract notification elements from organization data
        
        Args:
            org_data: Organization data
            
        Returns:
            List of notification elements
        """
        elements = []
        timestamp = datetime.utcnow()
        
        # Define key fields to track as notification elements
        key_fields = [
            'primaryName',
            'dunsControlStatus',
            'primaryAddress',
            'telephone',
            'numberOfEmployees',
            'financials',
            'corporateLinkage',
            'registrationNumbers',
            'legalForm'
        ]
        
        for field in key_fields:
            if field in org_data:
                element = NotificationElement(
                    element=f"organization.{field}",
                    current=org_data[field],
                    timestamp=timestamp
                )
                elements.append(element)
        
        return elements
    
    def _determine_notification_type(
        self, 
        header_info: Dict[str, Any], 
        source_file: Path
    ) -> NotificationType:
        """
        Determine notification type from header info and file name
        
        Args:
            header_info: Header metadata
            source_file: Source file path
            
        Returns:
            Notification type
        """
        # Check header type
        header_type = header_info.get('headerType', '').upper()
        if header_type == 'SEEDFILE':
            return NotificationType.SEED
        
        # Check filename for patterns
        filename = source_file.name.lower()
        
        if 'exception' in filename:
            return NotificationType.UPDATE  # Exceptions are typically updates
        elif 'export' in filename:
            return NotificationType.UPDATE
        elif 'seedfile' in filename:
            return NotificationType.SEED
        else:
            return NotificationType.UPDATE  # Default to update
    
    def _process_exception_file(self, exception_file: Path, headers: Dict[str, Any]) -> List[Notification]:
        """
        Process tab-delimited exception file
        
        Args:
            exception_file: Path to exception file
            headers: Header metadata
            
        Returns:
            List of notifications
        """
        notifications = []
        
        try:
            with exception_file.open('r', encoding='utf-8') as f:
                # Read tab-delimited file
                reader = csv.reader(f, delimiter='\t')
                
                for line_num, row in enumerate(reader, 1):
                    if len(row) >= 1:  # At least DUNS number
                        duns = row[0].strip()
                        
                        if len(duns) == 9 and duns.isdigit():
                            organization = Organization(duns=duns)
                            
                            # Create exception notification element
                            exception_data = {
                                'duns': duns,
                                'exception_type': row[1] if len(row) > 1 else 'UNKNOWN',
                                'source_file': str(exception_file)
                            }
                            
                            element = NotificationElement(
                                element="organization.exception",
                                current=exception_data,
                                timestamp=datetime.utcnow()
                            )
                            
                            notification = Notification(
                                type=NotificationType.UPDATE,
                                organization=organization,
                                elements=[element],
                                deliveryTimeStamp=datetime.utcnow()
                            )
                            
                            notifications.append(notification)
        
        except Exception as e:
            logger.error("Failed to process exception file", file=str(exception_file), error=str(e))
            raise
        
        return notifications
    
    def _process_duns_export_file(self, export_file: Path, headers: Dict[str, Any]) -> List[Notification]:
        """
        Process DUNS export file (one DUNS per line)
        
        Args:
            export_file: Path to export file
            headers: Header metadata
            
        Returns:
            List of notifications
        """
        notifications = []
        
        try:
            with export_file.open('r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    duns = line.strip()
                    
                    if len(duns) == 9 and duns.isdigit():
                        organization = Organization(duns=duns)
                        
                        # Create export notification element
                        export_data = {
                            'duns': duns,
                            'source_file': str(export_file),
                            'export_type': 'DUNS_LIST'
                        }
                        
                        element = NotificationElement(
                            element="organization.export",
                            current=export_data,
                            timestamp=datetime.utcnow()
                        )
                        
                        notification = Notification(
                            type=NotificationType.SEED,  # Export files often contain seed data
                            organization=organization,
                            elements=[element],
                            deliveryTimeStamp=datetime.utcnow()
                        )
                        
                        notifications.append(notification)
        
        except Exception as e:
            logger.error("Failed to process DUNS export file", file=str(export_file), error=str(e))
            raise
        
        return notifications
    
    def _process_zip_archive(self, zip_file: Path, headers: Dict[str, Any]) -> List[Notification]:
        """
        Process ZIP archive containing notification files
        
        Args:
            zip_file: Path to ZIP file
            headers: Header metadata
            
        Returns:
            List of notifications
        """
        notifications = []
        
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                # Extract to temporary directory
                temp_dir = self.input_path / f"temp_{zip_file.stem}"
                temp_dir.mkdir(exist_ok=True)
                
                try:
                    zip_ref.extractall(temp_dir)
                    
                    # Process extracted files
                    for extracted_file in temp_dir.iterdir():
                        if extracted_file.is_file():
                            if extracted_file.suffix.lower() == '.json':
                                # Process as header file
                                header_data = self._parse_header_file(extracted_file)
                                headers[extracted_file.stem] = header_data
                            elif extracted_file.suffix.lower() == '.txt':
                                # Determine file type and process accordingly
                                if 'seedfile' in extracted_file.name.lower():
                                    file_notifications = self._process_seedfile(extracted_file, headers)
                                elif 'exception' in extracted_file.name.lower():
                                    file_notifications = self._process_exception_file(extracted_file, headers)
                                elif 'export' in extracted_file.name.lower():
                                    file_notifications = self._process_duns_export_file(extracted_file, headers)
                                else:
                                    # Try to process as generic text file
                                    file_notifications = self._process_duns_export_file(extracted_file, headers)
                                
                                notifications.extend(file_notifications)
                
                finally:
                    # Cleanup temporary directory
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
        
        except Exception as e:
            logger.error("Failed to process ZIP archive", file=str(zip_file), error=str(e))
            raise
        
        return notifications
    
    def _archive_files(self, files_to_archive: List[Path]):
        """
        Archive processed files
        
        Args:
            files_to_archive: List of file paths to archive
        """
        if not self.archive_path:
            return
        
        archived_count = 0
        
        for file_path in files_to_archive:
            try:
                # Create date-based subdirectory
                date_dir = self.archive_path / datetime.now().strftime('%Y-%m-%d')
                date_dir.mkdir(exist_ok=True)
                
                # Move file to archive
                archive_file_path = date_dir / file_path.name
                file_path.rename(archive_file_path)
                archived_count += 1
                
                logger.debug("File archived", 
                           original=str(file_path),
                           archived=str(archive_file_path))
            
            except Exception as e:
                logger.error("Failed to archive file", 
                           file=str(file_path), 
                           error=str(e))
        
        if archived_count > 0:
            logger.info("Files archived", count=archived_count)


def create_local_file_input_processor(config: LocalFileInputConfig) -> LocalFileInputProcessor:
    """
    Factory function to create local file input processor
    
    Args:
        config: Local file input configuration
        
    Returns:
        Configured local file input processor
    """
    return LocalFileInputProcessor(config)
