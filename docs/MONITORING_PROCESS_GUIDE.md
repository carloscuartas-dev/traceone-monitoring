# TraceOne Monitoring Process - Complete Guide

## Overview

The TraceOne Monitoring System is a comprehensive solution for monitoring D&B (Dun & Bradstreet) data changes and automatically storing notifications to multiple storage backends. This guide explains the complete end-to-end process.

## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   D&B API       │    │  TraceOne        │    │  Storage        │
│                 │    │  Monitoring      │    │  Backends       │
│ - Authentication│◄──►│  Service         │◄──►│                 │
│ - Registrations │    │                  │    │ - SFTP Server   │
│ - Notifications │    │ - Registration   │    │ - Local Files   │
│                 │    │   Management     │    │ - Database      │
└─────────────────┘    │ - Notification   │    │ - Cloud Storage │
                       │   Processing     │    │                 │
                       │ - Multi-Storage  │    └─────────────────┘
                       │   Handlers       │
                       └──────────────────┘
```

## 📋 Complete Monitoring Workflow

### 1. System Initialization

#### Configuration Loading
```yaml
# Configuration file (e.g., config/multi_storage_demo.yaml)
environment: "development"
debug: true

dnb_api:
  base_url: "https://plus.dnb.com"
  client_id: "${DNB_CLIENT_ID}"
  client_secret: "${DNB_CLIENT_SECRET}"
  rate_limit: 5.0

database:
  url: "${DATABASE_URL}"
  pool_size: 10

monitoring:
  polling_interval: 300  # seconds
  max_notifications: 100
  notification_batch_size: 50

# Storage backends (can enable multiple)
sftp_storage:
  enabled: true
  hostname: "sftp.example.com"
  username: "user"
  private_key_path: "~/.ssh/id_rsa"
  remote_base_path: "/notifications"

local_storage:
  enabled: true
  base_path: "./notifications"
  file_format: "json"
  organize_by_date: true
```

#### Service Initialization Process
1. **Load Configuration**: Parse YAML config and environment variables
2. **Initialize Components**:
   - DNB API Authenticator
   - API Client with rate limiting
   - Pull API Client for notifications
   - Registration Manager
3. **Initialize Storage Handlers**: 
   - SFTP handler (if enabled)
   - Local file handler (if enabled)
   - Database handler (if configured)
4. **Register Notification Handlers**: Automatically register all enabled storage handlers

### 2. Authentication Process

#### D&B API Authentication Flow
```python
# Authentication happens automatically
authenticator = DNBAuthenticator(config.dnb_api)

# Token lifecycle management
1. Request initial token using client credentials
2. Monitor token expiration (with buffer time)
3. Automatically refresh before expiration
4. Handle authentication failures gracefully
```

#### Token Management
- **Grant Type**: Client Credentials OAuth2 flow
- **Token Storage**: In-memory with automatic refresh
- **Refresh Buffer**: Configurable buffer time before expiration
- **Error Handling**: Retry logic with exponential backoff

### 3. Registration Management

#### Creating Monitoring Registrations
A registration tells D&B what data to monitor and how to deliver notifications.

```python
# Example: Create a standard monitoring registration
registration_config = RegistrationConfig(
    reference="company_monitoring_001",
    description="Monitor key company information",
    duns_list=["123456789", "987654321"],  # Companies to monitor
    dataBlocks=[                           # What data to monitor
        "companyinfo_L2_v1",
        "principalscontacts_L1_v1",
        "hierarchyconnections_L1_v1"
    ],
    jsonPathInclusion=[                    # Specific fields to include
        "organization.primaryName",
        "organization.registeredAddress",
        "organization.telephone"
    ]
)

# Create the registration
registration = service.create_registration(registration_config)
```

#### Registration Lifecycle
1. **Creation**: Submit registration request to D&B
2. **Validation**: D&B validates DUNS numbers and configuration
3. **Activation**: Registration becomes active for monitoring
4. **Management**: Add/remove DUNS, modify configuration
5. **Status Monitoring**: Track registration health and status

### 4. Notification Monitoring

#### Continuous Monitoring Process

```python
# Option 1: Continuous monitoring with async generator
async for notifications in service.monitor_continuously(
    registration_reference="company_monitoring_001",
    polling_interval=300  # 5 minutes
):
    if notifications:
        print(f"Received {len(notifications)} notifications")
        # Notifications are automatically processed by registered handlers
```

#### Polling Mechanism
1. **Timer-Based Polling**: Configurable polling interval (default: 5 minutes)
2. **Pull API Calls**: Request new notifications from D&B
3. **Batch Processing**: Handle notifications in configurable batch sizes
4. **Error Handling**: Retry failed requests with exponential backoff
5. **Rate Limiting**: Respect D&B API rate limits

#### Notification Types
- **UPDATE**: Data changes for existing companies
- **DELETE**: Company records marked for deletion
- **TRANSFER**: Company ownership transfers
- **SEED**: Initial data load notifications
- **UNDELETE**: Previously deleted records restored
- **REVIEWED**: Manual review completed
- **UNDER_REVIEW**: Records flagged for manual review

### 5. Notification Processing

#### Processing Pipeline
Each notification goes through this pipeline:

```python
# 1. Receive notification from D&B Pull API
notification = Notification(
    type=NotificationType.UPDATE,
    organization=Organization(duns="123456789"),
    elements=[...],  # Changed data elements
    delivery_timestamp=datetime.now()
)

# 2. Process through monitoring service
success = await service.process_notification(notification)

# 3. Automatically triggers all registered handlers:
# - SFTP storage handler
# - Local file storage handler  
# - Database handler
# - Custom handlers
```

#### Multi-Handler Processing
1. **Sequential Processing**: Each handler processes notifications independently
2. **Error Isolation**: Handler failures don't affect other handlers
3. **Logging**: Detailed logging for each handler's operations
4. **Status Tracking**: Mark notifications as processed/failed

### 6. Storage Backend Operations

#### SFTP Storage Handler
```python
# Automatic SFTP storage when notifications are processed
sftp_handler = SFTPNotificationHandler(config.sftp_storage)

# Storage process:
1. Group notifications by registration
2. Connect to SFTP server (with SSH key or password)
3. Create directory structure: /notifications/2025/09/14/registration_name/
4. Store notifications as JSON/CSV/XML files
5. Optional compression
6. Connection pooling and retry logic
```

#### Local File Storage Handler
```python
# Automatic local file storage
local_handler = LocalFileNotificationHandler(config.local_storage)

# Storage process:
1. Create local directory structure: ./notifications/2025/09/14/registration_name/
2. Store notifications with metadata
3. Set proper file permissions
4. Optional compression and rotation
5. Statistics tracking
```

#### File Organization Structure
```
notifications/
├── 2025/
│   └── 09/
│       └── 14/
│           ├── company_monitoring_001/
│           │   ├── notifications_20250914_143022_001.json
│           │   └── notifications_20250914_150115_002.json
│           └── financial_monitoring_002/
│               └── notifications_20250914_144533_001.json
```

#### Stored File Format (JSON Example)
```json
{
  "metadata": {
    "export_timestamp": "2025-09-14T14:30:22.123456Z",
    "notification_count": 5,
    "format_version": "1.0",
    "storage_type": "local_file",
    "registration_reference": "company_monitoring_001"
  },
  "notifications": [
    {
      "id": "uuid-here",
      "type": "UPDATE",
      "organization": {
        "duns": "123456789"
      },
      "elements": [
        {
          "element": "organization.primaryName",
          "previous": "Old Company Name",
          "current": "New Company Name",
          "timestamp": "2025-09-14T14:28:15.123456Z"
        }
      ],
      "delivery_timestamp": "2025-09-14T14:30:00.000000Z",
      "processed": true,
      "processing_timestamp": "2025-09-14T14:30:22.123456Z"
    }
  ]
}
```

### 7. Background Monitoring

#### Automatic Background Processing
```python
# Start background monitoring (non-blocking)
service.start_background_monitoring(
    registration_reference="company_monitoring_001",
    notification_handler=custom_handler,  # Optional additional handler
    polling_interval=300
)

# Background process automatically:
# 1. Polls for notifications every 5 minutes
# 2. Processes through all registered handlers
# 3. Handles errors and retries
# 4. Logs all operations
# 5. Manages API rate limits
```

#### Task Management
- **Async Tasks**: Non-blocking background operations
- **Task Lifecycle**: Start, stop, health monitoring
- **Error Recovery**: Automatic restart on failures
- **Graceful Shutdown**: Clean task termination

### 8. Health Monitoring & Status

#### Service Health Checks
```python
# Get comprehensive service status
status = service.get_service_status()

# Status includes:
{
  "service": {"running": True, "environment": "development"},
  "authentication": {"is_authenticated": True, "token_expires_in": 3500},
  "api_client": {"health_check": True, "rate_limit": 5.0},
  "registrations": {"total_count": 3, "active_count": 2},
  "notification_handlers": {"count": 2},
  "sftp_storage": {"enabled": True, "status": "healthy", "files_stored": 150},
  "local_storage": {"enabled": True, "status": "healthy", "files_stored": 150}
}
```

#### Monitoring Capabilities
- **Real-time Status**: Current system health
- **Storage Statistics**: Files stored, errors, performance
- **API Metrics**: Rate limiting, response times, errors
- **Registration Health**: Active/inactive registrations
- **Handler Performance**: Processing success/failure rates

### 9. Error Handling & Recovery

#### Multi-Level Error Handling
1. **API Level**: HTTP errors, authentication failures, rate limiting
2. **Storage Level**: Connection failures, disk space, permissions
3. **Processing Level**: Malformed notifications, validation errors
4. **Service Level**: Configuration errors, startup failures

#### Recovery Strategies
- **Exponential Backoff**: Retry failed operations with increasing delays
- **Circuit Breaker**: Temporarily disable failing components
- **Graceful Degradation**: Continue operations with partial functionality
- **Comprehensive Logging**: Detailed error tracking and debugging

### 10. Configuration Management

#### Environment-Based Configuration
```bash
# Production environment variables
export DNB_CLIENT_ID="your_production_client_id"
export DNB_CLIENT_SECRET="your_production_secret"
export DATABASE_URL="postgresql://user:pass@host/db"
export SFTP_HOSTNAME="production.sftp.server.com"
export LOCAL_STORAGE_PATH="/data/notifications"
```

#### Configuration Validation
- **Schema Validation**: Pydantic models ensure configuration correctness
- **Environment Substitution**: Automatic environment variable replacement
- **Required Fields**: Validation of mandatory configuration
- **Type Safety**: Strong typing prevents configuration errors

## 🚀 Getting Started Examples

### Basic Monitoring Setup
```python
# 1. Initialize service
service = DNBMonitoringService.from_config("config/production.yaml")

# 2. Create registration
config = create_standard_monitoring_registration(
    reference="my_monitoring",
    duns_list=["123456789", "987654321"],
    description="Monitor key suppliers"
)
registration = service.create_registration(config)

# 3. Start monitoring
async for notifications in service.monitor_continuously(
    registration.reference
):
    print(f"Processed {len(notifications)} notifications")
    # Notifications automatically stored to configured backends
```

### Background Monitoring
```python
# Start non-blocking background monitoring
service.start_background_monitoring(
    registration_reference="my_monitoring",
    notification_handler=log_notification_handler,
    polling_interval=300
)

# Service continues monitoring in background
# Check status periodically
while True:
    status = service.get_service_status()
    print(f"Monitoring {status['registrations']['active_count']} registrations")
    await asyncio.sleep(60)
```

## 🔍 Monitoring Best Practices

1. **Registration Management**: Keep registrations focused and manageable
2. **Polling Frequency**: Balance between real-time needs and API limits
3. **Storage Strategy**: Use multiple storage backends for redundancy
4. **Error Monitoring**: Monitor logs for storage and API failures
5. **Capacity Planning**: Monitor disk space and API rate limits
6. **Security**: Secure storage of API credentials and SSH keys
7. **Backup Strategy**: Regular backups of stored notifications
8. **Performance Monitoring**: Track processing times and success rates

## 📊 Monitoring Metrics

The system provides comprehensive metrics for monitoring:

- **API Metrics**: Request count, response times, error rates
- **Storage Metrics**: Files stored, storage used, write times
- **Processing Metrics**: Notifications processed, success rates
- **System Metrics**: Memory usage, CPU usage, disk space
- **Business Metrics**: Companies monitored, notification types

This complete monitoring process provides a robust, scalable solution for tracking D&B data changes with automatic multi-backend storage and comprehensive error handling.
