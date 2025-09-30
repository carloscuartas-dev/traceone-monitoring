#!/usr/bin/env python3
"""
Explore SFTP server directory structure and test permissions
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from traceone_monitoring.storage.sftp_handler import SFTPConfig, SFTPNotificationStorage

def explore_sftp_server():
    """Explore SFTP server and test permissions"""
    print("🔍 Exploring SFTP Server")
    print("=" * 50)
    
    # Configuration with basic connection
    config = SFTPConfig(
        hostname="mft.dnb.com",
        port=22,
        username="trace",
        private_key_path=str(Path.home() / ".ssh" / "id_rsa"),
        remote_base_path="/",  # Start from root
        file_format="json",
        timeout=30
    )
    
    try:
        storage = SFTPNotificationStorage(config)
        print("   🔌 Connecting to SFTP server...")
        storage.connect()
        print("   ✅ Connection successful!")
        
        # Check what's in the root directory
        print("\n   📁 Root directory contents:")
        try:
            root_items = storage.sftp.listdir_attr("/")
            for item in root_items:
                is_dir = item.st_mode & 0o040000
                type_icon = "📁" if is_dir else "📄"
                permissions = oct(item.st_mode)[-3:]
                print(f"      {type_icon} {item.filename} (permissions: {permissions})")
                
        except Exception as e:
            print(f"      ❌ Cannot list root directory: {e}")
        
        # Try common directories where you might have write access
        test_paths = [
            "/home/trace",
            "/tmp", 
            "/var/tmp",
            "/upload",
            "/incoming",
            "/data",
            "/trace",
            ".",  # Current working directory
        ]
        
        print(f"\n   🔍 Testing write permissions in various directories:")
        
        for path in test_paths:
            try:
                print(f"\n      📂 Testing: {path}")
                
                # Try to list directory contents
                try:
                    items = storage.sftp.listdir(path)
                    print(f"         ✅ Can list directory ({len(items)} items)")
                    
                    # Show first few items
                    for item in items[:3]:
                        print(f"            - {item}")
                    if len(items) > 3:
                        print(f"            ... and {len(items) - 3} more")
                        
                except Exception as e:
                    print(f"         ❌ Cannot list: {e}")
                    continue
                
                # Try to create a test file
                test_file = f"{path.rstrip('/')}/sftp_test_file.txt"
                try:
                    test_content = b"SFTP connection test - you can delete this file"
                    with storage.sftp.file(test_file, 'w') as f:
                        f.write(test_content.decode())
                    print(f"         ✅ Can write files!")
                    
                    # Clean up test file
                    try:
                        storage.sftp.remove(test_file)
                        print(f"         🧹 Test file cleaned up")
                    except:
                        print(f"         ⚠️  Could not delete test file: {test_file}")
                    
                    # This directory has write access
                    print(f"         🎯 SUITABLE DIRECTORY FOUND: {path}")
                    break
                    
                except Exception as e:
                    print(f"         ❌ Cannot write: {e}")
                    
            except Exception as e:
                print(f"      ❌ Cannot access {path}: {e}")
        
        storage.disconnect()
        
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    explore_sftp_server()
