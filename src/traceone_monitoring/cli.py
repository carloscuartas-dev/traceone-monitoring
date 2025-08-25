"""
Command Line Interface for TraceOne Monitoring Service
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional
import click
import structlog

from .services.monitoring_service import (
    DNBMonitoringService,
    create_standard_monitoring_registration,
    create_financial_monitoring_registration,
    log_notification_handler
)
from .models.registration import RegistrationConfig
from .utils.config import init_config


logger = structlog.get_logger(__name__)


@click.group()
@click.option('--config', '-c', help='Configuration file path')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.pass_context
def cli(ctx, config, debug):
    """TraceOne D&B Monitoring Service CLI"""
    ctx.ensure_object(dict)
    
    # Initialize configuration
    try:
        app_config = init_config(config)
        ctx.obj['config'] = app_config
        
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
                structlog.processors.JSONRenderer() if app_config.logging.format == "json" 
                else structlog.dev.ConsoleRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        if debug:
            logger.setLevel("DEBUG")
        
        logger.info("TraceOne Monitoring CLI initialized",
                   environment=app_config.environment,
                   debug=debug)
        
    except Exception as e:
        click.echo(f"Error initializing configuration: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Check service status and configuration"""
    config = ctx.obj['config']
    
    click.echo("TraceOne Monitoring Service Status")
    click.echo("=" * 40)
    click.echo(f"Environment: {config.environment}")
    click.echo(f"Debug Mode: {config.debug}")
    click.echo(f"D&B API URL: {config.dnb_api.base_url}")
    click.echo(f"Rate Limit: {config.dnb_api.rate_limit} calls/second")
    click.echo(f"Polling Interval: {config.monitoring.polling_interval} seconds")
    click.echo(f"Max Notifications: {config.monitoring.max_notifications}")
    
    # Test authentication
    try:
        service = DNBMonitoringService.from_config()
        health = service.health_check()
        click.echo(f"Service Health: {'✅ Healthy' if health else '❌ Unhealthy'}")
    except Exception as e:
        click.echo(f"Service Health: ❌ Error - {e}")


@cli.command()
@click.option('--reference', '-r', required=True, help='Registration reference')
@click.option('--config-file', '-f', help='Registration configuration file')
@click.option('--duns', '-d', multiple=True, help='DUNS numbers to monitor')
@click.option('--type', 'reg_type', default='standard', 
              type=click.Choice(['standard', 'financial']), help='Registration type')
@click.pass_context
def create_registration(ctx, reference, config_file, duns, reg_type):
    """Create a new monitoring registration"""
    
    try:
        service = DNBMonitoringService.from_config()
        
        if config_file:
            # Create from file
            registration = service.create_registration_from_file(config_file)
        else:
            # Create from parameters
            duns_list = list(duns) if duns else []
            
            if reg_type == 'financial':
                config = create_financial_monitoring_registration(reference, duns_list)
            else:
                config = create_standard_monitoring_registration(reference, duns_list)
            
            registration = service.create_registration(config)
        
        click.echo(f"✅ Registration created successfully")
        click.echo(f"Reference: {registration.reference}")
        click.echo(f"ID: {registration.id}")
        click.echo(f"Status: {registration.status.value}")
        click.echo(f"DUNS Count: {registration.total_duns_monitored}")
        
    except Exception as e:
        click.echo(f"❌ Failed to create registration: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--reference', '-r', required=True, help='Registration reference')
@click.option('--duns', '-d', multiple=True, required=True, help='DUNS numbers to add')
@click.option('--batch/--individual', default=True, help='Add in batch or individually')
@click.pass_context
def add_duns(ctx, reference, duns, batch):
    """Add DUNS to monitoring registration"""
    
    async def add_duns_async():
        try:
            service = DNBMonitoringService.from_config()
            duns_list = list(duns)
            
            operation = await service.add_duns_to_monitoring(reference, duns_list, batch)
            
            click.echo(f"✅ Added {len(duns_list)} DUNS to monitoring")
            click.echo(f"Registration: {reference}")
            click.echo(f"Operation ID: {operation.id}")
            
        except Exception as e:
            click.echo(f"❌ Failed to add DUNS: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(add_duns_async())


@cli.command()
@click.option('--reference', '-r', required=True, help='Registration reference')
@click.option('--max-notifications', '-n', default=10, help='Maximum notifications to pull')
@click.pass_context
def pull(ctx, reference, max_notifications):
    """Pull notifications for a registration"""
    
    async def pull_async():
        try:
            service = DNBMonitoringService.from_config()
            
            notifications = await service.pull_notifications(reference, max_notifications)
            
            click.echo(f"✅ Pulled {len(notifications)} notifications")
            click.echo(f"Registration: {reference}")
            
            if notifications:
                click.echo("\\nNotifications:")
                for i, notification in enumerate(notifications, 1):
                    click.echo(f"  {i}. DUNS: {notification.duns}, Type: {notification.type.value}")
                    click.echo(f"     Elements: {len(notification.elements)}")
                    click.echo(f"     Delivery: {notification.delivery_timestamp}")
            else:
                click.echo("No notifications available")
                
        except Exception as e:
            click.echo(f"❌ Failed to pull notifications: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(pull_async())


@cli.command()
@click.option('--reference', '-r', required=True, help='Registration reference')
@click.option('--interval', '-i', default=300, help='Polling interval in seconds')
@click.option('--max-notifications', '-n', default=100, help='Maximum notifications per pull')
@click.pass_context
def monitor(ctx, reference, interval, max_notifications):
    """Start continuous monitoring for a registration"""
    
    async def monitor_async():
        try:
            service = DNBMonitoringService.from_config()
            
            # Add logging handler
            service.add_notification_handler(log_notification_handler)
            
            click.echo(f"🔄 Starting continuous monitoring...")
            click.echo(f"Registration: {reference}")
            click.echo(f"Polling Interval: {interval} seconds")
            click.echo(f"Max Notifications: {max_notifications}")
            click.echo("Press Ctrl+C to stop")
            
            notification_count = 0
            
            async for notifications in service.monitor_continuously(
                reference, interval, max_notifications
            ):
                if notifications:
                    notification_count += len(notifications)
                    click.echo(f"📬 Received {len(notifications)} notifications (total: {notification_count})")
                    
                    for notification in notifications:
                        await service.process_notification(notification)
                
        except KeyboardInterrupt:
            click.echo("\\n🛑 Monitoring stopped by user")
        except Exception as e:
            click.echo(f"❌ Monitoring failed: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(monitor_async())


@cli.command()
@click.option('--reference', '-r', required=True, help='Registration reference')
@click.pass_context
def activate(ctx, reference):
    """Activate monitoring for a registration"""
    
    async def activate_async():
        try:
            service = DNBMonitoringService.from_config()
            
            success = await service.activate_monitoring(reference)
            
            if success:
                click.echo(f"✅ Monitoring activated for registration: {reference}")
            else:
                click.echo(f"❌ Failed to activate monitoring for: {reference}")
                sys.exit(1)
                
        except Exception as e:
            click.echo(f"❌ Failed to activate monitoring: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(activate_async())


@cli.command()
@click.pass_context
def health(ctx):
    """Perform health check"""
    
    try:
        service = DNBMonitoringService.from_config()
        
        # Perform health check
        health_status = service.health_check()
        
        # Get detailed status
        status_info = service.get_service_status()
        
        click.echo("Health Check Results")
        click.echo("=" * 20)
        click.echo(f"Overall Health: {'✅ Healthy' if health_status else '❌ Unhealthy'}")
        click.echo(f"Authentication: {'✅' if status_info['authentication']['is_authenticated'] else '❌'}")
        click.echo(f"API Client: {'✅' if status_info['api_client']['health_check'] else '❌'}")
        click.echo(f"Token Expires In: {status_info['authentication']['token_expires_in']} seconds")
        click.echo(f"Active Registrations: {status_info['registrations']['active_count']}")
        click.echo(f"Background Monitors: {status_info['registrations']['background_monitors']}")
        
    except Exception as e:
        click.echo(f"❌ Health check failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--output', '-o', help='Output file for template')
@click.argument('template_type', type=click.Choice(['standard', 'financial']))
def generate_config(template_type, output):
    """Generate registration configuration template"""
    
    if template_type == 'standard':
        template = {
            "reference": "TraceOne_Standard_Template",
            "description": "Standard monitoring registration template",
            "lod": "duns_list",
            "duns_list": ["123456789", "987654321"],
            "dataBlocks": [
                "companyinfo_L2_v1",
                "principalscontacts_L1_v1",
                "hierarchyconnections_L1_v1"
            ],
            "seedData": False,
            "notificationType": "UPDATE",
            "deliveryTrigger": "API_PULL",
            "jsonPathInclusion": [
                "organization.primaryName",
                "organization.registeredAddress",
                "organization.telephone",
                "organization.websiteAddress"
            ]
        }
    else:  # financial
        template = {
            "reference": "TraceOne_Financial_Template",
            "description": "Financial monitoring registration template",
            "lod": "duns_list",
            "duns_list": ["123456789", "987654321"],
            "dataBlocks": [
                "companyfinancials_L1_v1",
                "paymentinsights_L1_v1",
                "financialstrengthinsight_L2_v1"
            ],
            "seedData": False,
            "notificationType": "UPDATE",
            "deliveryTrigger": "API_PULL",
            "jsonPathInclusion": [
                "organization.financials",
                "organization.paymentExperiences",
                "organization.riskAssessment"
            ]
        }
    
    if output:
        # Write to file
        with open(output, 'w') as f:
            import yaml
            yaml.dump(template, f, default_flow_style=False, indent=2)
        click.echo(f"✅ Template written to: {output}")
    else:
        # Print to stdout
        import yaml
        click.echo(yaml.dump(template, default_flow_style=False, indent=2))


def main():
    """Main CLI entry point"""
    cli()


if __name__ == '__main__':
    main()
