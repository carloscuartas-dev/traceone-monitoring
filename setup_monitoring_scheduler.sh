#!/bin/bash
# Setup Automated DUNS Monitoring Scheduler
# This script helps you set up automated monitoring via cron jobs or as a daemon.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITORING_SCRIPT="$SCRIPT_DIR/automated_monitoring.py"
REGISTRATION_NAME="TRACE_Company_info_dev"

echo "🔧 DUNS Monitoring Scheduler Setup"
echo "=================================="
echo "Script directory: $SCRIPT_DIR"
echo "Registration: $REGISTRATION_NAME"
echo ""

# Function to create cron job
setup_cron() {
    local interval=$1
    echo "⏰ Setting up cron job to run every $interval minutes..."
    
    # Create cron entry
    CRON_ENTRY="*/$interval * * * * cd $SCRIPT_DIR && python3 $MONITORING_SCRIPT --mode single --registration-name '$REGISTRATION_NAME' >> $SCRIPT_DIR/logs/cron-monitoring.log 2>&1"
    
    echo "Cron entry to add:"
    echo "$CRON_ENTRY"
    echo ""
    echo "To install this cron job, run:"
    echo "  (crontab -l 2>/dev/null; echo \"$CRON_ENTRY\") | crontab -"
    echo ""
    echo "To view current cron jobs:"
    echo "  crontab -l"
    echo ""
    echo "To remove the cron job later:"
    echo "  crontab -l | grep -v 'automated_monitoring.py' | crontab -"
    
    # Create log directory
    mkdir -p "$SCRIPT_DIR/logs"
}

# Function to create daemon script
setup_daemon() {
    local poll_interval=$1
    local duration=${2:-"unlimited"}
    
    echo "🔄 Setting up daemon for continuous monitoring..."
    
    cat > "$SCRIPT_DIR/start_monitoring_daemon.sh" << EOF
#!/bin/bash
# Start DUNS Monitoring Daemon

cd "$SCRIPT_DIR"

echo "🚀 Starting DUNS Monitoring Daemon..."
echo "Registration: $REGISTRATION_NAME"
echo "Poll interval: $poll_interval minutes"
echo "Duration: $duration hours"
echo "Log file: $SCRIPT_DIR/logs/daemon-monitoring.log"
echo ""

# Ensure logs directory exists
mkdir -p logs

# Start monitoring daemon
if [ "$duration" = "unlimited" ]; then
    nohup python3 "$MONITORING_SCRIPT" \\
        --mode continuous \\
        --registration-name "$REGISTRATION_NAME" \\
        --poll-interval $poll_interval \\
        >> logs/daemon-monitoring.log 2>&1 &
else
    nohup python3 "$MONITORING_SCRIPT" \\
        --mode continuous \\
        --registration-name "$REGISTRATION_NAME" \\
        --poll-interval $poll_interval \\
        --duration $duration \\
        >> logs/daemon-monitoring.log 2>&1 &
fi

# Save PID
echo \$! > monitoring_daemon.pid
echo "✅ Daemon started with PID: \$(cat monitoring_daemon.pid)"
echo "📋 Log file: logs/daemon-monitoring.log"
echo ""
echo "To stop the daemon:"
echo "  ./stop_monitoring_daemon.sh"
echo ""
echo "To check daemon status:"
echo "  ./check_monitoring_daemon.sh"
EOF

    chmod +x "$SCRIPT_DIR/start_monitoring_daemon.sh"
    
    # Create stop daemon script
    cat > "$SCRIPT_DIR/stop_monitoring_daemon.sh" << EOF
#!/bin/bash
# Stop DUNS Monitoring Daemon

cd "$SCRIPT_DIR"

if [ -f monitoring_daemon.pid ]; then
    PID=\$(cat monitoring_daemon.pid)
    if ps -p \$PID > /dev/null 2>&1; then
        echo "🛑 Stopping monitoring daemon (PID: \$PID)..."
        kill \$PID
        rm monitoring_daemon.pid
        echo "✅ Daemon stopped successfully"
    else
        echo "⚠️  Daemon not running (PID \$PID not found)"
        rm monitoring_daemon.pid
    fi
else
    echo "❌ No daemon PID file found"
fi
EOF

    chmod +x "$SCRIPT_DIR/stop_monitoring_daemon.sh"
    
    # Create check daemon script
    cat > "$SCRIPT_DIR/check_monitoring_daemon.sh" << EOF
#!/bin/bash
# Check DUNS Monitoring Daemon Status

cd "$SCRIPT_DIR"

if [ -f monitoring_daemon.pid ]; then
    PID=\$(cat monitoring_daemon.pid)
    if ps -p \$PID > /dev/null 2>&1; then
        echo "✅ Daemon is running (PID: \$PID)"
        echo "📊 Stats:"
        if [ -f monitoring_stats.json ]; then
            echo "   Total notifications: \$(cat monitoring_stats.json | python3 -c 'import json, sys; print(json.load(sys.stdin)[\"total_notifications\"])')"
            echo "   Total polls: \$(cat monitoring_stats.json | python3 -c 'import json, sys; print(json.load(sys.stdin)[\"total_polls\"])')"
            echo "   Last poll: \$(cat monitoring_stats.json | python3 -c 'import json, sys; print(json.load(sys.stdin)[\"current_time\"])')"
        fi
        echo ""
        echo "📋 Recent logs:"
        tail -10 logs/daemon-monitoring.log
    else
        echo "❌ Daemon not running (PID \$PID not found)"
        rm monitoring_daemon.pid
    fi
else
    echo "❌ No daemon running"
fi
EOF

    chmod +x "$SCRIPT_DIR/check_monitoring_daemon.sh"
    
    echo "Created daemon management scripts:"
    echo "  📁 start_monitoring_daemon.sh - Start continuous monitoring"
    echo "  📁 stop_monitoring_daemon.sh  - Stop the daemon"
    echo "  📁 check_monitoring_daemon.sh - Check daemon status"
}

# Main menu
echo "Choose monitoring setup option:"
echo "1. Cron job (runs at regular intervals)"
echo "2. Daemon (continuous background process)"
echo "3. Show current monitoring status"
echo "4. Test single poll"
echo ""
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo ""
        echo "Cron job options:"
        echo "1. Every 5 minutes"
        echo "2. Every 15 minutes"
        echo "3. Every 30 minutes"  
        echo "4. Every hour"
        echo "5. Custom interval"
        echo ""
        read -p "Choose interval (1-5): " interval_choice
        
        case $interval_choice in
            1) setup_cron 5 ;;
            2) setup_cron 15 ;;
            3) setup_cron 30 ;;
            4) setup_cron 60 ;;
            5) 
                read -p "Enter interval in minutes: " custom_interval
                setup_cron $custom_interval
                ;;
            *) echo "Invalid choice" ;;
        esac
        ;;
    2)
        echo ""
        echo "Daemon options:"
        echo "1. Poll every 5 minutes (unlimited duration)"
        echo "2. Poll every 15 minutes (unlimited duration)"
        echo "3. Poll every 30 minutes (unlimited duration)"
        echo "4. Custom configuration"
        echo ""
        read -p "Choose option (1-4): " daemon_choice
        
        case $daemon_choice in
            1) setup_daemon 5 ;;
            2) setup_daemon 15 ;;
            3) setup_daemon 30 ;;
            4)
                read -p "Poll interval (minutes): " poll_interval
                read -p "Duration (hours, or 'unlimited'): " duration
                setup_daemon $poll_interval $duration
                ;;
            *) echo "Invalid choice" ;;
        esac
        ;;
    3)
        echo ""
        echo "📊 Current Monitoring Status:"
        echo "=============================="
        
        if [ -f monitoring_stats.json ]; then
            python3 -c "
import json
with open('monitoring_stats.json') as f:
    stats = json.load(f)
print(f'Total notifications: {stats[\"total_notifications\"]}')
print(f'Total polls: {stats[\"total_polls\"]}')
print(f'Last poll: {stats[\"current_time\"]}')
print(f'Registrations monitored: {stats[\"registrations_monitored\"]}')
"
        else
            echo "No monitoring stats found. Run a test poll first."
        fi
        
        # Check if daemon is running
        if [ -f monitoring_daemon.pid ]; then
            PID=$(cat monitoring_daemon.pid)
            if ps -p $PID > /dev/null 2>&1; then
                echo ""
                echo "🔄 Daemon Status: RUNNING (PID: $PID)"
            else
                echo ""
                echo "🔄 Daemon Status: NOT RUNNING"
                rm monitoring_daemon.pid
            fi
        else
            echo ""
            echo "🔄 Daemon Status: NOT RUNNING"
        fi
        ;;
    4)
        echo ""
        echo "🧪 Running test poll..."
        python3 "$MONITORING_SCRIPT" --mode single --registration-name "$REGISTRATION_NAME"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "🎉 Setup completed!"
