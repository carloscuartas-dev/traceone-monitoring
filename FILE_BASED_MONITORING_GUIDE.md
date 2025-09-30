# File-Based DUNS Monitoring Guide

Monitor your `TRACE_Company_info_dev` registration using DUNS numbers stored in text files.

## 🎯 **Quick Start**

### **1. Your DUNS File**
Your DUNS are stored in `duns_list.txt`:
```
001017545
001211952
001316439
001344381
001389360
```

### **2. Run Monitoring**
```bash
# Single poll with your DUNS file
python3 automated_monitoring_from_file.py --duns-file duns_list.txt

# Continuous monitoring (polls every 10 minutes)
python3 automated_monitoring_from_file.py --duns-file duns_list.txt --mode continuous --poll-interval 10
```

## 📄 **DUNS File Format**

Your `duns_list.txt` file supports:
- **One DUNS per line** (9 digits)
- **Comments** starting with `#`
- **Empty lines** (ignored)

**Example:**
```
# Primary companies
001017545
001211952
001316439

# Secondary companies
001344381
001389360

# Additional DUNS to monitor:
# 123456789
# 987654321
```

## ⚙️ **Available Commands**

### **Single Poll**
```bash
# Basic single poll
python3 automated_monitoring_from_file.py --duns-file duns_list.txt

# With custom registration name
python3 automated_monitoring_from_file.py --duns-file duns_list.txt --registration-name "TRACE_Company_info_dev"

# Using different DUNS file
python3 automated_monitoring_from_file.py --duns-file my_companies.txt
```

### **Continuous Monitoring**
```bash
# Continuous monitoring (5 min intervals)
python3 automated_monitoring_from_file.py --duns-file duns_list.txt --mode continuous --poll-interval 5

# Limited duration (2 hours)
python3 automated_monitoring_from_file.py --duns-file duns_list.txt --mode continuous --duration 2

# Production monitoring (15 min intervals)
python3 automated_monitoring_from_file.py --duns-file duns_list.txt --mode continuous --poll-interval 15
```

### **Utility Commands**
```bash
# Create example DUNS file
python3 automated_monitoring_from_file.py --create-example --duns-file my_duns.txt

# Help
python3 automated_monitoring_from_file.py --help
```

## 📊 **Your Current Status**

**✅ Working Configuration:**
- **DUNS File:** `duns_list.txt` (5 DUNS numbers)
- **Registration:** `TRACE_Company_info_dev`
- **Last Test:** Received **100 notifications**!
- **Results:** Saved in `monitoring_stats_file.json`

## 🔄 **Dynamic DUNS Management**

### **Add More DUNS**
Simply edit `duns_list.txt`:
```bash
nano duns_list.txt
# Add new DUNS numbers, save file
```

In continuous mode, the file is re-read every poll cycle, so changes take effect immediately!

### **Multiple DUNS Files**
```bash
# Different portfolios
python3 automated_monitoring_from_file.py --duns-file suppliers.txt --registration-name "TRACE_Company_info_dev"
python3 automated_monitoring_from_file.py --duns-file customers.txt --registration-name "TRACE_Company_info_dev"
python3 automated_monitoring_from_file.py --duns-file partners.txt --registration-name "TRACE_Company_info_dev"
```

## 🏗️ **Production Setup Examples**

### **1. Scheduled Monitoring (Cron)**
```bash
# Every 15 minutes
*/15 * * * * cd /path/to/traceone-monitoring && python3 automated_monitoring_from_file.py --duns-file duns_list.txt >> logs/file-monitoring.log 2>&1
```

### **2. Long-Running Daemon**
```bash
# Start background monitoring
nohup python3 automated_monitoring_from_file.py \
  --duns-file duns_list.txt \
  --mode continuous \
  --poll-interval 15 \
  >> logs/daemon-file-monitoring.log 2>&1 &

# Save PID for later
echo $! > file_monitoring.pid
```

### **3. Multiple File Monitoring**
```bash
# Monitor different DUNS groups simultaneously
python3 automated_monitoring_from_file.py --duns-file critical_suppliers.txt --mode continuous --poll-interval 10 &
python3 automated_monitoring_from_file.py --duns-file key_customers.txt --mode continuous --poll-interval 15 &
python3 automated_monitoring_from_file.py --duns-file business_partners.txt --mode continuous --poll-interval 30 &
```

## 📁 **File Organization**

```
traceone-monitoring/
├── automated_monitoring_from_file.py    # File-based monitoring script
├── duns_list.txt                       # Your main DUNS file
├── monitoring_stats_file.json          # Results with DUNS list included
├── DUNS_files/                         # Optional: organize multiple files
│   ├── suppliers.txt
│   ├── customers.txt
│   └── partners.txt
└── logs/
    └── file-monitoring.log
```

## 🔍 **Checking Results**

### **View Stats with DUNS List**
```bash
# Full statistics including DUNS list
cat monitoring_stats_file.json | jq .

# Just the DUNS and counts
cat monitoring_stats_file.json | jq '{total_duns, duns_list, total_notifications}'

# Check which DUNS are being monitored
cat monitoring_stats_file.json | jq '.duns_list[]'
```

### **Verify DUNS File Loading**
```bash
# The script shows DUNS loaded on startup:
# "📊 DUNS loaded from file: 5"
```

## 🚨 **Important Features**

### **1. File Validation**
- ✅ **Format checking:** Only valid 9-digit DUNS accepted
- ✅ **Error reporting:** Invalid lines are logged with line numbers
- ✅ **Auto-creation:** Creates example file if not found

### **2. Dynamic Reloading**
- ✅ **Live updates:** File re-read every poll cycle in continuous mode
- ✅ **No restart needed:** Add/remove DUNS without stopping monitoring
- ✅ **Change detection:** Logs when DUNS count changes

### **3. Enhanced Reporting**
- ✅ **DUNS tracking:** Results include full DUNS list
- ✅ **Matching notifications:** Shows which notifications match your DUNS
- ✅ **File metadata:** Stats include source file information

## 🛠️ **Troubleshooting**

### **File Not Found**
```bash
# Script will create example file automatically
python3 automated_monitoring_from_file.py --duns-file my_duns.txt
# Edit the created file with your DUNS numbers
```

### **Invalid DUNS Format**
```bash
# Check your file format - should be 9 digits per line:
001234567  ✅ Valid
12345678   ❌ Too short
1234567890 ❌ Too long
ABC123456  ❌ Contains letters
```

### **No Notifications**
- ✅ Authentication successful = system working
- ✅ DUNS loaded = file format correct
- ✅ Your registration already received 100 notifications!

## 📞 **Quick Commands**

```bash
# Test with your current file
python3 automated_monitoring_from_file.py --duns-file duns_list.txt

# Start 1-hour monitoring session  
python3 automated_monitoring_from_file.py --duns-file duns_list.txt --mode continuous --duration 1

# Create new DUNS file
python3 automated_monitoring_from_file.py --create-example --duns-file new_companies.txt

# Check results
cat monitoring_stats_file.json | jq '{total_duns, total_notifications, duns_list}'
```

## 🎉 **Your System Status**

- ✅ **File-based monitoring:** Ready and tested
- ✅ **DUNS file:** `duns_list.txt` with 5 companies
- ✅ **Registration:** `TRACE_Company_info_dev` active
- ✅ **Notifications:** 100 received in latest test
- ✅ **Storage:** Results with DUNS list included

Your file-based DUNS monitoring system is production-ready! 🚀
