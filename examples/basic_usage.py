#!/usr/bin/env python3
"""
Basic usage example for TraceOne Monitoring Service
"""

import asyncio
from datetime import datetime, timedelta
import structlog

from traceone_monitoring import DNBMonitoringService
from traceone_monitoring.services.monitoring_service import (
    create_standard_monitoring_registration,
    log_notification_handler,
    alert_notification_handler
)


logger = structlog.get_logger(__name__)


async def basic_monitoring_example():
    """
    Basic example of setting up and running monitoring
    """
    logger.info("Starting basic monitoring example")
    
    # Initialize service from environment variables or config file
    service = DNBMonitoringService.from_config("config/dev.yaml")
    
    try:
        # Perform health check
        if not service.health_check():
            logger.error("Service health check failed")
            return
        
        # Create a standard monitoring registration
        config = create_standard_monitoring_registration(
            reference="TraceOne_Example_Standard",
            duns_list=["123456789", "987654321", "555666777"],
            description="Example standard monitoring for demo purposes"
        )
        
        registration = service.create_registration(config)
        logger.info("Registration created", 
                   reference=registration.reference,
                   id=str(registration.id))
        
        # Add notification handlers
        service.add_notification_handler(log_notification_handler)
        service.add_notification_handler(alert_notification_handler)
        
        # Activate monitoring
        await service.activate_monitoring(registration.reference)
        logger.info("Monitoring activated")
        
        # Pull notifications once to test
        notifications = await service.pull_notifications(registration.reference, max_notifications=10)
        logger.info("Pulled notifications", count=len(notifications))
        
        # Process notifications
        for notification in notifications:
            await service.process_notification(notification)
        
        # Example: Start continuous monitoring for 60 seconds
        logger.info("Starting continuous monitoring for 60 seconds...")
        
        end_time = datetime.now() + timedelta(seconds=60)
        async for notifications in service.monitor_continuously(registration.reference, polling_interval=10):
            if datetime.now() > end_time:
                break
                
            if notifications:
                logger.info("Received notifications in continuous mode", count=len(notifications))
                for notification in notifications:
                    await service.process_notification(notification)
        
        logger.info("Example completed successfully")
        
    except Exception as e:
        logger.error("Example failed", error=str(e))
        raise
    finally:
        # Cleanup
        await service.shutdown()


async def replay_example():
    """
    Example of using replay functionality to recover missed notifications
    """
    logger.info("Starting replay example")
    
    service = DNBMonitoringService.from_config()
    
    try:
        # Replay notifications from 24 hours ago
        start_time = datetime.utcnow() - timedelta(hours=24)
        
        replayed_notifications = await service.replay_notifications(
            "TraceOne_Example_Standard",
            start_time,
            max_notifications=50
        )
        
        logger.info("Replayed notifications", 
                   count=len(replayed_notifications),
                   start_time=start_time.isoformat())
        
        # Process replayed notifications
        for notification in replayed_notifications:
            await service.process_notification(notification)
            
    except Exception as e:
        logger.error("Replay example failed", error=str(e))
        raise
    finally:
        await service.shutdown()


async def batch_processing_example():
    """
    Example of batch processing for high-volume scenarios
    """
    logger.info("Starting batch processing example")
    
    service = DNBMonitoringService.from_config()
    
    try:
        # Pull all available notifications in batches
        from traceone_monitoring.api.pull_client import create_pull_client
        from traceone_monitoring.api.client import create_api_client
        from traceone_monitoring.auth.authenticator import create_authenticator
        
        # Create components
        config = service.config
        authenticator = create_authenticator(config.dnb_api)
        api_client = create_api_client(config.dnb_api, authenticator)
        pull_client = create_pull_client(api_client)
        
        # Pull all notifications
        batches = pull_client.pull_all_notifications(
            "TraceOne_Example_Standard",
            max_iterations=10,
            batch_size=25
        )
        
        logger.info("Pulled notification batches", count=len(batches))
        
        # Process batches
        total_processed = 0
        for batch in batches:
            processed_count = await service.process_notification_batch(batch)
            total_processed += processed_count
            
            logger.info("Processed batch",
                       batch_id=str(batch.id),
                       processed=processed_count,
                       total=total_processed)
        
        logger.info("Batch processing completed", total_processed=total_processed)
        
    except Exception as e:
        logger.error("Batch processing example failed", error=str(e))
        raise
    finally:
        await service.shutdown()


def custom_notification_handler(notifications):
    """
    Example custom notification handler
    """
    for notification in notifications:
        # Custom business logic here
        if notification.type.value == "UPDATE":
            logger.info("Processing UPDATE notification",
                       duns=notification.duns,
                       changes=len(notification.elements))
            
            # Example: Check for specific field changes
            for element in notification.elements:
                if "primaryName" in element.element:
                    logger.warning("Company name changed",
                                  duns=notification.duns,
                                  old_name=element.previous,
                                  new_name=element.current)
                elif "operatingStatus" in element.element:
                    logger.warning("Operating status changed",
                                  duns=notification.duns,
                                  old_status=element.previous,
                                  new_status=element.current)


async def custom_handler_example():
    """
    Example using custom notification handlers
    """
    logger.info("Starting custom handler example")
    
    service = DNBMonitoringService.from_config()
    
    try:
        # Add custom handler
        service.add_notification_handler(custom_notification_handler)
        
        # Pull and process notifications
        notifications = await service.pull_notifications("TraceOne_Example_Standard")
        
        for notification in notifications:
            await service.process_notification(notification)
            
    except Exception as e:
        logger.error("Custom handler example failed", error=str(e))
        raise
    finally:
        await service.shutdown()


def main():
    """
    Main function to run examples
    """
    # Setup logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Choose which example to run
    import sys
    if len(sys.argv) > 1:
        example_type = sys.argv[1]
    else:
        example_type = "basic"
    
    if example_type == "basic":
        asyncio.run(basic_monitoring_example())
    elif example_type == "replay":
        asyncio.run(replay_example())
    elif example_type == "batch":
        asyncio.run(batch_processing_example())
    elif example_type == "custom":
        asyncio.run(custom_handler_example())
    else:
        logger.error("Unknown example type", available=["basic", "replay", "batch", "custom"])


if __name__ == "__main__":
    main()
