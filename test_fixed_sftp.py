#!/usr/bin/env python3
"""
Test the fixed SFTP handler with automatic key detection
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from traceone_monitoring.storage.sftp_handler import SFTPConfig, SFTPNotificationStorage
from traceone_monitoring.models.notification import Notification, NotificationType
from datetime import datetime

def test_fixed_sftp():
    """Test the fixed SFTP handler"""
    print("🧪 Testing Fixed SFTP Handler")
    print("=" * 50)
    
    # Configuration
    config = SFTPConfig(
        hostname="mft.dnb.com",
        port=22,
        username="trace",
        private_key_path=str(Path.home() / ".ssh" / "id_rsa"),
        remote_base_path="/notifications",
        file_format="json",
        timeout=30
    )
    
    print(f"📋 Configuration:")
    print(f"   🌐 Host: {config.hostname}:{config.port}")
    print(f"   👤 User: {config.username}")
    print(f"   🔑 Key: {config.private_key_path}")
    print(f"   📁 Remote Path: {config.remote_base_path}")
    
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
    
    print(f"\n📤 Testing SFTP Storage...")
    print(f"   📊 Notifications to store: {len(notifications)}")
    
    try:
        # Create storage handler
        storage = SFTPNotificationStorage(config)
        
        print("   🔌 Connecting to SFTP server...")
        storage.connect()
        
        print("   ✅ Connection successful!")
        
        print("   📁 Testing directory listing...")
        try:
            files = storage.list_remote_files()
            print(f"   📋 Found {len(files)} files on remote server")
        except Exception as e:
            print(f"   ⚠️  Directory listing failed: {e}")
        
        print("   📤 Testing notification upload...")
        result = storage.store_notifications(notifications, "FixedHandlerTest")
        
        print(f"   ✅ Upload successful!")
        print(f"      📊 Stored: {result['stored']} notifications")
        print(f"      📁 File: {result['files'][0]}")
        print(f"      🕒 Timestamp: {result['timestamp']}")
        
        storage.disconnect()
        
        print(f"\n🎉 All tests passed! The SFTP handler is working correctly.")
        return True
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_fixed_sftp()
