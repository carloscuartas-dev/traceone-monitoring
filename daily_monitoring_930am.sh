#!/bin/bash
# Daily DUNS Monitoring Script - Runs at 9:30 AM
# Automatically uses the latest DUNS file from data folder

# Set script directory and change to it
SCRIPT_DIR="/Users/carlos.cuartas/traceone-monitoring"
cd "$SCRIPT_DIR" || exit 1

# Configuration
DATA_DIR="./data"
REGISTRATION_NAME="TRACE_Company_info_dev"
LOG_DIR="./logs"
DAILY_LOG="$LOG_DIR/daily-monitoring-930am.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to log with timestamp
log_with_timestamp() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$DAILY_LOG"
}

# Function to send notification (optional - for future use)
send_notification() {
    local message=$1
    # Uncomment and configure if you want system notifications
    # osascript -e "display notification \"$message\" with title \"DUNS Monitoring\""
    log_with_timestamp "NOTIFICATION: $message"
}

# Start daily monitoring
log_with_timestamp "🚀 Starting Daily DUNS Monitoring (9:30 AM Schedule)"
log_with_timestamp "=========================================================="
log_with_timestamp "Script Directory: $SCRIPT_DIR"
log_with_timestamp "Data Directory: $DATA_DIR"
log_with_timestamp "Registration: $REGISTRATION_NAME"

# Check if data directory exists
if [ ! -d "$DATA_DIR" ]; then
    log_with_timestamp "❌ ERROR: Data directory not found: $DATA_DIR"
    send_notification "Daily DUNS monitoring failed - data directory not found"
    exit 1
fi

# Find the latest DUNS file
LATEST_FILE=$(ls -t "$DATA_DIR"/*.txt 2>/dev/null | head -1)

if [ -z "$LATEST_FILE" ]; then
    log_with_timestamp "❌ ERROR: No DUNS files found in $DATA_DIR"
    send_notification "Daily DUNS monitoring failed - no DUNS files found"
    exit 1
fi

# Get file info
FILE_NAME=$(basename "$LATEST_FILE")
DUNS_COUNT=$(wc -l < "$LATEST_FILE" 2>/dev/null || echo "unknown")
FILE_SIZE=$(ls -lh "$LATEST_FILE" 2>/dev/null | awk '{print $5}' || echo "unknown")
FILE_DATE=$(ls -l "$LATEST_FILE" 2>/dev/null | awk '{print $6, $7, $8}' || echo "unknown")

log_with_timestamp "📄 Using DUNS file: $FILE_NAME"
log_with_timestamp "📊 DUNS count: $DUNS_COUNT"
log_with_timestamp "📁 File size: $FILE_SIZE"
log_with_timestamp "📅 File date: $FILE_DATE"
log_with_timestamp ""

# Run the monitoring
log_with_timestamp "🔍 Starting monitoring process..."

# Execute the monitoring script and capture output
MONITORING_OUTPUT=$(python3 "$SCRIPT_DIR/automated_monitoring_from_file.py" \
    --duns-file "$LATEST_FILE" \
    --registration-name "$REGISTRATION_NAME" \
    --mode single 2>&1)

MONITORING_EXIT_CODE=$?

# Log the monitoring output
echo "$MONITORING_OUTPUT" >> "$DAILY_LOG"

# Check if monitoring was successful
if [ $MONITORING_EXIT_CODE -eq 0 ]; then
    log_with_timestamp "✅ Monitoring completed successfully"
    
    # Extract results from monitoring stats file if it exists
    if [ -f "./monitoring_stats_file.json" ]; then
        NOTIFICATIONS_RECEIVED=$(cat "./monitoring_stats_file.json" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('total_notifications', 0))
except:
    print('unknown')
" 2>/dev/null)
        
        TOTAL_DUNS_MONITORED=$(cat "./monitoring_stats_file.json" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('total_duns', 0))
except:
    print('unknown')
" 2>/dev/null)
        
        log_with_timestamp "📊 Results Summary:"
        log_with_timestamp "   • DUNS monitored: $TOTAL_DUNS_MONITORED"
        log_with_timestamp "   • Notifications received: $NOTIFICATIONS_RECEIVED"
        log_with_timestamp "   • Results saved to: monitoring_stats_file.json"
        
        # Send success notification
        send_notification "Daily monitoring completed: $NOTIFICATIONS_RECEIVED notifications from $TOTAL_DUNS_MONITORED DUNS"
    else
        log_with_timestamp "⚠️  Warning: monitoring_stats_file.json not found"
    fi
    
else
    log_with_timestamp "❌ ERROR: Monitoring failed with exit code $MONITORING_EXIT_CODE"
    send_notification "Daily DUNS monitoring failed - check logs for details"
fi

# Log completion
log_with_timestamp ""
log_with_timestamp "🏁 Daily monitoring completed at $(date '+%Y-%m-%d %H:%M:%S')"
log_with_timestamp "=========================================================="
log_with_timestamp ""

# Keep only last 30 days of logs (optional cleanup)
find "$LOG_DIR" -name "daily-monitoring-930am.log.*" -mtime +30 -delete 2>/dev/null

# Rotate log file if it gets too large (>10MB)
if [ -f "$DAILY_LOG" ] && [ $(stat -f%z "$DAILY_LOG" 2>/dev/null || echo 0) -gt 10485760 ]; then
    mv "$DAILY_LOG" "$DAILY_LOG.$(date +%Y%m%d_%H%M%S)"
    log_with_timestamp "📋 Log file rotated due to size"
fi

exit $MONITORING_EXIT_CODE
