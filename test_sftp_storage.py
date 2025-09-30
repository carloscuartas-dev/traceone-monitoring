#!/usr/bin/env python3
"""
SFTP Storage Test
Tests the SFTP storage functionality for D&B notifications
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from traceone_monitoring.storage.sftp_handler import SFTPConfig, SFTPNotificationStorage
from traceone_monitoring.models.notification import Notification, NotificationType

def create_test_notifications():
    """Create some test notifications"""
    notifications = []
    
    for i in range(3):
        # Create notification data with proper field names
        notification_data = {
            "type": NotificationType.UPDATE,
            "organization": {"duns": f"12345678{i}"},
            "deliveryTimeStamp": datetime.utcnow(),  # Use the alias
            "elements": []
        }
        notification = Notification(**notification_data)
        notifications.append(notification)
    
    return notifications

def test_sftp_configuration():
    """Test SFTP configuration"""
    print("🔧 Testing SFTP Configuration...")
    
    # Example SFTP configuration
    config = SFTPConfig(
        hostname="test.sftp.server.com",
        port=22,
        username="test_user", 
        password="test_password",
        remote_base_path="/notifications",
        file_format="json",
        organize_by_date=True,
        organize_by_registration=True
    )
    
    print(f"   ✅ Hostname: {config.hostname}")
    print(f"   ✅ Port: {config.port}")
    print(f"   ✅ Username: {config.username}")
    print(f"   ✅ Remote path: {config.remote_base_path}")
    print(f"   ✅ File format: {config.file_format}")
    
    return config

def test_sftp_storage_local():
    """Test SFTP storage functionality (without actual connection)"""
    print("\\n📦 Testing SFTP Storage Functionality...")
    
    config = test_sftp_configuration()
    storage = SFTPNotificationStorage(config)
    
    # Test notification formatting
    notifications = create_test_notifications()
    
    print(f"\\n📄 Testing notification formatting:")
    print(f"   📊 Created {len(notifications)} test notifications")
    
    # Test JSON formatting
    json_content = storage._format_notifications(notifications)
    print(f"   ✅ JSON format: {len(json_content)} characters")
    print(f"   📝 JSON preview: {json_content[:100]}...")
    
    # Test CSV formatting
    storage.config.file_format = "csv"
    csv_content = storage._format_notifications(notifications)
    print(f"   ✅ CSV format: {len(csv_content)} characters")
    print(f"   📝 CSV preview: {csv_content[:100]}...")
    
    # Test XML formatting
    storage.config.file_format = "xml"
    xml_content = storage._format_notifications(notifications)
    print(f"   ✅ XML format: {len(xml_content)} characters")
    print(f"   📝 XML preview: {xml_content[:100]}...")
    
    # Test remote path generation
    storage.config.file_format = "json"
    remote_path = storage._generate_remote_path("TestRegistration", len(notifications))
    print(f"   ✅ Remote path: {remote_path}")
    
    print("\\n✅ SFTP storage functionality tests completed successfully!")

def test_with_real_sftp():
    """Test with real SFTP server (if configured)"""
    print("\\n🌐 Testing with Real SFTP Server...")
    print("(This test requires actual SFTP server credentials)")
    
    # Example of how to use with real SFTP server
    example_config = '''
# Example SFTP configuration in config file:

sftp_storage:
  enabled: true
  hostname: "your.sftp.server.com"
  port: 22
  username: "your_username"
  password: "your_password"
  # OR use private key:
  # private_key_path: "/path/to/private/key"
  # private_key_passphrase: "passphrase"
  
  remote_base_path: "/notifications"
  file_format: "json"
  organize_by_date: true
  organize_by_registration: true
    '''
    
    print(example_config)
    
    # Check if user wants to test with real server
    user_input = input("\\nDo you have SFTP server credentials to test? (y/n): ").lower().strip()
    
    if user_input in ['y', 'yes']:
        hostname = input("SFTP Hostname: ")
        username = input("SFTP Username: ")
        password = input("SFTP Password: ")
        
        config = SFTPConfig(
            hostname=hostname,
            username=username, 
            password=password,
            remote_base_path="/notifications",
            file_format="json"
        )
        
        try:
            storage = SFTPNotificationStorage(config)
            notifications = create_test_notifications()
            
            print("🔌 Testing SFTP connection...")
            result = storage.store_notifications(notifications, "TestRegistration")
            
            print(f"✅ SUCCESS: Stored {result['stored']} notifications!")
            print(f"   📁 Files created: {result['files']}")
            print(f"   🕒 Timestamp: {result['timestamp']}")
            
            # List remote files
            files = storage.list_remote_files("TestRegistration")
            print(f"\\n📋 Files in SFTP server: {len(files)}")
            for file in files[:5]:  # Show first 5 files
                print(f"   📄 {file}")
            
        except Exception as e:
            print(f"❌ SFTP test failed: {e}")
    else:
        print("⏭️  Skipping real SFTP test")

def main():
    """Main test runner"""
    print("🎯 SFTP Storage Test Suite")
    print("="*50)
    
    try:
        # Test configuration and local functionality
        test_sftp_storage_local()
        
        # Optional real SFTP test
        test_with_real_sftp()
        
        print("\\n" + "="*50)
        print("🎉 SFTP Storage tests completed!")
        print("\\n💡 To use SFTP storage in your monitoring:")
        print("   1. Configure SFTP settings in your config YAML file")
        print("   2. Set enabled: true in sftp_storage section") 
        print("   3. The monitoring service will automatically store notifications")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
