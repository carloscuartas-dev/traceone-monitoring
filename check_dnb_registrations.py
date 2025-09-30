#!/usr/bin/env python3
"""
Check existing D&B registrations directly from API
"""

import sys
import os
import asyncio

# Add the source directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
from traceone_monitoring.utils.config import ConfigManager
from traceone_monitoring.services.monitoring_service import DNBMonitoringService
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

async def check_dnb_registrations():
    """Check existing D&B registrations via API"""
    
    # Load configuration
    load_dotenv('config/real-test.env')
    config_manager = ConfigManager.from_file('config/real-test.yaml')
    app_config = config_manager.load_config()
    service = DNBMonitoringService(app_config)
    
    try:
        print("🔍 Checking D&B API for existing registrations...")
        
        # Try to get registrations from D&B API
        # This would use the pull client to check existing registrations
        
        # For now, let's check if we can authenticate and call the API
        auth_test = await asyncio.get_event_loop().run_in_executor(
            None, service.authenticator.get_token
        )
        
        if auth_test:
            print("✅ Successfully authenticated with D&B API")
            
            # Try to call the API endpoint that lists registrations
            try:
                endpoint = "/v1/monitoring/registrations"
                response = await asyncio.get_event_loop().run_in_executor(
                    None, service.api_client.get, endpoint
                )
                
                print(f"📋 D&B API Response: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    registrations = data.get('registrations', [])
                    
                    print(f"Found {len(registrations)} registrations:")
                    for reg in registrations:
                        print(f"   • ID: {reg.get('id')}")
                        print(f"   • Reference: {reg.get('reference')}")
                        print(f"   • Status: {reg.get('status')}")
                        print(f"   • Created: {reg.get('createdDate')}")
                        print("   " + "-"*50)
                else:
                    print(f"❌ API call failed with status: {response.status_code}")
                    print(f"Response: {response.text}")
                    
            except Exception as e:
                print(f"⚠️  Error calling registrations API: {e}")
                print("This might be expected if the endpoint format is different")
                
        else:
            print("❌ Authentication failed")
            
    except Exception as e:
        logger.error("Error checking registrations", error=str(e))
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_dnb_registrations())
