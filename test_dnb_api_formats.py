#!/usr/bin/env python3
"""
Test different content types and formats with D&B v3 API
"""

import base64
import requests
import os
import json
from dotenv import load_dotenv

# Load environment
load_dotenv("config/dev.env")

client_id = os.getenv('DNB_CLIENT_ID')
client_secret = os.getenv('DNB_CLIENT_SECRET')

print("🧪 Testing D&B v3 API Authentication Formats")
print("=" * 60)

if not client_id or not client_secret:
    print("❌ Missing credentials in config/dev.env")
    exit(1)

# Prepare credentials
credentials = f"{client_id}:{client_secret}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()

url = "https://plus.dnb.com/v3/token"

print(f"🌐 Testing URL: {url}")
print(f"🔑 Client ID: {client_id[:10]}...{client_id[-4:]}")

# Test 1: JSON content type with Bearer Basic auth
print("\n📋 Test 1: JSON content + Bearer Basic auth")
headers1 = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer Basic {encoded_credentials}",
}
payload1 = {"grant_type": "client_credentials"}

try:
    response1 = requests.post(url, json=payload1, headers=headers1, timeout=30)
    print(f"   Status: {response1.status_code}")
    if response1.status_code == 200:
        print("   ✅ SUCCESS!")
        token_data = response1.json()
        print(f"   Token: {token_data.get('access_token', 'N/A')[:20]}...")
    else:
        print(f"   ❌ Failed: {response1.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Form content type with Bearer Basic auth
print("\n📋 Test 2: Form content + Bearer Basic auth")
headers2 = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Authorization": f"Bearer Basic {encoded_credentials}",
}
payload2 = {"grant_type": "client_credentials"}

try:
    response2 = requests.post(url, data=payload2, headers=headers2, timeout=30)
    print(f"   Status: {response2.status_code}")
    if response2.status_code == 200:
        print("   ✅ SUCCESS!")
        token_data = response2.json()
        print(f"   Token: {token_data.get('access_token', 'N/A')[:20]}...")
    else:
        print(f"   ❌ Failed: {response2.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Form content type with Basic auth (standard)
print("\n📋 Test 3: Form content + Basic auth")
headers3 = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Authorization": f"Basic {encoded_credentials}",
}
payload3 = {"grant_type": "client_credentials"}

try:
    response3 = requests.post(url, data=payload3, headers=headers3, timeout=30)
    print(f"   Status: {response3.status_code}")
    if response3.status_code == 200:
        print("   ✅ SUCCESS!")
        token_data = response3.json()
        print(f"   Token: {token_data.get('access_token', 'N/A')[:20]}...")
    else:
        print(f"   ❌ Failed: {response3.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: JSON content type with Basic auth
print("\n📋 Test 4: JSON content + Basic auth")
headers4 = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {encoded_credentials}",
}
payload4 = {"grant_type": "client_credentials"}

try:
    response4 = requests.post(url, json=payload4, headers=headers4, timeout=30)
    print(f"   Status: {response4.status_code}")
    if response4.status_code == 200:
        print("   ✅ SUCCESS!")
        token_data = response4.json()
        print(f"   Token: {token_data.get('access_token', 'N/A')[:20]}...")
    else:
        print(f"   ❌ Failed: {response4.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("🏁 Test completed. Check which format succeeded above.")
