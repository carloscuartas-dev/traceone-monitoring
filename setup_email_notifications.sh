#!/bin/bash

echo "🔧 TraceOne Email Notifications Setup"
echo "======================================"

# Check if user wants to set up email notifications
read -p "Do you want to set up email notifications? (y/n): " setup_email
if [[ $setup_email != "y" && $setup_email != "Y" ]]; then
    echo "Email setup cancelled."
    exit 0
fi

# Create backup of existing env file if it exists
if [ -f "config/real-test.env" ]; then
    cp config/real-test.env config/real-test.env.backup.$(date +%Y%m%d_%H%M%S)
    echo "📋 Backed up existing environment file"
fi

echo ""
echo "📧 Email Configuration"
echo "Choose your email provider:"
echo "1) Gmail (recommended)"
echo "2) Outlook/Hotmail"
echo "3) Yahoo Mail"
echo "4) Custom SMTP"

read -p "Enter choice (1-4): " provider

case $provider in
    1)
        smtp_server="smtp.gmail.com"
        smtp_port="587"
        echo ""
        echo "📋 Gmail Setup Instructions:"
        echo "1. Go to Google Account Settings > Security"
        echo "2. Enable 2-Step Verification"
        echo "3. Generate an App Password for 'Mail'"
        echo "4. Use the App Password below (not your regular Gmail password)"
        echo ""
        ;;
    2)
        smtp_server="smtp.live.com"
        smtp_port="587"
        echo ""
        echo "📋 Outlook/Hotmail Setup:"
        echo "Use your regular Outlook/Hotmail credentials"
        echo ""
        ;;
    3)
        smtp_server="smtp.mail.yahoo.com"
        smtp_port="587"
        echo ""
        echo "📋 Yahoo Mail Setup Instructions:"
        echo "1. Enable 'Allow apps that use less secure sign in' OR"
        echo "2. Generate an App Password and use that"
        echo ""
        ;;
    4)
        read -p "Enter SMTP server (e.g., smtp.yourcompany.com): " smtp_server
        read -p "Enter SMTP port (usually 587 or 465): " smtp_port
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

# Get email credentials
read -p "Enter your email address: " email_username
read -s -p "Enter your password (or app password): " email_password
echo ""
read -p "Enter recipient email(s) (comma-separated): " to_emails

# Update or create environment file
cat > config/real-test.env << EOF
# TraceOne Monitoring Environment Configuration
# D&B API Configuration
DNB_BASE_URL=https://plus.dnb.com
DNB_CLIENT_ID=${DNB_CLIENT_ID}
DNB_CLIENT_SECRET=${DNB_CLIENT_SECRET}

# Database Configuration
DATABASE_URL=sqlite:///./real_test_results.db

# Email Notification Configuration
EMAIL_SMTP_SERVER=$smtp_server
EMAIL_USERNAME=$email_username
EMAIL_PASSWORD=$email_password
EMAIL_FROM_EMAIL=$email_username
EMAIL_TO_EMAILS=$to_emails

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF

echo ""
echo "✅ Email configuration saved to config/real-test.env"

# Enable email notifications in YAML
python3 << EOF
import yaml
import sys
from pathlib import Path

config_file = Path('config/real-test.yaml')
if config_file.exists():
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    if 'email_notifications' not in config:
        config['email_notifications'] = {}
    
    config['email_notifications']['enabled'] = True
    
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print("✅ Enabled email notifications in config/real-test.yaml")
else:
    print("❌ config/real-test.yaml not found")
    sys.exit(1)
EOF

echo ""
echo "🧪 Testing email configuration..."
echo ""

# Test the configuration
./test_email_notifications.py --test-connection --test-email

echo ""
echo "🎉 Email notifications setup complete!"
echo ""
echo "Next steps:"
echo "1. Test with sample notifications: ./test_email_notifications.py --test-notifications"
echo "2. Run your regular monitoring (emails will be sent automatically)"
echo "3. Check spam/junk folder if you don't see emails"
