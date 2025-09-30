"""
Example test demonstrating how to work with DUNS lists in the TraceOne monitoring system.

This test shows practical patterns for:
1. Creating test data with DUNS numbers
2. Testing registration with multiple DUNS
3. Testing notification processing for DUNS
4. Mocking API responses with DUNS data
5. Testing bulk operations with DUNS lists
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from traceone_monitoring.services.monitoring_service import DNBMonitoringService
from traceone_monitoring.models.registration import RegistrationConfig, Registration, RegistrationStatus
from traceone_monitoring.models.notification import (
    Notification,
    NotificationElement, 
    NotificationType,
    Organization,
    NotificationResponse
)


class TestDunsListOperations:
    """Test class demonstrating DUNS list operations"""
    
    @pytest.fixture
    def sample_duns_list(self):
        """Sample DUNS numbers for testing"""
        return [
            "123456789",  # Apple Inc.
            "987654321",  # Microsoft Corporation  
            "456789123",  # Amazon.com Inc.
            "789123456",  # Alphabet Inc.
            "321654987"   # Meta Platforms Inc.
        ]
    
    @pytest.fixture
    def registration_config_with_duns(self, sample_duns_list):
        """Create registration configuration with DUNS list"""
        return RegistrationConfig(
            reference="TestPortfolioMonitoring",
            description="Portfolio monitoring for major tech companies",
            duns_list=sample_duns_list,
            dataBlocks=["companyinfo_L2_v1", "principalscontacts_L1_v1", "financialstrength_L1_v1"],
            jsonPathInclusion=[
                "organization.primaryName",
                "organization.registeredAddress",
                "organization.telephone",
                "organization.websiteAddress",
                "organization.numberOfEmployees"
            ]
        )
    
    @pytest.fixture
    def sample_notifications_for_duns(self, sample_duns_list):
        """Create sample notifications for different DUNS"""
        notifications = []
        
        # Notification for Apple Inc. - Name change
        apple_notification = Notification(
            type=NotificationType.UPDATE,
            organization=Organization(duns=sample_duns_list[0]),
            elements=[
                NotificationElement(
                    element="organization.primaryName",
                    previous="Apple Computer Inc.",
                    current="Apple Inc.",
                    timestamp=datetime.utcnow()
                )
            ],
            deliveryTimeStamp=datetime.utcnow()
        )
        
        # Notification for Microsoft - Address change
        microsoft_notification = Notification(
            type=NotificationType.UPDATE,
            organization=Organization(duns=sample_duns_list[1]),
            elements=[
                NotificationElement(
                    element="organization.registeredAddress.streetAddress",
                    previous="One Microsoft Way",
                    current="1 Microsoft Way", 
                    timestamp=datetime.utcnow()
                )
            ],
            deliveryTimeStamp=datetime.utcnow()
        )
        
        # Notification for Amazon - Employee count change
        amazon_notification = Notification(
            type=NotificationType.UPDATE,
            organization=Organization(duns=sample_duns_list[2]),
            elements=[
                NotificationElement(
                    element="organization.numberOfEmployees",
                    previous="1540000",
                    current="1550000",
                    timestamp=datetime.utcnow()
                )
            ],
            deliveryTimeStamp=datetime.utcnow()
        )
        
        notifications.extend([apple_notification, microsoft_notification, amazon_notification])
        return notifications
    
    def test_registration_with_duns_list(self, registration_config_with_duns):
        """Test creating a registration with multiple DUNS numbers"""
        
        # Verify the registration config contains our DUNS list
        assert len(registration_config_with_duns.duns_list) == 5
        assert "123456789" in registration_config_with_duns.duns_list
        assert "987654321" in registration_config_with_duns.duns_list
        
        # Verify all DUNS are valid format (9 digits)
        for duns in registration_config_with_duns.duns_list:
            assert len(duns) == 9
            assert duns.isdigit()
    
    def test_add_duns_to_existing_registration(self, registration_config_with_duns):
        """Test adding new DUNS to an existing registration"""
        original_count = len(registration_config_with_duns.duns_list)
        
        # New DUNS to add
        new_duns_list = ["111222333", "444555666"]
        
        # Add new DUNS to existing list
        updated_duns_list = registration_config_with_duns.duns_list + new_duns_list
        
        # Create updated config
        updated_config = RegistrationConfig(
            reference=registration_config_with_duns.reference,
            description=registration_config_with_duns.description,
            duns_list=updated_duns_list,
            dataBlocks=registration_config_with_duns.data_blocks,
            jsonPathInclusion=registration_config_with_duns.json_path_inclusion
        )
        
        # Verify the DUNS were added
        assert len(updated_config.duns_list) == original_count + 2
        assert "111222333" in updated_config.duns_list
        assert "444555666" in updated_config.duns_list
    
    def test_notification_processing_by_duns(self, sample_notifications_for_duns, sample_duns_list):
        """Test processing notifications and filtering by DUNS"""
        
        # Group notifications by DUNS
        notifications_by_duns = {}
        for notification in sample_notifications_for_duns:
            duns = notification.organization.duns
            if duns not in notifications_by_duns:
                notifications_by_duns[duns] = []
            notifications_by_duns[duns].append(notification)
        
        # Verify we have notifications for expected DUNS
        assert sample_duns_list[0] in notifications_by_duns  # Apple
        assert sample_duns_list[1] in notifications_by_duns  # Microsoft  
        assert sample_duns_list[2] in notifications_by_duns  # Amazon
        
        # Test filtering notifications for specific DUNS
        apple_duns = sample_duns_list[0]
        apple_notifications = [n for n in sample_notifications_for_duns 
                              if n.organization.duns == apple_duns]
        
        assert len(apple_notifications) == 1
        assert apple_notifications[0].elements[0].element == "organization.primaryName"
    
    @pytest.mark.asyncio
    async def test_bulk_monitoring_setup(self, sample_duns_list, app_config):
        """Test setting up monitoring for multiple DUNS at once"""
        
        # Mock the monitoring service
        with patch('traceone_monitoring.services.monitoring_service.DNBMonitoringService') as MockService:
            mock_service = MockService.return_value
            mock_service.add_duns_to_monitoring = AsyncMock(return_value=True)
            mock_service.activate_monitoring = AsyncMock(return_value=True)
            
            service = mock_service
            
            # Test adding multiple DUNS to monitoring
            registration_ref = "BulkPortfolioTest"
            
            # Add DUNS in batches (simulating bulk operation)
            batch_size = 2
            for i in range(0, len(sample_duns_list), batch_size):
                batch = sample_duns_list[i:i + batch_size]
                await service.add_duns_to_monitoring(
                    registration_reference=registration_ref,
                    duns_list=batch,
                    batch_mode=True
                )
            
            # Verify the service was called with the expected DUNS
            assert mock_service.add_duns_to_monitoring.call_count == 3  # 5 DUNS, batch size 2
            
            # Activate monitoring for all
            await service.activate_monitoring(registration_ref)
            mock_service.activate_monitoring.assert_called_once_with(registration_ref)
    
    def test_mock_api_response_with_duns_data(self, sample_duns_list):
        """Test mocking D&B API responses with DUNS data"""
        
        # Mock API response for pull notifications
        mock_api_response = {
            "transactionDetail": {
                "transactionID": "test-123",
                "transactionTimestamp": "2025-09-23T13:00:00Z",
                "inLanguage": "en-US"
            },
            "inquiryDetail": {
                "reference": "TestPortfolioMonitoring"
            },
            "notifications": []
        }
        
        # Add notifications for each DUNS in our test list
        for i, duns in enumerate(sample_duns_list):
            notification_data = {
                "type": "UPDATE",
                "organization": {"duns": duns},
                "elements": [
                    {
                        "element": "organization.primaryName",
                        "previous": f"Old Company Name {i+1}",
                        "current": f"New Company Name {i+1}",
                        "timestamp": "2025-09-23T12:00:00Z"
                    }
                ],
                "deliveryTimeStamp": "2025-09-23T13:00:00Z"
            }
            mock_api_response["notifications"].append(notification_data)
        
        # Verify the mock response contains all our DUNS
        response_duns = [n["organization"]["duns"] for n in mock_api_response["notifications"]]
        for duns in sample_duns_list:
            assert duns in response_duns
    
    def test_duns_validation(self):
        """Test DUNS number validation"""
        
        # Valid DUNS examples
        valid_duns = ["123456789", "000000001", "999999999"]
        
        for duns in valid_duns:
            assert len(duns) == 9
            assert duns.isdigit()
        
        # Invalid DUNS examples
        invalid_duns = [
            "12345678",    # Too short
            "1234567890",  # Too long
            "12345678A",   # Contains letters
            "",            # Empty
            "000000000"    # All zeros (typically invalid)
        ]
        
        for duns in invalid_duns:
            if duns == "000000000":
                # This might be valid in some systems, check your business rules
                continue
            
            # These should fail validation
            assert not (len(duns) == 9 and duns.isdigit() and duns != "000000000")
    
    @pytest.mark.asyncio
    async def test_continuous_monitoring_with_duns_filter(self, sample_duns_list):
        """Test continuous monitoring with DUNS filtering"""
        
        # Mock the monitoring service for continuous monitoring
        with patch('traceone_monitoring.services.monitoring_service.DNBMonitoringService') as MockService:
            mock_service = MockService.return_value
            
            # Mock continuous monitoring generator
            async def mock_continuous_monitoring(registration_ref):
                """Mock async generator for continuous monitoring"""
                for duns in sample_duns_list:
                    # Simulate notifications coming in over time
                    notification = Notification(
                        type=NotificationType.UPDATE,
                        organization=Organization(duns=duns),
                        elements=[
                            NotificationElement(
                                element="organization.primaryName",
                                previous=f"Old Name for {duns}",
                                current=f"New Name for {duns}",
                                timestamp=datetime.utcnow()
                            )
                        ],
                        deliveryTimeStamp=datetime.utcnow()
                    )
                    yield [notification]  # Yield as batch
            
            mock_service.monitor_continuously = mock_continuous_monitoring
            
            # Test continuous monitoring
            service = mock_service
            collected_notifications = []
            
            async for notification_batch in service.monitor_continuously("TestPortfolio"):
                collected_notifications.extend(notification_batch)
                
                # Stop after collecting notifications for all DUNS
                if len(collected_notifications) >= len(sample_duns_list):
                    break
            
            # Verify we received notifications for all DUNS
            received_duns = {n.organization.duns for n in collected_notifications}
            expected_duns = set(sample_duns_list)
            
            assert received_duns == expected_duns


def test_practical_duns_workflow():
    """
    Practical example showing a complete DUNS monitoring workflow
    """
    
    # Step 1: Define your DUNS list (real companies for example)
    tech_companies_duns = [
        "804735132",  # Apple Inc. (example DUNS)
        "069032677",  # Microsoft Corporation (example DUNS)  
        "006273905",  # Amazon.com Inc. (example DUNS)
        "804735052",  # Alphabet Inc. (example DUNS)
        "042112940"   # Meta Platforms Inc. (example DUNS)
    ]
    
    # Step 2: Create registration configuration
    config = RegistrationConfig(
        reference="TechPortfolioQ4_2025",
        description="Technology portfolio monitoring for Q4 2025",
        duns_list=tech_companies_duns,
        dataBlocks=[
            "companyinfo_L2_v1",      # Basic company information
            "principalscontacts_L1_v1", # Key contacts
            "financialstrength_L1_v1"   # Financial indicators
        ],
        jsonPathInclusion=[
            "organization.primaryName",
            "organization.registeredAddress",
            "organization.telephone", 
            "organization.websiteAddress",
            "organization.numberOfEmployees",
            "organization.annualSalesRevenue"
        ]
    )
    
    # Step 3: Validate the configuration
    assert len(config.duns_list) == 5
    assert config.reference == "TechPortfolioQ4_2025"
    assert "companyinfo_L2_v1" in config.data_blocks
    
    # Step 4: Test notification handling for specific DUNS
    apple_duns = tech_companies_duns[0]
    
    sample_notification = Notification(
        type=NotificationType.UPDATE,
        organization=Organization(duns=apple_duns),
        elements=[
            NotificationElement(
                element="organization.numberOfEmployees",
                previous="164000",
                current="165000",
                timestamp=datetime.utcnow()
            )
        ],
        deliveryTimeStamp=datetime.utcnow()
    )
    
    # Verify notification structure
    assert sample_notification.organization.duns == apple_duns
    assert sample_notification.type == NotificationType.UPDATE
    assert len(sample_notification.elements) == 1
    
    print("✅ DUNS workflow test completed successfully!")
    print(f"   Monitoring {len(tech_companies_duns)} companies")
    print(f"   Tracking {len(config.json_path_inclusion)} data points")
    print(f"   Using {len(config.data_blocks)} data blocks")


if __name__ == "__main__":
    # Run the practical workflow test
    test_practical_duns_workflow()
    print("\n🚀 Ready to run with pytest:")
    print("   pytest test_duns_example.py -v")
