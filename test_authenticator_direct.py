#!/usr/bin/env python3
"""
Test that mimics the authenticator logic exactly
"""

import base64
import requests
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Load environment
load_dotenv("config/dev.env")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from traceone_monitoring.utils.config import init_config

print("🔍 Testing Authenticator Logic Directly")
print("=" * 50)

try:
    # Load config exactly like the authenticator does
    config = init_config("config/dev.yaml")
    
    print(f"🔑 Using credentials from config:")
    print(f"   Client ID: {config.dnb_api.client_id[:10]}...{config.dnb_api.client_id[-4:]}")
    print(f"   Client Secret: {config.dnb_api.client_secret[:10]}...{config.dnb_api.client_secret[-4:]}")
    
    # Prepare credentials exactly like authenticator does
    credentials = f"{config.dnb_api.client_id}:{config.dnb_api.client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    # Prepare request exactly like authenticator does
    url = f"{config.dnb_api.base_url}/v3/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}",
    }
    
    payload = {
        "grant_type": "client_credentials"
    }
    
    print(f"\n🌐 Making request to: {url}")
    print(f"🔐 Authorization header: Basic {encoded_credentials[:20]}...")
    print(f"📋 Content-Type: {headers['Content-Type']}")
    print(f"📦 Payload: {payload}")
    
    # Create session with retry strategy like authenticator does
    session = requests.Session()
    retry_strategy = Retry(
        total=config.dnb_api.retry_attempts,
        backoff_factor=config.dnb_api.backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Make request exactly like authenticator does
    response = session.post(
        url,
        data=payload,
        headers=headers,
        timeout=config.dnb_api.timeout
    )
    
    print(f"\n📊 Response:")
    print(f"   Status Code: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        print("   ✅ SUCCESS!")
        token_data = response.json()
        print(f"   🎫 Access Token: {token_data.get('access_token', 'N/A')[:20]}...")
        print(f"   ⏱️  Expires In: {token_data.get('expiresIn', 'N/A')} seconds")
        print(f"   📝 Full Response: {token_data}")
    else:
        print("   ❌ FAILED!")
        print(f"   📝 Response Text: {response.text}")
        
        # Debug the exact difference
        print(f"\n🔍 Debugging:")
        print(f"   Raw credentials: {credentials[:30]}...")
        print(f"   Encoded credentials: {encoded_credentials[:30]}...")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
