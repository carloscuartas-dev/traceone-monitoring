"""
Unit tests for DNB API client
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import requests

from traceone_monitoring.api.client import (
    DNBApiClient,
    DNBApiError,
    RateLimitExceededError,
    ServerError,
    NotFoundError
)
from traceone_monitoring.auth.authenticator import DNBAuthenticator
from traceone_monitoring.utils.config import DNBApiConfig


@pytest.mark.api
class TestDNBApiClient:
    """Test cases for DNB API client"""

    def test_initialization(self, dnb_api_config, mock_authenticator):
        """Test API client initialization"""
        client = DNBApiClient(dnb_api_config, mock_authenticator)
        
        assert client.config == dnb_api_config
        assert client.authenticator == mock_authenticator
        assert client.session is not None
        assert client.rate_limiter is not None

    def test_base_url_construction(self, dnb_api_config, mock_authenticator):
        """Test base URL construction"""
        client = DNBApiClient(dnb_api_config, mock_authenticator)
        
        expected_base = "https://api.test.traceone.app"
        assert client.config.base_url == expected_base

    @patch('requests.Session.get')
    def test_successful_get_request(self, mock_get, dnb_api_config, mock_authenticator):
        """Test successful GET request"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "data": "test"}
        mock_get.return_value = mock_response
        
        client = DNBApiClient(dnb_api_config, mock_authenticator)
        
        # Make request
        response = client._make_request("GET", "/test/endpoint")
        
        assert response == {"status": "success", "data": "test"}
        mock_get.assert_called_once()

    @patch('requests.Session.post')
    def test_successful_post_request(self, mock_post, dnb_api_config, mock_authenticator):
        """Test successful POST request"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "123", "created": True}
        mock_post.return_value = mock_response
        
        client = DNBApiClient(dnb_api_config, mock_authenticator)
        
        # Make request with data
        test_data = {"name": "test", "value": 123}
        response = client._make_request("POST", "/test/endpoint", json=test_data)
        
        assert response == {"id": "123", "created": True}
        mock_post.assert_called_once()
        
        # Verify data was passed correctly
        call_args = mock_post.call_args
        assert call_args[1]["json"] == test_data

    @patch('requests.Session.get')
    def test_rate_limit_handling(self, mock_get, dnb_api_config, mock_authenticator):
        """Test rate limit error handling"""
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.text = "Rate limit exceeded"
        mock_get.return_value = mock_response
        
        client = DNBApiClient(dnb_api_config, mock_authenticator)
        
        with pytest.raises(RateLimitExceededError) as exc_info:
            client._make_request("GET", "/test/endpoint")
        
        assert "Rate limit exceeded" in str(exc_info.value)

    @patch('requests.Session.get')
    def test_authentication_error_handling(self, mock_get, dnb_api_config, mock_authenticator):
        """Test authentication error handling"""
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response
        
        client = DNBApiClient(dnb_api_config, mock_authenticator)
        
        with pytest.raises(DNBApiError) as exc_info:
            client._make_request("GET", "/test/endpoint")
        
        assert exc_info.value.status_code == 401
        assert "Unauthorized" in str(exc_info.value)

    @patch('requests.Session.get')
    def test_server_error_handling(self, mock_get, dnb_api_config, mock_authenticator):
        """Test server error handling"""
        # Mock 500 response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response
        
        client = DNBApiClient(dnb_api_config, mock_authenticator)
        
        with pytest.raises(DNBApiError) as exc_info:
            client._make_request("GET", "/test/endpoint")
        
        assert exc_info.value.status_code == 500

    @patch('requests.Session.get')
    def test_network_error_handling(self, mock_get, dnb_api_config, mock_authenticator):
        """Test network error handling"""
        # Mock network error
        mock_get.side_effect = requests.ConnectionError("Network unreachable")
        
        client = DNBApiClient(dnb_api_config, mock_authenticator)
        
        with pytest.raises(DNBApiError):
            client._make_request("GET", "/test/endpoint")

    @patch('requests.Session.get')
    def test_timeout_handling(self, mock_get, dnb_api_config, mock_authenticator):
        """Test timeout handling"""
        # Mock timeout error
        mock_get.side_effect = requests.Timeout("Request timeout")
        
        client = DNBApiClient(dnb_api_config, mock_authenticator)
        
        with pytest.raises(DNBApiError):
            client._make_request("GET", "/test/endpoint")

    @patch('requests.Session.get')
    def test_retry_mechanism(self, mock_get, dnb_api_config, mock_authenticator):
        """Test retry mechanism for temporary failures"""
        # Configure for fewer retries in test
        dnb_api_config.retry_attempts = 2
        
        # First call fails, second succeeds
        mock_responses = [
            Mock(status_code=503, text="Service Unavailable"),
            Mock(status_code=200, json=lambda: {"status": "success"})
        ]
        mock_get.side_effect = mock_responses
        
        client = DNBApiClient(dnb_api_config, mock_authenticator)
        
        # Should succeed after retry
        response = client._make_request("GET", "/test/endpoint")
        
        assert response == {"status": "success"}
        assert mock_get.call_count == 2

    @patch('requests.Session.get')
    def test_authentication_header_inclusion(self, mock_get, dnb_api_config, mock_authenticator):
        """Test that authentication headers are included"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response
        
        client = DNBApiClient(dnb_api_config, mock_authenticator)
        client._make_request("GET", "/test/endpoint")
        
        # Verify authenticator was called to get headers
        mock_authenticator.get_auth_headers.assert_called()
        
        # Verify headers were included in request
        call_args = mock_get.call_args
        headers = call_args[1]["headers"]
        assert "Authorization" in headers

    def test_health_check_success(self, dnb_api_config, mock_authenticator):
        """Test successful health check"""
        client = DNBApiClient(dnb_api_config, mock_authenticator)
        
        with patch.object(client, '_make_request') as mock_request:
            mock_request.return_value = {"status": "healthy", "version": "1.0.0"}
            
            result = client.health_check()
            
            assert result is True
            mock_request.assert_called_once_with("GET", "/health")

    def test_health_check_failure(self, dnb_api_config, mock_authenticator):
        """Test failed health check"""
        client = DNBApiClient(dnb_api_config, mock_authenticator)
        
        with patch.object(client, '_make_request') as mock_request:
            mock_request.side_effect = DNBApiError("Health check failed", 500)
            
            result = client.health_check()
            
            assert result is False

    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_rate_limiting_delay(self, mock_sleep, dnb_api_config, mock_authenticator):
        """Test rate limiting introduces proper delays"""
        # Set low rate limit for testing
        dnb_api_config.rate_limit = 1.0  # 1 request per second
        
        client = DNBApiClient(dnb_api_config, mock_authenticator)
        
        with patch.object(client, '_make_request') as mock_request:
            mock_request.return_value = {"data": "test"}
            
            # Make two quick requests
            client._make_request("GET", "/test1")
            client._make_request("GET", "/test2")
            
            # Should have introduced a delay
            assert mock_sleep.call_count >= 1

    def test_context_manager(self, dnb_api_config, mock_authenticator):
        """Test context manager functionality"""
        client = DNBApiClient(dnb_api_config, mock_authenticator)
        
        with client as api_client:
            assert api_client is client
        
        # Session should be closed after context exit
        client.session.close.assert_called_once()

    def test_get_api_info(self, dnb_api_config, mock_authenticator):
        """Test API info retrieval"""
        client = DNBApiClient(dnb_api_config, mock_authenticator)
        
        with patch.object(client, '_make_request') as mock_request:
            mock_request.return_value = {
                "name": "TraceOne API",
                "version": "1.0.0",
                "environment": "test"
            }
            
            info = client.get_api_info()
            
            assert info["name"] == "TraceOne API"
            assert info["version"] == "1.0.0"
            mock_request.assert_called_once_with("GET", "/api/info")

    def test_custom_headers(self, dnb_api_config, mock_authenticator):
        """Test custom headers are merged correctly"""
        client = DNBApiClient(dnb_api_config, mock_authenticator)
        
        with patch.object(client, 'session') as mock_session:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": "test"}
            mock_session.get.return_value = mock_response
            
            custom_headers = {"X-Custom-Header": "test-value"}
            client._make_request("GET", "/test", headers=custom_headers)
            
            # Verify custom headers were included
            call_args = mock_session.get.call_args
            headers = call_args[1]["headers"]
            assert "X-Custom-Header" in headers
            assert "Authorization" in headers  # Auth headers should still be there

    @patch('requests.Session.get')
    def test_json_parsing_error(self, mock_get, dnb_api_config, mock_authenticator):
        """Test handling of invalid JSON responses"""
        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "Invalid JSON response"
        mock_get.return_value = mock_response
        
        client = DNBApiClient(dnb_api_config, mock_authenticator)
        
        with pytest.raises(DNBApiError) as exc_info:
            client._make_request("GET", "/test/endpoint")
        
        assert "Invalid JSON" in str(exc_info.value)

    def test_request_logging(self, dnb_api_config, mock_authenticator, caplog):
        """Test request logging functionality"""
        dnb_api_config.log_requests = True
        client = DNBApiClient(dnb_api_config, mock_authenticator)
        
        with patch.object(client, 'session') as mock_session:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": "test"}
            mock_session.get.return_value = mock_response
            
            client._make_request("GET", "/test/endpoint")
            
            # Check that request was logged
            assert "Making request" in caplog.text
            assert "GET" in caplog.text
            assert "/test/endpoint" in caplog.text
