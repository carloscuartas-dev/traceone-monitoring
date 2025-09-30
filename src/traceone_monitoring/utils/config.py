"""
Configuration management system for TraceOne Monitoring Service
"""

import os
import yaml
from typing import Optional, Dict, Any, List
from pathlib import Path
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv
import structlog

logger = structlog.get_logger(__name__)


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


class SFTPStorageConfig(BaseModel):
    """SFTP storage configuration"""
    enabled: bool = Field(default=False, description="Enable SFTP storage")
    hostname: str = Field(default="", description="SFTP server hostname")
    port: int = Field(default=22, description="SFTP server port")
    username: str = Field(default="", description="SFTP username")
    password: Optional[str] = Field(default=None, description="SFTP password")
    private_key_path: Optional[str] = Field(default=None, description="Path to private key file")
    private_key_passphrase: Optional[str] = Field(default=None, description="Private key passphrase")
    
    # Remote paths
    remote_base_path: str = Field(default="/notifications", description="Base path on SFTP server")
    
    # File format options
    file_format: str = Field(default="json", description="File format (json, csv, xml)")
    compress_files: bool = Field(default=False, description="Compress files before upload")
    
    # Connection settings
    timeout: int = Field(default=30, description="Connection timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    
    # File organization
    organize_by_date: bool = Field(default=True, description="Organize files by date")
    organize_by_registration: bool = Field(default=True, description="Organize files by registration")


class LocalFileStorageConfig(BaseModel):
    """Local file storage configuration"""
    enabled: bool = Field(default=False, description="Enable local file storage")
    base_path: str = Field(default="./notifications", description="Base directory path for storage")
    file_format: str = Field(default="json", description="File format (json, csv, xml)")
    compress_files: bool = Field(default=False, description="Compress files after creation")
    
    # File organization
    organize_by_date: bool = Field(default=True, description="Organize files by date")
    organize_by_registration: bool = Field(default=True, description="Organize files by registration")
    
    # File permissions
    file_permissions: int = Field(default=0o644, description="File permissions (octal)")
    directory_permissions: int = Field(default=0o755, description="Directory permissions (octal)")
    
    # Retention settings
    max_files_per_directory: int = Field(default=1000, description="Maximum files per directory")
    enable_rotation: bool = Field(default=False, description="Enable file rotation")


class EmailNotificationConfig(BaseModel):
    """Email notification configuration"""
    enabled: bool = Field(default=False, description="Enable email notifications")
    
    # SMTP Configuration
    smtp_server: str = Field(default="smtp.gmail.com", description="SMTP server hostname")
    smtp_port: int = Field(default=587, description="SMTP server port")
    username: str = Field(default="", description="SMTP username")
    password: str = Field(default="", description="SMTP password")
    use_tls: bool = Field(default=True, description="Use TLS encryption")
    use_ssl: bool = Field(default=False, description="Use SSL encryption")
    timeout: int = Field(default=30, description="SMTP timeout in seconds")
    
    # Email Headers
    from_email: str = Field(default="", description="From email address")
    from_name: str = Field(default="TraceOne Monitoring", description="From name")
    to_emails: List[str] = Field(default_factory=list, description="Recipient email addresses")
    cc_emails: List[str] = Field(default_factory=list, description="CC email addresses")
    bcc_emails: List[str] = Field(default_factory=list, description="BCC email addresses")
    
    # Notification Settings
    send_individual_notifications: bool = Field(default=False, description="Send individual emails per notification")
    send_summary_notifications: bool = Field(default=True, description="Send summary emails")
    summary_frequency: str = Field(default="immediate", description="Summary frequency (immediate, hourly, daily)")
    critical_notifications_only: bool = Field(default=False, description="Send only critical notifications")
    max_notifications_per_email: int = Field(default=100, description="Maximum notifications per email")
    
    # Email Content
    subject_prefix: str = Field(default="[TraceOne Alert]", description="Email subject prefix")
    template_dir: Optional[str] = Field(default=None, description="Custom email template directory")
    
    @validator('smtp_port')
    def validate_smtp_port(cls, v):
        if v < 1 or v > 65535:
            raise ValueError('SMTP port must be between 1 and 65535')
        return v
    
    @validator('summary_frequency')
    def validate_summary_frequency(cls, v):
        valid_frequencies = ['immediate', 'hourly', 'daily']
        if v.lower() not in valid_frequencies:
            raise ValueError(f'Summary frequency must be one of: {valid_frequencies}')
        return v.lower()
    
    @validator('to_emails', pre=True)
    def validate_to_emails(cls, v):
        if isinstance(v, str):
            return [email.strip() for email in v.split(',') if email.strip()]
        return v or []


class HubSpotNotificationConfig(BaseModel):
    """HubSpot notification configuration"""
    enabled: bool = Field(default=False, description="Enable HubSpot notifications")
    
    # API Configuration
    api_token: str = Field(default="", description="HubSpot API access token")
    base_url: str = Field(default="https://api.hubapi.com", description="HubSpot API base URL")
    timeout: int = Field(default=30, description="API request timeout in seconds")
    rate_limit_delay: float = Field(default=0.1, description="Delay between API calls in seconds")
    batch_size: int = Field(default=10, description="Batch size for processing notifications")
    
    # Company Mapping
    duns_property_name: str = Field(default="duns_number", description="HubSpot property name for DUNS numbers")
    company_domain_property: str = Field(default="domain", description="HubSpot property name for company domain")
    create_missing_companies: bool = Field(default=True, description="Create companies if they don't exist in HubSpot")
    
    # Default Properties for New Companies
    default_company_properties: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "TraceOne D&B Monitoring",
            "lifecyclestage": "lead"
        },
        description="Default properties to set when creating new companies"
    )
    
    # Task and Note Configuration
    task_owner_email: Optional[str] = Field(default=None, description="Email of default task owner")
    pipeline_id: Optional[str] = Field(default=None, description="HubSpot pipeline ID for deals")
    deal_stage_id: Optional[str] = Field(default=None, description="HubSpot deal stage ID")
    
    # Notification Action Mappings
    notification_actions: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "DELETE": ["create_task", "create_note", "update_property"],
            "TRANSFER": ["create_task", "create_note", "update_property"],
            "UNDER_REVIEW": ["create_task", "create_note"],
            "UPDATE": ["create_note", "update_property"],
            "SEED": ["update_company", "create_note"],
            "UNDELETE": ["create_note", "update_property"],
            "REVIEWED": ["create_note"],
            "EXIT": ["create_task", "create_note"],
            "REMOVED": ["create_task", "create_note"]
        },
        description="Actions to take for each notification type"
    )
    
    @validator('rate_limit_delay')
    def validate_rate_limit_delay(cls, v):
        if v < 0 or v > 10:
            raise ValueError('Rate limit delay must be between 0 and 10 seconds')
        return v
    
    @validator('batch_size')
    def validate_batch_size(cls, v):
        if v < 1 or v > 100:
            raise ValueError('Batch size must be between 1 and 100')
        return v
    
    
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
    sftp_storage: SFTPStorageConfig = Field(default_factory=SFTPStorageConfig)
    local_storage: LocalFileStorageConfig = Field(default_factory=LocalFileStorageConfig)
    email_notifications: EmailNotificationConfig = Field(default_factory=EmailNotificationConfig)
    hubspot_notifications: HubSpotNotificationConfig = Field(default_factory=HubSpotNotificationConfig)

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
        
        if self.config_path:
            # Load environment variables from corresponding .env file
            self._load_env_file_for_config(self.config_path)
            # Load from YAML file
            config_data = self._load_yaml_config(self.config_path)
        else:
            # Load environment variables from default locations
            load_dotenv()
            # Load from environment variables
            config_data = self._load_env_config()
        
        # Validate and create configuration object
        self._config = AppConfig(**config_data)
        return self._config
    
    def _load_env_file_for_config(self, config_path: str):
        """Load corresponding .env file for a YAML config file"""
        config_file = Path(config_path)
        config_dir = config_file.parent
        config_name = config_file.stem  # e.g., 'dev' from 'dev.yaml'
        
        # Try multiple .env file patterns
        env_patterns = [
            config_dir / f"{config_name}.env",  # e.g., config/dev.env
            config_dir / ".env",               # e.g., config/.env
            Path(".env"),                      # project root .env
        ]
        
        for env_file in env_patterns:
            if env_file.exists():
                logger.debug(f"Loading environment file: {env_file}")
                load_dotenv(env_file)
                return
        
        # If no specific .env file found, try default load_dotenv
        load_dotenv()
    
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
            "sftp_storage": {
                "enabled": os.getenv("SFTP_ENABLED", "false").lower() == "true",
                "hostname": os.getenv("SFTP_HOSTNAME", ""),
                "port": int(os.getenv("SFTP_PORT", "22")),
                "username": os.getenv("SFTP_USERNAME", ""),
                "password": os.getenv("SFTP_PASSWORD"),
                "private_key_path": os.getenv("SFTP_PRIVATE_KEY_PATH"),
                "private_key_passphrase": os.getenv("SFTP_PRIVATE_KEY_PASSPHRASE"),
                "remote_base_path": os.getenv("SFTP_REMOTE_PATH", "/notifications"),
                "file_format": os.getenv("SFTP_FILE_FORMAT", "json"),
                "compress_files": os.getenv("SFTP_COMPRESS", "false").lower() == "true",
                "timeout": int(os.getenv("SFTP_TIMEOUT", "30")),
                "max_retries": int(os.getenv("SFTP_MAX_RETRIES", "3")),
                "organize_by_date": os.getenv("SFTP_ORGANIZE_BY_DATE", "true").lower() == "true",
                "organize_by_registration": os.getenv("SFTP_ORGANIZE_BY_REGISTRATION", "true").lower() == "true",
            },
            "local_storage": {
                "enabled": os.getenv("LOCAL_STORAGE_ENABLED", "false").lower() == "true",
                "base_path": os.getenv("LOCAL_STORAGE_PATH", "./notifications"),
                "file_format": os.getenv("LOCAL_STORAGE_FORMAT", "json"),
                "compress_files": os.getenv("LOCAL_STORAGE_COMPRESS", "false").lower() == "true",
                "organize_by_date": os.getenv("LOCAL_STORAGE_ORGANIZE_BY_DATE", "true").lower() == "true",
                "organize_by_registration": os.getenv("LOCAL_STORAGE_ORGANIZE_BY_REGISTRATION", "true").lower() == "true",
                "file_permissions": int(os.getenv("LOCAL_STORAGE_FILE_PERMS", "644"), 8),
                "directory_permissions": int(os.getenv("LOCAL_STORAGE_DIR_PERMS", "755"), 8),
                "max_files_per_directory": int(os.getenv("LOCAL_STORAGE_MAX_FILES", "1000")),
                "enable_rotation": os.getenv("LOCAL_STORAGE_ROTATION", "false").lower() == "true",
            },
            "hubspot_notifications": {
                "enabled": os.getenv("HUBSPOT_ENABLED", "false").lower() == "true",
                "api_token": os.getenv("HUBSPOT_API_TOKEN", ""),
                "base_url": os.getenv("HUBSPOT_BASE_URL", "https://api.hubapi.com"),
                "timeout": int(os.getenv("HUBSPOT_TIMEOUT", "30")),
                "rate_limit_delay": float(os.getenv("HUBSPOT_RATE_LIMIT_DELAY", "0.1")),
                "batch_size": int(os.getenv("HUBSPOT_BATCH_SIZE", "10")),
                "duns_property_name": os.getenv("HUBSPOT_DUNS_PROPERTY", "duns_number"),
                "company_domain_property": os.getenv("HUBSPOT_DOMAIN_PROPERTY", "domain"),
                "create_missing_companies": os.getenv("HUBSPOT_CREATE_MISSING", "true").lower() == "true",
                "task_owner_email": os.getenv("HUBSPOT_TASK_OWNER_EMAIL"),
                "pipeline_id": os.getenv("HUBSPOT_PIPELINE_ID"),
                "deal_stage_id": os.getenv("HUBSPOT_DEAL_STAGE_ID"),
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
