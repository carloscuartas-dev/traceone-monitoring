# DUNS Numbers Usage Guide for Real-time Testing

This guide explains all the different ways you can provide DUNS numbers for real-time testing with your TraceOne Monitoring Service.

## 🔢 **Multiple Ways to Provide DUNS Numbers**

### **1. Individual DUNS Numbers (Single or Multiple)**

```bash
# Single DUNS number
python3 scripts/real_time_testing.py -d 123456789

# Multiple DUNS numbers (recommended for testing)
python3 scripts/real_time_testing.py -d 123456789 -d 987654321 -d 555666777

# With monitoring options
python3 scripts/real_time_testing.py \
  -d 123456789 \
  -d 987654321 \
  -t financial \
  -dur 10 \
  -p 30
```

### **2. CSV File Support**

You can load DUNS numbers from various CSV file formats:

#### **Standard CSV with Headers**
```csv
company_name,duns,industry
Apple Inc,123456789,Technology
Microsoft Corp,987654321,Technology
Amazon.com Inc,555666777,Retail
```

```bash
# Load from CSV file
python3 scripts/real_time_testing.py -f sample_duns.csv

# Specify different column name
python3 scripts/real_time_testing.py -f my_companies.csv -c company_duns

# Limit number of DUNS from large CSV
python3 scripts/real_time_testing.py -f large_file.csv --max-duns 10
```

#### **Simple CSV Format (One Per Line)**
```csv
123456789
987654321
555666777
```

```bash
# Works with simple format too
python3 scripts/real_time_testing.py -f simple_duns.csv
```

#### **Complex CSV with Multiple Columns**
```csv
id,company_name,duns_number,sector,risk_level
1,Company A,123456789,Tech,High
2,Company B,987654321,Finance,Medium
```

```bash
# Use specific column name
python3 scripts/real_time_testing.py -f complex.csv -c duns_number
```

### **3. Combination Approach**

You can combine individual DUNS and CSV files:

```bash
# Individual DUNS + CSV file
python3 scripts/real_time_testing.py \
  -d 111111111 \
  -d 222222222 \
  -f additional_companies.csv \
  -t standard \
  -dur 5
```

## 📁 **CSV File Management Tools**

### **Create Sample Files for Testing**
```bash
# Generate sample CSV files
python3 scripts/duns_csv_loader.py create-sample
```

### **Validate and Load CSV Files**
```bash
# Load and validate DUNS from CSV
python3 scripts/duns_csv_loader.py load your_file.csv

# Load with specific column
python3 scripts/duns_csv_loader.py load companies.csv --column duns_num

# Load CSV without headers
python3 scripts/duns_csv_loader.py load data.csv --no-header

# Save valid DUNS to new file
python3 scripts/duns_csv_loader.py load input.csv --output clean_duns.csv
```

### **Simple CSV Loading**
```bash
# Load simple format (one DUNS per line or comma-separated)
python3 scripts/duns_csv_loader.py simple simple_duns.csv
```

## 🎯 **Real-world Examples**

### **Example 1: Small Test with Manual DUNS**
```bash
# Test with 3 specific companies
python3 scripts/real_time_testing.py \
  -d 804735132 \
  -d 006951541 \
  -d 149781646 \
  -t standard \
  -dur 3 \
  -p 15
```

### **Example 2: Portfolio Testing from CSV**
```bash
# Load supplier portfolio from CSV
python3 scripts/real_time_testing.py \
  -f supplier_portfolio.csv \
  -c supplier_duns \
  -t financial \
  -dur 10 \
  --max-duns 15
```

### **Example 3: Mixed Sources**
```bash
# Combine high-priority manual DUNS with CSV file
python3 scripts/real_time_testing.py \
  -d 123456789 \
  -f additional_companies.csv \
  -t standard \
  -dur 5
```

### **Example 4: Large-scale Testing**
```bash
# Test with large portfolio, limited to 20 companies
python3 scripts/real_time_testing.py \
  -f master_company_list.csv \
  --max-duns 20 \
  -t financial \
  -dur 15 \
  -p 60
```

## 📊 **CSV File Formats Supported**

### **Format 1: Standard Business CSV**
```csv
company_name,duns,industry,location
Apple Inc,123456789,Technology,USA
Microsoft Corporation,987654321,Technology,USA
```

### **Format 2: Financial Risk CSV**
```csv
entity_name,duns_number,risk_rating,exposure_amount
High Risk Corp,123456789,High,5000000
Medium Risk LLC,987654321,Medium,2000000
```

### **Format 3: Simple List**
```csv
123456789
987654321
555666777
```

### **Format 4: Comma-Separated**
```csv
123456789,987654321,555666777,444555666
```

## ⚙️ **CSV Loader Options**

The CSV loader automatically:
- **Detects delimiters** (comma, semicolon, tab)
- **Validates DUNS format** (9 digits)
- **Removes duplicates**
- **Cleans formatting** (removes hyphens, spaces)
- **Handles missing values**

### **Common Column Names Recognized:**
- `duns`
- `DUNS`
- `duns_number`
- `duns_num`
- `company_duns`

## 🔍 **DUNS Number Validation**

The system validates DUNS numbers to ensure they:
- Are exactly **9 digits**
- Contain only **numeric characters**
- Are **properly formatted**

Invalid DUNS numbers are reported but don't stop processing.

## 🚀 **Quick Start Examples**

### **First-time Setup**
```bash
# 1. Create sample CSV for testing
python3 scripts/duns_csv_loader.py create-sample

# 2. Validate your CSV file
python3 scripts/duns_csv_loader.py load sample_duns.csv

# 3. Run real-time test
python3 scripts/real_time_testing.py -f sample_duns.csv
```

### **With Your Real Data**
```bash
# 1. Prepare your CSV file with real DUNS from dev registration
# 2. Validate the file
python3 scripts/duns_csv_loader.py load your_real_duns.csv

# 3. Run comprehensive test
python3 scripts/real_time_testing.py \
  -f your_real_duns.csv \
  -t standard \
  -dur 10 \
  --max-duns 10
```

## 💡 **Pro Tips**

1. **Start Small**: Begin with 2-3 DUNS numbers to test the system
2. **Use CSV for Bulk**: For 10+ DUNS, CSV files are more manageable
3. **Validate First**: Always use the CSV loader to validate your files
4. **Limit Large Files**: Use `--max-duns` to limit processing for testing
5. **Mix Sources**: Combine high-priority manual DUNS with CSV files
6. **Monitor Rate Limits**: The system automatically handles D&B rate limits (5/second)

## 🔧 **Troubleshooting**

### **Common Issues**

1. **Invalid CSV Format**
   ```bash
   # Check your CSV structure
   python3 scripts/duns_csv_loader.py load your_file.csv
   ```

2. **Wrong Column Name**
   ```bash
   # Specify the correct column
   python3 scripts/real_time_testing.py -f file.csv -c your_column_name
   ```

3. **Too Many DUNS**
   ```bash
   # Limit the number processed
   python3 scripts/real_time_testing.py -f file.csv --max-duns 5
   ```

4. **File Not Found**
   ```bash
   # Check the file path
   ls -la *.csv
   python3 scripts/real_time_testing.py -f ./path/to/your/file.csv
   ```

## 📝 **File Examples**

You can find example CSV files in your project directory after running:
```bash
python3 scripts/duns_csv_loader.py create-sample
```

This creates:
- `sample_duns.csv` - CSV with headers and company information
- `simple_duns.csv` - Simple format with one DUNS per line

---

**Ready to test?** Replace the sample DUNS numbers with actual ones from your D&B dev registration and start monitoring! 🚀
