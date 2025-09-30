#!/usr/bin/env python3
"""
Simple DUNS Test
Tests individual DUNS API operations to verify our request formats
"""

import sys
import asyncio
import logging
from pathlib import Path
import structlog

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from traceone_monitoring import DNBMonitoringService
from traceone_monitoring.api.client import DNBApiClient, DNBApiError

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s:%(levelname)s:%(message)s')
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

# Test data
TEST_DUNS = "004295520"  # D&B's own DUNS
FAKE_REGISTRATION_ID = "test-registration-123"

async def test_api_calls():
    """Test individual API calls to understand what works"""
    print("🔍 Testing individual D&B API calls...")
    print("="*60)
    
    service = None
    try:
        # Initialize service
        print("🚀 Initializing service...")
        service = DNBMonitoringService.from_config("config/dev.yaml")
        
        # Get the API client directly
        client = service.api_client
        
        # Test 1: Try to list existing registrations (if any)
        print("\n📋 Test 1: Attempting to list existing registrations...")
        try:
            response = client.get("/v1/monitoring/registrations")
            print(f"   ✅ Registrations list call successful: {response.status_code}")
            
            # Try to parse response
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                print(f"   📊 Response data: {data}")
            else:
                print(f"   📄 Response text: {response.text[:200]}...")
                
        except Exception as e:
            print(f"   ⚠️  List registrations failed: {e}")
        
        # Test 2: Try health check or basic API endpoint
        print("\n🏥 Test 2: Testing basic API health...")
        try:
            # Try different potential endpoints
            endpoints = [
                "/v1/health",
                "/v1/status", 
                "/v1/monitoring/health",
                "/v1/monitoring",
            ]
            
            for endpoint in endpoints:
                try:
                    response = client.get(endpoint)
                    print(f"   ✅ {endpoint}: {response.status_code}")
                    if response.ok:
                        if response.headers.get('content-type', '').startswith('application/json'):
                            print(f"      📊 Data: {response.json()}")
                        break
                except DNBApiError as e:
                    print(f"   ❌ {endpoint}: {e.status_code} - {e}")
                except Exception as e:
                    print(f"   ⚠️  {endpoint}: {e}")
                    
        except Exception as e:
            print(f"   ⚠️  Health check failed: {e}")
        
        # Test 3: Try to understand the registration creation API
        print("\n📝 Test 3: Testing registration creation API format...")
        try:
            # Read the standard monitoring config to see what format we should send
            import yaml
            with open("config/registrations/standard_monitoring.yaml", 'r') as f:
                config_data = yaml.safe_load(f)
            
            print(f"   📋 Config data structure: {list(config_data.keys())}")
            print(f"   🏷️  Reference: {config_data.get('reference')}")
            print(f"   🔧 Data blocks: {config_data.get('dataBlocks', [])}")
            
            # Try to create the registration via API
            endpoint = "/v1/monitoring/registrations"
            print(f"   📤 Attempting to POST to {endpoint}")
            
            response = client.post(endpoint, json=config_data)
            print(f"   ✅ Registration creation: {response.status_code}")
            
            if response.ok:
                registration_data = response.json()
                print(f"   📊 Created registration: {registration_data}")
                
                # Now try to add DUNS to this real registration
                actual_ref = registration_data.get('reference', config_data['reference'])
                return await test_duns_addition_with_real_registration(client, actual_ref)
            else:
                print(f"   📄 Response: {response.text[:300]}...")
                
        except Exception as e:
            print(f"   ⚠️  Registration creation test failed: {e}")
        
        print("\n💡 Suggestion: The registration may need to be created via API before adding DUNS")
        return False
        
    except Exception as e:
        print(f"❌ API test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if service:
            await service.shutdown()

async def test_duns_addition_with_real_registration(client: DNBApiClient, registration_ref: str):
    """Test DUNS addition with a real registration"""
    print(f"\n📥 Test 4: Adding DUNS to real registration '{registration_ref}'...")
    
    try:
        # Test the batch add endpoint
        endpoint = f"/v1/monitoring/registrations/{registration_ref}/subjects"
        csv_data = TEST_DUNS
        
        headers = {"Content-Type": "text/csv"}
        
        print(f"   📤 PATCH {endpoint}")
        print(f"   📋 CSV data: '{csv_data}'")
        print(f"   📑 Headers: {headers}")
        
        response = client.patch(endpoint, data=csv_data, headers=headers)
        print(f"   ✅ DUNS addition successful: {response.status_code}")
        return True
        
    except Exception as e:
        print(f"   ❌ DUNS addition failed: {e}")
        return False

def main():
    """Main test runner"""
    print("🎯 Simple D&B API DUNS Test")
    print("Testing individual API calls to understand the proper format")
    print("="*60)
    
    success = asyncio.run(test_api_calls())
    
    print("\n" + "="*60)
    if success:
        print("🎉 DUNS test PASSED!")
    else:
        print("💡 Test revealed API format/registration issues")
        print("   This helps us understand what needs to be fixed")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
