#!/usr/bin/env python3
"""
Portfolio Creation Examples for TraceOne Monitoring Service

This module demonstrates different approaches to creating and managing 
a portfolio of companies for monitoring in the TraceOne system.
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Optional
import structlog

from traceone_monitoring import DNBMonitoringService
from traceone_monitoring.models.registration import RegistrationConfig
from traceone_monitoring.services.monitoring_service import (
    create_standard_monitoring_registration,
    create_financial_monitoring_registration,
    log_notification_handler
)


logger = structlog.get_logger(__name__)


class PortfolioManager:
    """
    Portfolio manager for organizing and monitoring groups of companies
    """
    
    def __init__(self, service: DNBMonitoringService):
        self.service = service
        self.portfolios: Dict[str, Dict] = {}
    
    async def create_portfolio(
        self,
        portfolio_name: str,
        companies: List[Dict[str, str]],
        monitoring_type: str = "standard",
        description: Optional[str] = None
    ) -> str:
        """
        Create a monitoring portfolio for a group of companies
        
        Args:
            portfolio_name: Name of the portfolio
            companies: List of company dictionaries with 'name' and 'duns'
            monitoring_type: 'standard' or 'financial' monitoring
            description: Portfolio description
            
        Returns:
            Registration reference
        """
        logger.info("Creating portfolio",
                   portfolio_name=portfolio_name,
                   company_count=len(companies),
                   monitoring_type=monitoring_type)
        
        # Extract DUNS numbers
        duns_list = [company['duns'] for company in companies]
        
        # Create registration reference
        registration_ref = f"TraceOne_Portfolio_{portfolio_name.replace(' ', '_')}"
        
        # Create registration configuration
        if monitoring_type == "financial":
            config = create_financial_monitoring_registration(
                reference=registration_ref,
                duns_list=duns_list,
                description=description or f"Financial monitoring portfolio: {portfolio_name}"
            )
        else:
            config = create_standard_monitoring_registration(
                reference=registration_ref,
                duns_list=duns_list,
                description=description or f"Standard monitoring portfolio: {portfolio_name}"
            )
        
        # Create registration
        registration = self.service.create_registration(config)
        
        # Store portfolio metadata
        self.portfolios[portfolio_name] = {
            'registration_reference': registration_ref,
            'registration_id': str(registration.id),
            'companies': companies,
            'monitoring_type': monitoring_type,
            'created_at': datetime.utcnow(),
            'description': description
        }
        
        logger.info("Portfolio created successfully",
                   portfolio_name=portfolio_name,
                   registration_reference=registration_ref,
                   company_count=len(companies))
        
        return registration_ref
    
    async def add_companies_to_portfolio(
        self,
        portfolio_name: str,
        companies: List[Dict[str, str]]
    ):
        """
        Add companies to an existing portfolio
        
        Args:
            portfolio_name: Name of the portfolio
            companies: List of company dictionaries to add
        """
        if portfolio_name not in self.portfolios:
            raise ValueError(f"Portfolio '{portfolio_name}' not found")
        
        portfolio = self.portfolios[portfolio_name]
        registration_ref = portfolio['registration_reference']
        
        # Extract DUNS numbers
        duns_list = [company['duns'] for company in companies]
        
        # Add to monitoring
        await self.service.add_duns_to_monitoring(
            registration_ref, 
            duns_list, 
            batch_mode=True
        )
        
        # Update portfolio metadata
        portfolio['companies'].extend(companies)
        
        logger.info("Companies added to portfolio",
                   portfolio_name=portfolio_name,
                   added_count=len(companies),
                   total_count=len(portfolio['companies']))
    
    async def activate_portfolio_monitoring(self, portfolio_name: str):
        """
        Activate monitoring for a portfolio
        
        Args:
            portfolio_name: Name of the portfolio
        """
        if portfolio_name not in self.portfolios:
            raise ValueError(f"Portfolio '{portfolio_name}' not found")
        
        portfolio = self.portfolios[portfolio_name]
        registration_ref = portfolio['registration_reference']
        
        success = await self.service.activate_monitoring(registration_ref)
        
        if success:
            logger.info("Portfolio monitoring activated",
                       portfolio_name=portfolio_name,
                       registration_ref=registration_ref)
        else:
            raise RuntimeError(f"Failed to activate monitoring for portfolio '{portfolio_name}'")
    
    def get_portfolio_summary(self, portfolio_name: str) -> Dict:
        """
        Get portfolio summary information
        
        Args:
            portfolio_name: Name of the portfolio
            
        Returns:
            Portfolio summary
        """
        if portfolio_name not in self.portfolios:
            raise ValueError(f"Portfolio '{portfolio_name}' not found")
        
        portfolio = self.portfolios[portfolio_name]
        
        return {
            'name': portfolio_name,
            'registration_reference': portfolio['registration_reference'],
            'company_count': len(portfolio['companies']),
            'monitoring_type': portfolio['monitoring_type'],
            'created_at': portfolio['created_at'],
            'description': portfolio['description'],
            'companies': portfolio['companies']
        }
    
    def list_portfolios(self) -> List[str]:
        """
        List all portfolio names
        
        Returns:
            List of portfolio names
        """
        return list(self.portfolios.keys())


async def create_supplier_portfolio():
    """
    Example: Create a supplier monitoring portfolio
    """
    logger.info("Creating supplier portfolio example")
    
    service = DNBMonitoringService.from_config("config/dev.yaml")
    portfolio_manager = PortfolioManager(service)
    
    try:
        # Define supplier companies
        suppliers = [
            {"name": "ABC Manufacturing Corp", "duns": "123456789"},
            {"name": "XYZ Components Ltd", "duns": "987654321"},
            {"name": "Global Supply Chain Inc", "duns": "555666777"},
            {"name": "Precision Parts LLC", "duns": "444555666"},
            {"name": "Innovation Materials Co", "duns": "777888999"}
        ]
        
        # Create supplier portfolio
        registration_ref = await portfolio_manager.create_portfolio(
            portfolio_name="Key Suppliers Q4 2024",
            companies=suppliers,
            monitoring_type="standard",
            description="Critical suppliers for Q4 manufacturing operations"
        )
        
        # Activate monitoring
        await portfolio_manager.activate_portfolio_monitoring("Key Suppliers Q4 2024")
        
        # Add notification handler
        service.add_notification_handler(log_notification_handler)
        
        # Start monitoring
        logger.info("Starting supplier portfolio monitoring for 60 seconds...")
        
        end_time = datetime.now() + timedelta(seconds=60)
        async for notifications in service.monitor_continuously(registration_ref, polling_interval=15):
            if datetime.now() > end_time:
                break
            
            if notifications:
                logger.info("Supplier notifications received",
                           count=len(notifications))
                for notification in notifications:
                    await service.process_notification(notification)
        
        # Get portfolio summary
        summary = portfolio_manager.get_portfolio_summary("Key Suppliers Q4 2024")
        logger.info("Portfolio summary", summary=summary)
        
    except Exception as e:
        logger.error("Supplier portfolio example failed", error=str(e))
        raise
    finally:
        await service.shutdown()


async def create_financial_risk_portfolio():
    """
    Example: Create a financial risk monitoring portfolio
    """
    logger.info("Creating financial risk portfolio example")
    
    service = DNBMonitoringService.from_config()
    portfolio_manager = PortfolioManager(service)
    
    try:
        # Define high-risk companies
        high_risk_companies = [
            {"name": "High Value Customer A", "duns": "111222333"},
            {"name": "Large Supplier B", "duns": "444555666"},
            {"name": "Strategic Partner C", "duns": "777888999"}
        ]
        
        # Create financial risk portfolio
        registration_ref = await portfolio_manager.create_portfolio(
            portfolio_name="High Risk Entities",
            companies=high_risk_companies,
            monitoring_type="financial",
            description="High-value entities requiring financial risk monitoring"
        )
        
        # Activate monitoring
        await portfolio_manager.activate_portfolio_monitoring("High Risk Entities")
        
        # Pull notifications to check for financial changes
        notifications = await service.pull_notifications(registration_ref, max_notifications=20)
        
        logger.info("Financial risk notifications pulled",
                   count=len(notifications))
        
        # Process notifications with focus on financial indicators
        for notification in notifications:
            if any("financial" in element.element.lower() or 
                   "payment" in element.element.lower() or
                   "rating" in element.element.lower()
                   for element in notification.elements):
                logger.warning("Critical financial change detected",
                              duns=notification.duns,
                              type=notification.type.value,
                              elements=[e.element for e in notification.elements])
            
            await service.process_notification(notification)
        
    except Exception as e:
        logger.error("Financial risk portfolio example failed", error=str(e))
        raise
    finally:
        await service.shutdown()


async def create_multi_tier_portfolio():
    """
    Example: Create multiple portfolios for different business segments
    """
    logger.info("Creating multi-tier portfolio example")
    
    service = DNBMonitoringService.from_config()
    portfolio_manager = PortfolioManager(service)
    
    try:
        # Tier 1: Critical suppliers
        tier1_suppliers = [
            {"name": "Critical Supplier 1", "duns": "100200300"},
            {"name": "Critical Supplier 2", "duns": "200300400"}
        ]
        
        # Tier 2: Important customers
        tier2_customers = [
            {"name": "Major Customer 1", "duns": "300400500"},
            {"name": "Major Customer 2", "duns": "400500600"},
            {"name": "Major Customer 3", "duns": "500600700"}
        ]
        
        # Tier 3: Strategic partners
        tier3_partners = [
            {"name": "Strategic Partner 1", "duns": "600700800"},
            {"name": "Strategic Partner 2", "duns": "700800900"}
        ]
        
        # Create multiple portfolios
        portfolios = [
            ("Tier 1 Critical Suppliers", tier1_suppliers, "financial"),
            ("Tier 2 Major Customers", tier2_customers, "standard"),
            ("Tier 3 Strategic Partners", tier3_partners, "standard")
        ]
        
        for name, companies, monitoring_type in portfolios:
            registration_ref = await portfolio_manager.create_portfolio(
                portfolio_name=name,
                companies=companies,
                monitoring_type=monitoring_type,
                description=f"Multi-tier monitoring: {name}"
            )
            
            await portfolio_manager.activate_portfolio_monitoring(name)
            
            logger.info("Portfolio created and activated",
                       portfolio_name=name,
                       registration_ref=registration_ref,
                       company_count=len(companies))
        
        # List all portfolios
        all_portfolios = portfolio_manager.list_portfolios()
        logger.info("All portfolios created", portfolios=all_portfolios)
        
        # Get summary for each portfolio
        for portfolio_name in all_portfolios:
            summary = portfolio_manager.get_portfolio_summary(portfolio_name)
            logger.info("Portfolio details", portfolio=summary)
        
    except Exception as e:
        logger.error("Multi-tier portfolio example failed", error=str(e))
        raise
    finally:
        await service.shutdown()


async def create_dynamic_portfolio():
    """
    Example: Create and dynamically manage a portfolio
    """
    logger.info("Creating dynamic portfolio example")
    
    service = DNBMonitoringService.from_config()
    portfolio_manager = PortfolioManager(service)
    
    try:
        # Start with initial companies
        initial_companies = [
            {"name": "Initial Company 1", "duns": "111111111"},
            {"name": "Initial Company 2", "duns": "222222222"}
        ]
        
        # Create portfolio
        await portfolio_manager.create_portfolio(
            portfolio_name="Dynamic Growth Portfolio",
            companies=initial_companies,
            monitoring_type="standard",
            description="Portfolio that grows over time"
        )
        
        # Activate monitoring
        await portfolio_manager.activate_portfolio_monitoring("Dynamic Growth Portfolio")
        
        # Simulate adding companies over time
        additional_batches = [
            [{"name": "New Company 3", "duns": "333333333"}],
            [{"name": "New Company 4", "duns": "444444444"},
             {"name": "New Company 5", "duns": "555555555"}],
            [{"name": "New Company 6", "duns": "666666666"}]
        ]
        
        for i, batch in enumerate(additional_batches, 1):
            logger.info(f"Adding batch {i} to portfolio", companies=batch)
            
            await portfolio_manager.add_companies_to_portfolio(
                "Dynamic Growth Portfolio",
                batch
            )
            
            # Show updated summary
            summary = portfolio_manager.get_portfolio_summary("Dynamic Growth Portfolio")
            logger.info("Portfolio updated", 
                       company_count=summary['company_count'],
                       batch=i)
            
            # Simulate time delay
            await asyncio.sleep(2)
        
        # Final portfolio summary
        final_summary = portfolio_manager.get_portfolio_summary("Dynamic Growth Portfolio")
        logger.info("Final portfolio state", summary=final_summary)
        
    except Exception as e:
        logger.error("Dynamic portfolio example failed", error=str(e))
        raise
    finally:
        await service.shutdown()


def main():
    """
    Main function to run portfolio examples
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
        example_type = "supplier"
    
    if example_type == "supplier":
        asyncio.run(create_supplier_portfolio())
    elif example_type == "financial":
        asyncio.run(create_financial_risk_portfolio())
    elif example_type == "multi":
        asyncio.run(create_multi_tier_portfolio())
    elif example_type == "dynamic":
        asyncio.run(create_dynamic_portfolio())
    else:
        logger.error("Unknown example type", 
                    available=["supplier", "financial", "multi", "dynamic"])


if __name__ == "__main__":
    main()
