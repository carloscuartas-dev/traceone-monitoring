"""
Data models for D&B monitoring notifications
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator
from uuid import UUID, uuid4


class NotificationType(str, Enum):
    """Types of notifications from D&B monitoring"""
    UPDATE = "UPDATE"
    DELETE = "DELETE" 
    TRANSFER = "TRANSFER"
    SEED = "SEED"
    UNDELETE = "UNDELETE"
    REVIEWED = "REVIEWED"
    UNDER_REVIEW = "UNDER_REVIEW"
    EXIT = "EXIT"
    REMOVED = "REMOVED"


class NotificationElement(BaseModel):
    """Individual data element change within a notification"""
    element: str = Field(..., description="JSON path of the changed element")
    previous: Optional[Any] = Field(default=None, description="Previous value")
    current: Optional[Any] = Field(default=None, description="Current value")
    timestamp: datetime = Field(..., description="Timestamp of the change")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z' if v.tzinfo is None else v.isoformat()
        }


class Organization(BaseModel):
    """Organization information in notification"""
    duns: str = Field(..., description="DUNS number")
    
    @validator('duns')
    def validate_duns(cls, v):
        if not v or len(v) != 9 or not v.isdigit():
            raise ValueError('DUNS must be a 9-digit number')
        return v


class TransactionDetail(BaseModel):
    """Transaction metadata"""
    transaction_id: str = Field(..., alias="transactionID")
    transaction_timestamp: datetime = Field(..., alias="transactionTimestamp")
    in_language: str = Field(default="en-US", alias="inLanguage")
    
    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z' if v.tzinfo is None else v.isoformat()
        }


class InquiryDetail(BaseModel):
    """Inquiry metadata"""
    reference: str = Field(..., description="Registration reference")


class Notification(BaseModel):
    """D&B monitoring notification"""
    id: UUID = Field(default_factory=uuid4, description="Internal notification ID")
    type: NotificationType = Field(..., description="Type of notification")
    organization: Organization = Field(..., description="Organization information")
    elements: List[NotificationElement] = Field(default_factory=list, description="Changed elements")
    delivery_timestamp: datetime = Field(..., alias="deliveryTimeStamp", description="Delivery timestamp")
    
    # Internal processing fields
    processed: bool = Field(default=False, description="Whether notification has been processed")
    processing_timestamp: Optional[datetime] = Field(default=None, description="When notification was processed")
    error_count: int = Field(default=0, description="Number of processing errors")
    last_error: Optional[str] = Field(default=None, description="Last processing error message")
    
    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z' if v.tzinfo is None else v.isoformat()
        }
    
    @property
    def duns(self) -> str:
        """Get DUNS number from organization"""
        return self.organization.duns
    
    def mark_processed(self):
        """Mark notification as processed"""
        self.processed = True
        self.processing_timestamp = datetime.utcnow()
    
    def mark_error(self, error_message: str):
        """Mark notification processing error"""
        self.error_count += 1
        self.last_error = error_message
    
    def is_retriable(self, max_retries: int = 3) -> bool:
        """Check if notification can be retried"""
        return self.error_count < max_retries and not self.processed


class NotificationResponse(BaseModel):
    """Response from D&B Pull API"""
    transaction_detail: TransactionDetail = Field(..., alias="transactionDetail")
    inquiry_detail: InquiryDetail = Field(..., alias="inquiryDetail")
    notifications: List[Notification] = Field(default_factory=list)
    
    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z' if v.tzinfo is None else v.isoformat()
        }
    
    @property
    def registration_reference(self) -> str:
        """Get registration reference"""
        return self.inquiry_detail.reference
    
    @property
    def has_notifications(self) -> bool:
        """Check if response has notifications"""
        return len(self.notifications) > 0
    
    def get_last_timestamp(self) -> Optional[datetime]:
        """Get the timestamp of the last notification for replay purposes"""
        if not self.notifications:
            return None
        
        # Return the latest delivery timestamp
        timestamps = [n.delivery_timestamp for n in self.notifications]
        return max(timestamps)


class NotificationBatch(BaseModel):
    """Batch of notifications for processing"""
    id: UUID = Field(default_factory=uuid4)
    registration_id: str = Field(..., description="Registration ID")
    notifications: List[Notification] = Field(..., description="Notifications in batch")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = Field(default=None)
    
    @property
    def size(self) -> int:
        """Get batch size"""
        return len(self.notifications)
    
    @property
    def duns_count(self) -> int:
        """Get unique DUNS count in batch"""
        return len(set(n.duns for n in self.notifications))
    
    def get_notifications_by_duns(self) -> Dict[str, List[Notification]]:
        """Group notifications by DUNS"""
        duns_notifications = {}
        for notification in self.notifications:
            duns = notification.duns
            if duns not in duns_notifications:
                duns_notifications[duns] = []
            duns_notifications[duns].append(notification)
        return duns_notifications
    
    def mark_processed(self):
        """Mark entire batch as processed"""
        self.processed_at = datetime.utcnow()
        for notification in self.notifications:
            notification.mark_processed()


class NotificationStats(BaseModel):
    """Statistics for notification processing"""
    total_notifications: int = 0
    processed_notifications: int = 0
    failed_notifications: int = 0
    unique_duns: int = 0
    notification_types: Dict[str, int] = Field(default_factory=dict)
    processing_start_time: Optional[datetime] = None
    processing_end_time: Optional[datetime] = None
    
    @property
    def processing_duration(self) -> Optional[float]:
        """Get processing duration in seconds"""
        if self.processing_start_time and self.processing_end_time:
            return (self.processing_end_time - self.processing_start_time).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """Get success rate as percentage"""
        if self.total_notifications == 0:
            return 0.0
        return (self.processed_notifications / self.total_notifications) * 100
    
    def add_notification(self, notification: Notification):
        """Add notification to statistics"""
        self.total_notifications += 1
        
        # Count by type
        notification_type = notification.type.value
        if notification_type not in self.notification_types:
            self.notification_types[notification_type] = 0
        self.notification_types[notification_type] += 1
        
        # Update processed count
        if notification.processed:
            self.processed_notifications += 1
        elif notification.error_count > 0:
            self.failed_notifications += 1
