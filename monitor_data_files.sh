#!/bin/bash
# Utility script to monitor DUNS files from data folder

set -e

DATA_DIR="./data"
SCRIPT="./automated_monitoring_from_file.py"
REGISTRATION_NAME="TRACE_Company_info_dev"

echo "🔍 DUNS Data Folder Monitoring Utility"
echo "======================================"
echo "Data directory: $DATA_DIR"
echo "Registration: $REGISTRATION_NAME"
echo ""

# Function to list available files
list_files() {
    echo "📁 Available DUNS files:"
    echo "========================"
    
    if [ -d "$DATA_DIR" ] && [ "$(ls -A $DATA_DIR/*.txt 2>/dev/null)" ]; then
        local count=1
        for file in $DATA_DIR/*.txt; do
            if [ -f "$file" ]; then
                local duns_count=$(wc -l < "$file")
                local file_size=$(ls -lh "$file" | awk '{print $5}')
                local file_date=$(ls -l "$file" | awk '{print $6, $7, $8}')
                echo "   $count. $(basename "$file")"
                echo "      📊 DUNS: $duns_count | 📁 Size: $file_size | 📅 Date: $file_date"
                echo ""
                ((count++))
            fi
        done
    else
        echo "   No DUNS files found in $DATA_DIR"
    fi
}

# Function to run monitoring with selected file
run_monitoring() {
    local file_path=$1
    local mode=$2
    local duration=${3:-""}
    
    echo "🚀 Starting monitoring with file: $(basename "$file_path")"
    echo "   Mode: $mode"
    if [ -n "$duration" ]; then
        echo "   Duration: $duration hours"
    fi
    echo ""
    
    if [ "$mode" = "single" ]; then
        python3 "$SCRIPT" --duns-file "$file_path" --registration-name "$REGISTRATION_NAME" --mode single
    elif [ "$mode" = "continuous" ] && [ -n "$duration" ]; then
        python3 "$SCRIPT" --duns-file "$file_path" --registration-name "$REGISTRATION_NAME" --mode continuous --poll-interval 15 --duration "$duration"
    else
        python3 "$SCRIPT" --duns-file "$file_path" --registration-name "$REGISTRATION_NAME" --mode continuous --poll-interval 15
    fi
}

# Main menu
if [ "$1" = "--list" ]; then
    list_files
    exit 0
fi

if [ "$1" = "--latest" ]; then
    # Find the latest file
    latest_file=$(ls -t $DATA_DIR/*.txt 2>/dev/null | head -1)
    if [ -n "$latest_file" ]; then
        echo "🔍 Using latest file: $(basename "$latest_file")"
        run_monitoring "$latest_file" "${2:-single}" "$3"
    else
        echo "❌ No DUNS files found in $DATA_DIR"
        exit 1
    fi
    exit 0
fi

# Interactive menu
echo "Choose an option:"
echo "1. List available files"
echo "2. Monitor with latest file (single poll)"
echo "3. Monitor with latest file (continuous)"
echo "4. Monitor with latest file (2-hour session)"
echo "5. Select specific file"
echo ""
read -p "Enter your choice (1-5): " choice

case $choice in
    1)
        list_files
        ;;
    2)
        latest_file=$(ls -t $DATA_DIR/*.txt 2>/dev/null | head -1)
        if [ -n "$latest_file" ]; then
            run_monitoring "$latest_file" "single"
        else
            echo "❌ No DUNS files found"
        fi
        ;;
    3)
        latest_file=$(ls -t $DATA_DIR/*.txt 2>/dev/null | head -1)
        if [ -n "$latest_file" ]; then
            run_monitoring "$latest_file" "continuous"
        else
            echo "❌ No DUNS files found"
        fi
        ;;
    4)
        latest_file=$(ls -t $DATA_DIR/*.txt 2>/dev/null | head -1)
        if [ -n "$latest_file" ]; then
            run_monitoring "$latest_file" "continuous" "2"
        else
            echo "❌ No DUNS files found"
        fi
        ;;
    5)
        list_files
        echo "Enter the file number to monitor:"
        read -p "File number: " file_num
        
        files=($DATA_DIR/*.txt)
        selected_file=${files[$((file_num-1))]}
        
        if [ -f "$selected_file" ]; then
            echo ""
            echo "Selected: $(basename "$selected_file")"
            echo "Choose monitoring mode:"
            echo "1. Single poll"
            echo "2. Continuous"
            echo "3. 2-hour session"
            read -p "Mode (1-3): " mode_choice
            
            case $mode_choice in
                1) run_monitoring "$selected_file" "single" ;;
                2) run_monitoring "$selected_file" "continuous" ;;
                3) run_monitoring "$selected_file" "continuous" "2" ;;
                *) echo "Invalid choice" ;;
            esac
        else
            echo "❌ Invalid file selection"
        fi
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "🎉 Monitoring completed!"
