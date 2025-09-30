#!/usr/bin/env python3
"""
Debug SFTP Connection Issues
Compares CLI SSH connection with programmatic connection
"""

import sys
import os
import socket
from pathlib import Path
import paramiko
import getpass

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_connection_details():
    """Test and display connection details"""
    print("🔍 Testing Connection Details")
    print("=" * 50)
    
    hostname = "mft.dnb.com"
    port = 22
    username = "trace"
    
    print(f"Hostname: {hostname}")
    print(f"Port: {port}")
    print(f"Username: {username}")
    
    # Test DNS resolution
    print(f"\n🌐 DNS Resolution:")
    try:
        ip_addresses = socket.getaddrinfo(hostname, port)
        for addr in ip_addresses:
            print(f"   ✅ {addr[4][0]}:{addr[4][1]} ({addr[1]})")
    except Exception as e:
        print(f"   ❌ DNS Resolution failed: {e}")
        return False
    
    return True

def detect_key_type(private_key_path):
    """Detect the type of SSH private key"""
    print(f"\n🔑 Detecting key type for: {private_key_path}")
    
    try:
        with open(private_key_path, 'r') as f:
            key_content = f.read()
        
        if "BEGIN OPENSSH PRIVATE KEY" in key_content:
            print("   📋 Key format: OpenSSH format")
            # This could be RSA, Ed25519, ECDSA, etc. in OpenSSH format
            if "ssh-rsa" in key_content or "rsa" in private_key_path.lower():
                return "rsa-openssh"
            elif "ssh-ed25519" in key_content or "ed25519" in private_key_path.lower():
                return "ed25519"
            elif "ecdsa" in private_key_path.lower():
                return "ecdsa"
            else:
                return "unknown-openssh"
        elif "BEGIN RSA PRIVATE KEY" in key_content:
            print("   📋 Key format: RSA PKCS#1")
            return "rsa-pkcs1"
        elif "BEGIN PRIVATE KEY" in key_content:
            print("   📋 Key format: PKCS#8")
            return "pkcs8"
        elif "BEGIN DSA PRIVATE KEY" in key_content:
            print("   📋 Key format: DSA")
            return "dsa"
        elif "BEGIN EC PRIVATE KEY" in key_content:
            print("   📋 Key format: ECDSA")
            return "ecdsa"
        else:
            print("   ❓ Key format: Unknown")
            return "unknown"
    
    except Exception as e:
        print(f"   ❌ Error reading key: {e}")
        return None

def load_private_key_auto(private_key_path, passphrase=None):
    """Automatically detect and load private key"""
    key_type = detect_key_type(private_key_path)
    
    print(f"   🔧 Attempting to load {key_type} key...")
    
    # Try different key types
    key_loaders = [
        ("RSA", paramiko.RSAKey.from_private_key_file),
        ("Ed25519", paramiko.Ed25519Key.from_private_key_file), 
        ("ECDSA", paramiko.ECDSAKey.from_private_key_file),
    ]
    
    for key_name, loader in key_loaders:
        try:
            print(f"   🔄 Trying {key_name} loader...")
            key = loader(private_key_path, password=passphrase)
            print(f"   ✅ Success! Loaded as {key_name} key")
            return key
        except Exception as e:
            print(f"   ❌ {key_name} loader failed: {e}")
            continue
    
    raise Exception("Failed to load private key with any supported format")

def test_ssh_connection_methods():
    """Test different SSH connection methods"""
    print("\n🔌 Testing SSH Connection Methods")
    print("=" * 50)
    
    hostname = "mft.dnb.com"
    port = 22
    username = "trace"
    private_key_path = str(Path.home() / ".ssh" / "id_rsa")
    
    if not Path(private_key_path).exists():
        print(f"❌ Private key not found: {private_key_path}")
        return False
    
    print(f"Using private key: {private_key_path}")
    
    # Ask for passphrase if needed
    has_passphrase = input("Does your SSH key have a passphrase? (y/n): ").lower().strip()
    passphrase = None
    if has_passphrase in ['y', 'yes']:
        passphrase = getpass.getpass("SSH Key Passphrase: ")
    
    # Method 1: Using AutoAddPolicy (like in current code)
    print(f"\n📡 Method 1: Using AutoAddPolicy")
    try:
        client1 = paramiko.SSHClient()
        client1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Load key using auto-detection
        private_key = load_private_key_auto(private_key_path, passphrase)
        
        client1.connect(
            hostname=hostname,
            port=port,
            username=username,
            pkey=private_key,
            timeout=30
        )
        
        print("   ✅ Method 1 SUCCESS: AutoAddPolicy connection established!")
        
        # Test SFTP
        sftp1 = client1.open_sftp()
        print("   ✅ Method 1 SUCCESS: SFTP session opened!")
        sftp1.close()
        client1.close()
        
    except Exception as e:
        print(f"   ❌ Method 1 FAILED: {e}")
    
    # Method 2: Using known hosts (like CLI)
    print(f"\n📡 Method 2: Using known hosts file")
    try:
        client2 = paramiko.SSHClient()
        client2.load_system_host_keys()
        client2.load_host_keys(str(Path.home() / ".ssh" / "known_hosts"))
        
        # Load key using auto-detection
        private_key = load_private_key_auto(private_key_path, passphrase)
        
        client2.connect(
            hostname=hostname,
            port=port,
            username=username,
            pkey=private_key,
            timeout=30
        )
        
        print("   ✅ Method 2 SUCCESS: Known hosts connection established!")
        
        # Test SFTP
        sftp2 = client2.open_sftp()
        print("   ✅ Method 2 SUCCESS: SFTP session opened!")
        sftp2.close()
        client2.close()
        
    except Exception as e:
        print(f"   ❌ Method 2 FAILED: {e}")
    
    # Method 3: Using WarningPolicy (permissive but warns)
    print(f"\n📡 Method 3: Using WarningPolicy")
    try:
        client3 = paramiko.SSHClient()
        client3.set_missing_host_key_policy(paramiko.WarningPolicy())
        
        # Load key using auto-detection
        private_key = load_private_key_auto(private_key_path, passphrase)
        
        client3.connect(
            hostname=hostname,
            port=port,
            username=username,
            pkey=private_key,
            timeout=30
        )
        
        print("   ✅ Method 3 SUCCESS: WarningPolicy connection established!")
        
        # Test SFTP
        sftp3 = client3.open_sftp()
        print("   ✅ Method 3 SUCCESS: SFTP session opened!")
        sftp3.close()
        client3.close()
        
    except Exception as e:
        print(f"   ❌ Method 3 FAILED: {e}")
    
    return True

def test_connection_parameters():
    """Test connection with different parameters"""
    print("\n⚙️  Testing Connection Parameters")
    print("=" * 50)
    
    hostname = "mft.dnb.com"
    port = 22
    username = "trace"
    private_key_path = str(Path.home() / ".ssh" / "id_rsa")
    
    # Ask for passphrase if needed
    has_passphrase = input("Does your SSH key have a passphrase? (y/n): ").lower().strip()
    passphrase = None
    if has_passphrase in ['y', 'yes']:
        passphrase = getpass.getpass("SSH Key Passphrase: ")
    
    # Test with different parameters that CLI uses
    print(f"\n📡 Testing with CLI-like parameters")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Load key using auto-detection
        private_key = load_private_key_auto(private_key_path, passphrase)
        
        # Use similar settings as CLI
        client.connect(
            hostname=hostname,
            port=port,
            username=username,
            pkey=private_key,
            timeout=30,
            look_for_keys=False,  # Don't look for additional keys
            allow_agent=False,    # Don't use SSH agent (like CLI without agent)
            disabled_algorithms={'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']}  # Try without SHA-2
        )
        
        print("   ✅ SUCCESS: CLI-like connection established!")
        
        # Test SFTP
        sftp = client.open_sftp()
        print("   ✅ SUCCESS: SFTP session opened!")
        sftp.close()
        client.close()
        
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        
        # Try without disabled algorithms
        print(f"\n📡 Retrying without disabled algorithms")
        try:
            client2 = paramiko.SSHClient()
            client2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            private_key = load_private_key_auto(private_key_path, passphrase)
            
            client2.connect(
                hostname=hostname,
                port=port,
                username=username,
                pkey=private_key,
                timeout=30,
                look_for_keys=False,
                allow_agent=False
            )
            
            print("   ✅ SUCCESS: Connection without disabled algorithms!")
            
            # Test SFTP
            sftp2 = client2.open_sftp()
            print("   ✅ SUCCESS: SFTP session opened!")
            sftp2.close()
            client2.close()
            
        except Exception as e2:
            print(f"   ❌ FAILED again: {e2}")

def main():
    """Main debug runner"""
    print("🐛 SFTP Connection Debug Tool")
    print("=" * 50)
    
    # Test basic connectivity
    if not test_connection_details():
        print("❌ Basic connectivity failed, aborting")
        return
    
    # Test different connection methods
    test_ssh_connection_methods()
    
    # Test connection parameters
    test_connection_parameters()
    
    print(f"\n✅ Debug testing complete!")
    print("💡 Check which methods succeeded to identify the issue")

if __name__ == "__main__":
    main()
