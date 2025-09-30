# Real-time Testing Guide for TraceOne Monitoring

This guide explains how to work with **real-time D&B data** using your **dev registration entity** for comprehensive testing of the TraceOne Monitoring Service.

## 🚀 Quick Start

### 1. Setup Your Environment

First, configure your D&B API credentials:

```bash
# Option 1: Interactive setup
python scripts/setup_real_time_testing.py setup

# Option 2: Quick setup with credentials
python scripts/setup_real_time_testing.py quick-setup --client-id YOUR_ID --client-secret YOUR_SECRET

# Option 3: Check existing configuration
python scripts/setup_real_time_testing.py check
```

### 2. Install Dependencies

Make sure you have all required packages:

```bash
pip install -e ".[dev,test]"
```

### 3. Run Your First Real-time Test

```bash
# Simple authentication test
python scripts/real_time_testing.py

# Test with specific DUNS from your dev registration
python scripts/real_time_testing.py -d YOUR_DUNS_NUMBER

# Monitor for 10 minutes with 30-second polling
python scripts/real_time_testing.py -d YOUR_DUNS_NUMBER -dur 10 -p 30
```

## 📋 Testing Scenarios

### Authentication Testing

Test your D&B API connection:

```python
from scripts.real_time_testing import RealTimeTestRunner

async def test_connection():
    test_runner = RealTimeTestRunner()
    await test_runner.setup()
    success = await test_runner.test_authentication()
    print(f"Authentication: {'✅ Success' if success else '❌ Failed'}")
```

### Real-time Monitoring

Monitor companies for data changes:

```bash
# Monitor specific companies for 5 minutes
python scripts/real_time_testing.py \
  -d 123456789 \
  -d 987654321 \
  --monitoring-type standard \
  --duration 5 \
  --polling-interval 30
```

### Portfolio Testing

Test portfolio management features:

```bash
# Run portfolio creation example
python examples/portfolio_creation.py supplier

# Run financial risk portfolio
python examples/portfolio_creation.py financial

# Run multi-tier portfolio setup
python examples/portfolio_creation.py multi
```

## 🧪 Integration Testing

Run comprehensive integration tests with your dev registration:

```bash
# Basic integration tests
python -m pytest tests/integration/test_dev_registration.py -v

# Include slow tests (longer monitoring sessions)
python -m pytest tests/integration/test_dev_registration.py -v -m "slow"

# Run specific test
python -m pytest tests/integration/test_dev_registration.py::TestDevRegistrationIntegration::test_authentication -v
```

## 📊 CLI Commands for Real-time Testing

### Service Status and Health

```bash
# Check service status
traceone-monitor status

# Perform health check
traceone-monitor health

# Generate configuration template
traceone-monitor generate-config standard
```

### Registration Management

```bash
# Create new registration
traceone-monitor create-registration \
  --reference "MyTest_Registration" \
  --type standard \
  --duns 123456789 \
  --duns 987654321

# Add DUNS to existing registration
traceone-monitor add-duns \
  --reference "MyTest_Registration" \
  --duns 555666777 \
  --batch

# Activate monitoring
traceone-monitor activate --reference "MyTest_Registration"
```

### Real-time Operations

```bash
# Pull notifications on-demand
traceone-monitor pull \
  --reference "MyTest_Registration" \
  --max-notifications 20

# Start continuous monitoring
traceone-monitor monitor \
  --reference "MyTest_Registration" \
  --interval 60 \
  --max-notifications 50
```

## 🔧 Configuration for Testing

### Environment Variables

Your `config/dev.env` should contain:

```bash
# D&B API Credentials (REQUIRED)
DNB_CLIENT_ID=your_actual_client_id
DNB_CLIENT_SECRET=your_actual_client_secret

# Development Settings
DATABASE_URL=sqlite:///./data/traceone_monitoring_dev.db
ENCRYPTION_KEY=your_generated_encryption_key
LOG_LEVEL=DEBUG
ENVIRONMENT=development
DEBUG=true

# Testing-specific Settings
MONITORING_POLLING_INTERVAL=60    # Faster polling for testing
MONITORING_MAX_NOTIFICATIONS=50   # Manageable batch size
API_TIMEOUT=30                    # Shorter timeout for testing
```

### Registration Types

**Standard Monitoring** - Basic company information:
- Company info, contacts, hierarchy
- Address changes, status updates
- Business entity modifications

**Financial Monitoring** - Financial and risk data:
- Financial statements, payment history
- Credit ratings, risk assessments
- Financial strength indicators

## 📝 Real DUNS Numbers

**⚠️ IMPORTANT**: Replace placeholder DUNS numbers with actual ones from your D&B dev registration:

```python
# In test files, replace these placeholders:
test_duns = [
    "123456789",  # ← Replace with your actual DUNS
    "987654321",  # ← Replace with your actual DUNS
    "555666777"   # ← Replace with your actual DUNS
]
```

## 🔍 Monitoring and Debugging

### Structured Logging

All real-time operations use structured logging:

```bash
# View logs in real-time
tail -f logs/traceone-monitoring-dev.log

# Filter for specific events
tail -f logs/traceone-monitoring-dev.log | grep "notification"
```

### Debug Information

Enable debug mode for detailed information:

```bash
export LOG_LEVEL=DEBUG
python scripts/real_time_testing.py -d YOUR_DUNS
```

## 🎯 Common Testing Patterns

### 1. Authentication First

Always test authentication before other operations:

```python
# Test pattern
async def my_test():
    service = DNBMonitoringService.from_config("config/dev.yaml")
    
    # Always check authentication first
    if not service.health_check():
        raise RuntimeError("Authentication failed")
    
    # Your test logic here...
```

### 2. Short Polling Intervals

Use short intervals for testing:

```python
# Good for testing - polls every 15 seconds
async for notifications in service.monitor_continuously(
    registration_ref,
    polling_interval=15,
    max_notifications=10
):
    # Process notifications
```

### 3. Limited Duration

Set time limits for monitoring tests:

```python
from datetime import datetime, timedelta

end_time = datetime.now() + timedelta(minutes=2)
async for notifications in service.monitor_continuously(...):
    if datetime.now() > end_time:
        break
    # Process notifications
```

## 📈 Performance Testing

### Load Testing

Test with multiple registrations:

```python
# Create multiple registrations for load testing
for i in range(5):
    registration = await service.create_registration(
        f"LoadTest_{i}",
        your_duns_list
    )
```

### Rate Limit Testing

Monitor API rate limiting:

```python
# Service automatically handles rate limiting (5 calls/second)
# Monitor logs for rate limit warnings
```

## 🚨 Troubleshooting

### Common Issues

1. **Authentication Failures**
   ```bash
   # Check credentials
   python scripts/setup_real_time_testing.py check
   ```

2. **No Notifications**
   ```bash
   # Data may not have changed - try replay
   traceone-monitor pull --reference YOUR_REF --max-notifications 10
   ```

3. **Connection Timeouts**
   ```bash
   # Check network and increase timeout
   export API_TIMEOUT=60
   ```

### Debug Commands

```bash
# Test service health
traceone-monitor health

# Check configuration
traceone-monitor status

# Validate registration
python -c "
from traceone_monitoring import DNBMonitoringService
service = DNBMonitoringService.from_config()
status = service.get_service_status()
print(status)
"
```

## 🎉 Success Indicators

Your real-time testing setup is working correctly when you see:

✅ **Authentication successful** - API credentials validated  
✅ **Registration created** - Monitoring registration established  
✅ **Monitoring activated** - Ready to receive notifications  
✅ **Notifications pulled** - Successfully retrieving data updates  
✅ **Continuous monitoring** - Real-time polling operational  

## 📚 Next Steps

Once your real-time testing is working:

1. **Expand test coverage** with more DUNS numbers
2. **Test different data blocks** (financial vs. standard)
3. **Implement custom notification handlers**
4. **Set up automated monitoring workflows**
5. **Integrate with your existing systems**

## 📞 Support

If you encounter issues:

1. Check the logs: `tail -f logs/traceone-monitoring-dev.log`
2. Verify credentials: `python scripts/setup_real_time_testing.py check`
3. Test authentication: `traceone-monitor health`
4. Review D&B API documentation for your registration limits

---

**Ready to start real-time testing?** Run:
```bash
python scripts/setup_real_time_testing.py setup
```
