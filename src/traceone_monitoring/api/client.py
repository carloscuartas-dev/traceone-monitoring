"""
D&B API Client with rate limiting and comprehensive error handling
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..auth.authenticator import DNBAuthenticator, AuthenticationError
from ..utils.config import DNBApiConfig
from ..models.notification import NotificationResponse


logger = structlog.get_logger(__name__)


class RateLimiter:
    """Rate limiter to enforce API call limits"""
    
    def __init__(self, calls_per_second: float):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0.0
    
    def wait(self):
        """Wait if necessary to respect rate limits"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.min_interval:
            sleep_time = self.min_interval - time_since_last_call
            time.sleep(sleep_time)
        
        self.last_call_time = time.time()


class DNBApiError(Exception):
    """Base class for D&B API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class RateLimitExceededError(DNBApiError):
    """Rate limit exceeded error"""
    pass


class NotFoundError(DNBApiError):
    """Resource not found error"""
    pass


class ServerError(DNBApiError):
    """Server error (5xx)"""
    pass


class DNBApiClient:
    """
    D&B API client with rate limiting, error handling, and automatic retries
    """
    
    def __init__(self, authenticator: DNBAuthenticator, config: DNBApiConfig):
        """
        Initialize API client
        
        Args:
            authenticator: DNB authenticator instance
            config: API configuration
        """
        self.auth = authenticator
        self.config = config
        self.rate_limiter = RateLimiter(config.rate_limit)
        self.base_url = config.base_url
        
        # Setup HTTP session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=config.retry_attempts,
            backoff_factor=config.backoff_factor,
            status_forcelist=[500, 502, 503, 504],  # Don't retry 429 (rate limit)
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        logger.info("DNB API Client initialized",
                   base_url=self.base_url,
                   rate_limit=config.rate_limit)
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> requests.Response:
        """
        Make HTTP request with rate limiting and error handling
        
        Args:
            method: HTTP method
            endpoint: API endpoint (without base URL)
            params: Query parameters
            json: JSON payload
            data: Raw data payload
            headers: Additional headers
            timeout: Request timeout
            
        Returns:
            HTTP response
            
        Raises:
            DNBApiError: If API call fails
        """
        # Apply rate limiting
        self.rate_limiter.wait()
        
        # Prepare URL
        url = f"{self.base_url}{endpoint}"
        
        # Prepare headers
        request_headers = self.auth.get_auth_headers()
        if headers:
            request_headers.update(headers)
        
        # Use configured timeout if not specified
        if timeout is None:
            timeout = self.config.timeout
        
        try:
            logger.debug("Making API request",
                        method=method,
                        url=url,
                        params=params)
            
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                data=data,
                headers=request_headers,
                timeout=timeout
            )
            
            # Handle different response status codes
            if response.status_code == 401:
                logger.warning("API authentication failed, invalidating token")
                self.auth.invalidate_token()
                raise AuthenticationError("Authentication failed")
            elif response.status_code == 404:
                raise NotFoundError("Resource not found", response.status_code, response.text)
            elif response.status_code == 429:
                logger.warning("Rate limit exceeded", 
                              retry_after=response.headers.get('Retry-After'))
                raise RateLimitExceededError("Rate limit exceeded", response.status_code)
            elif response.status_code >= 500:
                raise ServerError(f"Server error: {response.status_code}", response.status_code, response.text)
            elif not response.ok:
                raise DNBApiError(f"API error: {response.status_code}", response.status_code, response.text)
            
            logger.debug("API request successful",
                        method=method,
                        url=url,
                        status_code=response.status_code)
            
            return response
            
        except requests.exceptions.Timeout as e:
            logger.error("API request timeout", method=method, url=url, timeout=timeout)
            raise DNBApiError(f"Request timeout: {e}")
        except requests.exceptions.ConnectionError as e:
            logger.error("API connection error", method=method, url=url, error=str(e))
            raise DNBApiError(f"Connection error: {e}")
        except requests.exceptions.RequestException as e:
            logger.error("API request error", method=method, url=url, error=str(e))
            raise DNBApiError(f"Request error: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((RateLimitExceededError, ServerError))
    )
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> requests.Response:
        """Make GET request with automatic retries"""
        return self._make_request("GET", endpoint, params=params, **kwargs)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((RateLimitExceededError, ServerError))
    )
    def post(self, endpoint: str, json: Optional[Dict[str, Any]] = None, **kwargs) -> requests.Response:
        """Make POST request with automatic retries"""
        return self._make_request("POST", endpoint, json=json, **kwargs)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((RateLimitExceededError, ServerError))
    )
    def patch(self, endpoint: str, json: Optional[Dict[str, Any]] = None, **kwargs) -> requests.Response:
        """Make PATCH request with automatic retries"""
        return self._make_request("PATCH", endpoint, json=json, **kwargs)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((RateLimitExceededError, ServerError))
    )
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """Make DELETE request with automatic retries"""
        return self._make_request("DELETE", endpoint, **kwargs)
    
    def get_json(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Make GET request and return JSON response"""
        response = self.get(endpoint, params=params, **kwargs)
        try:
            return response.json()
        except ValueError as e:
            logger.error("Failed to parse JSON response", 
                        endpoint=endpoint,
                        response_text=response.text[:500])
            raise DNBApiError(f"Invalid JSON response: {e}")
    
    def post_json(self, endpoint: str, json: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Make POST request and return JSON response"""
        response = self.post(endpoint, json=json, **kwargs)
        try:
            return response.json()
        except ValueError as e:
            logger.error("Failed to parse JSON response",
                        endpoint=endpoint,
                        response_text=response.text[:500])
            raise DNBApiError(f"Invalid JSON response: {e}")
    
    def health_check(self) -> bool:
        """Perform health check by testing authentication"""
        try:
            # Try to get a token (this will test the authentication)
            token = self.auth.get_token()
            return bool(token)
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return False
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources"""
        if self.session:
            self.session.close()


class ApiMetrics:
    """Metrics collection for API client"""
    
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.rate_limit_errors = 0
        self.server_errors = 0
        self.auth_errors = 0
        self.total_response_time = 0.0
        self.start_time = datetime.utcnow()
    
    def record_request(self, success: bool, response_time: float, error_type: Optional[str] = None):
        """Record API request metrics"""
        self.total_requests += 1
        self.total_response_time += response_time
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            
            if error_type == "rate_limit":
                self.rate_limit_errors += 1
            elif error_type == "server_error":
                self.server_errors += 1
            elif error_type == "auth_error":
                self.auth_errors += 1
    
    @property
    def success_rate(self) -> float:
        """Get API success rate as percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def average_response_time(self) -> float:
        """Get average response time in seconds"""
        if self.total_requests == 0:
            return 0.0
        return self.total_response_time / self.total_requests
    
    @property
    def requests_per_minute(self) -> float:
        """Get requests per minute rate"""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        if uptime == 0:
            return 0.0
        return (self.total_requests / uptime) * 60
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.success_rate,
            "average_response_time": self.average_response_time,
            "requests_per_minute": self.requests_per_minute,
            "rate_limit_errors": self.rate_limit_errors,
            "server_errors": self.server_errors,
            "auth_errors": self.auth_errors,
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
        }
</function_calls>

<function_calls>
<invoke name="mark_todo_as_done">
<parameter name="todo_ids">["0d2582d3-9a96-4784-bcf5-686d4e69207e", "d3f44bc2-2dc2-4baf-83e8-76891c630418", "d81cd6df-7344-4caf-a9fc-73586ddd7c07"]
