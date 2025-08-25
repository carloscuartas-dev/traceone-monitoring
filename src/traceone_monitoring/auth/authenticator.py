"""
D&B API Authentication Module
OAuth 2.0 token management with automatic refresh
"""

import base64
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import structlog

from ..utils.config import DNBApiConfig


logger = structlog.get_logger(__name__)


class AuthenticationError(Exception):
    """Authentication related errors"""
    pass


class TokenExpiredError(AuthenticationError):
    """Token has expired"""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Invalid API credentials"""
    pass


class DNBAuthenticator:
    """D&B API authentication handler with OAuth 2.0 support"""
    
    def __init__(self, config: DNBApiConfig):
        """
        Initialize authenticator with D&B API configuration
        
        Args:
            config: D&B API configuration
        """
        self.config = config
        self.token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self.refresh_buffer = timedelta(seconds=config.timeout)
        
        # Setup HTTP session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=config.retry_attempts,
            backoff_factor=config.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        logger.info("DNB Authenticator initialized", 
                   base_url=config.base_url,
                   rate_limit=config.rate_limit)
    
    def get_token(self) -> str:
        """
        Get valid access token, refreshing if necessary
        
        Returns:
            Valid access token
            
        Raises:
            AuthenticationError: If authentication fails
        """
        if self._is_token_valid():
            return self.token
        
        return self._refresh_token()
    
    def _is_token_valid(self) -> bool:
        """Check if current token is valid and not expiring soon"""
        if not self.token or not self.token_expiry:
            return False
        
        # Check if token expires within the refresh buffer
        expires_soon = datetime.utcnow() + self.refresh_buffer
        return self.token_expiry > expires_soon
    
    def _refresh_token(self) -> str:
        """
        Refresh access token using client credentials
        
        Returns:
            New access token
            
        Raises:
            AuthenticationError: If token refresh fails
        """
        logger.info("Refreshing D&B access token")
        
        try:
            # Prepare credentials
            credentials = f"{self.config.client_id}:{self.config.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            # Prepare request
            url = f"{self.config.base_url}/v2/token"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Basic {encoded_credentials}",
            }
            
            payload = {
                "grant_type": "client_credentials"
            }
            
            # Make request
            response = self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.config.timeout
            )
            
            if response.status_code == 401:
                logger.error("Invalid D&B API credentials")
                raise InvalidCredentialsError("Invalid API credentials")
            elif response.status_code != 200:
                logger.error("Token refresh failed", 
                           status_code=response.status_code,
                           response_text=response.text)
                raise AuthenticationError(f"Token refresh failed: {response.status_code}")
            
            # Parse response
            token_data = response.json()
            self.token = token_data.get("access_token")
            expires_in = token_data.get("expiresIn", 86400)  # Default 24 hours
            
            if not self.token:
                raise AuthenticationError("No access token in response")
            
            # Calculate expiry time
            self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
            
            logger.info("D&B access token refreshed successfully", 
                       expires_in=expires_in,
                       expires_at=self.token_expiry.isoformat())
            
            return self.token
            
        except requests.exceptions.RequestException as e:
            logger.error("Network error during token refresh", error=str(e))
            raise AuthenticationError(f"Network error during authentication: {e}")
        except Exception as e:
            logger.error("Unexpected error during token refresh", error=str(e))
            raise AuthenticationError(f"Unexpected authentication error: {e}")
    
    def invalidate_token(self):
        """Invalidate current token (force refresh on next request)"""
        logger.info("Invalidating D&B access token")
        self.token = None
        self.token_expiry = None
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests
        
        Returns:
            Dictionary with Authorization header
        """
        token = self.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    
    @property
    def is_authenticated(self) -> bool:
        """Check if authenticator has a valid token"""
        return self._is_token_valid()
    
    @property
    def token_expires_in(self) -> Optional[int]:
        """Get seconds until token expires"""
        if not self.token_expiry:
            return None
        
        delta = self.token_expiry - datetime.utcnow()
        return max(0, int(delta.total_seconds()))
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources"""
        if self.session:
            self.session.close()


class TokenManager:
    """
    Advanced token manager with caching and automatic refresh
    Useful for multi-threaded environments
    """
    
    def __init__(self, authenticator: DNBAuthenticator):
        self.authenticator = authenticator
        self._lock = None  # Would use threading.Lock() in multi-threaded environment
    
    def get_cached_token(self) -> str:
        """Get token with thread-safe caching"""
        # In a multi-threaded environment, this would use locking
        return self.authenticator.get_token()
    
    def preemptive_refresh(self, buffer_seconds: int = 300):
        """Preemptively refresh token before it expires"""
        if self.authenticator.token_expires_in and self.authenticator.token_expires_in < buffer_seconds:
            logger.info("Preemptively refreshing token", 
                       expires_in=self.authenticator.token_expires_in)
            self.authenticator._refresh_token()


def create_authenticator(config: DNBApiConfig) -> DNBAuthenticator:
    """
    Factory function to create DNB authenticator
    
    Args:
        config: D&B API configuration
        
    Returns:
        Configured DNB authenticator
    """
    return DNBAuthenticator(config)
