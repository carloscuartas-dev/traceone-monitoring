#!/usr/bin/env python3
"""
Test for possible upload directories on SFTP server
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from traceone_monitoring.storage.sftp_handler import SFTPConfig, SFTPNotificationStorage

def test_upload_directories():
    """Test for possible upload directories"""
    print("📤 Testing for Upload Directories")
    print("=" * 50)
    
    # Configuration
    config = SFTPConfig(
        hostname="mft.dnb.com",
        port=22,
        username="trace",
        private_key_path=str(Path.home() / ".ssh" / "id_rsa"),
        remote_base_path="/",
        file_format="json",
        timeout=30
    )
    
    try:
        storage = SFTPNotificationStorage(config)
        print("   🔌 Connecting to SFTP server...")
        storage.connect()
        print("   ✅ Connection successful!")
        
        # Test common upload directory names
        possible_upload_dirs = [
            "/puts",
            "/put", 
            "/upload",
            "/uploads",
            "/incoming", 
            "/inbound",
            "/outbound",
            "/outgoing",
            "/send",
            "/sends",
            "/drop",
            "/dropzone",
            "/data",
            "/files",
            "/exchange",
            "/trace/upload",
            "/trace/outgoing",
            "/trace/puts",
            "/home/trace",
            "/home/trace/upload",
            "/home/trace/outgoing"
        ]
        
        print(f"\n   🔍 Testing possible upload directories:")
        
        working_dirs = []
        
        for dir_path in possible_upload_dirs:
            try:
                print(f"\n      📂 Testing: {dir_path}")
                
                # Try to access the directory
                try:
                    items = storage.sftp.listdir(dir_path)
                    print(f"         ✅ Directory exists ({len(items)} items)")
                    
                    # Test write permissions
                    test_file = f"{dir_path.rstrip('/')}/write_test.tmp"
                    try:
                        with storage.sftp.file(test_file, 'w') as f:
                            f.write("write test")
                        print(f"         ✅ Write permission confirmed!")
                        
                        # Clean up immediately
                        storage.sftp.remove(test_file)
                        print(f"         🧹 Test file cleaned up")
                        
                        working_dirs.append(dir_path)
                        
                    except Exception as e:
                        print(f"         ❌ No write permission: {e}")
                        
                except FileNotFoundError:
                    print(f"         ❌ Directory does not exist")
                except Exception as e:
                    print(f"         ❌ Cannot access: {e}")
                    
            except Exception as e:
                print(f"      ❌ Failed to test {dir_path}: {e}")
        
        storage.disconnect()
        
        if working_dirs:
            print(f"\n🎯 FOUND WORKING DIRECTORIES:")
            for dir_path in working_dirs:
                print(f"   ✅ {dir_path}")
            print(f"\n💡 You can use any of these as your remote_base_path")
            return working_dirs
        else:
            print(f"\n❌ No writable directories found")
            print(f"💡 You may need to contact your SFTP server administrator")
            print(f"   to set up an upload directory or grant write permissions")
            return None
            
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return None

if __name__ == "__main__":
    test_upload_directories()
