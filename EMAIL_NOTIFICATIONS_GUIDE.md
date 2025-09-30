# 📧 TraceOne Email Notifications Setup Guide

This guide walks you through setting up email notifications for your TraceOne DUNS monitoring system.

## 🎯 Quick Start

### 1. Configure Your Email Settings

Create or update your `config/real-test.env` file with your email settings:

```bash
# Copy the example file
cp config/real-test-with-email.env.example config/real-test.env

# Edit with your actual email credentials
nano config/real-test.env
```

### 2. Enable Email Notifications

Update your `config/real-test.yaml`:

```yaml
email_notifications:
  enabled: true  # Change from false to true
```

### 3. Test Your Setup

```bash
# Test SMTP connection
./test_email_notifications.py --test-connection --enable-emails

# Send a test email
./test_email_notifications.py --test-email --enable-emails

# Test with sample notifications
./test_email_notifications.py --test-notifications --enable-emails
```

### 4. Run Monitoring with Email Alerts

Your existing monitoring scripts will now automatically send email alerts:

```bash
# Daily monitoring (already scheduled in cron)
./daily_monitoring_930am.sh

# Manual monitoring with file
./automated_monitoring_from_file.py --duns-file data/your_duns_file.txt
```

## 📋 Detailed Configuration

### Email Provider Settings

#### Gmail (Recommended)
```bash
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_USERNAME=your.email@gmail.com
EMAIL_PASSWORD=your_app_password_here  # Use App Password, not regular password
EMAIL_FROM_EMAIL=your.email@gmail.com
EMAIL_TO_EMAILS=alerts@yourcompany.com,manager@yourcompany.com
```

**Important**: For Gmail, you must use an App Password:
1. Go to Google Account Settings > Security
2. Enable 2-Step Verification
3. Generate an App Password for "Mail"
4. Use the generated password (not your regular Gmail password)

#### Outlook/Hotmail
```bash
EMAIL_SMTP_SERVER=smtp.live.com
EMAIL_USERNAME=your.email@outlook.com
EMAIL_PASSWORD=your_password_here
EMAIL_FROM_EMAIL=your.email@outlook.com
```

#### Yahoo Mail
```bash
EMAIL_SMTP_SERVER=smtp.mail.yahoo.com
EMAIL_USERNAME=your.email@yahoo.com
EMAIL_PASSWORD=your_app_password_here  # Use App Password
EMAIL_FROM_EMAIL=your.email@yahoo.com
```

#### Corporate SMTP
```bash
EMAIL_SMTP_SERVER=smtp.yourcompany.com
EMAIL_USERNAME=alerts@yourcompany.com
EMAIL_PASSWORD=your_password_here
EMAIL_FROM_EMAIL=alerts@yourcompany.com
```

### Notification Settings

In your `config/real-test.yaml`, customize these settings:

```yaml
email_notifications:
  enabled: true
  
  # Email behavior
  send_individual_notifications: false    # Send one email per notification
  send_summary_notifications: true        # Send summary emails (recommended)
  critical_notifications_only: false     # Only send critical alerts (DELETE, TRANSFER)
  max_notifications_per_email: 50        # Max notifications in one email
  
  # Email appearance
  subject_prefix: "[TraceOne Alert]"      # Email subject prefix
  from_name: "TraceOne DUNS Monitoring"  # Sender name
  
  # Recipients
  to_emails:
    - "primary@company.com"
    - "backup@company.com"
  cc_emails:
    - "manager@company.com"
  bcc_emails: []
```

## 📧 Email Types

### 1. Test Email
- Sent when running `--test-email`
- Confirms your SMTP configuration is working
- Contains configuration details

### 2. Notification Summary Emails
- Default email type for regular monitoring
- Contains multiple notifications in one email
- Professional HTML format with charts and details
- Shows notification counts by type

### 3. Critical Alert Emails
- Automatically sent for DELETE, TRANSFER, UNDER_REVIEW notifications
- High-priority styling with red alerts
- Immediate delivery regardless of summary settings

### 4. Individual Notification Emails
- One email per notification (if enabled)
- Useful for real-time alerts
- Can generate many emails with high DUNS counts

## 🔧 Testing Your Setup

### Test SMTP Connection Only
```bash
./test_email_notifications.py --test-connection --enable-emails
```

### Send Test Email
```bash
./test_email_notifications.py --test-email --enable-emails
```

### Test with Sample Notifications
```bash
./test_email_notifications.py --test-notifications --enable-emails
```

### Test All Functions
```bash
./test_email_notifications.py --test-connection --test-email --test-notifications --enable-emails
```

## 🚀 Integration with Existing Monitoring

Your email notifications work seamlessly with your existing monitoring setup:

### Daily 9:30 AM Monitoring
Your existing cron job at 9:30 AM will now send email alerts:
```bash
30 9 * * * /Users/carlos.cuartas/traceone-monitoring/daily_monitoring_930am.sh
```

### File-based Monitoring
```bash
./automated_monitoring_from_file.py \
    --config config/real-test.yaml \
    --env config/real-test.env \
    --duns-file data/your_file.txt \
    --registration-name "TRACE_Company_info_dev"
```

### Continuous Monitoring
```bash
./automated_monitoring_from_file.py \
    --mode continuous \
    --poll-interval 30 \
    --duration 8
```

## 📊 Email Content

### Notification Summary Email Contains:
- **Alert Header**: Critical or regular notification indicator
- **Summary Table**: Notification counts by type (UPDATE, INSERT, DELETE)
- **Detailed Notifications**: Up to 50 notifications with:
  - DUNS number and company name
  - Notification type and timestamp
  - Number of elements changed
- **System Statistics**: Email counts and processing stats
- **Professional Styling**: Clean HTML format for easy reading

### Critical Alert Email Features:
- ⚠️ **Red Alert Styling**: Immediately recognizable critical notifications
- 🔴 **Priority Indicators**: Visual markers for critical notification types
- ⏰ **Immediate Delivery**: Sent regardless of summary frequency settings
- 📋 **Detailed Context**: Full notification details for quick action

## ⚙️ Advanced Settings

### Custom Email Templates
Create custom email templates (optional):
```bash
mkdir -p email_templates
# Create custom templates in this directory
```

Set in configuration:
```yaml
email_notifications:
  template_dir: "./email_templates"
```

### Environment Variables Override
You can override any setting with environment variables:
```bash
# Override SMTP settings
export EMAIL_SMTP_SERVER="custom.smtp.server"
export EMAIL_SMTP_PORT="465"
export EMAIL_USE_SSL="true"

# Override recipients
export EMAIL_TO_EMAILS="urgent@company.com,alerts@company.com"
```

### Notification Filtering
```yaml
email_notifications:
  critical_notifications_only: true  # Only DELETE, TRANSFER, UNDER_REVIEW
  max_notifications_per_email: 20    # Limit email size
```

## 🛠️ Troubleshooting

### Common Issues

#### "SMTP connection failed"
- Check SMTP server and port settings
- Verify username and password
- For Gmail/Yahoo: Use App Password, not regular password
- Check firewall/network restrictions

#### "Authentication failed"
- Gmail: Enable 2FA and use App Password
- Yahoo: Enable "Allow apps that use less secure sign in"
- Outlook: Check account settings

#### "No emails received"
- Check spam/junk folder
- Verify recipient email addresses
- Test with `--test-email` first
- Check email handler statistics

#### "Email enabled but not working"
```bash
# Debug with verbose logging
LOG_level=DEBUG ./test_email_notifications.py --test-notifications --enable-emails
```

### Verification Commands

```bash
# Check configuration
./test_email_notifications.py --config config/real-test.yaml --env config/real-test.env

# Test specific email provider
EMAIL_SMTP_SERVER=smtp.gmail.com ./test_email_notifications.py --test-connection --enable-emails

# Verify with your actual monitoring
./automated_monitoring_from_file.py --mode single --duns-file data/small_test_file.txt
```

## 📈 Statistics and Monitoring

### Email Handler Statistics
Available in service status and logs:
```json
{
  "email_notifications": {
    "enabled": true,
    "smtp_server": "smtp.gmail.com",
    "recipients": 2,
    "statistics": {
      "emails_sent": 45,
      "notifications_processed": 127,
      "critical_notifications_sent": 3,
      "errors": 0,
      "last_email_time": "2025-09-25T14:30:05Z"
    }
  }
}
```

### Log Monitoring
Email activities are logged in your monitoring logs:
```bash
tail -f logs/daily-monitoring-930am.log | grep -i email
```

## 🔒 Security Best Practices

1. **Use App Passwords**: Never use your main email password
2. **Limit Recipients**: Only send to necessary email addresses
3. **Environment Variables**: Store credentials in `.env` files, not config files
4. **Test Environment**: Test with a separate email account first
5. **Monitor Logs**: Watch for authentication failures or errors

## 🎉 Success Indicators

You'll know email notifications are working when you see:
- ✅ SMTP connection test passes
- ✅ Test email received in inbox
- ✅ Notification emails during monitoring runs
- ✅ Statistics showing emails sent > 0
- ✅ No errors in monitoring logs

## 📞 Next Steps

1. **Complete Setup**: Follow the Quick Start section
2. **Test Thoroughly**: Use all test commands to verify functionality
3. **Monitor First Run**: Watch your first monitoring run with emails enabled
4. **Customize Settings**: Adjust notification preferences as needed
5. **Document Recipients**: Keep track of who receives notifications
6. **Set Up Escalation**: Consider multiple recipient tiers for critical alerts

Your TraceOne monitoring system now has comprehensive email notification capabilities! 🚀

## 📧 Example Email Preview

### Regular Notification Summary
```
Subject: [TraceOne Alert] 15 D&B Notifications Received

TraceOne D&B Monitoring Alert
========================================
Time: 2025-09-25 14:30:05 UTC
Notifications: 15

Summary by Type:
• UPDATE: 12 notification(s) 🟢
• INSERT: 2 notification(s) 🟢  
• DELETE: 1 notification(s) 🔴

Notification Details:
1. DUNS 123456789 - Acme Corporation
   Type: UPDATE 🟢
   Time: 2025-09-25 14:29:45
   Elements Changed: 3

[Additional notifications...]

System Statistics:
Total emails sent today: 1
Total notifications processed: 15
Critical notifications sent: 1
```

### Critical Alert Email
```
Subject: [TraceOne Alert] CRITICAL - 1 DELETE Alert

⚠️ CRITICAL ALERT
========================================
Time: 2025-09-25 14:30:05 UTC
Notifications: 1
⚠️ Critical notifications detected - immediate attention required!

Summary by Type:
DELETE: 1 🔴 Critical

Notification Details:
1. DUNS 987654321 - Important Client Corp
   Type: DELETE 🔴
   Time: 2025-09-25 14:29:50
   Elements Changed: 1

This requires immediate attention!
```
