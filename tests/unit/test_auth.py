"""
Unit tests for D&B authentication module
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import requests

from traceone_monitoring.auth.authenticator import (
    DNBAuthenticator,
    AuthenticationError,
    InvalidCredentialsError,
    TokenExpiredError
)
from traceone_monitoring.utils.config import DNBApiConfig


@pytest.fixture
def dnb_config():
    """Create test D&B API configuration"""
    return DNBApiConfig(
        client_id="test_client_id",
        client_secret="test_client_secret",
        base_url="https://test.dnb.com",
        rate_limit=5.0,
        timeout=30,
        retry_attempts=3,
        backoff_factor=2.0
    )


@pytest.fixture
def authenticator(dnb_config):
    """Create DNB authenticator for testing"""
    return DNBAuthenticator(dnb_config)


class TestDNBAuthenticator:
    """Test cases for DNB authenticator"""
    
    def test_initialization(self, authenticator, dnb_config):
        """Test authenticator initialization"""
        assert authenticator.config == dnb_config
        assert authenticator.token is None
        assert authenticator.token_expiry is None
        assert authenticator.session is not None
    
    @patch('requests.Session.post')
    def test_successful_token_refresh(self, mock_post, authenticator):
        """Test successful token refresh"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token_123",
            "expiresIn": 86400
        }
        mock_post.return_value = mock_response
        
        # Test token refresh
        token = authenticator.get_token()
        
        assert token == "test_token_123"
        assert authenticator.token == "test_token_123"
        assert authenticator.token_expiry is not None
        
        # Verify API call was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "https://test.dnb.com/v2/token" in str(call_args)
    
    @patch('requests.Session.post')
    def test_invalid_credentials_error(self, mock_post, authenticator):
        """Test handling of invalid credentials"""
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        with pytest.raises(InvalidCredentialsError):
            authenticator.get_token()
    
    @patch('requests.Session.post')
    def test_server_error_handling(self, mock_post, authenticator):
        """Test handling of server errors"""
        # Mock 500 response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        with pytest.raises(AuthenticationError):
            authenticator.get_token()
    
    def test_token_validation(self, authenticator):
        """Test token validation logic"""
        # No token initially
        assert not authenticator._is_token_valid()
        
        # Set valid token
        authenticator.token = "test_token"
        authenticator.token_expiry = datetime.utcnow() + timedelta(hours=1)
        assert authenticator._is_token_valid()
        
        # Expired token
        authenticator.token_expiry = datetime.utcnow() - timedelta(hours=1)
        assert not authenticator._is_token_valid()
        
        # Token expiring soon (within refresh buffer)
        authenticator.token_expiry = datetime.utcnow() + timedelta(seconds=10)
        assert not authenticator._is_token_valid()
    
    @patch('requests.Session.post')
    def test_token_reuse(self, mock_post, authenticator):
        """Test that valid tokens are reused"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token_123",
            "expiresIn": 86400
        }
        mock_post.return_value = mock_response
        
        # First call should refresh token
        token1 = authenticator.get_token()
        assert mock_post.call_count == 1
        
        # Second call should reuse token
        token2 = authenticator.get_token()
        assert mock_post.call_count == 1  # No additional call
        assert token1 == token2
    
    def test_get_auth_headers(self, authenticator):
        """Test authentication headers generation"""
        # Mock token
        authenticator.token = "test_token_123"
        authenticator.token_expiry = datetime.utcnow() + timedelta(hours=1)
        
        headers = authenticator.get_auth_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_token_123"
        assert headers["Content-Type"] == "application/json"
    
    def test_invalidate_token(self, authenticator):
        """Test token invalidation"""
        # Set token
        authenticator.token = "test_token"
        authenticator.token_expiry = datetime.utcnow() + timedelta(hours=1)
        
        # Invalidate
        authenticator.invalidate_token()
        
        assert authenticator.token is None
        assert authenticator.token_expiry is None
    
    def test_token_expires_in_property(self, authenticator):
        """Test token_expires_in property"""
        # No token
        assert authenticator.token_expires_in is None
        
        # Token expiring in 1 hour
        authenticator.token_expiry = datetime.utcnow() + timedelta(hours=1)
        expires_in = authenticator.token_expires_in
        assert 3590 <= expires_in <= 3600  # Allow some variance
        
        # Expired token
        authenticator.token_expiry = datetime.utcnow() - timedelta(hours=1)
        assert authenticator.token_expires_in == 0
    
    def test_context_manager(self, authenticator):
        """Test context manager functionality"""
        with authenticator as auth:
            assert auth is authenticator
        
        # Session should be closed after context exit
        # Note: In real implementation, we'd check if session is closed
