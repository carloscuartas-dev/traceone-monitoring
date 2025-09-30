"""
Unit tests for TraceOne Monitoring Service
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, call

from traceone_monitoring.services.monitoring_service import (
    DNBMonitoringService,
    MonitoringServiceError,
    log_notification_handler,
    alert_notification_handler
)
from traceone_monitoring.models.notification import NotificationType


@pytest.mark.services
class TestDNBMonitoringService:
    """Test cases for TraceOne monitoring service"""

    def test_initialization(self, monitoring_service, app_config):
        """Test monitoring service initialization"""
        assert monitoring_service.config == app_config
        assert monitoring_service.authenticator is not None
        assert monitoring_service.api_client is not None
        assert monitoring_service.pull_client is not None
        assert monitoring_service.registration_manager is not None
        assert len(monitoring_service._running_monitors) == 0
        assert len(monitoring_service._notification_handlers) == 0

    def test_from_config_file(self, temp_config_file):
        """Test creating service from config file"""
        service = DNBMonitoringService.from_config(temp_config_file)
        
        assert service.config.environment == "test"
        assert service.config.debug is True
        assert service.config.dnb_api.api_key == "test_api_key"

    def test_from_config_env(self):
        """Test creating service from environment variables"""
        with patch.dict('os.environ', {
            'TRACEONE_API_KEY': 'env_api_key',
            'TRACEONE_API_SECRET': 'env_api_secret',
            'ENVIRONMENT': 'test'
        }):
            service = DNBMonitoringService.from_config()
            assert service.config.dnb_api.api_key == 'env_api_key'

    def test_create_registration_from_config(self, monitoring_service, sample_registration_config):
        """Test creating registration from config"""
        # Mock registration manager
        monitoring_service.registration_manager.create_registration_from_config.return_value = Mock()
        
        result = monitoring_service.create_registration(sample_registration_config)
        
        monitoring_service.registration_manager.create_registration_from_config.assert_called_once_with(
            sample_registration_config
        )
        assert result is not None

    def test_create_registration_from_file(self, monitoring_service):
        """Test creating registration from file"""
        # Mock registration manager
        monitoring_service.registration_manager.create_registration_from_file.return_value = Mock()
        
        result = monitoring_service.create_registration_from_file("/path/to/config.yaml")
        
        monitoring_service.registration_manager.create_registration_from_file.assert_called_once_with(
            "/path/to/config.yaml"
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_add_duns_to_monitoring(self, monitoring_service):
        """Test adding DUNS to monitoring asynchronously"""
        duns_list = ["123456789", "987654321"]
        
        # Mock the registration manager method
        monitoring_service.registration_manager.add_duns_to_monitoring.return_value = True
        
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor.return_value = asyncio.Future()
            mock_loop.return_value.run_in_executor.return_value.set_result(True)
            
            result = await monitoring_service.add_duns_to_monitoring(
                "TestRegistration", duns_list, batch_mode=True
            )
            
            assert result is True

    @pytest.mark.asyncio
    async def test_remove_duns_from_monitoring(self, monitoring_service):
        """Test removing DUNS from monitoring asynchronously"""
        duns_list = ["123456789", "987654321"]
        
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor.return_value = asyncio.Future()
            mock_loop.return_value.run_in_executor.return_value.set_result(True)
            
            result = await monitoring_service.remove_duns_from_monitoring(
                "TestRegistration", duns_list
            )
            
            assert result is True

    @pytest.mark.asyncio
    async def test_activate_monitoring(self, monitoring_service):
        """Test activating monitoring for a registration"""
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor.return_value = asyncio.Future()
            mock_loop.return_value.run_in_executor.return_value.set_result(True)
            
            result = await monitoring_service.activate_monitoring("TestRegistration")
            
            assert result is True

    @pytest.mark.asyncio
    async def test_pull_notifications(self, monitoring_service, sample_notification_response):
        """Test pulling notifications for a registration"""
        # Mock pull client
        monitoring_service.pull_client.pull_notifications.return_value = sample_notification_response
        
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor.return_value = asyncio.Future()
            mock_loop.return_value.run_in_executor.return_value.set_result(sample_notification_response)
            
            result = await monitoring_service.pull_notifications("TestRegistration", max_notifications=100)
            
            assert len(result) == 1  # One notification in sample response

    @pytest.mark.asyncio
    async def test_replay_notifications(self, monitoring_service, sample_notification_response):
        """Test replaying notifications from a specific timestamp"""
        start_time = datetime(2025, 8, 26, 10, 0, 0)
        
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor.return_value = asyncio.Future()
            mock_loop.return_value.run_in_executor.return_value.set_result(sample_notification_response)
            
            result = await monitoring_service.replay_notifications(
                "TestRegistration", start_time, max_notifications=50
            )
            
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_monitor_continuously(self, monitoring_service, sample_registration):
        """Test continuous monitoring"""
        # Mock registration manager
        monitoring_service.registration_manager.get_registration.return_value = sample_registration
        
        # Mock pull client to return notifications
        async def mock_pull_continuously(*args, **kwargs):
            yield [Mock(), Mock()]  # Mock notifications
        
        monitoring_service.pull_client.pull_notifications_continuously = mock_pull_continuously
        
        # Test continuous monitoring
        result_count = 0
        async for notifications in monitoring_service.monitor_continuously("TestRegistration"):
            result_count += len(notifications)
            if result_count >= 2:  # Stop after getting some notifications
                break
        
        assert result_count == 2

    @pytest.mark.asyncio
    async def test_monitor_continuously_registration_not_found(self, monitoring_service):
        """Test continuous monitoring with non-existent registration"""
        # Mock registration manager to return None
        monitoring_service.registration_manager.get_registration.return_value = None
        
        with pytest.raises(MonitoringServiceError, match="Registration not found"):
            async for _ in monitoring_service.monitor_continuously("NonExistentReg"):
                pass

    def test_start_background_monitoring(self, monitoring_service):
        """Test starting background monitoring task"""
        handler = Mock()
        
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = Mock()
            mock_create_task.return_value = mock_task
            
            monitoring_service.start_background_monitoring(
                "TestRegistration", handler, polling_interval=30
            )
            
            assert "TestRegistration" in monitoring_service._running_monitors
            assert monitoring_service._running_monitors["TestRegistration"] == mock_task
            mock_create_task.assert_called_once()

    def test_start_background_monitoring_already_running(self, monitoring_service):
        """Test starting background monitoring when already running"""
        handler = Mock()
        
        # Mock already running task
        existing_task = Mock()
        monitoring_service._running_monitors["TestRegistration"] = existing_task
        
        with patch('asyncio.create_task') as mock_create_task:
            monitoring_service.start_background_monitoring("TestRegistration", handler)
            
            # Should not create new task
            mock_create_task.assert_not_called()

    def test_stop_background_monitoring(self, monitoring_service):
        """Test stopping background monitoring task"""
        # Mock running task
        mock_task = Mock()
        monitoring_service._running_monitors["TestRegistration"] = mock_task
        
        monitoring_service.stop_background_monitoring("TestRegistration")
        
        mock_task.cancel.assert_called_once()
        assert "TestRegistration" not in monitoring_service._running_monitors

    def test_stop_background_monitoring_not_running(self, monitoring_service):
        """Test stopping monitoring when not running"""
        # Should not raise exception
        monitoring_service.stop_background_monitoring("NonExistentReg")

    def test_stop_all_monitoring(self, monitoring_service):
        """Test stopping all background monitoring tasks"""
        # Mock running tasks
        mock_task1 = Mock()
        mock_task2 = Mock()
        monitoring_service._running_monitors = {
            "Reg1": mock_task1,
            "Reg2": mock_task2
        }
        
        monitoring_service.stop_all_monitoring()
        
        mock_task1.cancel.assert_called_once()
        mock_task2.cancel.assert_called_once()
        assert len(monitoring_service._running_monitors) == 0

    @pytest.mark.asyncio
    async def test_process_notification_success(self, monitoring_service, sample_notification):
        """Test successful notification processing"""
        handler = Mock()
        monitoring_service.add_notification_handler(handler)
        
        result = await monitoring_service.process_notification(sample_notification)
        
        assert result is True
        assert sample_notification.processed is True
        handler.assert_called_once_with([sample_notification])

    @pytest.mark.asyncio
    async def test_process_notification_handler_error(self, monitoring_service, sample_notification):
        """Test notification processing with handler error"""
        handler = Mock(side_effect=Exception("Handler error"))
        monitoring_service.add_notification_handler(handler)
        
        result = await monitoring_service.process_notification(sample_notification)
        
        assert result is False
        assert sample_notification.last_error == "Handler error"
        assert sample_notification.error_count == 1

    @pytest.mark.asyncio
    async def test_process_notification_batch(self, monitoring_service, test_helpers):
        """Test processing notification batch"""
        from traceone_monitoring.models.notification import NotificationBatch
        
        # Create mock notifications
        notifications = test_helpers.create_notification_batch(3)
        batch = NotificationBatch(notifications=notifications)
        
        # Add mock handler
        handler = Mock()
        monitoring_service.add_notification_handler(handler)
        
        result = await monitoring_service.process_notification_batch(batch)
        
        assert result == 3  # All notifications processed successfully
        assert batch.processed is True
        assert handler.call_count == 3  # Called once per notification

    def test_add_notification_handler(self, monitoring_service):
        """Test adding notification handler"""
        handler = Mock()
        
        monitoring_service.add_notification_handler(handler)
        
        assert len(monitoring_service._notification_handlers) == 1
        assert handler in monitoring_service._notification_handlers

    def test_remove_notification_handler(self, monitoring_service):
        """Test removing notification handler"""
        handler = Mock()
        monitoring_service.add_notification_handler(handler)
        
        monitoring_service.remove_notification_handler(handler)
        
        assert len(monitoring_service._notification_handlers) == 0
        assert handler not in monitoring_service._notification_handlers

    def test_get_service_status(self, monitoring_service, sample_registration):
        """Test getting comprehensive service status"""
        # Mock dependencies
        monitoring_service.registration_manager.list_registrations.return_value = [sample_registration]
        monitoring_service._running_monitors["TestReg"] = Mock()
        monitoring_service._notification_handlers.append(Mock())
        
        status = monitoring_service.get_service_status()
        
        assert status["service"]["running"] is True
        assert status["service"]["environment"] == "test"
        assert status["authentication"]["is_authenticated"] is True
        assert status["api_client"]["health_check"] is True
        assert status["registrations"]["total_count"] == 1
        assert status["registrations"]["background_monitors"] == 1
        assert status["notification_handlers"]["count"] == 1

    def test_health_check_success(self, monitoring_service):
        """Test successful health check"""
        result = monitoring_service.health_check()
        
        assert result is True
        monitoring_service.api_client.health_check.assert_called_once()

    def test_health_check_failure(self, monitoring_service):
        """Test health check failure"""
        # Mock API client health check failure
        monitoring_service.api_client.health_check.return_value = False
        
        result = monitoring_service.health_check()
        
        assert result is False

    def test_health_check_exception(self, monitoring_service):
        """Test health check with exception"""
        # Mock exception during health check
        monitoring_service.api_client.health_check.side_effect = Exception("Health check error")
        
        result = monitoring_service.health_check()
        
        assert result is False

    @pytest.mark.asyncio
    async def test_shutdown(self, monitoring_service):
        """Test graceful shutdown"""
        # Mock running tasks
        mock_task1 = AsyncMock()
        mock_task2 = AsyncMock()
        monitoring_service._running_monitors = {
            "Reg1": mock_task1,
            "Reg2": mock_task2
        }
        
        # Mock sessions with close method
        monitoring_service.api_client.session = Mock()
        monitoring_service.authenticator.session = Mock()
        
        await monitoring_service.shutdown()
        
        # Verify tasks were cancelled
        mock_task1.cancel.assert_called_once()
        mock_task2.cancel.assert_called_once()
        
        # Verify sessions were closed
        monitoring_service.api_client.session.close.assert_called_once()
        monitoring_service.authenticator.session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, monitoring_service):
        """Test async context manager functionality"""
        with patch.object(monitoring_service, 'shutdown', new_callable=AsyncMock) as mock_shutdown:
            async with monitoring_service as service:
                assert service is monitoring_service
            
            mock_shutdown.assert_called_once()

    def test_notification_handler_integration(self, monitoring_service, sample_notification):
        """Test integration with different notification handlers"""
        # Test log handler
        with patch('structlog.get_logger') as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log
            
            log_notification_handler([sample_notification])
            mock_log.info.assert_called_once()

        # Test alert handler for critical notification
        sample_notification.type = NotificationType.DELETE
        
        with patch('structlog.get_logger') as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log
            
            alert_notification_handler([sample_notification])
            mock_log.warning.assert_called_once()


@pytest.mark.services
class TestMonitoringServiceFactories:
    """Test factory functions for monitoring service"""

    def test_create_standard_monitoring_registration(self):
        """Test creating standard monitoring registration"""
        from traceone_monitoring.services.monitoring_service import create_standard_monitoring_registration
        
        config = create_standard_monitoring_registration(
            reference="StandardTest",
            duns_list=["123456789", "987654321"],
            description="Standard monitoring test"
        )
        
        assert config.reference == "StandardTest"
        assert len(config.duns_list) == 2
        assert "companyinfo_L2_v1" in config.data_blocks
        assert "organization.primaryName" in config.json_path_inclusion

    def test_create_financial_monitoring_registration(self):
        """Test creating financial monitoring registration"""
        from traceone_monitoring.services.monitoring_service import create_financial_monitoring_registration
        
        config = create_financial_monitoring_registration(
            reference="FinancialTest",
            duns_list=["123456789"],
            description="Financial monitoring test"
        )
        
        assert config.reference == "FinancialTest"
        assert len(config.duns_list) == 1
        assert "companyfinancials_L1_v1" in config.data_blocks
        assert "organization.financials" in config.json_path_inclusion


@pytest.mark.services
class TestNotificationHandlers:
    """Test notification handler functions"""

    def test_log_notification_handler(self, sample_notification):
        """Test log notification handler"""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            log_notification_handler([sample_notification])
            
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[1]
            assert call_args["duns"] == sample_notification.duns
            assert call_args["type"] == sample_notification.type.value

    def test_update_database_handler(self, sample_notification):
        """Test database update handler"""
        from traceone_monitoring.services.monitoring_service import update_database_handler
        
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            update_database_handler([sample_notification])
            
            mock_logger.info.assert_called_once()

    def test_alert_notification_handler_critical(self, sample_notification):
        """Test alert handler for critical notifications"""
        # Set to critical type
        sample_notification.type = NotificationType.DELETE
        
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            alert_notification_handler([sample_notification])
            
            mock_logger.warning.assert_called_once()

    def test_alert_notification_handler_non_critical(self, sample_notification):
        """Test alert handler for non-critical notifications"""
        # UPDATE is not critical
        assert sample_notification.type == NotificationType.UPDATE
        
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            alert_notification_handler([sample_notification])
            
            # Should not log warning for non-critical types
            mock_logger.warning.assert_not_called()

    def test_custom_notification_handler(self, monitoring_service, sample_notification):
        """Test custom notification handler integration"""
        handled_notifications = []
        
        def custom_handler(notifications):
            handled_notifications.extend(notifications)
        
        monitoring_service.add_notification_handler(custom_handler)
        
        # Simulate notification processing
        asyncio.run(monitoring_service.process_notification(sample_notification))
        
        assert len(handled_notifications) == 1
        assert handled_notifications[0] == sample_notification
