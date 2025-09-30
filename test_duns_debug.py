#!/usr/bin/env python3
"""
Debug DUNS Test
Captures exact error messages from D&B API to understand the proper format
"""

import sys
import asyncio
import logging
from pathlib import Path
import structlog

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from traceone_monitoring import DNBMonitoringService

# Setup logging with DEBUG level to see all request details
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
TEST_REGISTRATION = "TRACE_Company_info_dev"
TEST_DUNS = "004295520"  # D&B's own DUNS

async def debug_duns_operations():
    """Debug DUNS operations with detailed error capture"""
    print("🔍 Debug DUNS Operations - Capturing Exact Errors")
    print("="*60)
    
    service = None
    try:
        # Initialize service
        print("🚀 Initializing service...")
        service = DNBMonitoringService.from_config("config/dev.yaml")
        client = service.api_client
        
        print(f"🎯 Using registration: {TEST_REGISTRATION}")
        print(f"📋 Test DUNS: {TEST_DUNS}")
        
        # Test 1: Try individual DUNS addition with detailed error capture
        print(f"\n🎯 Test 1: Individual DUNS addition (detailed debugging)...")
        try:
            endpoint = f"/v1/monitoring/registrations/{TEST_REGISTRATION}/subjects/{TEST_DUNS}"
            
            print(f"   📤 POST {endpoint}")
            print(f"   📋 DUNS: {TEST_DUNS}")
            
            # Try different approaches
            
            # Approach A: With subject parameter
            print("\\n   🅰️  Approach A: With subject parameter...")
            try:
                params = {"subject": "duns"}
                print(f"      📑 Params: {params}")
                response = client.post(endpoint, params=params)
                print(f"      ✅ Success: {response.status_code}")
                print(f"      📄 Response: {response.text}")
            except Exception as e:
                print(f"      ❌ Failed: {e}")
                # Try to get the actual error response
                if hasattr(e, 'response_text'):
                    print(f"      📄 Error Response: {e.response_text}")
                if hasattr(e, 'status_code'):
                    print(f"      📊 Status Code: {e.status_code}")
            
            # Approach B: Without parameters
            print("\\n   🅱️  Approach B: No parameters...")
            try:
                response = client.post(endpoint)
                print(f"      ✅ Success: {response.status_code}")
                print(f"      📄 Response: {response.text}")
            except Exception as e:
                print(f"      ❌ Failed: {e}")
                if hasattr(e, 'response_text'):
                    print(f"      📄 Error Response: {e.response_text}")
            
            # Approach C: With JSON body
            print("\\n   ©️  Approach C: With JSON body...")
            try:
                json_data = {"subject": TEST_DUNS, "subjectType": "duns"}
                print(f"      📑 JSON: {json_data}")
                response = client.post(endpoint, json=json_data)
                print(f"      ✅ Success: {response.status_code}")
                print(f"      📄 Response: {response.text}")
            except Exception as e:
                print(f"      ❌ Failed: {e}")
                if hasattr(e, 'response_text'):
                    print(f"      📄 Error Response: {e.response_text}")
                    
        except Exception as e:
            print(f"   ❌ Individual DUNS test failed: {e}")
        
        # Test 2: Try batch DUNS addition with different formats
        print(f"\\n📥 Test 2: Batch DUNS addition (detailed debugging)...")
        try:
            endpoint = f"/v1/monitoring/registrations/{TEST_REGISTRATION}/subjects"
            print(f"   📤 PATCH {endpoint}")
            
            # Format A: Simple CSV
            print("\\n   🅰️  Format A: Simple CSV...")
            try:
                csv_data = TEST_DUNS
                headers = {"Content-Type": "text/csv"}
                print(f"      📝 Data: '{csv_data}'")
                print(f"      📑 Headers: {headers}")
                response = client.patch(endpoint, data=csv_data, headers=headers)
                print(f"      ✅ Success: {response.status_code}")
                print(f"      📄 Response: {response.text}")
            except Exception as e:
                print(f"      ❌ Failed: {e}")
                if hasattr(e, 'response_text'):
                    print(f"      📄 Error Response: {e.response_text}")
            
            # Format B: CSV with headers
            print("\\n   🅱️  Format B: CSV with headers...")
            try:
                csv_data = f"duns\\n{TEST_DUNS}"
                headers = {"Content-Type": "text/csv"}
                print(f"      📝 Data: '{csv_data}'")
                print(f"      📑 Headers: {headers}")
                response = client.patch(endpoint, data=csv_data, headers=headers)
                print(f"      ✅ Success: {response.status_code}")
                print(f"      📄 Response: {response.text}")
            except Exception as e:
                print(f"      ❌ Failed: {e}")
                if hasattr(e, 'response_text'):
                    print(f"      📄 Error Response: {e.response_text}")
            
            # Format C: JSON format
            print("\\n   ©️  Format C: JSON format...")
            try:
                json_data = {"subjects": [{"duns": TEST_DUNS}]}
                print(f"      📑 JSON: {json_data}")
                response = client.patch(endpoint, json=json_data)
                print(f"      ✅ Success: {response.status_code}")
                print(f"      📄 Response: {response.text}")
            except Exception as e:
                print(f"      ❌ Failed: {e}")
                if hasattr(e, 'response_text'):
                    print(f"      📄 Error Response: {e.response_text}")
                    
        except Exception as e:
            print(f"   ❌ Batch DUNS test failed: {e}")
        
        print("\\n💡 All tests completed. Check the error messages above for format clues.")
        return False  # We expect failures, this is about learning
        
    except Exception as e:
        print(f"❌ Debug test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if service:
            print("\\n🧹 Cleaning up...")
            await service.shutdown()

def main():
    """Main test runner"""
    print("🎯 D&B DUNS Debug Test")
    print("Capturing exact error messages to understand proper API format")
    print("="*60)
    
    asyncio.run(debug_duns_operations())
    
    print("\\n" + "="*60)
    print("📊 DEBUG COMPLETE")
    print("💡 Review the error messages above to understand the correct API format")
    print("   This information will help us fix the DUNS addition functionality")
    
    return True  # Success means we gathered debug info

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
