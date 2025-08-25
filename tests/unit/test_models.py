"""
Unit tests for data models
"""

import pytest
from datetime import datetime
from uuid import UUID

from traceone_monitoring.models.notification import (
    Notification,
    NotificationElement,
    NotificationType,
    Organization,
    NotificationResponse,
    TransactionDetail,
    InquiryDetail
)
from traceone_monitoring.models.registration import (
    Registration,
    RegistrationConfig,
    RegistrationStatus,
    DeliveryTrigger,
    NotificationMode
)


class TestNotificationModels:
    """Test cases for notification models"""
    
    def test_notification_element_creation(self):
        """Test notification element creation"""
        element = NotificationElement(
            element="organization.primaryName",
            previous="Old Company Name",
            current="New Company Name",
            timestamp=datetime.utcnow()
        )
        
        assert element.element == "organization.primaryName"
        assert element.previous == "Old Company Name"
        assert element.current == "New Company Name"
        assert isinstance(element.timestamp, datetime)
    
    def test_organization_validation(self):
        """Test organization DUNS validation"""
        # Valid DUNS
        org = Organization(duns="123456789")
        assert org.duns == "123456789"
        
        # Invalid DUNS - too short
        with pytest.raises(ValueError):
            Organization(duns="12345")
        
        # Invalid DUNS - non-numeric
        with pytest.raises(ValueError):
            Organization(duns="12345678A")
        
        # Invalid DUNS - empty
        with pytest.raises(ValueError):
            Organization(duns="")
    
    def test_notification_creation(self):
        """Test notification creation and methods"""
        org = Organization(duns="123456789")
        element = NotificationElement(
            element="organization.primaryName",
            previous="Old Name",
            current="New Name",
            timestamp=datetime.utcnow()
        )
        
        notification = Notification(
            type=NotificationType.UPDATE,
            organization=org,
            elements=[element],
            delivery_timestamp=datetime.utcnow()
        )
        
        assert notification.type == NotificationType.UPDATE
        assert notification.duns == "123456789"
        assert len(notification.elements) == 1
        assert not notification.processed
        assert notification.error_count == 0
    
    def test_notification_processing_methods(self):
        """Test notification processing methods"""
        notification = Notification(
            type=NotificationType.UPDATE,
            organization=Organization(duns="123456789"),
            elements=[],
            delivery_timestamp=datetime.utcnow()
        )
        
        # Test mark_processed
        notification.mark_processed()
        assert notification.processed
        assert notification.processing_timestamp is not None
        
        # Test mark_error
        notification.mark_error("Test error")
        assert notification.error_count == 1
        assert notification.last_error == "Test error"
        
        # Test is_retriable
        assert not notification.is_retriable()  # Processed notifications are not retriable
        
        # Test retriable notification
        notification2 = Notification(
            type=NotificationType.UPDATE,
            organization=Organization(duns="987654321"),
            elements=[],
            delivery_timestamp=datetime.utcnow()
        )
        notification2.mark_error("Error 1")
        assert notification2.is_retriable()
        
        notification2.mark_error("Error 2")
        notification2.mark_error("Error 3")
        assert not notification2.is_retriable()  # Too many errors
    
    def test_notification_response_parsing(self):
        """Test notification response parsing from API"""
        response_data = {
            "transactionDetail": {
                "transactionID": "test-transaction-123",
                "transactionTimestamp": "2025-08-25T18:00:00Z",
                "inLanguage": "en-US"
            },
            "inquiryDetail": {
                "reference": "TestRegistration"
            },
            "notifications": [
                {
                    "type": "UPDATE",
                    "organization": {
                        "duns": "123456789"
                    },
                    "elements": [
                        {
                            "element": "organization.primaryName",
                            "previous": "Old Name",
                            "current": "New Name",
                            "timestamp": "2025-08-25T17:00:00Z"
                        }
                    ],
                    "deliveryTimeStamp": "2025-08-25T18:00:00Z"
                }
            ]
        }
        
        response = NotificationResponse(**response_data)
        
        assert response.registration_reference == "TestRegistration"
        assert response.has_notifications
        assert len(response.notifications) == 1
        
        notification = response.notifications[0]
        assert notification.type == NotificationType.UPDATE
        assert notification.duns == "123456789"
        assert len(notification.elements) == 1


class TestRegistrationModels:
    """Test cases for registration models"""
    
    def test_registration_config_creation(self):
        """Test registration configuration creation"""
        config = RegistrationConfig(
            reference="TestRegistration",
            description="Test registration",
            duns_list=["123456789", "987654321"],
            data_blocks=["companyinfo_L2_v1"],
            json_path_inclusion=["organization.primaryName"]
        )
        
        assert config.reference == "TestRegistration"
        assert len(config.duns_list) == 2
        assert len(config.data_blocks) == 1
        assert config.notification_type == NotificationMode.UPDATE
        assert config.delivery_trigger == DeliveryTrigger.API_PULL
    
    def test_registration_config_validation(self):
        """Test registration configuration validation"""
        # Valid reference
        config = RegistrationConfig(
            reference="Valid_Reference-123",
            duns_list=["123456789"],
            data_blocks=["companyinfo_L2_v1"]
        )
        assert config.reference == "Valid_Reference-123"
        
        # Invalid reference - too short
        with pytest.raises(ValueError):
            RegistrationConfig(
                reference="ab",
                duns_list=["123456789"],
                data_blocks=["companyinfo_L2_v1"]
            )
        
        # Invalid reference - special characters
        with pytest.raises(ValueError):
            RegistrationConfig(
                reference="Invalid@Reference",
                duns_list=["123456789"],
                data_blocks=["companyinfo_L2_v1"]
            )
        
        # Invalid DUNS
        with pytest.raises(ValueError):
            RegistrationConfig(
                reference="TestRef",
                duns_list=["12345"],  # Too short
                data_blocks=["companyinfo_L2_v1"]
            )
        
        # No data blocks
        with pytest.raises(ValueError):
            RegistrationConfig(
                reference="TestRef",
                duns_list=["123456789"],
                data_blocks=[]
            )
    
    def test_registration_lifecycle(self):
        """Test registration lifecycle methods"""
        config = RegistrationConfig(
            reference="TestRegistration",
            duns_list=["123456789"],
            data_blocks=["companyinfo_L2_v1"]
        )
        
        registration = Registration(
            reference="TestRegistration",
            config=config
        )
        
        # Initial state
        assert registration.status == RegistrationStatus.PENDING
        assert not registration.is_active
        assert registration.activated_at is None
        
        # Activate registration
        registration.activate()
        assert registration.status == RegistrationStatus.ACTIVE
        assert registration.is_active
        assert registration.activated_at is not None
        
        # Suspend registration
        registration.suspend("Test suspension")
        assert registration.status == RegistrationStatus.SUSPENDED
        assert not registration.is_active
        assert registration.last_error == "Test suspension"
    
    def test_registration_statistics(self):
        """Test registration statistics tracking"""
        config = RegistrationConfig(
            reference="TestRegistration",
            duns_list=["123456789"],
            data_blocks=["companyinfo_L2_v1"]
        )
        
        registration = Registration(
            reference="TestRegistration",
            config=config
        )
        
        # Update statistics
        registration.update_notification_stats(10, 8)
        
        assert registration.total_notifications_received == 10
        assert registration.total_notifications_processed == 8
        assert registration.processing_success_rate == 80.0
        
        # Record error
        registration.record_error("Test error")
        assert registration.error_count == 1
        assert registration.last_error == "Test error"
        assert registration.last_error_timestamp is not None
