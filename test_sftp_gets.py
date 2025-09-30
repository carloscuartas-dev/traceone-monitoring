#!/usr/bin/env python3
"""
Test SFTP handler with /gets directory
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from traceone_monitoring.storage.sftp_handler import SFTPConfig, SFTPNotificationStorage
from traceone_monitoring.models.notification import Notification, NotificationType
from datetime import datetime

def test_gets_directory():
    """Test SFTP with /gets directory"""
    print("📁 Testing SFTP with /gets Directory")
    print("=" * 50)
    
    # Configuration with /gets directory
    config = SFTPConfig(
        hostname="mft.dnb.com",
        port=22,
        username="trace",
        private_key_path=str(Path.home() / ".ssh" / "id_rsa"),
        remote_base_path="/gets",  # Use the existing gets directory
        file_format="json",
        timeout=30
    )
    
    try:
        storage = SFTPNotificationStorage(config)
        print("   🔌 Connecting to SFTP server...")
        storage.connect()
        print("   ✅ Connection successful!")
        
        # Check what's in the gets directory
        print(f"\n   📁 /gets directory contents:")
        try:
            gets_items = storage.sftp.listdir_attr("/gets")
            for item in gets_items:
                is_dir = item.st_mode & 0o040000
                type_icon = "📁" if is_dir else "📄"
                permissions = oct(item.st_mode)[-3:]
                print(f"      {type_icon} {item.filename} (permissions: {permissions})")
                
        except Exception as e:
            print(f"      ❌ Cannot list /gets directory: {e}")
        
        # Test write permissions
        print(f"\n   📝 Testing write permissions in /gets:")
        test_file = "/gets/sftp_connection_test.txt"
        try:
            test_content = "SFTP connection test - connection working!\n"
            with storage.sftp.file(test_file, 'w') as f:
                f.write(test_content)
            print(f"      ✅ Can write files to /gets!")
            
            # Read back the file to confirm
            with storage.sftp.file(test_file, 'r') as f:
                content = f.read()
            print(f"      ✅ File content confirmed: '{content.strip()}'")
            
            # Clean up
            storage.sftp.remove(test_file)
            print(f"      🧹 Test file cleaned up")
            
        except Exception as e:
            print(f"      ❌ Cannot write to /gets: {e}")
            storage.disconnect()
            return False
        
        # Test with actual notifications
        print(f"\n   📤 Testing notification storage:")
        
        # Create test notifications
        notifications = []
        for i in range(2):
            notification_data = {
                "type": NotificationType.UPDATE,
                "organization": {"duns": f"12345678{i}"},
                "deliveryTimeStamp": datetime.utcnow(),
                "elements": []
            }
            notification = Notification(**notification_data)
            notifications.append(notification)
        
        result = storage.store_notifications(notifications, "ConnectionTest")
        
        print(f"      ✅ Upload successful!")
        print(f"         📊 Stored: {result['stored']} notifications")
        print(f"         📁 File: {result['files'][0]}")
        print(f"         🕒 Timestamp: {result['timestamp']}")
        
        storage.disconnect()
        
        print(f"\n🎉 SUCCESS! SFTP connection and storage is working correctly!")
        print(f"💡 Use '/gets' as your remote_base_path for SFTP storage")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_gets_directory()
