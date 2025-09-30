# DUNS List Testing Guide

This guide shows you how to start testing with DUNS lists in your TraceOne monitoring system.

## Quick Start

### 1. Run the Basic DUNS Test

```bash
# Run the immediate test script
python3 tests/examples/run_duns_test.py
```

### 2. Run the Pytest Examples

```bash
# Run all DUNS tests
pytest tests/examples/test_duns_example.py -v

# Run specific DUNS test
pytest tests/examples/test_duns_example.py::TestDunsListOperations::test_registration_with_duns_list -v

# Run notification processing test
pytest tests/examples/test_duns_example.py::TestDunsListOperations::test_notification_processing_by_duns -v
```

## Basic DUNS Setup Pattern

### Step 1: Define Your DUNS List
```python
# Example DUNS numbers (replace with your actual company DUNS)
my_portfolio_duns = [
    "804735132",  # Apple Inc. (example)
    "069032677",  # Microsoft Corp (example)  
    "006273905",  # Amazon.com Inc. (example)
    "804735052",  # Alphabet Inc. (example)
    "042112940"   # Meta Platforms (example)
]
```

### Step 2: Create Registration Configuration
```python
from traceone_monitoring.models.registration import RegistrationConfig

config = RegistrationConfig(
    reference="MyPortfolio_Q4_2025",
    description="My company portfolio monitoring",
    duns_list=my_portfolio_duns,
    dataBlocks=[
        "companyinfo_L2_v1",      # Basic company info
        "principalscontacts_L1_v1", # Key contacts
        "financialstrength_L1_v1"   # Financial data
    ],
    jsonPathInclusion=[
        "organization.primaryName",
        "organization.registeredAddress",
        "organization.numberOfEmployees",
        "organization.annualSalesRevenue",
        "organization.operatingStatus"
    ]
)
```

### Step 3: Test Notifications
```python
from traceone_monitoring.models.notification import (
    Notification, NotificationElement, NotificationType, Organization
)
from datetime import datetime

# Create a test notification for a specific DUNS
notification = Notification(
    type=NotificationType.UPDATE,
    organization=Organization(duns="804735132"),
    elements=[
        NotificationElement(
            element="organization.numberOfEmployees",
            previous="164000",
            current="165000",
            timestamp=datetime.utcnow()
        )
    ],
    deliveryTimeStamp=datetime.utcnow()
)
```

## Common Testing Patterns

### 1. DUNS Validation
```python
def validate_duns(duns: str) -> bool:
    """Validate a DUNS number"""
    return len(duns) == 9 and duns.isdigit() and duns != "000000000"

# Test all DUNS in your list
for duns in my_portfolio_duns:
    assert validate_duns(duns), f"Invalid DUNS: {duns}"
```

### 2. Filter Notifications by DUNS
```python
def filter_notifications_by_duns(notifications, target_duns):
    """Filter notifications for a specific DUNS"""
    return [n for n in notifications if n.organization.duns == target_duns]

# Example usage
apple_notifications = filter_notifications_by_duns(notifications, "804735132")
```

### 3. Group Notifications by Company
```python
def group_notifications_by_duns(notifications):
    """Group notifications by DUNS number"""
    grouped = {}
    for notification in notifications:
        duns = notification.organization.duns
        if duns not in grouped:
            grouped[duns] = []
        grouped[duns].append(notification)
    return grouped
```

### 4. Mock API Responses with DUNS Data
```python
def create_mock_api_response(duns_list):
    """Create mock D&B API response with notifications for each DUNS"""
    return {
        "transactionDetail": {
            "transactionID": "test-123",
            "transactionTimestamp": "2025-09-23T13:00:00Z",
            "inLanguage": "en-US"
        },
        "inquiryDetail": {
            "reference": "TestPortfolio"
        },
        "notifications": [
            {
                "type": "UPDATE",
                "organization": {"duns": duns},
                "elements": [{
                    "element": "organization.primaryName",
                    "previous": f"Old Name {i}",
                    "current": f"New Name {i}",
                    "timestamp": "2025-09-23T12:00:00Z"
                }],
                "deliveryTimeStamp": "2025-09-23T13:00:00Z"
            }
            for i, duns in enumerate(duns_list, 1)
        ]
    }
```

## Data Blocks Reference

Common D&B data blocks you can monitor:

```python
# Basic company information
"companyinfo_L2_v1"

# Principal contacts and management
"principalscontacts_L1_v1"

# Financial strength indicators
"financialstrength_L1_v1"

# Business information
"businessinfo_L1_v1"

# Corporate linkage
"corporatelinkage_L1_v1"
```

## JSON Path Fields Reference

Common fields to monitor:

```python
# Company basics
"organization.primaryName"
"organization.registeredAddress"
"organization.telephone"
"organization.websiteAddress"

# Business data
"organization.numberOfEmployees"
"organization.annualSalesRevenue"
"organization.operatingStatus"
"organization.yearStarted"

# Financial indicators
"organization.financialStrength"
"organization.creditRating"
"organization.paydexScore"
```

## Running Tests

### Individual Tests
```bash
# Test registration creation
pytest tests/examples/test_duns_example.py::TestDunsListOperations::test_registration_with_duns_list

# Test adding DUNS to existing registration
pytest tests/examples/test_duns_example.py::TestDunsListOperations::test_add_duns_to_existing_registration

# Test DUNS validation
pytest tests/examples/test_duns_example.py::TestDunsListOperations::test_duns_validation
```

### Async Tests
```bash
# Run async monitoring tests
pytest tests/examples/test_duns_example.py -k async -v

# Test continuous monitoring
pytest tests/examples/test_duns_example.py::TestDunsListOperations::test_continuous_monitoring_with_duns_filter
```

### Integration Tests
```bash
# Run your project's integration tests
pytest tests/integration/ -v

# Run specific integration test
pytest tests/integration/test_dev_registration.py -v
```

## Next Steps

1. **Replace Example DUNS**: Update the example DUNS numbers with your actual company DUNS numbers.

2. **Customize Data Blocks**: Choose the specific D&B data blocks relevant to your monitoring needs.

3. **Set Monitoring Fields**: Define which organization fields you want to track changes for.

4. **Test Your Configuration**: Run the tests with your actual DUNS data.

5. **Integration Testing**: Test with your actual D&B API credentials in a development environment.

## Tips for Production

- **DUNS Validation**: Always validate DUNS format before sending to D&B API
- **Rate Limiting**: Respect D&B API rate limits when testing with many DUNS
- **Error Handling**: Handle cases where DUNS numbers might not be found in D&B
- **Batch Processing**: When working with large DUNS lists, process them in batches
- **Monitoring**: Set up alerts for when notifications arrive for critical DUNS numbers

## Example Test Command

```bash
# Run the complete DUNS testing suite
pytest tests/examples/test_duns_example.py -v --tb=short
```

This will run all DUNS-related tests and show you exactly how the system handles your DUNS lists!
