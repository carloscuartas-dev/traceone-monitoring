# SFTP SSH Key Authentication Setup Guide

This guide explains how to configure SSH key authentication for the SFTP storage feature in TraceOne Monitoring Service.

## 🔐 SSH Key Authentication Overview

SSH key authentication is more secure than password authentication and is the recommended method for SFTP connections. It uses public-key cryptography where:

- **Private Key**: Stored securely on your monitoring server
- **Public Key**: Provided to the SFTP server administrator for your account

## 📋 Prerequisites

1. SSH key pair (private and public keys)
2. Public key installed on the SFTP server
3. SFTP server hostname, username, and connection details

## 🔧 Step-by-Step Setup

### Step 1: Check for Existing SSH Keys

First, check if you already have SSH keys:

```bash
# Check for existing SSH keys
ls -la ~/.ssh/

# Common key files:
# id_rsa (private key)
# id_rsa.pub (public key)
# id_ed25519 (modern private key)
# id_ed25519.pub (modern public key)
```

### Step 2: Generate SSH Key Pair (if needed)

If you don't have SSH keys, generate a new pair:

```bash
# Generate RSA key pair
ssh-keygen -t rsa -b 4096 -f ~/.ssh/traceone_sftp_key -C "traceone-monitoring@yourcompany.com"

# Or generate Ed25519 key (more modern, recommended)
ssh-keygen -t ed25519 -f ~/.ssh/traceone_sftp_key -C "traceone-monitoring@yourcompany.com"
```

**Options explained:**
- `-t rsa` or `-t ed25519`: Key type
- `-b 4096`: Key length (for RSA)
- `-f ~/.ssh/traceone_sftp_key`: Output file path
- `-C "comment"`: Comment for identification

### Step 3: Provide Public Key to SFTP Administrator

Send your **public key** to the SFTP server administrator:

```bash
# Display your public key
cat ~/.ssh/traceone_sftp_key.pub

# Example output:
# ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDExample... traceone-monitoring@yourcompany.com
```

**⚠️ SECURITY NOTE**: Only share the **public key** (`.pub` file), never the private key!

### Step 4: Test SSH Connection

Test the connection before configuring the monitoring service:

```bash
# Test SSH connection to SFTP server
ssh -i ~/.ssh/traceone_sftp_key username@your-sftp-server.com

# Test SFTP connection specifically
sftp -i ~/.ssh/traceone_sftp_key username@your-sftp-server.com
```

### Step 5: Configure TraceOne Monitoring

#### Option A: Using Configuration File

Edit your `config/dev-with-sftp.yaml`:

```yaml
sftp_storage:
  enabled: true
  hostname: "your-sftp-server.com"
  port: 22
  username: "your-username"
  # SSH Key Authentication
  private_key_path: "/Users/carlos.cuartas/.ssh/traceone_sftp_key"
  private_key_passphrase: "your-passphrase"  # Optional, only if key has passphrase
  
  # Remote paths and settings
  remote_base_path: "/notifications"
  file_format: "json"
  organize_by_date: true
  organize_by_registration: true
```

#### Option B: Using Environment Variables

Add to your `config/dev.env`:

```bash
# SFTP SSH Key Configuration
SFTP_HOSTNAME=your-sftp-server.com
SFTP_USERNAME=your-username
SFTP_PRIVATE_KEY_PATH=/Users/carlos.cuartas/.ssh/traceone_sftp_key
SFTP_KEY_PASSPHRASE=your-passphrase-if-any
```

## 🔒 Security Best Practices

### 1. Key Permissions
Set proper permissions on your private key:

```bash
# Set restrictive permissions (owner read-only)
chmod 600 ~/.ssh/traceone_sftp_key
chmod 644 ~/.ssh/traceone_sftp_key.pub

# Verify permissions
ls -la ~/.ssh/traceone_sftp_key*
```

### 2. Dedicated Key Pair
Consider using a dedicated key pair just for SFTP:

```bash
# Generate dedicated SFTP key
ssh-keygen -t ed25519 -f ~/.ssh/traceone_sftp_key -C "traceone-sftp-$(date +%Y%m%d)"
```

### 3. Key Passphrase
Use a strong passphrase for additional security:

```bash
# Add passphrase to existing key
ssh-keygen -p -f ~/.ssh/traceone_sftp_key
```

### 4. SSH Config (Optional)
Create SSH config for easier management:

```bash
# Edit SSH config
nano ~/.ssh/config

# Add SFTP server configuration:
Host traceone-sftp
    HostName your-sftp-server.com
    User your-username
    IdentityFile ~/.ssh/traceone_sftp_key
    Port 22
    IdentitiesOnly yes
```

## 🧪 Testing SFTP Configuration

### Test Script

Create a test script to verify your SFTP setup:

```bash
#!/bin/bash
# Test SFTP connection with SSH key

echo "🔐 Testing SFTP SSH Key Authentication..."

# Test basic connection
echo "📡 Testing SSH connection..."
ssh -i ~/.ssh/traceone_sftp_key -o ConnectTimeout=10 your-username@your-sftp-server.com "echo 'SSH connection successful!'"

# Test SFTP connection
echo "📁 Testing SFTP connection..."
echo "ls /" | sftp -i ~/.ssh/traceone_sftp_key your-username@your-sftp-server.com

echo "✅ SFTP tests completed!"
```

### Using TraceOne Test Script

Run the SFTP test with your configuration:

```bash
# Run SFTP storage test
python3 test_sftp_storage.py
```

## 🚨 Troubleshooting

### Common Issues and Solutions

#### 1. Permission Denied
```bash
# Check key permissions
chmod 600 ~/.ssh/traceone_sftp_key

# Verify SSH agent
ssh-add ~/.ssh/traceone_sftp_key
```

#### 2. Host Key Verification Failed
```bash
# Add server to known hosts
ssh-keyscan -H your-sftp-server.com >> ~/.ssh/known_hosts
```

#### 3. Connection Timeout
- Verify hostname and port
- Check firewall settings
- Confirm with SFTP administrator

#### 4. Authentication Failed
- Verify public key is installed on server
- Check username is correct
- Confirm private key path in configuration

### Debug Mode

Enable debug logging in your configuration:

```yaml
logging:
  level: "DEBUG"  # Enable debug logging
```

## 📁 Directory Structure Example

With the configuration, your notifications will be organized like:

```
/notifications/
├── 2025/
│   └── 09/
│       └── 14/
│           ├── Registration1/
│           │   ├── notifications_20250914_143022_001_5.json
│           │   └── notifications_20250914_143055_002_3.json
│           └── Registration2/
│               └── notifications_20250914_143033_001_2.json
```

## 🔄 Key Rotation

For security, rotate your SSH keys periodically:

1. Generate new key pair
2. Provide new public key to SFTP administrator
3. Update TraceOne configuration with new private key path
4. Test connection
5. Remove old keys once confirmed working

## 📞 Support

If you need help with SSH key setup:

1. Check the troubleshooting section above
2. Verify configuration with test script
3. Contact your SFTP server administrator
4. Review TraceOne monitoring service logs

## 🎯 Next Steps

After successful SSH key authentication setup:

1. ✅ Configure notification monitoring
2. ✅ Set up registration monitoring
3. ✅ Test end-to-end notification storage
4. ✅ Monitor SFTP upload logs
5. ✅ Set up alerts for SFTP failures
