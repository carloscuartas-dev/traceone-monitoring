# Real-World DUNS Testing Guide

This guide shows you how to perform real tests with actual DUNS numbers and where the results are stored.

## 🚀 Quick Start - Real Testing

### 1. Set Up Your Environment

First, create your environment configuration file:

```bash
# Copy example environment
cp config/dev.env.example config/real-test.env

# Edit with your actual D&B credentials
nano config/real-test.env
```

Edit `config/real-test.env` with your credentials:
```bash
# D&B API Configuration
DNB_CLIENT_ID=your_actual_client_id
DNB_CLIENT_SECRET=your_actual_client_secret
DNB_BASE_URL=https://plus.dnb.com
DNB_RATE_LIMIT=5.0

# Database Configuration  
DATABASE_URL=sqlite:///./real_test_results.db

# Storage Configuration - Choose where to store results
LOCAL_STORAGE_ENABLED=true
LOCAL_STORAGE_PATH=./test_results
LOCAL_STORAGE_FORMAT=json
LOCAL_STORAGE_ORGANIZE_BY_DATE=true
LOCAL_STORAGE_ORGANIZE_BY_REGISTRATION=true

# Optional: SFTP Storage
SFTP_ENABLED=false
# SFTP_HOSTNAME=your-sftp-server.com
# SFTP_USERNAME=your_username
# SFTP_PASSWORD=your_password

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

### 2. Create Real-World Configuration

Create a configuration file for real testing:

```bash
# Create real test config
cp config/dev.yaml config/real-test.yaml
```

Edit `config/real-test.yaml`:
```yaml
# Real-World Test Configuration
environment: development
debug: true

# D&B API Configuration
dnb_api:
  base_url: "${DNB_BASE_URL:https://plus.dnb.com}"
  client_id: "${DNB_CLIENT_ID}"
  client_secret: "${DNB_CLIENT_SECRET}"
  rate_limit: 5.0
  timeout: 30
  retry_attempts: 3
  backoff_factor: 2.0

# Database Configuration
database:
  url: "${DATABASE_URL:sqlite:///./real_test_results.db}"
  pool_size: 10
  max_overflow: 20
  pool_timeout: 30
  pool_recycle: 3600

# Monitoring Configuration
monitoring:
  polling_interval: 60  # Poll every minute for testing
  max_notifications: 50
  notification_batch_size: 25
  replay_window_days: 7

# Storage Configuration
local_storage:
  enabled: true
  base_path: "./test_results"
  file_format: "json"
  compress_files: false
  organize_by_date: true
  organize_by_registration: true
  file_permissions: 0o644
  directory_permissions: 0o755
  max_files_per_directory: 1000
  enable_rotation: false

sftp_storage:
  enabled: false
  # Uncomment and configure if you want SFTP storage
  # hostname: "your-sftp-server.com"
  # port: 22
  # username: "${SFTP_USERNAME}"
  # password: "${SFTP_PASSWORD}"
  # remote_base_path: "/duns-test-results"
  # file_format: "json"
  # organize_by_date: true
  # organize_by_registration: true

# Logging Configuration
logging:
  level: "INFO"
  format: "json"
  file: "./logs/real-test.log"
  max_size: "50MB"
  backup_count: 3
```

## 📋 Step-by-Step Real Testing

### Step 1: Create Your Test Script

I've created a comprehensive real-world test script (`real_duns_test.py`) that handles:
- Real D&B API authentication
- Registration creation with actual DUNS
- Notification pulling and processing
- Result storage in multiple formats

### Step 2: Set Up Your Configuration Files

```bash
# 1. Create your environment file
cp config/dev.env.example config/real-test.env

# 2. Edit with YOUR actual D&B credentials
nano config/real-test.env
```

Add your real D&B credentials:
```bash
# Replace with your actual D&B credentials
DNB_CLIENT_ID=your_actual_client_id_here
DNB_CLIENT_SECRET=your_actual_secret_here
DNB_BASE_URL=https://plus.dnb.com
```

### Step 3: Run Real-World Tests

**Basic Test with Example DUNS:**
```bash
python3 real_duns_test.py --config config/real-test.yaml --env config/real-test.env
```

**Test with Your Actual DUNS:**
```bash
python3 real_duns_test.py \
  --config config/real-test.yaml \
  --env config/real-test.env \
  --duns 123456789 987654321 456789123 \
  --registration-name "MyCompanyPortfolio"
```

**Test with Continuous Monitoring:**
```bash
python3 real_duns_test.py \
  --config config/real-test.yaml \
  --env config/real-test.env \
  --duns 123456789 987654321 \
  --continuous-minutes 10 \
  --registration-name "ContinuousTest"
```

## 📁 Where Results Are Stored

Your test results are stored in multiple locations:

### 1. Local File Storage (Primary)

**Location:** `./test_results/` (configurable)

**Structure:**
```
test_results/
├── 2025/
│   └── 09/
│       └── 23/
│           └── MyCompanyPortfolio/
│               ├── notifications_20250923_143022_123_3.json
│               ├── notifications_20250923_143045_456_2.json
│               └── notifications_20250923_143110_789_1.json
└── logs/
    └── real-test.log
```

**File Contents Example:**
```json
{
  "metadata": {
    "export_timestamp": "2025-09-23T14:30:22.123Z",
    "notification_count": 3,
    "format_version": "1.0",
    "storage_type": "local_file"
  },
  "notifications": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "type": "UPDATE",
      "organization": {
        "duns": "123456789"
      },
      "elements": [
        {
          "element": "organization.numberOfEmployees",
          "previous": "50000",
          "current": "52000",
          "timestamp": "2025-09-23T14:30:00Z"
        }
      ],
      "deliveryTimeStamp": "2025-09-23T14:30:22Z"
    }
  ]
}
```

### 2. Database Storage

**Location:** SQLite database (default: `./real_test_results.db`)

**Tables:**
- `registrations` - Your created monitoring registrations
- `notifications` - Individual notifications received
- `registration_stats` - Statistics and metadata

**View Database:**
```bash
# Install SQLite browser or use command line
sqlite3 real_test_results.db

# View tables
.tables

# View registrations
SELECT * FROM registrations;

# View notifications
SELECT * FROM notifications LIMIT 10;
```

### 3. Test Results Summary

**Location:** `./real_test_results.json`

**Contains:**
- Test execution summary
- Authentication results
- Registration creation details
- Notification counts and samples
- Storage locations
- Error logs

### 4. SFTP Storage (Optional)

If enabled in config:
**Location:** Your SFTP server at `/duns-test-results/`

**Structure:**
```
/duns-test-results/
├── 2025/09/23/
│   └── MyCompanyPortfolio/
│       ├── notifications_20250923_143022_123_3.json
│       └── notifications_20250923_143045_456_2.json
```

## 🔍 Checking Your Results

### View Local Files
```bash
# List stored notification files
find ./test_results -name "*.json" -type f

# View a notification file
cat ./test_results/2025/09/23/MyCompanyPortfolio/notifications_*.json | jq .

# Count total notifications
find ./test_results -name "*.json" -exec jq '.metadata.notification_count' {} \; | paste -sd+ - | bc
```

### Check Database
```bash
# Quick database summary
sqlite3 real_test_results.db "SELECT COUNT(*) as total_notifications FROM notifications;"
sqlite3 real_test_results.db "SELECT reference, duns_count, status FROM registrations;"
```

### View Test Summary
```bash
# View test results summary  
cat real_test_results.json | jq .

# Check for errors
cat real_test_results.json | jq '.errors[]'

# View storage info
cat real_test_results.json | jq '.storage_info'
```

## 🚀 Advanced Usage

### Multiple Registration Tests
```bash
# Test different portfolios
python3 real_duns_test.py --duns 111111111 222222222 --registration-name "TechPortfolio"
python3 real_duns_test.py --duns 333333333 444444444 --registration-name "FinancePortfolio"
```

### Production-like Continuous Monitoring
```bash
# Run for 1 hour with monitoring
python3 real_duns_test.py \
  --duns $(cat my_portfolio_duns.txt) \
  --continuous-minutes 60 \
  --registration-name "ProductionTest"
```

### Custom Configuration
```bash
# Use different storage location
cp config/real-test.yaml config/custom-test.yaml
# Edit custom-test.yaml to change storage paths

python3 real_duns_test.py --config config/custom-test.yaml
```

## 📊 What You'll See

When running real tests, you'll see output like:

```
🚀 Starting Real-World DUNS Testing
📋 Configuration: config/real-test.yaml
🔑 Environment: config/real-test.env
📊 DUNS to test: ['123456789', '987654321', '456789123']
📝 Registration: RealWorldTest
============================================================

1️⃣ Setting up monitoring service...
✅ Setup completed successfully

2️⃣ Creating registration 'RealWorldTest'...
✅ Registration created successfully

3️⃣ Pulling notifications for 'RealWorldTest'...
✅ Pulled 15 notifications

5️⃣ Checking storage locations...

📁 Storage Information:
   Local Storage: ./test_results
   Format: json
   Files: 3
   Database: sqlite:///./real_test_results.db

6️⃣ Saving test results...
✅ Results saved to: ./real_test_results.json

🎉 Real-world testing completed successfully!

📋 Next Steps:
   1. Check the local storage directory for notification files
   2. Review the database for stored registration data
   3. Check the log files for detailed execution logs
   4. Review real_test_results.json for comprehensive results
```

## 🛠️ Troubleshooting

### Authentication Issues
```bash
# Check your credentials
grep DNB_ config/real-test.env

# Test authentication directly
python3 -c "
from dotenv import load_dotenv
load_dotenv('config/real-test.env')
from src.traceone_monitoring.auth.authenticator import DNBAuthenticator
from src.traceone_monitoring.utils.config import DNBApiConfig
import os
config = DNBApiConfig(client_id=os.getenv('DNB_CLIENT_ID'), client_secret=os.getenv('DNB_CLIENT_SECRET'))
auth = DNBAuthenticator(config)
token = auth.get_token()
print('✅ Authentication successful' if token else '❌ Authentication failed')
"
```

### Storage Issues
```bash
# Check permissions
ls -la ./test_results/

# Check disk space
df -h .

# Verify configuration
python3 -c "from src.traceone_monitoring.utils.config import ConfigManager; cm = ConfigManager.from_file('config/real-test.yaml'); config = cm.load_config(); print(f'Local storage: {config.local_storage.enabled} at {config.local_storage.base_path}')"
```

### DUNS Issues
```bash
# Validate DUNS format
python3 -c "duns_list = ['123456789', '987654321']; [print(f'{d}: valid' if len(d)==9 and d.isdigit() else f'{d}: invalid') for d in duns_list]"
```

## 🎯 Summary

**This real-world testing setup gives you:**

1. **Complete D&B Integration** - Real API calls with your credentials
2. **Actual DUNS Monitoring** - Test with your company's actual DUNS numbers
3. **Multiple Storage Options** - Local files, database, SFTP
4. **Comprehensive Results** - Detailed logging and result tracking
5. **Production Readiness** - Test the same code you'll use in production

**Your results will be in:**
- `./test_results/` - JSON notification files organized by date/registration
- `./real_test_results.db` - SQLite database with all data
- `./real_test_results.json` - Test execution summary
- `./logs/real-test.log` - Detailed execution logs
