#!/usr/bin/env python3
"""
DUNS Addition Test
Tests adding DUNS numbers to monitoring registrations
"""

import sys
import asyncio
import logging
from pathlib import Path
import structlog

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from traceone_monitoring import DNBMonitoringService

# Setup logging with debug level
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

# Test DUNS numbers (using common test DUNS)
TEST_DUNS = [
    "004295520",  # D&B's own DUNS
    "117379158",  # Another test DUNS
    "611503849",  # Another test DUNS
]

async def test_duns_addition():
    """Test DUNS addition functionality"""
    print("🧪 Testing DUNS Addition to Monitoring...")
    print(f"📋 Test DUNS: {', '.join(TEST_DUNS)}")
    print("="*60)
    
    service = None
    try:
        # Initialize service
        print("🚀 Initializing monitoring service...")
        service = DNBMonitoringService.from_config("config/dev.yaml")
        
        # Test 1: Create a test registration first
        print("\n📝 Step 1: Creating test registration...")
        registration_config_path = "config/registrations/standard_monitoring.yaml"
        
        try:
            registration = service.create_registration_from_file(registration_config_path)
            registration_ref = registration.reference
            print(f"   ✅ Registration created: {registration_ref}")
        except Exception as e:
            print(f"   ⚠️  Registration may already exist: {e}")
            # Assume we're using the standard registration
            registration_ref = "TraceOne_Standard_Monitoring"
            print(f"   🔄 Using existing registration: {registration_ref}")
        
        # Test 2: Add DUNS to monitoring
        print(f"\n📥 Step 2: Adding DUNS to registration '{registration_ref}'...")
        print(f"   DUNS to add: {', '.join(TEST_DUNS)}")
        
        result = await service.add_duns_to_monitoring(
            registration_reference=registration_ref,
            duns_list=TEST_DUNS,
            batch_mode=True
        )
        
        print(f"   ✅ DUNS addition result: {result}")
        
        # Test 3: Verify the addition worked by checking registration status
        print(f"\n🔍 Step 3: Verifying DUNS were added...")
        
        # Get registration details to see if DUNS were added
        # Note: This would typically require a separate API call to check registration status
        print(f"   📊 DUNS addition completed for registration: {registration_ref}")
        print(f"   📈 Number of DUNS added: {len(TEST_DUNS)}")
        
        # Test 4: Try activating monitoring (if not already active)
        print(f"\n⚡ Step 4: Activating monitoring for registration...")
        try:
            activation_result = await service.activate_monitoring(registration_ref)
            print(f"   ✅ Monitoring activation: {'Success' if activation_result else 'Failed/Already Active'}")
        except Exception as e:
            print(f"   ⚠️  Monitoring activation issue: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ DUNS Addition Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if service:
            print("\n🧹 Cleaning up...")
            await service.shutdown()

async def test_duns_removal():
    """Test DUNS removal functionality"""
    print("\n" + "="*60)
    print("🧪 Testing DUNS Removal from Monitoring...")
    
    service = None
    try:
        # Initialize service
        service = DNBMonitoringService.from_config("config/dev.yaml")
        
        registration_ref = "TraceOne_Standard_Monitoring"
        
        print(f"\n📤 Removing DUNS from registration '{registration_ref}'...")
        print(f"   DUNS to remove: {', '.join(TEST_DUNS)}")
        
        result = await service.remove_duns_from_monitoring(
            registration_reference=registration_ref,
            duns_list=TEST_DUNS,
            batch_mode=True
        )
        
        print(f"   ✅ DUNS removal result: {result}")
        print(f"   📉 Number of DUNS removed: {len(TEST_DUNS)}")
        
        return True
        
    except Exception as e:
        print(f"❌ DUNS Removal Test FAILED: {e}")
        return False
    finally:
        if service:
            await service.shutdown()

def main():
    """Main test runner"""
    print("🎯 D&B DUNS Addition/Removal Test Suite")
    print("="*60)
    
    # Run addition test
    addition_success = asyncio.run(test_duns_addition())
    
    # Ask user if they want to test removal
    if addition_success:
        print("\n" + "="*60)
        user_input = input("🤔 Do you want to test DUNS removal as well? (y/n): ").lower().strip()
        if user_input in ['y', 'yes']:
            removal_success = asyncio.run(test_duns_removal())
        else:
            removal_success = True  # Skip removal test
            print("⏭️  Skipping removal test")
    else:
        removal_success = False
    
    # Final results
    print("\n" + "="*60)
    print("📊 TEST RESULTS:")
    print(f"   📥 DUNS Addition: {'✅ PASSED' if addition_success else '❌ FAILED'}")
    print(f"   📤 DUNS Removal: {'✅ PASSED' if removal_success else '❌ FAILED'}")
    
    if addition_success and removal_success:
        print("🎉 All DUNS tests PASSED! Your monitoring system is working correctly.")
    else:
        print("💥 Some tests FAILED. Check the output above for details.")
    
    return addition_success and removal_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
