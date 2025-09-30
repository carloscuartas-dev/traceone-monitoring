# 🚀 Quick Email Notification Testing Guide

## Method 1: Interactive Setup (Recommended)
```bash
# Run the interactive setup script
./setup_email_notifications.sh
```

## Method 2: Manual Configuration

### Step 1: Configure Email in Environment File

Edit `config/real-test.env` and add these lines:

```bash
# For Gmail (recommended):
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_USERNAME=your.email@gmail.com
EMAIL_PASSWORD=your_app_password_here  # Use App Password!
EMAIL_FROM_EMAIL=your.email@gmail.com
EMAIL_TO_EMAILS=recipient@company.com,backup@company.com
```

### Step 2: Enable Notifications in Config
Edit `config/real-test.yaml` and set:
```yaml
email_notifications:
  enabled: true
```

## Step 3: Test Your Setup

### Test 1: SMTP Connection
```bash
./test_email_notifications.py --test-connection --enable-emails
```

### Test 2: Send Test Email
```bash
./test_email_notifications.py --test-email --enable-emails
```

### Test 3: Sample Notifications
```bash
./test_email_notifications.py --test-notifications --enable-emails
```

### Test 4: All Tests at Once
```bash
./test_email_notifications.py --test-connection --test-email --test-notifications --enable-emails
```

## Step 4: Test with Real Monitoring

### Test with Small DUNS File
```bash
# Create a small test file
echo -e "123456789\n987654321\n555666777" > small_test.txt

# Run monitoring with emails enabled
./automated_monitoring_from_file.py \
    --duns-file small_test.txt \
    --mode single \
    --registration-name "TRACE_Company_info_dev"
```

### Test with Your Existing Data
```bash
# Your daily monitoring will now send emails
./daily_monitoring_930am.sh

# Or test with your existing DUNS files
./automated_monitoring_from_file.py \
    --duns-file data/TRACE_Company_info_dev_20250923140806_DunsExport_1.txt \
    --mode single
```

## Email Types You'll Receive

### 1. Test Email
- Subject: `[TraceOne Alert] Test Email`
- Confirms SMTP is working
- Shows configuration details

### 2. Notification Summary
- Subject: `[TraceOne Alert] X D&B Notifications Received`
- Beautiful HTML with notification details
- Summary tables and statistics

### 3. Critical Alerts  
- Subject: `[TraceOne Alert] CRITICAL - X DELETE Alert`
- Red alert styling for urgent notifications
- Immediate delivery for DELETE/TRANSFER/UNDER_REVIEW

## Troubleshooting

### Gmail Users
1. **Enable 2-Factor Authentication**
2. **Generate App Password**: Google Account > Security > 2-Step Verification > App passwords
3. **Use App Password** (not regular Gmail password)

### No Emails Received?
- Check spam/junk folder
- Verify email addresses in config
- Test SMTP connection first
- Check logs: `tail -f logs/daily-monitoring-930am.log`

### Connection Errors?
- Verify SMTP server and port
- Check firewall/network restrictions  
- For Gmail: Use port 587 with TLS
- For Gmail: Must use App Password

## Email Configuration Examples

### Gmail
```bash
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_USERNAME=alerts@yourcompany.com
EMAIL_PASSWORD=abcd efgh ijkl mnop  # 16-character app password
```

### Outlook
```bash
EMAIL_SMTP_SERVER=smtp.live.com
EMAIL_USERNAME=alerts@outlook.com  
EMAIL_PASSWORD=your_outlook_password
```

### Corporate SMTP
```bash
EMAIL_SMTP_SERVER=mail.yourcompany.com
EMAIL_USERNAME=monitoring@yourcompany.com
EMAIL_PASSWORD=your_company_password
```

## Success Indicators

✅ **SMTP connection test passes**
✅ **Test email received in inbox**  
✅ **Sample notification emails sent**
✅ **Real monitoring sends emails**
✅ **No errors in logs**

## Next Steps After Testing

1. **Enable in production**: Set `enabled: true` permanently
2. **Customize recipients**: Add team members to `EMAIL_TO_EMAILS`
3. **Set notification preferences**: Adjust critical-only, summary frequency
4. **Monitor email statistics**: Check service status for email metrics
5. **Set up email filtering**: Create rules for TraceOne alerts in your inbox

Your email notifications are now ready for production use! 🎉
