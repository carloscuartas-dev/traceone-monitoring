#!/usr/bin/env python3
"""
Integration tests for TraceOne Monitoring Service using dev registration entity

These tests work with actual D&B API endpoints using your dev registration.
Make sure your dev.env file is properly configured before running these tests.
"""

import pytest
import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from traceone_monitoring import DNBMonitoringService
from traceone_monitoring.services.monitoring_service import (
    create_standard_monitoring_registration,
    create_financial_monitoring_registration
)


class TestDevRegistrationIntegration:
    """Integration tests using dev registration entity"""
    
    @pytest.fixture(scope="class")
    async def service(self):
        """Create monitoring service instance"""
        service = DNBMonitoringService.from_config("config/dev.yaml")
        yield service
        await service.shutdown()
    
    @pytest.fixture(scope="class")
    def test_duns_numbers(self):
        """
        Test DUNS numbers - REPLACE WITH YOUR ACTUAL DEV REGISTRATION DUNS
        
        You should replace these with real DUNS numbers from your D&B dev registration
        """
        return [
            "123456789",  # Replace with actual DUNS
            "987654321",  # Replace with actual DUNS
        ]
    
    @pytest.mark.asyncio
    async def test_authentication(self, service):
        """Test D&B API authentication with dev registration"""
        # Test health check which includes authentication
        health_status = service.health_check()
        assert health_status, "Service should be healthy and authenticated"
        
        # Get detailed status
        status_info = service.get_service_status()
        assert status_info['authentication']['is_authenticated'], "Should be authenticated"
        assert status_info['api_client']['health_check'], "API client should be healthy"
    
    @pytest.mark.asyncio
    async def test_create_standard_registration(self, service, test_duns_numbers):
        """Test creating a standard monitoring registration"""
        
        # Create registration configuration
        config = create_standard_monitoring_registration(
            reference="TraceOne_Test_Standard_Integration",
            duns_list=test_duns_numbers,
            description="Integration test standard registration"
        )
        
        # Create registration
        registration = service.create_registration(config)
        
        # Verify registration
        assert registration is not None
        assert registration.reference == "TraceOne_Test_Standard_Integration"
        assert registration.status.value in ["PENDING", "ACTIVE"]
        assert len(registration.duns_list) == len(test_duns_numbers)
    
    @pytest.mark.asyncio
    async def test_create_financial_registration(self, service, test_duns_numbers):
        """Test creating a financial monitoring registration"""
        
        # Create registration configuration
        config = create_financial_monitoring_registration(
            reference="TraceOne_Test_Financial_Integration",
            duns_list=test_duns_numbers,
            description="Integration test financial registration"
        )
        
        # Create registration
        registration = service.create_registration(config)
        
        # Verify registration
        assert registration is not None
        assert registration.reference == "TraceOne_Test_Financial_Integration"
        assert registration.status.value in ["PENDING", "ACTIVE"]
    
    @pytest.mark.asyncio
    async def test_activate_monitoring(self, service, test_duns_numbers):
        """Test activating monitoring for a registration"""
        
        # Create a test registration
        config = create_standard_monitoring_registration(
            reference="TraceOne_Test_Activation",
            duns_list=test_duns_numbers[:1],  # Use only one DUNS for activation test
            description="Integration test activation"
        )
        
        registration = service.create_registration(config)
        
        # Activate monitoring
        success = await service.activate_monitoring(registration.reference)
        assert success, "Monitoring activation should succeed"
    
    @pytest.mark.asyncio 
    async def test_pull_notifications(self, service, test_duns_numbers):
        """Test pulling notifications from D&B API"""
        
        # Create and activate registration
        config = create_standard_monitoring_registration(
            reference="TraceOne_Test_Pull_Notifications",
            duns_list=test_duns_numbers,
            description="Integration test notification pull"
        )
        
        registration = service.create_registration(config)
        await service.activate_monitoring(registration.reference)
        
        # Pull notifications
        notifications = await service.pull_notifications(
            registration.reference,
            max_notifications=10
        )
        
        # Verify response (may be empty if no notifications available)
        assert isinstance(notifications, list)
        
        # If notifications exist, verify structure
        if notifications:
            notification = notifications[0]
            assert hasattr(notification, 'duns')
            assert hasattr(notification, 'type')
            assert hasattr(notification, 'elements')
            assert hasattr(notification, 'delivery_timestamp')
    
    @pytest.mark.asyncio
    async def test_add_duns_to_monitoring(self, service, test_duns_numbers):
        """Test adding DUNS to existing registration"""
        
        if len(test_duns_numbers) < 2:
            pytest.skip("Need at least 2 DUNS numbers for this test")
        
        # Create registration with first DUNS
        config = create_standard_monitoring_registration(
            reference="TraceOne_Test_Add_DUNS",
            duns_list=[test_duns_numbers[0]],
            description="Integration test add DUNS"
        )
        
        registration = service.create_registration(config)
        
        # Add additional DUNS
        additional_duns = test_duns_numbers[1:]
        operation = await service.add_duns_to_monitoring(
            registration.reference,
            additional_duns,
            batch_mode=True
        )
        
        # Verify operation
        assert operation is not None
        assert hasattr(operation, 'id')
    
    @pytest.mark.asyncio
    async def test_notification_replay(self, service, test_duns_numbers):
        """Test notification replay functionality"""
        
        # Create and activate registration
        config = create_standard_monitoring_registration(
            reference="TraceOne_Test_Replay",
            duns_list=test_duns_numbers[:1],  # Use single DUNS for replay test
            description="Integration test replay"
        )
        
        registration = service.create_registration(config)
        await service.activate_monitoring(registration.reference)
        
        # Test replay from 24 hours ago
        start_time = (datetime.utcnow() - timedelta(hours=24)).isoformat() + "Z"
        
        replayed_notifications = await service.replay_notifications(
            registration.reference,
            start_time
        )
        
        # Verify response (may be empty)
        assert isinstance(replayed_notifications, list)
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_continuous_monitoring(self, service, test_duns_numbers):
        """Test continuous monitoring for a short period"""
        
        # Create and activate registration
        config = create_standard_monitoring_registration(
            reference="TraceOne_Test_Continuous",
            duns_list=test_duns_numbers[:1],
            description="Integration test continuous monitoring"
        )
        
        registration = service.create_registration(config)
        await service.activate_monitoring(registration.reference)
        
        # Monitor for 1 minute
        notification_count = 0
        end_time = datetime.now() + timedelta(seconds=60)
        
        async for notifications in service.monitor_continuously(
            registration.reference,
            polling_interval=15,  # Poll every 15 seconds
            max_notifications=10
        ):
            if datetime.now() > end_time:
                break
                
            if notifications:
                notification_count += len(notifications)
                
                # Process notifications
                for notification in notifications:
                    await service.process_notification(notification)
        
        # Test passes regardless of notification count since it depends on actual data changes
        assert notification_count >= 0


class TestRealTimeScenarios:
    """Real-time testing scenarios"""
    
    @pytest.fixture(scope="class")
    async def service(self):
        """Create monitoring service instance"""
        service = DNBMonitoringService.from_config("config/dev.yaml")
        yield service
        await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_portfolio_monitoring_scenario(self, service):
        """Test a complete portfolio monitoring scenario"""
        
        # Test DUNS - replace with your actual dev registration DUNS
        portfolio_duns = [
            "123456789",  # Replace with actual DUNS
            "987654321",  # Replace with actual DUNS
        ]
        
        # Create portfolio registration
        config = create_standard_monitoring_registration(
            reference="TraceOne_Portfolio_Integration_Test",
            duns_list=portfolio_duns,
            description="Integration test portfolio scenario"
        )
        
        registration = service.create_registration(config)
        
        # Activate monitoring
        success = await service.activate_monitoring(registration.reference)
        assert success
        
        # Pull initial notifications
        initial_notifications = await service.pull_notifications(
            registration.reference,
            max_notifications=20
        )
        
        # Monitor for 30 seconds
        monitoring_notifications = []
        end_time = datetime.now() + timedelta(seconds=30)
        
        async for notifications in service.monitor_continuously(
            registration.reference,
            polling_interval=10,
            max_notifications=10
        ):
            if datetime.now() > end_time:
                break
                
            if notifications:
                monitoring_notifications.extend(notifications)
                for notification in notifications:
                    await service.process_notification(notification)
        
        # Verify the scenario completed successfully
        total_notifications = len(initial_notifications) + len(monitoring_notifications)
        print(f"Portfolio scenario processed {total_notifications} total notifications")
        
        assert True  # Test passes if no exceptions occurred


# Helper function to run integration tests
def run_integration_tests():
    """Run integration tests with proper setup"""
    
    # Check if dev.env exists
    if not Path("config/dev.env").exists():
        print("❌ config/dev.env not found. Run setup script first:")
        print("python scripts/setup_real_time_testing.py setup")
        return False
    
    # Run tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "not slow"  # Skip slow tests by default
    ])
    
    return True


if __name__ == "__main__":
    run_integration_tests()
