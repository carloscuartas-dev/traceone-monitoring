#!/usr/bin/env python3
"""
Debug credentials encoding and usage
"""

import base64
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment from the config file
env_path = Path("config/dev.env")
print(f"📁 Loading environment from: {env_path}")
load_dotenv(env_path)

# Get credentials
client_id = os.getenv('DNB_CLIENT_ID')
client_secret = os.getenv('DNB_CLIENT_SECRET')

print("\n🔑 Credential Check:")
print(f"   Client ID: {client_id[:10] if client_id else 'None'}...{client_id[-4:] if client_id else 'None'}")
print(f"   Client Secret: {client_secret[:10] if client_secret else 'None'}...{client_secret[-4:] if client_secret else 'None'}")

if not client_id or not client_secret:
    print("❌ Missing credentials!")
    sys.exit(1)

# Test encoding
print("\n🔐 Encoding Test:")
credentials = f"{client_id}:{client_secret}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()
print(f"   Raw: {credentials[:20]}...")
print(f"   Encoded: {encoded_credentials[:20]}...")

# Test what our service would use
print("\n🧪 Service Configuration Test:")
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from traceone_monitoring.utils.config import init_config
    
    config = init_config("config/dev.yaml")
    print(f"   Config Client ID: {config.dnb_api.client_id[:10]}...{config.dnb_api.client_id[-4:]}")
    print(f"   Config Client Secret: {config.dnb_api.client_secret[:10]}...{config.dnb_api.client_secret[-4:]}")
    
    # Test if they match
    if config.dnb_api.client_id == client_id:
        print("   ✅ Client ID matches")
    else:
        print("   ❌ Client ID mismatch!")
        
    if config.dnb_api.client_secret == client_secret:
        print("   ✅ Client Secret matches")
    else:
        print("   ❌ Client Secret mismatch!")

except Exception as e:
    print(f"   ❌ Config error: {e}")

print("\n" + "="*50)
