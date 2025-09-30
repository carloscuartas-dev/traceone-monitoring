#!/usr/bin/env python3
"""
SFTP SSH Key Authentication Test
Tests SSH key authentication with your SFTP server
"""

import sys
import os
from pathlib import Path
import getpass

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from traceone_monitoring.storage.sftp_handler import SFTPConfig, SFTPNotificationStorage
from traceone_monitoring.models.notification import Notification, NotificationType
from datetime import datetime

def check_ssh_keys():
    """Check available SSH keys"""
    print("🔍 Checking available SSH keys...")
    
    ssh_dir = Path.home() / ".ssh"
    if not ssh_dir.exists():
        print("❌ No ~/.ssh directory found")
        return []
    
    key_files = []
    common_keys = ["id_rsa", "id_ed25519", "id_dsa", "id_ecdsa"]
    
    for key_name in common_keys:
        private_key = ssh_dir / key_name
        public_key = ssh_dir / f"{key_name}.pub"
        
        if private_key.exists() and public_key.exists():
            # Check permissions
            stat = private_key.stat()
            permissions = oct(stat.st_mode)[-3:]
            
            print(f"   ✅ Found: {key_name}")
            print(f"      📁 Private: {private_key}")
            print(f"      🔐 Permissions: {permissions}")
            
            if permissions == "600" or permissions == "644":
                print(f"      ✅ Permissions OK")
            else:
                print(f"      ⚠️  Permissions should be 600, run: chmod 600 {private_key}")
            
            key_files.append({
                "name": key_name,
                "private_key": str(private_key),
                "public_key": str(public_key),
                "permissions": permissions
            })
    
    if not key_files:
        print("❌ No SSH key pairs found")
        print("💡 Generate a new key pair with:")
        print("   ssh-keygen -t ed25519 -f ~/.ssh/traceone_sftp_key")
    
    return key_files

def display_public_key(public_key_path):
    """Display public key content"""
    print(f"\\n📋 Public Key Content ({public_key_path}):")
    print("="*60)
    
    try:
        with open(public_key_path, 'r') as f:
            public_key_content = f.read().strip()
        
        print(public_key_content)
        print("="*60)
        print("\\n💡 Share this public key with your SFTP server administrator")
        print("⚠️  NEVER share the private key file!")
        
        return public_key_content
    except Exception as e:
        print(f"❌ Error reading public key: {e}")
        return None

def test_sftp_connection_interactive():
    """Interactive SFTP connection test"""
    print("\\n🌐 SFTP Connection Test with SSH Key Authentication")
    print("="*60)
    
    # Get connection details
    hostname = input("SFTP Hostname: ").strip()
    if not hostname:
        print("❌ Hostname is required")
        return False
    
    username = input("SFTP Username: ").strip() 
    if not username:
        print("❌ Username is required")
        return False
    
    port = input("SFTP Port [22]: ").strip()
    port = int(port) if port else 22
    
    # Show available keys
    print("\\n🔑 Available SSH Keys:")
    ssh_keys = check_ssh_keys()
    
    if not ssh_keys:
        return False
    
    # Let user choose key
    print("\\nChoose SSH key:")
    for i, key in enumerate(ssh_keys):
        print(f"   {i+1}. {key['name']} ({key['private_key']})")
    
    try:
        choice = int(input("\\nSelect key number: ")) - 1
        if choice < 0 or choice >= len(ssh_keys):
            print("❌ Invalid selection")
            return False
        
        selected_key = ssh_keys[choice]
        private_key_path = selected_key['private_key']
        
    except ValueError:
        print("❌ Invalid selection")
        return False
    
    # Display public key
    display_public_key(selected_key['public_key'])
    
    # Ask about passphrase
    has_passphrase = input("\\nDoes your SSH key have a passphrase? (y/n): ").lower().strip()
    
    passphrase = None
    if has_passphrase in ['y', 'yes']:
        passphrase = getpass.getpass("SSH Key Passphrase: ")
    
    print("\\n🔌 Testing SFTP connection...")
    
    # Create SFTP configuration
    config = SFTPConfig(
        hostname=hostname,
        port=port,
        username=username,
        private_key_path=private_key_path,
        private_key_passphrase=passphrase,
        remote_base_path="/notifications",
        file_format="json",
        timeout=30
    )
    
    try:
        # Test connection
        storage = SFTPNotificationStorage(config)
        
        print("   📡 Connecting to SFTP server...")
        storage.connect()
        
        print("   ✅ Connection successful!")
        
        # Test directory listing
        print("   📁 Testing directory access...")
        try:
            files = storage.list_remote_files()
            print(f"   📋 Found {len(files)} files in remote directory")
            
            # Show first few files
            for file_path in files[:3]:
                print(f"      📄 {file_path}")
            if len(files) > 3:
                print(f"      ... and {len(files) - 3} more files")
                
        except Exception as e:
            print(f"   ⚠️  Directory listing failed: {e}")
        
        # Test notification upload
        print("   📤 Testing notification upload...")
        test_notifications = create_test_notifications()
        
        result = storage.store_notifications(test_notifications, "SSHKeyTest")
        
        print(f"   ✅ Upload successful!")
        print(f"      📊 Stored {result['stored']} notifications")
        print(f"      📁 File: {result['files'][0]}")
        
        storage.disconnect()
        
        return True
        
    except Exception as e:
        print(f"   ❌ SFTP test failed: {e}")
        return False

def create_test_notifications():
    """Create test notifications"""
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
    
    return notifications

def generate_new_ssh_key():
    """Generate a new SSH key pair for SFTP"""
    print("\\n🔧 Generate New SSH Key for SFTP")
    print("="*40)
    
    key_name = input("Key name [traceone_sftp_key]: ").strip()
    if not key_name:
        key_name = "traceone_sftp_key"
    
    email = input("Email for key comment: ").strip()
    if not email:
        email = "traceone-monitoring@example.com"
    
    key_path = Path.home() / ".ssh" / key_name
    
    if key_path.exists():
        print(f"⚠️  Key {key_path} already exists")
        overwrite = input("Overwrite? (y/n): ").lower().strip()
        if overwrite not in ['y', 'yes']:
            return False
    
    # Generate key
    import subprocess
    
    print(f"🔑 Generating Ed25519 key: {key_path}")
    
    try:
        cmd = [
            "ssh-keygen", 
            "-t", "ed25519",
            "-f", str(key_path),
            "-C", email
        ]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print("✅ SSH key generated successfully!")
        print(f"   🔐 Private key: {key_path}")
        print(f"   📄 Public key: {key_path}.pub")
        
        # Set proper permissions
        os.chmod(key_path, 0o600)
        os.chmod(f"{key_path}.pub", 0o644)
        
        print("   ✅ Permissions set correctly")
        
        # Display public key
        display_public_key(f"{key_path}.pub")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Key generation failed: {e}")
        return False

def main():
    """Main test runner"""
    print("🎯 SFTP SSH Key Authentication Setup & Test")
    print("="*50)
    
    while True:
        print("\\nChoose an option:")
        print("1. 🔍 Check existing SSH keys")
        print("2. 🔧 Generate new SSH key for SFTP")
        print("3. 🌐 Test SFTP connection")
        print("4. 📋 Display public key")
        print("5. ❌ Exit")
        
        choice = input("\\nSelect option (1-5): ").strip()
        
        if choice == "1":
            check_ssh_keys()
        elif choice == "2":
            generate_new_ssh_key()
        elif choice == "3":
            test_sftp_connection_interactive()
        elif choice == "4":
            ssh_keys = check_ssh_keys()
            if ssh_keys:
                print("\\nSelect key to display:")
                for i, key in enumerate(ssh_keys):
                    print(f"   {i+1}. {key['name']}")
                
                try:
                    choice = int(input("Select key number: ")) - 1
                    if 0 <= choice < len(ssh_keys):
                        display_public_key(ssh_keys[choice]['public_key'])
                except ValueError:
                    print("❌ Invalid selection")
        elif choice == "5":
            break
        else:
            print("❌ Invalid option")
    
    print("\\n👋 SFTP SSH Key setup completed!")

if __name__ == "__main__":
    main()
