"""
Configuration management system for TraceOne Monitoring Service
"""

import os
import yaml
from typing import Optional, Dict, Any, List
from pathlib import Path
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv


class DNBApiConfig(BaseModel):
    """D&B API configuration"""
    base_url: str = Field(default="https://plus.dnb.com", description="D&B API base URL")
    client_id: str = Field(..., description="D&B API client ID")
    client_secret: str = Field(..., description="D&B API client secret")
    rate_limit: float = Field(default=5.0, description="API calls per second")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    backoff_factor: float = Field(default=2.0, description="Exponential backoff factor")

    @validator('rate_limit')
    def validate_rate_limit(cls, v):
        if v <= 0 or v > 10:
            raise ValueError('Rate limit must be between 0 and 10 calls per second')
        return v


class DatabaseConfig(BaseModel):
    """Database configuration"""
    url: str = Field(..., description="Database connection URL")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Maximum pool overflow")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    pool_recycle: int = Field(default=3600, description="Pool recycle time in seconds")


class MonitoringConfig(BaseModel):
    """Monitoring service configuration"""
    polling_interval: int = Field(default=300, description="Polling interval in seconds")
    max_notifications: int = Field(default=100, description="Maximum notifications per API call")
    notification_batch_size: int = Field(default=50, description="Notification processing batch size")
    replay_window_days: int = Field(default=14, description="Replay window in days")
    
    @validator('max_notifications')
    def validate_max_notifications(cls, v):
        if v < 1 or v > 100:
            raise ValueError('Max notifications must be between 1 and 100')
        return v


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format (json or text)")
    file: Optional[str] = Field(default=None, description="Log file path")
    max_size: str = Field(default="100MB", description="Maximum log file size")
    backup_count: int = Field(default=5, description="Number of backup log files")

    @validator('level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()


class SecurityConfig(BaseModel):
    """Security configuration"""
    encryption_key: Optional[str] = Field(default=None, description="Data encryption key")
    audit_logging: bool = Field(default=True, description="Enable audit logging")
    rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    token_refresh_buffer: int = Field(default=300, description="Token refresh buffer in seconds")


class MetricsConfig(BaseModel):
    """Metrics and monitoring configuration"""
    enabled: bool = Field(default=True, description="Enable metrics collection")
    port: int = Field(default=9090, description="Metrics server port")
    path: str = Field(default="/metrics", description="Metrics endpoint path")
    
    
class AppConfig(BaseModel):
    """Main application configuration"""
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")
    dnb_api: DNBApiConfig
    database: DatabaseConfig
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)

    @validator('environment')
    def validate_environment(cls, v):
        valid_envs = ['development', 'staging', 'production']
        if v.lower() not in valid_envs:
            raise ValueError(f'Environment must be one of: {valid_envs}')
        return v.lower()


class ConfigManager:
    """Configuration manager for loading and validating configuration"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self._config: Optional[AppConfig] = None
    
    @classmethod
    def from_file(cls, config_path: str) -> "ConfigManager":
        """Create configuration manager from file"""
        return cls(config_path)
    
    @classmethod
    def from_env(cls) -> "ConfigManager":
        """Create configuration manager from environment variables"""
        return cls()
    
    def load_config(self) -> AppConfig:
        """Load and validate configuration"""
        if self._config is not None:
            return self._config
        
        # Load environment variables
        load_dotenv()
        
        if self.config_path:
            # Load from YAML file
            config_data = self._load_yaml_config(self.config_path)
        else:
            # Load from environment variables
            config_data = self._load_env_config()
        
        # Validate and create configuration object
        self._config = AppConfig(**config_data)
        return self._config
    
    def _load_yaml_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # Substitute environment variables
        config_data = self._substitute_env_vars(config_data)
        return config_data
    
    def _load_env_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        return {
            "environment": os.getenv("ENVIRONMENT", "development"),
            "debug": os.getenv("DEBUG", "false").lower() == "true",
            "dnb_api": {
                "base_url": os.getenv("DNB_BASE_URL", "https://plus.dnb.com"),
                "client_id": os.getenv("DNB_CLIENT_ID"),
                "client_secret": os.getenv("DNB_CLIENT_SECRET"),
                "rate_limit": float(os.getenv("DNB_RATE_LIMIT", "5.0")),
                "timeout": int(os.getenv("DNB_TIMEOUT", "30")),
                "retry_attempts": int(os.getenv("DNB_RETRY_ATTEMPTS", "3")),
                "backoff_factor": float(os.getenv("DNB_BACKOFF_FACTOR", "2.0")),
            },
            "database": {
                "url": os.getenv("DATABASE_URL"),
                "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
                "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
                "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
                "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
            },
            "monitoring": {
                "polling_interval": int(os.getenv("MONITORING_POLLING_INTERVAL", "300")),
                "max_notifications": int(os.getenv("MONITORING_MAX_NOTIFICATIONS", "100")),
                "notification_batch_size": int(os.getenv("MONITORING_BATCH_SIZE", "50")),
                "replay_window_days": int(os.getenv("MONITORING_REPLAY_WINDOW_DAYS", "14")),
            },
            "logging": {
                "level": os.getenv("LOG_LEVEL", "INFO"),
                "format": os.getenv("LOG_FORMAT", "json"),
                "file": os.getenv("LOG_FILE"),
                "max_size": os.getenv("LOG_MAX_SIZE", "100MB"),
                "backup_count": int(os.getenv("LOG_BACKUP_COUNT", "5")),
            },
            "security": {
                "encryption_key": os.getenv("ENCRYPTION_KEY"),
                "audit_logging": os.getenv("AUDIT_LOGGING", "true").lower() == "true",
                "rate_limiting": os.getenv("RATE_LIMITING", "true").lower() == "true",
                "token_refresh_buffer": int(os.getenv("TOKEN_REFRESH_BUFFER", "300")),
            },
            "metrics": {
                "enabled": os.getenv("METRICS_ENABLED", "true").lower() == "true",
                "port": int(os.getenv("METRICS_PORT", "9090")),
                "path": os.getenv("METRICS_PATH", "/metrics"),
            },
        }
    
    def _substitute_env_vars(self, obj: Any) -> Any:
        """Recursively substitute environment variables in configuration"""
        if isinstance(obj, str):
            # Handle ${VAR_NAME} and ${VAR_NAME:default} patterns
            import re
            pattern = r'\$\{([^}]+)\}'
            
            def replace_var(match):
                var_expr = match.group(1)
                if ':' in var_expr:
                    var_name, default_value = var_expr.split(':', 1)
                    return os.getenv(var_name.strip(), default_value.strip())
                else:
                    return os.getenv(var_expr.strip(), '')
            
            return re.sub(pattern, replace_var, obj)
        elif isinstance(obj, dict):
            return {k: self._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        else:
            return obj
    
    @property
    def config(self) -> AppConfig:
        """Get the loaded configuration"""
        if self._config is None:
            self._config = self.load_config()
        return self._config


# Global configuration instance
_config_manager: Optional[ConfigManager] = None


def get_config() -> AppConfig:
    """Get the global configuration instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager.from_env()
    return _config_manager.load_config()


def init_config(config_path: Optional[str] = None) -> AppConfig:
    """Initialize configuration from file or environment"""
    global _config_manager
    if config_path:
        _config_manager = ConfigManager.from_file(config_path)
    else:
        _config_manager = ConfigManager.from_env()
    return _config_manager.load_config()


def reload_config() -> AppConfig:
    """Reload configuration"""
    global _config_manager
    if _config_manager is not None:
        _config_manager._config = None
    return get_config()
