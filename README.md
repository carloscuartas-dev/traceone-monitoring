# TraceOne Monitoring Service

D&B Direct+ API Integration for Real-time Company Data Monitoring

## Overview

This service provides real-time monitoring capabilities for company data using D&B's Direct+ V2.02 Pull API. It enables TraceOne to maintain up-to-date third-party information through automated monitoring and notification processing.

## Features

- ✅ **Real-time Monitoring**: Pull API integration for immediate data updates
- ✅ **Authentication Management**: OAuth 2.0 token handling with automatic refresh
- ✅ **Rate Limiting**: Built-in rate limiting (5 calls/second) with exponential backoff
- ✅ **Error Recovery**: Comprehensive error handling with replay functionality
- ✅ **Scalable Architecture**: Microservices-ready with async support
- ✅ **Monitoring & Alerting**: Prometheus metrics and structured logging
- ✅ **Security**: Encryption, audit trails, and secure credential management

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 13+ (or Docker)
- D&B Direct+ API credentials

### Installation

1. **Clone and setup the project:**
```bash
cd traceone-monitoring
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

2. **Install development dependencies:**
```bash
pip install -e ".[dev,test]"
```

3. **Set up environment variables:**
```bash
cp config/dev.env.example config/dev.env
# Edit config/dev.env with your D&B API credentials
```

4. **Initialize the database:**
```bash
alembic upgrade head
```

5. **Run the service:**
```bash
traceone-monitor start --config config/dev.yaml
```

## Architecture

```
traceone-monitoring/
├── src/traceone_monitoring/     # Main application code
│   ├── auth/                    # Authentication and security
│   ├── api/                     # API clients and endpoints
│   ├── models/                  # Data models and schemas
│   ├── services/                # Business logic services
│   └── utils/                   # Utility functions
├── tests/                       # Test suite
├── config/                      # Configuration files
├── docs/                        # Documentation
├── scripts/                     # Deployment and utility scripts
└── docker/                      # Container configurations
```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DNB_CLIENT_ID` | D&B API Client ID | Yes | - |
| `DNB_CLIENT_SECRET` | D&B API Client Secret | Yes | - |
| `DATABASE_URL` | PostgreSQL connection string | Yes | - |
| `LOG_LEVEL` | Logging level | No | INFO |
| `ENVIRONMENT` | Environment (dev/staging/prod) | No | dev |

### Registration Configuration

Create monitoring registrations using YAML configuration:

```yaml
# config/registrations/standard_monitoring.yaml
reference: "TraceOne_Standard_Monitoring"
lod: "duns_list"
seedData: false
dataBlocks:
  - "companyinfo_L2_v1"
  - "principalscontacts_L1_v1"
  - "hierarchyconnections_L1_v1"
notificationType: "UPDATE"
mode: "API_PULL"
jsonPathInclusion:
  - "organization.primaryName"
  - "organization.registeredAddress"
  - "organization.telephone"
```

## Usage Examples

### Basic Monitoring Setup

```python
from traceone_monitoring import DNBMonitoringService

# Initialize the service
service = DNBMonitoringService.from_config("config/dev.yaml")

# Create a registration
registration = await service.create_registration("standard_monitoring.yaml")

# Add DUNS to monitoring
duns_list = ["123456789", "987654321"]
await service.add_duns_to_monitoring(registration.id, duns_list)

# Start monitoring
async for notifications in service.monitor_continuously(registration.id):
    for notification in notifications:
        print(f"Update for DUNS {notification.duns}: {notification.type}")
        await service.process_notification(notification)
```

### Replay Missed Notifications

```python
# Replay notifications from a specific timestamp
start_time = "2025-08-20T10:00:00Z"
replayed_notifications = await service.replay_notifications(
    registration.id, 
    start_time
)
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/traceone_monitoring --cov-report=html

# Run specific test categories
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Development Server

```bash
# Start development server with hot reload
python -m traceone_monitoring.server --reload --config config/dev.yaml
```

## Deployment

### Docker

```bash
# Build the image
docker build -f docker/Dockerfile -t traceone-monitoring:latest .

# Run the container
docker run -p 8080:8080 --env-file config/prod.env traceone-monitoring:latest
```

### Kubernetes

```bash
# Apply Kubernetes configurations
kubectl apply -f docker/k8s/
```

## Monitoring and Observability

### Metrics

The service exposes Prometheus metrics at `/metrics`:

- `dnb_api_calls_total`: Total API calls made
- `dnb_api_errors_total`: Total API errors
- `notifications_processed_total`: Total notifications processed
- `notifications_processing_duration`: Notification processing time
- `active_registrations`: Number of active registrations

### Health Checks

- **Liveness**: `/health/live`
- **Readiness**: `/health/ready`
- **Metrics**: `/metrics`

### Logging

Structured JSON logging with configurable levels:

```json
{
  "timestamp": "2025-08-25T18:00:00Z",
  "level": "INFO",
  "logger": "traceone_monitoring.api.pull_client",
  "message": "Processing notification",
  "duns": "123456789",
  "notification_type": "UPDATE",
  "registration_id": "TraceOne_Standard"
}
```

## Security

- **Encryption**: All sensitive data encrypted at rest and in transit
- **Authentication**: OAuth 2.0 with automatic token refresh
- **Rate Limiting**: Built-in rate limiting with configurable limits
- **Audit Trail**: Comprehensive logging of all operations
- **Secrets Management**: Environment-based secret management

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions and support:
- 📧 Email: support@traceone.com
- 📖 Documentation: [docs/](docs/)
- 🐛 Issues: [GitHub Issues](https://github.com/traceone/traceone-monitoring/issues)

## Roadmap

- [x] **Phase 1**: Core Pull API implementation
- [ ] **Phase 2**: Advanced error handling and resilience
- [ ] **Phase 3**: Performance optimization and monitoring
- [ ] **Phase 4**: ML-based anomaly detection
- [ ] **Phase 5**: Multi-region deployment support
