"""
Pytest configuration and shared fixtures for TraceOne monitoring tests
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, AsyncMock
from typing import Dict, List, Any
import tempfile
import os
import yaml

from traceone_monitoring.utils.config import (
    AppConfig,
    DNBApiConfig,
    MonitoringConfig,
    LoggingConfig
)
from traceone_monitoring.auth.authenticator import DNBAuthenticator
from traceone_monitoring.api.client import DNBApiClient
from traceone_monitoring.api.pull_client import PullApiClient
from traceone_monitoring.services.registration_service import RegistrationManager
from traceone_monitoring.services.monitoring_service import DNBMonitoringService
from traceone_monitoring.models.notification import (
    Notification,
    NotificationElement,
    NotificationType,
    Organization,
    NotificationResponse
)
from traceone_monitoring.models.registration import (
    Registration,
    RegistrationConfig,
    RegistrationStatus
)


# Pytest configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Configuration fixtures
@pytest.fixture
def dnb_api_config():
    """Create test D&B API configuration"""
    return DNBApiConfig(
        client_id="test_client_id",
        client_secret="test_client_secret",
        base_url="https://plus.dnb.com",
        rate_limit=5.0,
        timeout=30,
        retry_attempts=3,
        backoff_factor=2.0
    )


@pytest.fixture
def monitoring_config():
    """Create test monitoring configuration"""
    return MonitoringConfig(
        polling_interval=60,
        max_notifications=100,
        notification_batch_size=50,
        retry_attempts=3,
        retry_delay=5,
        health_check_interval=300
    )


@pytest.fixture
def logging_config():
    """Create test logging configuration"""
    return LoggingConfig(
        level="INFO",
        format="json",
        enable_structlog=True,
        log_requests=False,
        log_responses=False
    )


@pytest.fixture
def database_config():
    """Create test database configuration"""
    from traceone_monitoring.utils.config import DatabaseConfig
    return DatabaseConfig(
        url="sqlite:///test.db",
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600
    )

@pytest.fixture
def app_config(dnb_api_config, database_config, monitoring_config, logging_config):
    """Create complete application configuration"""
    return AppConfig(
        environment="test",
        debug=True,
        dnb_api=dnb_api_config,
        database=database_config,
        monitoring=monitoring_config,
        logging=logging_config
    )


@pytest.fixture
def temp_config_file(app_config):
    """Create temporary configuration file"""
    config_data = {
        "environment": app_config.environment,
        "debug": app_config.debug,
        "traceone_api": {
            "api_key": app_config.traceone_api.api_key,
            "api_secret": app_config.traceone_api.api_secret,
            "base_url": app_config.traceone_api.base_url,
            "rate_limit": app_config.traceone_api.rate_limit,
            "timeout": app_config.traceone_api.timeout,
            "retry_attempts": app_config.traceone_api.retry_attempts,
            "backoff_factor": app_config.traceone_api.backoff_factor
        },
        "monitoring": {
            "polling_interval": app_config.monitoring.polling_interval,
            "max_notifications": app_config.monitoring.max_notifications,
            "notification_batch_size": app_config.monitoring.notification_batch_size,
            "retry_attempts": app_config.monitoring.retry_attempts,
            "retry_delay": app_config.monitoring.retry_delay,
            "health_check_interval": app_config.monitoring.health_check_interval
        },
        "logging": {
            "level": app_config.logging.level,
            "format": app_config.logging.format,
            "enable_structlog": app_config.logging.enable_structlog
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    os.unlink(temp_path)


# Mock fixtures
@pytest.fixture
def mock_session():
    """Create mock HTTP session"""
    session = Mock()
    session.post = Mock()
    session.get = Mock()
    session.put = Mock()
    session.delete = Mock()
    session.close = Mock()
    return session


@pytest.fixture
def mock_successful_auth_response():
    """Mock successful authentication response"""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "access_token": "test_token_12345",
        "expires_in": 3600,
        "token_type": "Bearer"
    }
    return response


@pytest.fixture
def mock_failed_auth_response():
    """Mock failed authentication response"""
    response = Mock()
    response.status_code = 401
    response.json.return_value = {
        "error": "invalid_credentials",
        "error_description": "Invalid API credentials"
    }
    return response


# Component fixtures
@pytest.fixture
def mock_authenticator():
    """Create mock D&B authenticator"""
    authenticator = Mock(spec=DNBAuthenticator)
    authenticator.is_authenticated = True
    authenticator.token = "test_token_12345"
    authenticator.token_expires_in = 3600
    authenticator.get_token.return_value = "test_token_12345"
    authenticator.get_auth_headers.return_value = {
        "Authorization": "Bearer test_token_12345",
        "Content-Type": "application/json"
    }
    return authenticator


@pytest.fixture
def mock_api_client():
    """Create mock D&B API client"""
    client = Mock(spec=DNBApiClient)
    client.health_check.return_value = True
    client.session = Mock()
    return client


@pytest.fixture
def mock_pull_client():
    """Create mock pull client"""
    client = Mock(spec=PullApiClient)
    return client


@pytest.fixture
def mock_registration_manager():
    """Create mock registration manager"""
    manager = Mock(spec=RegistrationManager)
    manager.list_registrations.return_value = []
    return manager


# Model fixtures
@pytest.fixture
def sample_notification_element():
    """Create sample notification element"""
    return NotificationElement(
        element="organization.primaryName",
        previous="Old Company Name",
        current="New Company Name",
        timestamp=datetime.utcnow()
    )


@pytest.fixture
def sample_organization():
    """Create sample organization"""
    return Organization(duns="123456789")


@pytest.fixture
def sample_notification(sample_organization, sample_notification_element):
    """Create sample notification"""
    return Notification(
        type=NotificationType.UPDATE,
        organization=sample_organization,
        elements=[sample_notification_element],
        delivery_timestamp=datetime.utcnow()
    )


@pytest.fixture
def sample_notification_response(sample_notification):
    """Create sample notification response"""
    return NotificationResponse(
        transaction_detail={
            "transaction_id": "test-transaction-123",
            "transaction_timestamp": datetime.utcnow().isoformat(),
            "in_language": "en-US"
        },
        inquiry_detail={
            "reference": "TestRegistration"
        },
        notifications=[sample_notification]
    )


@pytest.fixture
def sample_registration_config():
    """Create sample registration configuration"""
    return RegistrationConfig(
        reference="TestRegistration",
        description="Test registration for unit tests",
        duns_list=["123456789", "987654321"],
        data_blocks=["companyinfo_L2_v1", "principalscontacts_L1_v1"],
        json_path_inclusion=[
            "organization.primaryName",
            "organization.registeredAddress"
        ]
    )


@pytest.fixture
def sample_registration(sample_registration_config):
    """Create sample registration"""
    return Registration(
        reference="TestRegistration",
        config=sample_registration_config,
        status=RegistrationStatus.ACTIVE
    )


# Service fixtures
@pytest.fixture
def monitoring_service(
    app_config,
    mock_authenticator,
    mock_api_client,
    mock_pull_client,
    mock_registration_manager
):
    """Create monitoring service with mocked dependencies"""
    return DNBMonitoringService(
        config=app_config,
        authenticator=mock_authenticator,
        api_client=mock_api_client,
        pull_client=mock_pull_client,
        registration_manager=mock_registration_manager
    )


# Test data fixtures
@pytest.fixture
def api_response_data():
    """Sample API response data"""
    return {
        "transactionDetail": {
            "transactionID": "test-transaction-123",
            "transactionTimestamp": "2025-08-26T14:00:00Z",
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
                        "previous": "Old Company Name",
                        "current": "New Company Name",
                        "timestamp": "2025-08-26T13:00:00Z"
                    },
                    {
                        "element": "organization.registeredAddress.streetAddress",
                        "previous": "123 Old Street",
                        "current": "456 New Avenue",
                        "timestamp": "2025-08-26T13:00:00Z"
                    }
                ],
                "deliveryTimeStamp": "2025-08-26T14:00:00Z"
            },
            {
                "type": "DELETE",
                "organization": {
                    "duns": "987654321"
                },
                "elements": [],
                "deliveryTimeStamp": "2025-08-26T14:00:00Z"
            }
        ]
    }


@pytest.fixture
def registration_response_data():
    """Sample registration API response"""
    return {
        "transactionDetail": {
            "transactionID": "reg-transaction-456",
            "transactionTimestamp": "2025-08-26T14:00:00Z",
            "inLanguage": "en-US"
        },
        "registrationId": "REG123456789",
        "registrationReference": "TestRegistration",
        "registrationStatus": "ACTIVE",
        "dunsCount": 2,
        "createdDate": "2025-08-26T10:00:00Z",
        "activatedDate": "2025-08-26T11:00:00Z"
    }


# Async fixtures
@pytest.fixture
async def async_mock_monitoring_service():
    """Create async mock monitoring service"""
    service = AsyncMock(spec=DNBMonitoringService)
    service.health_check.return_value = True
    service.get_service_status.return_value = {
        "service": {"running": True},
        "authentication": {"is_authenticated": True},
        "api_client": {"health_check": True}
    }
    return service


# Helper fixtures
@pytest.fixture
def assert_logs():
    """Helper fixture for testing log messages"""
    def _assert_logs(caplog, level, message_part):
        """Assert that log contains message at specified level"""
        records = [record for record in caplog.records if record.levelname == level]
        assert any(message_part in record.message for record in records), \
            f"Expected log message containing '{message_part}' at {level} level"
    
    return _assert_logs


@pytest.fixture
def freeze_time():
    """Helper fixture for time-based testing"""
    def _freeze_time(frozen_datetime):
        """Context manager that freezes datetime.utcnow()"""
        from unittest.mock import patch
        mock_datetime = patch('datetime.datetime')
        mock_datetime.utcnow.return_value = frozen_datetime
        return mock_datetime
    
    return _freeze_time


# Test markers and parametrize helpers
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "auth: marks tests related to authentication"
    )
    config.addinivalue_line(
        "markers", "api: marks tests related to API clients"
    )
    config.addinivalue_line(
        "markers", "models: marks tests related to data models"
    )
    config.addinivalue_line(
        "markers", "services: marks tests related to service classes"
    )


# Common test utilities
class TestHelpers:
    """Common test helper methods"""
    
    @staticmethod
    def create_mock_response(status_code: int, json_data: Dict[str, Any] = None):
        """Create mock HTTP response"""
        response = Mock()
        response.status_code = status_code
        if json_data:
            response.json.return_value = json_data
        return response
    
    @staticmethod
    def create_notification_batch(count: int = 3) -> List[Notification]:
        """Create a batch of test notifications"""
        notifications = []
        for i in range(count):
            org = Organization(duns=f"12345678{i}")
            element = NotificationElement(
                element=f"organization.field{i}",
                previous=f"old_value_{i}",
                current=f"new_value_{i}",
                timestamp=datetime.utcnow()
            )
            notification = Notification(
                type=NotificationType.UPDATE,
                organization=org,
                elements=[element],
                delivery_timestamp=datetime.utcnow()
            )
            notifications.append(notification)
        return notifications


@pytest.fixture
def test_helpers():
    """Provide test helper methods"""
    return TestHelpers
