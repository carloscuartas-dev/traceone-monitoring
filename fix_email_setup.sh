#!/bin/bash

echo "🔧 Completing Email Setup"
echo "========================="

echo "I see your email setup needs to be completed."
echo ""
echo "Current configuration:"
echo "  Email: cuartasnetorg@gmail.com"
echo "  SMTP: Gmail (smtp.gmail.com)"
echo ""

# Get recipient emails
echo "📧 Who should receive the notification emails?"
read -p "Enter recipient email(s) (comma-separated, or press Enter to use carloscuartasm@gmail.com): " to_emails

# Use sender email as recipient if no recipients provided
if [ -z "$to_emails" ]; then
    to_emails="cuartasnetorg@gmail.com"
fi

# Get Gmail App Password
echo ""
echo "🔑 Gmail App Password Setup:"
echo "For Gmail, you need to use an App Password (NOT your regular Gmail password)"
echo ""
echo "Steps to get Gmail App Password:"
echo "1. Go to https://myaccount.google.com/security"
echo "2. Enable 2-Step Verification (if not already enabled)"
echo "3. Go to 'App passwords' section"
echo "4. Generate a new app password for 'Mail'"
echo "5. Use the 16-character password below"
echo ""

read -s -p "Enter your Gmail App Password (16 characters, like 'abcd efgh ijkl mnop'): " app_password
echo ""

if [ -z "$app_password" ]; then
    echo "❌ App password cannot be empty."
    echo "Please generate a Gmail App Password first:"
    echo "https://support.google.com/accounts/answer/185833"
    exit 1
fi

# Update environment file
echo "📝 Updating email configuration..."

# Read the existing env file and update the email fields
sed -i.bak \
    -e "s/EMAIL_PASSWORD=.*/EMAIL_PASSWORD=$app_password/" \
    -e "s/EMAIL_TO_EMAILS=.*/EMAIL_TO_EMAILS=$to_emails/" \
    config/real-test.env

echo "✅ Email configuration updated!"
echo ""
echo "📧 Final Configuration:"
echo "  From: carloscuartasm@gmail.com"
echo "  To: $to_emails"
echo "  SMTP: Gmail with App Password"
echo ""

# Test the configuration
echo "🧪 Testing email configuration..."
./test_email_notifications.py --test-connection --test-email --enable-emails

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Success! Your email notifications are working!"
    echo ""
    echo "Next steps:"
    echo "1. Test with sample notifications:"
    echo "   ./test_email_notifications.py --test-notifications --enable-emails"
    echo ""
    echo "2. Your regular monitoring will now send email alerts:"
    echo "   ./daily_monitoring_930am.sh"
    echo ""
    echo "3. Check your email inbox (including spam folder) for test messages"
else
    echo ""
    echo "❌ Email test failed. Common issues:"
    echo "1. Make sure you're using a Gmail App Password (not regular password)"
    echo "2. Check that 2-Step Verification is enabled on your Google account"
    echo "3. Verify the App Password is exactly 16 characters"
    echo ""
    echo "Need help? Check: https://support.google.com/accounts/answer/185833"
fi
