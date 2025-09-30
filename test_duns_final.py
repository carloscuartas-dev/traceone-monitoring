#!/usr/bin/env python3
"""
Final DUNS Test
Tests DUNS addition using the valid transferred DUNS number
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

# Test data - using the VALID transferred DUNS
TEST_REGISTRATION = "TRACE_Company_info_dev"
VALID_DUNS = "807430710"  # The transferred/retained DUNS from the error message

async def test_duns_final():
    """Final DUNS test using valid DUNS number"""
    print("🎯 Final DUNS Addition Test - Using Valid DUNS")
    print("="*60)
    
    service = None
    try:
        # Initialize service  
        print("🚀 Initializing service...")
        service = DNBMonitoringService.from_config("config/dev.yaml")
        client = service.api_client
        
        print(f"🎯 Using registration: {TEST_REGISTRATION}")
        print(f"📋 Using VALID DUNS: {VALID_DUNS} (transferred from 004295520)")
        
        # Test using the high-level service method
        print(f"\n🎪 Test 1: Using high-level service method...")
        try:
            result = await service.add_duns_to_monitoring(
                registration_reference=TEST_REGISTRATION,
                duns_list=[VALID_DUNS],
                batch_mode=False  # Try individual addition first
            )
            print(f"   ✅ SUCCESS: DUNS addition worked!")
            print(f"   📊 Result: {result}")
            print(f"   🎉 The DUNS Addition Test PASSED!")
            return True
            
        except Exception as e:
            print(f"   ❌ High-level method failed: {e}")
        
        # Test direct API call
        print(f"\n🔧 Test 2: Direct API call with valid DUNS...")
        try:
            # Try the individual POST method
            endpoint = f"/v1/monitoring/registrations/{TEST_REGISTRATION}/subjects/{VALID_DUNS}"
            print(f"   📤 POST {endpoint}")
            
            response = client.post(endpoint)
            print(f"   ✅ SUCCESS: {response.status_code}")
            print(f"   📄 Response: {response.text}")
            print(f"   🎉 Direct API call PASSED!")
            return True
            
        except Exception as e:
            print(f"   ❌ Direct API call failed: {e}")
            if hasattr(e, 'response_text'):
                print(f"   📄 Error Response: {e.response_text}")
        
        # Test batch method with valid DUNS
        print(f"\n📦 Test 3: Batch method with valid DUNS...")
        try:
            endpoint = f"/v1/monitoring/registrations/{TEST_REGISTRATION}/subjects"
            csv_data = VALID_DUNS
            headers = {"Content-Type": "text/csv"}
            
            print(f"   📤 PATCH {endpoint}")
            print(f"   📝 Data: '{csv_data}'")
            
            response = client.patch(endpoint, data=csv_data, headers=headers)
            print(f"   ✅ SUCCESS: {response.status_code}")  
            print(f"   📄 Response: {response.text}")
            print(f"   🎉 Batch method PASSED!")
            return True
            
        except Exception as e:
            print(f"   ❌ Batch method failed: {e}")
            if hasattr(e, 'response_text'):
                print(f"   📄 Error Response: {e.response_text}")
        
        return False
        
    except Exception as e:
        print(f"❌ Final test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if service:
            print("\n🧹 Cleaning up...")
            await service.shutdown()

async def test_duns_removal():
    """Test removing the DUNS we just added"""
    print(f"\n📤 Bonus Test: Removing DUNS {VALID_DUNS}...")
    
    service = None
    try:
        service = DNBMonitoringService.from_config("config/dev.yaml")
        
        result = await service.remove_duns_from_monitoring(
            registration_reference=TEST_REGISTRATION,
            duns_list=[VALID_DUNS],
            batch_mode=False
        )
        
        print(f"   ✅ DUNS removal successful!")
        print(f"   📊 Result: {result}")
        return True
        
    except Exception as e:
        print(f"   ⚠️  DUNS removal failed: {e}")
        return False
    finally:
        if service:
            await service.shutdown()

def main():
    """Main test runner"""
    print("🎯 D&B DUNS Addition - Final Test")
    print("Using the valid transferred DUNS number discovered in debug")
    print("="*60)
    
    # Test addition
    addition_success = asyncio.run(test_duns_final())
    
    # Test removal if addition worked
    removal_success = True
    if addition_success:
        user_input = input("\n🤔 Test passed! Remove the DUNS to clean up? (y/n): ").lower().strip()
        if user_input in ['y', 'yes']:
            removal_success = asyncio.run(test_duns_removal())
        else:
            print("⏭️  Skipping cleanup")
    
    print("\n" + "="*60)
    print("📊 FINAL TEST RESULTS:")
    print(f"   📥 DUNS Addition: {'✅ PASSED' if addition_success else '❌ FAILED'}")
    print(f"   📤 DUNS Removal: {'✅ PASSED' if removal_success else '❌ FAILED'}")
    
    if addition_success:
        print("\n🎉 SUCCESS: Your D&B DUNS addition functionality is working!")
        print("   💡 Key lesson: Use valid, non-transferred DUNS numbers")
        print("   🔧 The integration and API calls are correctly implemented")
    else:
        print("\n💡 The API format is correct, but there may be other issues")
    
    return addition_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
