#!/bin/bash
# Setup Daily 9:30 AM DUNS Monitoring Schedule

echo "⏰ Setting up Daily DUNS Monitoring at 9:30 AM"
echo "==============================================="
echo ""

# Check current cron jobs
echo "📋 Current cron jobs:"
crontab -l 2>/dev/null | grep -v "automated_monitoring\|daily_monitoring" || echo "   No DUNS monitoring cron jobs found"
echo ""

# Prepare the cron entry
SCRIPT_PATH="/Users/carlos.cuartas/traceone-monitoring/daily_monitoring_930am.sh"
CRON_ENTRY="30 9 * * * $SCRIPT_PATH"

echo "🔧 Cron job to be added:"
echo "   $CRON_ENTRY"
echo ""
echo "   This will run every day at 9:30 AM"
echo "   • 30 = minute (9:30)"
echo "   • 9  = hour (9 AM)"  
echo "   • *  = any day of month"
echo "   • *  = any month"
echo "   • *  = any day of week"
echo ""

# Function to install cron job
install_cron() {
    echo "📥 Installing cron job..."
    
    # Create temporary file with current cron jobs + new job
    TEMP_CRON=$(mktemp)
    
    # Get existing cron jobs (excluding any old monitoring jobs)
    crontab -l 2>/dev/null | grep -v "automated_monitoring\|daily_monitoring" > "$TEMP_CRON"
    
    # Add new cron job
    echo "$CRON_ENTRY" >> "$TEMP_CRON"
    
    # Install the new crontab
    crontab "$TEMP_CRON"
    
    # Clean up
    rm "$TEMP_CRON"
    
    echo "✅ Cron job installed successfully!"
    echo ""
    echo "📋 Updated cron jobs:"
    crontab -l
}

# Function to test the script
test_script() {
    echo "🧪 Testing the daily monitoring script..."
    echo ""
    
    if [ -x "$SCRIPT_PATH" ]; then
        echo "✅ Script is executable"
        echo "🚀 Running test..."
        echo ""
        "$SCRIPT_PATH"
        echo ""
        echo "✅ Test completed - check the output above"
    else
        echo "❌ Script not found or not executable: $SCRIPT_PATH"
        exit 1
    fi
}

# Function to show status
show_status() {
    echo "📊 Monitoring Schedule Status:"
    echo "=============================="
    echo ""
    
    # Check cron jobs
    if crontab -l 2>/dev/null | grep -q "daily_monitoring_930am.sh"; then
        echo "✅ Cron job: ACTIVE"
        echo "   Schedule: Daily at 9:30 AM"
        crontab -l | grep "daily_monitoring_930am.sh"
    else
        echo "❌ Cron job: NOT INSTALLED"
    fi
    echo ""
    
    # Check script
    if [ -x "$SCRIPT_PATH" ]; then
        echo "✅ Script: READY"
        echo "   Path: $SCRIPT_PATH"
    else
        echo "❌ Script: NOT FOUND"
    fi
    echo ""
    
    # Check last log
    LOG_FILE="/Users/carlos.cuartas/traceone-monitoring/logs/daily-monitoring-930am.log"
    if [ -f "$LOG_FILE" ]; then
        echo "📋 Last execution:"
        tail -5 "$LOG_FILE" | grep "🏁\|✅\|❌" | tail -1
    else
        echo "📋 Last execution: No logs found"
    fi
}

# Function to remove cron job
remove_cron() {
    echo "🗑️  Removing daily monitoring cron job..."
    
    # Create temporary file with current cron jobs minus monitoring jobs
    TEMP_CRON=$(mktemp)
    crontab -l 2>/dev/null | grep -v "automated_monitoring\|daily_monitoring" > "$TEMP_CRON"
    
    # Install the updated crontab
    crontab "$TEMP_CRON"
    rm "$TEMP_CRON"
    
    echo "✅ Cron job removed"
    echo ""
    echo "📋 Remaining cron jobs:"
    crontab -l 2>/dev/null || echo "   No cron jobs"
}

# Main menu
case "$1" in
    "install" | "--install")
        install_cron
        ;;
    "test" | "--test")
        test_script
        ;;
    "status" | "--status")
        show_status
        ;;
    "remove" | "--remove")
        remove_cron
        ;;
    *)
        echo "Choose an option:"
        echo "1. Install 9:30 AM daily schedule"
        echo "2. Test the monitoring script"
        echo "3. Show current status"
        echo "4. Remove scheduled job"
        echo ""
        read -p "Enter your choice (1-4): " choice
        
        case $choice in
            1) install_cron ;;
            2) test_script ;;
            3) show_status ;;
            4) remove_cron ;;
            *) echo "Invalid choice" ;;
        esac
        ;;
esac

echo ""
echo "📞 Quick Commands:"
echo "   Status:  ./setup_930am_schedule.sh status"
echo "   Test:    ./setup_930am_schedule.sh test"  
echo "   Remove:  ./setup_930am_schedule.sh remove"
echo ""
echo "📋 Log file: /Users/carlos.cuartas/traceone-monitoring/logs/daily-monitoring-930am.log"
