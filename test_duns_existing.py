#!/usr/bin/env python3
"""
DUNS Test with Existing Registration
Tests DUNS addition using an existing registration from your dev account
"""

import sys
import asyncio
import logging
from pathlib import Path
import structlog

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from traceone_monitoring import DNBMonitoringService

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(name)s:%(levelname)s:%(message)s')
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Test data - using existing registrations from your dev account
EXISTING_REGISTRATIONS = [
    "TRACE_Company_info_dev",
    "traceone_test", 
    "traceone_training",
]

TEST_DUNS = [
    "004295520",  # D&B's own DUNS
    "117379158",  # Another test DUNS
]

async def test_duns_with_existing_registration():
    """Test DUNS operations with existing registration"""
    print("🧪 Testing DUNS Operations with Existing Registration")
    print("="*60)
    
    service = None
    try:
        # Initialize service
        print("🚀 Initializing service...")
        service = DNBMonitoringService.from_config("config/dev.yaml")
        client = service.api_client
        
        # Choose a registration to test with
        test_registration = EXISTING_REGISTRATIONS[0]  # Use TRACE_Company_info_dev
        print(f"🎯 Using existing registration: {test_registration}")
        
        # Test 1: Try to get registration details
        print(f"\n📋 Test 1: Getting details for registration '{test_registration}'...")
        try:
            # Try to get registration info
            endpoint = f"/v1/monitoring/registrations/{test_registration}"
            response = client.get(endpoint)
            
            print(f"   ✅ Registration details: {response.status_code}")
            if response.ok:
                data = response.json()
                print(f"   📊 Registration exists and is accessible")
                # Don't print full data as it might be large
                if 'transactionDetail' in data:
                    print(f"   🆔 Transaction ID: {data['transactionDetail'].get('transactionID', 'N/A')}")
        except Exception as e:
            print(f"   ⚠️  Could not get registration details: {e}")
        
        # Test 2: Try to add DUNS using the corrected batch method
        print(f"\n📥 Test 2: Adding DUNS to registration '{test_registration}'...")
        print(f"   📋 DUNS to add: {', '.join(TEST_DUNS)}")
        
        try:
            # Use the batch endpoint
            endpoint = f"/v1/monitoring/registrations/{test_registration}/subjects"
            csv_data = "\n".join(TEST_DUNS)  # Each DUNS on a new line
            
            headers = {
                "Content-Type": "text/csv",
            }
            
            print(f"   📤 PATCH {endpoint}")
            print(f"   📝 CSV data: '{csv_data}'")
            print(f"   📑 Headers: {headers}")
            
            # Make the request (this will show us the exact error)
            response = client.patch(endpoint, data=csv_data, headers=headers)
            
            print(f"   ✅ DUNS addition successful: {response.status_code}")
            if response.ok:
                print(f"   🎉 Successfully added {len(TEST_DUNS)} DUNS to monitoring!")
                result_data = response.text if response.text else "No response body"
                print(f"   📄 Response: {result_data[:200]}...")
                return True
            else:
                print(f"   📄 Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ DUNS addition failed: {e}")
            print(f"   💡 This helps us understand the correct format")
        
        # Test 3: Try individual DUNS addition
        print(f"\n🎯 Test 3: Trying individual DUNS addition...")
        try:
            single_duns = TEST_DUNS[0]
            endpoint = f"/v1/monitoring/registrations/{test_registration}/subjects/{single_duns}"
            params = {"subject": "duns"}
            
            print(f"   📤 POST {endpoint}")
            print(f"   📋 DUNS: {single_duns}")
            print(f"   📑 Params: {params}")
            
            response = client.post(endpoint, params=params)
            print(f"   ✅ Individual DUNS addition: {response.status_code}")
            if response.ok:
                print(f"   🎉 Successfully added DUNS {single_duns}!")
                return True
            else:
                print(f"   📄 Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Individual DUNS addition failed: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if service:
            print("\\n🧹 Cleaning up...")
            await service.shutdown()

def main():
    """Main test runner"""
    print("🎯 D&B DUNS Addition Test - Using Existing Registration")
    print("Testing with real registrations from your dev account")
    print("="*60)
    
    success = asyncio.run(test_duns_with_existing_registration())
    
    print("\\n" + "="*60)
    print("📊 TEST RESULTS:")
    if success:
        print("🎉 DUNS addition test PASSED!")
        print("   Your D&B integration is working correctly!")
    else:
        print("💡 DUNS addition revealed format/permission issues")
        print("   This is valuable information for debugging")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
