#!/usr/bin/env python3
"""
Simple Authentication Test
Just tests D&B API connection without creating registrations
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

async def test_authentication():
    """Simple authentication test"""
    print("🔐 Testing D&B API Authentication...")
    
    try:
        # Initialize service
        service = DNBMonitoringService.from_config("config/dev.yaml")
        
        # Test health check (includes authentication)
        health_status = service.health_check()
        
        if health_status:
            print("✅ SUCCESS: Authentication working!")
            
            # Get status details
            status = service.get_service_status()
            print(f"   🔑 Authenticated: {status['authentication']['is_authenticated']}")
            print(f"   ⏱️  Token expires in: {status['authentication']['token_expires_in']} seconds")
            print(f"   🌐 API Health: {status['api_client']['health_check']}")
            return True
        else:
            print("❌ FAILED: Authentication not working")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    finally:
        if 'service' in locals():
            await service.shutdown()

if __name__ == "__main__":
    success = asyncio.run(test_authentication())
    print("\n" + "="*50)
    if success:
        print("🎉 Authentication test PASSED! Ready for real-time testing.")
    else:
        print("💥 Authentication test FAILED. Check your credentials in config/dev.env")
    sys.exit(0 if success else 1)
