#!/usr/bin/env python3
"""
Real-World Test Runner for TraceOne Monitoring System
Provides multiple test scenarios to choose from
"""

import subprocess
import sys
from pathlib import Path


def print_banner():
    """Print test runner banner"""
    print("🧪 TraceOne Real-World Test Suite")
    print("=" * 50)
    print("Choose your test scenario:")
    print()


def print_test_options():
    """Print available test options"""
    tests = [
        {
            "id": "1",
            "name": "Quick Integration Test",
            "description": "Fast test of basic file processing functionality",
            "script": "test_local_file_integration.py",
            "duration": "~1 minute"
        },
        {
            "id": "2", 
            "name": "Comprehensive Real-World Test",
            "description": "Full integration test with performance metrics and output verification",
            "script": "real_world_test.py",
            "duration": "~3-5 minutes"
        },
        {
            "id": "3",
            "name": "Continuous Monitoring Test",
            "description": "Test real-time monitoring (runs until stopped with Ctrl+C)",
            "script": "test_continuous_monitoring.py", 
            "duration": "Continuous"
        },
        {
            "id": "4",
            "name": "Performance Benchmark",
            "description": "Process all files and measure detailed performance metrics",
            "script": "performance_benchmark.py",
            "duration": "~2-3 minutes"
        }
    ]
    
    for test in tests:
        print(f"{test['id']}. {test['name']}")
        print(f"   Description: {test['description']}")
        print(f"   Duration: {test['duration']}")
        print()
    
    return tests


def create_performance_benchmark_script():
    """Create the performance benchmark script"""
    script_path = Path(__file__).parent / "performance_benchmark.py"
    
    script_content = '''#!/usr/bin/env python3
"""
Performance Benchmark Test for TraceOne Local File Integration
"""

import asyncio
import sys
import time
import psutil
import os
from pathlib import Path
from datetime import datetime

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from traceone_monitoring.services.local_file_input_processor import (
    LocalFileInputConfig,
    create_local_file_input_processor
)

async def run_performance_benchmark():
    """Run performance benchmark"""
    print("⚡ TraceOne Performance Benchmark")
    print("=" * 40)
    
    # Monitor system resources
    process = psutil.Process(os.getpid())
    start_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    config = LocalFileInputConfig(
        input_directory="~/Library/Mobile Documents/com~apple~CloudDocs/Projects/Traceone/dev/sftp",
        auto_archive_processed=False
    )
    
    processor = create_local_file_input_processor(config)
    
    # Benchmark file discovery
    print("\\n🔍 Benchmarking file discovery...")
    start_time = time.time()
    
    discovered_files = processor.discover_files()
    total_files = sum(len(files) for files in discovered_files.values())
    
    discovery_time = time.time() - start_time
    print(f"✅ File discovery: {discovery_time:.3f}s for {total_files} files")
    
    if total_files == 0:
        print("No files found for benchmarking")
        return
    
    # Benchmark processing
    print("\\n⚡ Benchmarking file processing...")
    start_time = time.time()
    start_cpu = psutil.cpu_percent()
    
    notifications = processor.process_all_files()
    
    end_time = time.time()
    end_cpu = psutil.cpu_percent()
    end_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    processing_time = end_time - start_time
    memory_used = end_memory - start_memory
    
    # Calculate metrics
    notifications_per_second = len(notifications) / processing_time if processing_time > 0 else 0
    memory_per_notification = memory_used / len(notifications) if notifications else 0
    
    print(f"\\n📊 Performance Results:")
    print(f"   Files processed: {total_files}")
    print(f"   Notifications generated: {len(notifications)}")
    print(f"   Total processing time: {processing_time:.2f}s")
    print(f"   Throughput: {notifications_per_second:.1f} notifications/second")
    print(f"   Memory used: {memory_used:.1f} MB")
    print(f"   Memory per notification: {memory_per_notification:.3f} MB")
    print(f"   CPU usage during processing: {end_cpu:.1f}%")
    
    # File size analysis
    total_size = 0
    for files in discovered_files.values():
        for file_path in files:
            if file_path.exists():
                total_size += file_path.stat().st_size
    
    total_size_mb = total_size / 1024 / 1024
    mb_per_second = total_size_mb / processing_time if processing_time > 0 else 0
    
    print(f"   Total file size: {total_size_mb:.1f} MB")
    print(f"   Processing speed: {mb_per_second:.1f} MB/second")
    
    print("\\n🎯 Benchmark completed!")

if __name__ == "__main__":
    asyncio.run(run_performance_benchmark())
'''
    
    with script_path.open('w') as f:
        f.write(script_content)
    
    script_path.chmod(0o755)  # Make executable
    return script_path


def run_test(test_script: str):
    """Run the selected test script"""
    script_path = Path(__file__).parent / test_script
    
    # Create performance benchmark if it doesn't exist
    if test_script == "performance_benchmark.py" and not script_path.exists():
        create_performance_benchmark_script()
    
    if not script_path.exists():
        print(f"❌ Test script not found: {script_path}")
        return False
    
    print(f"🚀 Running {test_script}...")
    print("=" * 50)
    
    try:
        # Run the test script
        result = subprocess.run([sys.executable, str(script_path)], 
                              check=False, 
                              text=True)
        
        if result.returncode == 0:
            print(f"\\n✅ Test completed successfully!")
        else:
            print(f"\\n⚠️  Test completed with exit code: {result.returncode}")
        
        return True
        
    except KeyboardInterrupt:
        print("\\n🛑 Test interrupted by user")
        return True
    except Exception as e:
        print(f"\\n❌ Error running test: {e}")
        return False


def check_environment():
    """Check if the environment is ready for testing"""
    print("🔍 Environment Check:")
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major == 3 and python_version.minor >= 8:
        print("✅ Python version compatible")
    else:
        print("⚠️  Python 3.8+ recommended")
    
    # Check SFTP directory
    sftp_dir = Path("~/Library/Mobile Documents/com~apple~CloudDocs/Projects/Traceone/dev/sftp").expanduser()
    if sftp_dir.exists():
        files = list(sftp_dir.glob("*"))
        print(f"✅ SFTP directory found with {len(files)} files")
        return True
    else:
        print("❌ SFTP directory not found")
        print(f"   Expected path: {sftp_dir}")
        return False


def main():
    """Main test runner"""
    print_banner()
    
    # Check environment
    if not check_environment():
        print("\\n❌ Environment check failed. Please verify your setup.")
        return
    
    print("\\n" + "=" * 50)
    tests = print_test_options()
    
    try:
        choice = input("Enter your choice (1-4) or 'q' to quit: ").strip().lower()
        
        if choice == 'q':
            print("👋 Goodbye!")
            return
        
        # Find the selected test
        selected_test = None
        for test in tests:
            if test["id"] == choice:
                selected_test = test
                break
        
        if not selected_test:
            print("❌ Invalid choice. Please select 1-4.")
            return
        
        print(f"\\n🎯 Selected: {selected_test['name']}")
        print(f"📝 {selected_test['description']}")
        print(f"⏱️  Expected duration: {selected_test['duration']}")
        
        confirm = input("\\nProceed with this test? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("Test cancelled.")
            return
        
        # Run the test
        success = run_test(selected_test["script"])
        
        if success:
            print("\\n🎉 Test run completed!")
            print("📁 Check the test_output/ directory for results and logs.")
        
    except KeyboardInterrupt:
        print("\\n🛑 Test runner interrupted")
    except Exception as e:
        print(f"\\n💥 Unexpected error: {e}")


if __name__ == "__main__":
    main()
