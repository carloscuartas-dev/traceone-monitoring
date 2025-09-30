# Automated DUNS Monitoring Guide

Your `TRACE_Company_info_dev` registration is now set up for automated monitoring. Here's how to use it.

## 🎯 **Quick Start**

### **1. Manual Single Poll**
Check for notifications right now:
```bash
python3 automated_monitoring.py --mode single
```

### **2. Set Up Automated Monitoring** 
Run the interactive setup:
```bash
./setup_monitoring_scheduler.sh
```

### **3. Check Current Status**
See monitoring statistics and daemon status:
```bash
./setup_monitoring_scheduler.sh
# Choose option 3
```

## 📋 **Monitoring Options**

### **Option A: Cron Jobs (Scheduled)**
Perfect for regular polling at specific intervals:

```bash
# Every 15 minutes (recommended for production)
./setup_monitoring_scheduler.sh
# Choose 1 → 2

# Every hour
./setup_monitoring_scheduler.sh  
# Choose 1 → 4
```

**Pros:** Reliable, system-managed, survives reboots  
**Cons:** Discrete polling intervals  
**Best for:** Production environments, regular monitoring

### **Option B: Daemon (Continuous)**
Runs continuously in background:

```bash
# Start daemon (polls every 15 minutes)
./setup_monitoring_scheduler.sh
# Choose 2 → 2

# This creates management scripts:
./start_monitoring_daemon.sh   # Start daemon
./stop_monitoring_daemon.sh    # Stop daemon  
./check_monitoring_daemon.sh   # Check status
```

**Pros:** Immediate response, continuous monitoring  
**Cons:** Needs to be restarted after system reboot  
**Best for:** Development, active monitoring periods

## 📊 **Current Status**

Your registration `TRACE_Company_info_dev` is monitoring:
- **5 DUNS numbers**: 001017545, 001211952, 001316439, 001344381, 001389360
- **Last check**: Received **50 notifications**! 
- **Storage**: Results saved to `./test_results/` and database

## 🔍 **Checking Results**

### **View Monitoring Stats**
```bash
cat monitoring_stats.json | jq .
```

### **Check Notification Files** 
```bash
find ./test_results -name "*.json" -type f | head -5
```

### **View Logs**
```bash
# Cron job logs
tail -f logs/cron-monitoring.log

# Daemon logs  
tail -f logs/daemon-monitoring.log
```

### **Database Check**
```bash
# If you have sqlite3 installed
sqlite3 real_test_results.db "SELECT COUNT(*) FROM notifications;"
```

## ⚙️ **Available Commands**

### **Direct Script Usage**
```bash
# Single poll
python3 automated_monitoring.py --mode single --registration-name "TRACE_Company_info_dev"

# Continuous for 2 hours, poll every 10 minutes
python3 automated_monitoring.py --mode continuous --poll-interval 10 --duration 2 --registration-name "TRACE_Company_info_dev"

# Continuous unlimited (until Ctrl+C)
python3 automated_monitoring.py --mode continuous --poll-interval 5 --registration-name "TRACE_Company_info_dev"
```

### **Scheduler Options**
```bash
./setup_monitoring_scheduler.sh       # Interactive setup
echo "3" | ./setup_monitoring_scheduler.sh  # Show status
echo "4" | ./setup_monitoring_scheduler.sh  # Test poll
```

## 🔧 **Recommended Production Setup**

### **For Regular Monitoring**
1. Set up a cron job to run every 15-30 minutes
2. Monitor logs for any errors
3. Set up log rotation to prevent disk usage issues

```bash
# Example cron setup (every 15 minutes)
./setup_monitoring_scheduler.sh
# Choose: 1 → 2

# Then install the cron job as suggested
```

### **For Active Monitoring Periods**  
1. Use daemon mode during active periods
2. Start daemon before business hours
3. Stop daemon when monitoring is complete

```bash
# Start daemon
./start_monitoring_daemon.sh

# Check status periodically  
./check_monitoring_daemon.sh

# Stop when done
./stop_monitoring_daemon.sh
```

## 📁 **File Structure**

```
traceone-monitoring/
├── automated_monitoring.py          # Main monitoring script
├── setup_monitoring_scheduler.sh    # Interactive setup
├── monitoring_stats.json           # Current statistics
├── start_monitoring_daemon.sh      # Start daemon (created by setup)
├── stop_monitoring_daemon.sh       # Stop daemon (created by setup)  
├── check_monitoring_daemon.sh      # Check daemon (created by setup)
├── monitoring_daemon.pid           # Daemon PID (when running)
├── config/
│   ├── real-test.yaml              # Configuration
│   └── real-test.env               # Credentials
├── logs/
│   ├── cron-monitoring.log         # Cron job logs
│   └── daemon-monitoring.log       # Daemon logs  
└── test_results/                   # Notification files
    └── 2025/09/23/TRACE_Company_info_dev/
```

## 🚨 **Important Notes**

1. **Registration Exists**: The script only monitors your existing `TRACE_Company_info_dev` registration - it doesn't create new ones

2. **Credentials**: Make sure `config/real-test.env` has your valid D&B credentials

3. **Notifications**: You already received 50 notifications, indicating active monitoring is working!

4. **Storage**: Results are automatically stored in multiple formats (JSON files, database, logs)

5. **Error Handling**: The system handles temporary API errors with backoff retry logic

## 🆘 **Troubleshooting**

### **No notifications received**
- This is normal for new registrations
- D&B generates notifications when company data changes
- Your system is working if authentication succeeds

### **Authentication errors**
- Check credentials in `config/real-test.env`
- Verify D&B API access is active

### **Permission errors**  
```bash
chmod -R 755 test_results logs
```

### **Daemon not starting**
```bash
# Check if another instance is running
ps aux | grep automated_monitoring

# Remove stale PID file
rm monitoring_daemon.pid
```

## 📞 **Quick Commands Reference**

```bash
# Test single poll
python3 automated_monitoring.py --mode single

# Interactive setup
./setup_monitoring_scheduler.sh

# Start continuous monitoring (5 min intervals)  
python3 automated_monitoring.py --mode continuous --poll-interval 5

# Check current status
cat monitoring_stats.json | jq .

# View recent logs
tail -20 logs/*-monitoring.log
```

Your monitoring system is ready and already receiving notifications! 🎉
