"""
Data models for D&B monitoring registrations
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator
from uuid import UUID, uuid4


class DeliveryTrigger(str, Enum):
    """Delivery trigger types"""
    API_PULL = "API_PULL"
    FTP_PUSH = "FTP_PUSH"


class NotificationMode(str, Enum):
    """Notification modes"""
    UPDATE = "UPDATE"
    FULL_PRODUCT = "FULL_PRODUCT"


class RegistrationStatus(str, Enum):
    """Registration status"""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DELETED = "DELETED"


class RegistrationConfig(BaseModel):
    """Configuration for creating a D&B monitoring registration"""
    reference: str = Field(..., description="Unique registration reference")
    description: Optional[str] = Field(default=None, description="Registration description")
    
    # Monitoring scope
    lod: str = Field(default="duns_list", description="List of DUNS (LOD)")
    duns_list: List[str] = Field(default_factory=list, description="Initial DUNS to monitor")
    
    # Data configuration
    data_blocks: List[str] = Field(..., alias="dataBlocks", description="DataBlocks to monitor")
    seed_data: bool = Field(default=False, alias="seedData", description="Generate SEED file")
    
    # Notification configuration
    notification_type: NotificationMode = Field(default=NotificationMode.UPDATE, alias="notificationType")
    delivery_trigger: DeliveryTrigger = Field(default=DeliveryTrigger.API_PULL, alias="deliveryTrigger")
    
    # Filtering
    json_path_inclusion: Optional[List[str]] = Field(default=None, alias="jsonPathInclusion")
    json_path_exclusion: Optional[List[str]] = Field(default=None, alias="jsonPathExclusion")
    
    # Contact information
    email_addresses: Optional[List[str]] = Field(default=None, description="Notification email addresses")
    
    class Config:
        allow_population_by_field_name = True
    
    @validator('reference')
    def validate_reference(cls, v):
        if not v or len(v) < 3 or len(v) > 50:
            raise ValueError('Reference must be between 3 and 50 characters')
        # Only allow alphanumeric, underscore, and hyphen
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Reference can only contain alphanumeric characters, underscores, and hyphens')
        return v
    
    @validator('duns_list')
    def validate_duns_list(cls, v):
        for duns in v:
            if not duns or len(duns) != 9 or not duns.isdigit():
                raise ValueError(f'Invalid DUNS number: {duns}. DUNS must be a 9-digit number')
        return v
    
    @validator('data_blocks')
    def validate_data_blocks(cls, v):
        if not v:
            raise ValueError('At least one DataBlock must be specified')
        return v
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API calls"""
        return self.dict(by_alias=True, exclude_none=True)


class Registration(BaseModel):
    """D&B monitoring registration"""
    id: UUID = Field(default_factory=uuid4, description="Internal registration ID")
    reference: str = Field(..., description="D&B registration reference")
    status: RegistrationStatus = Field(default=RegistrationStatus.PENDING)
    
    # Configuration
    config: RegistrationConfig = Field(..., description="Registration configuration")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    activated_at: Optional[datetime] = Field(default=None)
    last_pull_timestamp: Optional[datetime] = Field(default=None)
    
    # Statistics
    total_duns_monitored: int = Field(default=0)
    total_notifications_received: int = Field(default=0)
    total_notifications_processed: int = Field(default=0)
    last_notification_timestamp: Optional[datetime] = Field(default=None)
    
    # Error tracking
    error_count: int = Field(default=0)
    last_error: Optional[str] = Field(default=None)
    last_error_timestamp: Optional[datetime] = Field(default=None)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z' if v.tzinfo is None else v.isoformat()
        }
    
    def activate(self):
        """Activate the registration"""
        self.status = RegistrationStatus.ACTIVE
        self.activated_at = datetime.utcnow()
    
    def suspend(self, reason: Optional[str] = None):
        """Suspend the registration"""
        self.status = RegistrationStatus.SUSPENDED
        if reason:
            self.last_error = reason
            self.last_error_timestamp = datetime.utcnow()
    
    def update_pull_timestamp(self, timestamp: datetime):
        """Update last pull timestamp"""
        self.last_pull_timestamp = timestamp
    
    def update_notification_stats(self, notification_count: int, processed_count: int):
        """Update notification statistics"""
        self.total_notifications_received += notification_count
        self.total_notifications_processed += processed_count
        self.last_notification_timestamp = datetime.utcnow()
    
    def record_error(self, error_message: str):
        """Record an error"""
        self.error_count += 1
        self.last_error = error_message
        self.last_error_timestamp = datetime.utcnow()
    
    @property
    def is_active(self) -> bool:
        """Check if registration is active"""
        return self.status == RegistrationStatus.ACTIVE
    
    @property
    def processing_success_rate(self) -> float:
        """Get notification processing success rate"""
        if self.total_notifications_received == 0:
            return 0.0
        return (self.total_notifications_processed / self.total_notifications_received) * 100


class RegistrationSummary(BaseModel):
    """Summary information about a registration"""
    id: UUID
    reference: str
    status: RegistrationStatus
    total_duns_monitored: int
    total_notifications_received: int
    created_at: datetime
    activated_at: Optional[datetime]
    last_pull_timestamp: Optional[datetime]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z' if v.tzinfo is None else v.isoformat()
        }


class DunsSubject(BaseModel):
    """DUNS subject in monitoring registration"""
    duns: str = Field(..., description="DUNS number")
    added_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="ACTIVE", description="Monitoring status")
    
    @validator('duns')
    def validate_duns(cls, v):
        if not v or len(v) != 9 or not v.isdigit():
            raise ValueError('DUNS must be a 9-digit number')
        return v


class RegistrationOperation(BaseModel):
    """Operation performed on a registration"""
    id: UUID = Field(default_factory=uuid4)
    registration_id: UUID = Field(..., description="Registration ID")
    operation_type: str = Field(..., description="Type of operation")
    duns_affected: List[str] = Field(default_factory=list, description="DUNS affected by operation")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool = Field(default=True, description="Operation success status")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z' if v.tzinfo is None else v.isoformat()
        }
