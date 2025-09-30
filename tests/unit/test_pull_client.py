"""
Unit tests for TraceOne Pull API client
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from traceone_monitoring.api.pull_client import (
    PullApiClient,
    NotFoundError,
    NotFoundError
)
from traceone_monitoring.models.notification import NotificationResponse
from traceone_monitoring.models.registration import Registration


@pytest.mark.api
class TestPullApiClient:
    """Test cases for Pull API client"""

    def test_initialization(self, mock_api_client):
        """Test pull client initialization"""
        client = PullApiClient(mock_api_client)
        
        assert client.api_client == mock_api_client
        assert client.base_endpoint == "/monitoring/pull"

    def test_pull_notifications_success(self, mock_api_client, api_response_data, sample_registration):
        """Test successful notification pulling"""
        # Mock API response
        mock_api_client._make_request.return_value = api_response_data
        
        client = PullApiClient(mock_api_client)
        
        # Pull notifications
        response = client.pull_notifications(sample_registration.reference, max_count=100)
        
        # Verify response
        assert isinstance(response, NotificationResponse)
        assert len(response.notifications) == 2
        assert response.registration_reference == "TestRegistration"
        
        # Verify API call
        mock_api_client._make_request.assert_called_once()
        call_args = mock_api_client._make_request.call_args
        assert call_args[0][0] == "GET"  # HTTP method
        assert "/monitoring/pull" in call_args[0][1]  # endpoint

    def test_pull_notifications_with_parameters(self, mock_api_client, api_response_data, sample_registration):
        """Test notification pulling with specific parameters"""
        mock_api_client._make_request.return_value = api_response_data
        
        client = PullApiClient(mock_api_client)
        
        # Pull with specific parameters
        response = client.pull_notifications(
            registration_reference="TestReg",
            max_count=50,
            include_processed=False
        )
        
        # Verify API call parameters
        call_args = mock_api_client._make_request.call_args
        params = call_args[1]["params"]
        assert params["registrationReference"] == "TestReg"
        assert params["maxCount"] == 50
        assert params["includeProcessed"] == False

    def test_pull_notifications_empty_response(self, mock_api_client, sample_registration):
        """Test handling of empty notification response"""
        # Mock empty response
        empty_response = {
            "transactionDetail": {
                "transactionID": "test-transaction-123",
                "transactionTimestamp": "2025-08-26T14:00:00Z",
                "inLanguage": "en-US"
            },
            "inquiryDetail": {
                "reference": "TestRegistration"
            },
            "notifications": []
        }
        mock_api_client._make_request.return_value = empty_response
        
        client = PullApiClient(mock_api_client)
        
        with pytest.raises(NotFoundError):
            client.pull_notifications(sample_registration.reference)

    def test_replay_notifications_success(self, mock_api_client, api_response_data, sample_registration):
        """Test successful notification replay"""
        mock_api_client._make_request.return_value = api_response_data
        
        client = PullApiClient(mock_api_client)
        
        # Replay from specific timestamp
        start_time = datetime(2025, 8, 26, 10, 0, 0)
        response = client.replay_notifications(
            registration_reference=sample_registration.reference,
            start_timestamp=start_time,
            max_count=100
        )
        
        # Verify response
        assert isinstance(response, NotificationResponse)
        assert len(response.notifications) == 2
        
        # Verify API call
        call_args = mock_api_client._make_request.call_args
        params = call_args[1]["params"]
        assert params["startTimestamp"] == start_time.isoformat()

    def test_replay_notifications_with_end_time(self, mock_api_client, api_response_data, sample_registration):
        """Test notification replay with end timestamp"""
        mock_api_client._make_request.return_value = api_response_data
        
        client = PullApiClient(mock_api_client)
        
        start_time = datetime(2025, 8, 26, 10, 0, 0)
        end_time = datetime(2025, 8, 26, 12, 0, 0)
        
        response = client.replay_notifications(
            registration_reference=sample_registration.reference,
            start_timestamp=start_time,
            end_timestamp=end_time
        )
        
        # Verify API call includes end timestamp
        call_args = mock_api_client._make_request.call_args
        params = call_args[1]["params"]
        assert params["startTimestamp"] == start_time.isoformat()
        assert params["endTimestamp"] == end_time.isoformat()

    @pytest.mark.asyncio
    async def test_pull_notifications_continuously(self, mock_api_client, api_response_data, sample_registration):
        """Test continuous notification pulling"""
        # Mock API responses - first has notifications, second is empty
        responses = [
            api_response_data,
            {
                "transactionDetail": {
                    "transactionID": "test-transaction-124",
                    "transactionTimestamp": "2025-08-26T14:01:00Z",
                    "inLanguage": "en-US"
                },
                "inquiryDetail": {
                    "reference": "TestRegistration"
                },
                "notifications": []
            }
        ]
        mock_api_client._make_request.side_effect = responses
        
        client = PullApiClient(mock_api_client)
        
        # Collect results
        results = []
        async for notifications in client.pull_notifications_continuously(
            registration=sample_registration,
            polling_interval=0.1,  # Very short for testing
            max_notifications=100
        ):
            results.append(notifications)
            if len(results) >= 1:  # Stop after first batch
                break
        
        # Verify results
        assert len(results) == 1
        assert len(results[0]) == 2  # Two notifications in first response

    @pytest.mark.asyncio
    async def test_continuous_pulling_handles_errors(self, mock_api_client, sample_registration):
        """Test continuous pulling error handling"""
        from traceone_monitoring.api.client import ApiError
        
        # Mock API error then success
        mock_api_client._make_request.side_effect = [
            ApiError("Server error", 500),
            {
                "transactionDetail": {"transactionID": "test-123"},
                "inquiryDetail": {"reference": "TestRegistration"},
                "notifications": []
            }
        ]
        
        client = PullApiClient(mock_api_client)
        
        # Should handle error and continue
        iteration_count = 0
        async for notifications in client.pull_notifications_continuously(
            registration=sample_registration,
            polling_interval=0.1,
            max_notifications=100
        ):
            iteration_count += 1
            if iteration_count >= 1:  # Stop after first successful iteration
                break
        
        # Should have made at least 2 API calls (error + success)
        assert mock_api_client._make_request.call_count >= 2

    def test_get_notification_statistics(self, mock_api_client, sample_registration):
        """Test getting notification statistics"""
        # Mock statistics response
        stats_response = {
            "transactionDetail": {
                "transactionID": "stats-123",
                "transactionTimestamp": "2025-08-26T14:00:00Z"
            },
            "inquiryDetail": {
                "reference": "TestRegistration"
            },
            "statistics": {
                "totalNotifications": 150,
                "processedNotifications": 145,
                "pendingNotifications": 5,
                "errorNotifications": 0,
                "lastNotificationTimestamp": "2025-08-26T13:55:00Z"
            }
        }
        mock_api_client._make_request.return_value = stats_response
        
        client = PullApiClient(mock_api_client)
        
        # Get statistics
        stats = client.get_notification_statistics(sample_registration.reference)
        
        assert stats["totalNotifications"] == 150
        assert stats["processedNotifications"] == 145
        assert stats["pendingNotifications"] == 5
        
        # Verify API call
        call_args = mock_api_client._make_request.call_args
        assert "/monitoring/pull/statistics" in call_args[0][1]

    def test_acknowledge_notifications(self, mock_api_client):
        """Test acknowledging processed notifications"""
        # Mock acknowledgment response
        ack_response = {
            "transactionDetail": {
                "transactionID": "ack-123",
                "transactionTimestamp": "2025-08-26T14:00:00Z"
            },
            "acknowledged": True,
            "acknowledgedCount": 5
        }
        mock_api_client._make_request.return_value = ack_response
        
        client = PullApiClient(mock_api_client)
        
        # Acknowledge notifications
        notification_ids = ["notif-1", "notif-2", "notif-3"]
        result = client.acknowledge_notifications("TestReg", notification_ids)
        
        assert result["acknowledged"] is True
        assert result["acknowledgedCount"] == 5
        
        # Verify API call
        call_args = mock_api_client._make_request.call_args
        assert call_args[0][0] == "POST"  # HTTP method
        assert "/monitoring/pull/acknowledge" in call_args[0][1]
        
        # Verify request body
        json_data = call_args[1]["json"]
        assert json_data["registrationReference"] == "TestReg"
        assert json_data["notificationIds"] == notification_ids

    def test_pull_error_handling(self, mock_api_client, sample_registration):
        """Test pull-specific error handling"""
        from traceone_monitoring.api.client import ApiError
        
        # Mock API error
        mock_api_client._make_request.side_effect = ApiError("Pull service unavailable", 503)
        
        client = PullApiClient(mock_api_client)
        
        with pytest.raises(PullError) as exc_info:
            client.pull_notifications(sample_registration.reference)
        
        assert "Pull service unavailable" in str(exc_info.value)

    def test_invalid_registration_reference(self, mock_api_client):
        """Test handling of invalid registration reference"""
        from traceone_monitoring.api.client import ApiError
        
        # Mock 404 response for invalid registration
        mock_api_client._make_request.side_effect = ApiError("Registration not found", 404)
        
        client = PullApiClient(mock_api_client)
        
        with pytest.raises(PullError) as exc_info:
            client.pull_notifications("InvalidRef")
        
        assert exc_info.value.status_code == 404

    def test_max_count_validation(self, mock_api_client):
        """Test validation of max_count parameter"""
        client = PullApiClient(mock_api_client)
        
        # Invalid max_count values
        with pytest.raises(ValueError):
            client.pull_notifications("TestReg", max_count=0)
        
        with pytest.raises(ValueError):
            client.pull_notifications("TestReg", max_count=-1)
        
        with pytest.raises(ValueError):
            client.pull_notifications("TestReg", max_count=1001)  # Too large

    def test_timestamp_validation(self, mock_api_client):
        """Test validation of timestamp parameters"""
        client = PullApiClient(mock_api_client)
        
        start_time = datetime(2025, 8, 26, 12, 0, 0)
        end_time = datetime(2025, 8, 26, 10, 0, 0)  # End before start
        
        # End timestamp before start timestamp
        with pytest.raises(ValueError):
            client.replay_notifications("TestReg", start_time, end_timestamp=end_time)

    @pytest.mark.asyncio
    async def test_async_context_manager(self, mock_api_client, api_response_data, sample_registration):
        """Test async context manager for continuous pulling"""
        mock_api_client._make_request.return_value = api_response_data
        
        client = PullApiClient(mock_api_client)
        
        notification_count = 0
        async with client.continuous_pull_context(
            registration=sample_registration,
            polling_interval=0.1
        ) as pull_stream:
            async for notifications in pull_stream:
                notification_count += len(notifications)
                if notification_count >= 2:  # Stop after getting some notifications
                    break
        
        assert notification_count >= 2

    def test_response_parsing_error(self, mock_api_client):
        """Test handling of malformed API responses"""
        # Mock malformed response
        malformed_response = {
            "transactionDetail": {
                "transactionID": "test-123"
                # Missing required fields
            }
            # Missing inquiryDetail and notifications
        }
        mock_api_client._make_request.return_value = malformed_response
        
        client = PullApiClient(mock_api_client)
        
        with pytest.raises(PullError):
            client.pull_notifications("TestReg")

    @patch('time.sleep')
    def test_retry_on_temporary_failure(self, mock_sleep, mock_api_client, api_response_data):
        """Test retry mechanism for temporary failures"""
        from traceone_monitoring.api.client import ApiError
        
        # First call fails, second succeeds
        mock_api_client._make_request.side_effect = [
            ApiError("Temporary failure", 503),
            api_response_data
        ]
        
        client = PullApiClient(mock_api_client)
        
        # Should succeed after retry
        response = client.pull_notifications("TestReg")
        
        assert isinstance(response, NotificationResponse)
        assert mock_api_client._make_request.call_count == 2

    def test_batch_processing_support(self, mock_api_client, test_helpers):
        """Test support for batch processing of notifications"""
        # Create mock response with many notifications
        batch_response = {
            "transactionDetail": {
                "transactionID": "batch-123",
                "transactionTimestamp": "2025-08-26T14:00:00Z",
                "inLanguage": "en-US"
            },
            "inquiryDetail": {
                "reference": "TestRegistration"
            },
            "notifications": []
        }
        
        # Add 10 mock notifications
        for i in range(10):
            batch_response["notifications"].append({
                "type": "UPDATE",
                "organization": {"duns": f"12345678{i}"},
                "elements": [{
                    "element": f"organization.field{i}",
                    "previous": f"old_{i}",
                    "current": f"new_{i}",
                    "timestamp": "2025-08-26T13:00:00Z"
                }],
                "deliveryTimeStamp": "2025-08-26T14:00:00Z"
            })
        
        mock_api_client._make_request.return_value = batch_response
        
        client = PullApiClient(mock_api_client)
        response = client.pull_notifications("TestReg", max_count=10)
        
        assert len(response.notifications) == 10
        
        # Test batch processing
        batch_size = 5
        batches = client.batch_notifications(response.notifications, batch_size)
        
        assert len(batches) == 2
        assert len(batches[0]) == 5
        assert len(batches[1]) == 5
