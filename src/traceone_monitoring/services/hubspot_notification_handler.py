"""
HubSpot Notification Handler for TraceOne Monitoring Service
Integrates D&B notifications with HubSpot CRM by updating company records,
creating tasks, and logging activities based on notification types.
"""

import json
import requests
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set
from enum import Enum
import structlog

from ..models.notification import Notification, NotificationType

logger = structlog.get_logger(__name__)


class HubSpotActionType(str, Enum):
    """Types of actions to take in HubSpot based on notification type"""
    UPDATE_COMPANY = "update_company"
    CREATE_TASK = "create_task"
    CREATE_NOTE = "create_note"
    UPDATE_PROPERTY = "update_property"
    TRIGGER_WORKFLOW = "trigger_workflow"
    CREATE_DEAL = "create_deal"


class HubSpotConfig:
    """HubSpot API configuration"""
    
    def __init__(
        self,
        enabled: bool = False,
        api_token: str = "",
        base_url: str = "https://api.hubapi.com",
        duns_property_name: str = "duns_number",
        company_domain_property: str = "domain",
        timeout: int = 30,
        rate_limit_delay: float = 0.1,
        batch_size: int = 10,
        # Action mappings for different notification types
        notification_actions: Dict[str, List[str]] = None,
        # HubSpot object settings
        create_missing_companies: bool = True,
        default_company_properties: Dict[str, Any] = None,
        task_owner_email: Optional[str] = None,
        pipeline_id: Optional[str] = None,
        deal_stage_id: Optional[str] = None,
    ):
        self.enabled = enabled
        self.api_token = api_token
        self.base_url = base_url.rstrip('/')
        self.duns_property_name = duns_property_name
        self.company_domain_property = company_domain_property
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self.batch_size = batch_size
        self.create_missing_companies = create_missing_companies
        self.default_company_properties = default_company_properties or {}
        self.task_owner_email = task_owner_email
        self.pipeline_id = pipeline_id
        self.deal_stage_id = deal_stage_id
        
        # Default action mappings if not provided
        self.notification_actions = notification_actions or {
            "DELETE": ["create_task", "create_note", "update_property"],
            "TRANSFER": ["create_task", "create_note", "update_property"],
            "UNDER_REVIEW": ["create_task", "create_note"],
            "UPDATE": ["create_note", "update_property"],
            "SEED": ["update_company", "create_note"],
            "UNDELETE": ["create_note", "update_property"],
            "REVIEWED": ["create_note"],
            "EXIT": ["create_task", "create_note"],
            "REMOVED": ["create_task", "create_note"]
        }


class HubSpotNotificationHandler:
    """
    Notification handler that integrates D&B notifications with HubSpot CRM
    """
    
    def __init__(self, config: HubSpotConfig):
        """
        Initialize HubSpot notification handler
        
        Args:
            config: HubSpot configuration
        """
        self.config = config
        self.enabled = config.enabled
        
        # Critical notification types that require immediate attention
        self.critical_types = {
            NotificationType.DELETE,
            NotificationType.TRANSFER,
            NotificationType.UNDER_REVIEW,
            NotificationType.EXIT
        }
        
        # HTTP session for API calls
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {config.api_token}',
            'Content-Type': 'application/json'
        })
        
        # Statistics
        self.stats = {
            "companies_updated": 0,
            "tasks_created": 0,
            "notes_created": 0,
            "notifications_processed": 0,
            "errors": 0,
            "api_calls_made": 0,
            "last_sync_time": None
        }
        
        if self.enabled:
            logger.info("HubSpot notification handler initialized",
                       base_url=config.base_url,
                       duns_property=config.duns_property_name)
        else:
            logger.info("HubSpot notification handler disabled")
    
    def handle_notifications(self, notifications: List[Notification]):
        """
        Handle notifications by updating HubSpot CRM
        
        Args:
            notifications: List of notifications to handle
        """
        if not self.enabled or not notifications:
            return
        
        try:
            self.stats["notifications_processed"] += len(notifications)
            
            # Process notifications by DUNS number to batch updates
            notifications_by_duns = self._group_notifications_by_duns(notifications)
            
            for duns, duns_notifications in notifications_by_duns.items():
                self._process_duns_notifications(duns, duns_notifications)
            
            self.stats["last_sync_time"] = datetime.utcnow().isoformat()
            
        except Exception as e:
            logger.error("HubSpot notification handling failed",
                        error=str(e),
                        notification_count=len(notifications))
            self.stats["errors"] += 1
    
    def _group_notifications_by_duns(self, notifications: List[Notification]) -> Dict[str, List[Notification]]:
        """Group notifications by DUNS number"""
        notifications_by_duns = {}
        for notification in notifications:
            duns = notification.duns
            if duns not in notifications_by_duns:
                notifications_by_duns[duns] = []
            notifications_by_duns[duns].append(notification)
        return notifications_by_duns
    
    def _process_duns_notifications(self, duns: str, notifications: List[Notification]):
        """Process all notifications for a specific DUNS number"""
        try:
            # Find or create HubSpot company
            company_id = self._find_or_create_company(duns, notifications)
            
            if not company_id:
                logger.warning("Could not find or create HubSpot company", duns=duns)
                return
            
            # Process each notification
            for notification in notifications:
                self._process_single_notification(company_id, notification)
                
        except Exception as e:
            logger.error("Failed to process DUNS notifications",
                        duns=duns,
                        notification_count=len(notifications),
                        error=str(e))
            self.stats["errors"] += 1
    
    def _find_or_create_company(self, duns: str, notifications: List[Notification]) -> Optional[str]:
        """Find HubSpot company by DUNS or create if it doesn't exist"""
        try:
            # Search for existing company by DUNS
            company_id = self._search_company_by_duns(duns)
            
            if company_id:
                return company_id
            
            # Create new company if enabled
            if self.config.create_missing_companies:
                return self._create_company(duns, notifications)
            
            return None
            
        except Exception as e:
            logger.error("Failed to find or create company",
                        duns=duns,
                        error=str(e))
            return None
    
    def _search_company_by_duns(self, duns: str) -> Optional[str]:
        """Search for HubSpot company by DUNS number"""
        try:
            url = f"{self.config.base_url}/crm/v3/objects/companies/search"
            
            search_payload = {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": self.config.duns_property_name,
                                "operator": "EQ",
                                "value": duns
                            }
                        ]
                    }
                ],
                "limit": 1
            }
            
            response = self.session.post(url, json=search_payload, timeout=self.config.timeout)
            self.stats["api_calls_made"] += 1
            
            if response.status_code == 200:
                results = response.json()
                if results.get("results"):
                    company_id = results["results"][0]["id"]
                    logger.debug("Found existing company", duns=duns, company_id=company_id)
                    return company_id
            
            return None
            
        except Exception as e:
            logger.error("Failed to search company by DUNS",
                        duns=duns,
                        error=str(e))
            return None
    
    def _create_company(self, duns: str, notifications: List[Notification]) -> Optional[str]:
        """Create new HubSpot company"""
        try:
            url = f"{self.config.base_url}/crm/v3/objects/companies"
            
            # Build company properties
            properties = {
                self.config.duns_property_name: duns,
                "name": f"Company {duns}",  # Default name, can be updated later
                "lifecyclestage": "lead",
                "source": "TraceOne D&B Monitoring"
            }
            
            # Add default properties
            properties.update(self.config.default_company_properties)
            
            # Try to extract company info from notifications
            for notification in notifications:
                if notification.elements:
                    for element in notification.elements:
                        if "primaryName" in element.element and element.current:
                            properties["name"] = element.current
                        elif "website" in element.element and element.current:
                            properties[self.config.company_domain_property] = element.current
            
            company_payload = {"properties": properties}
            
            response = self.session.post(url, json=company_payload, timeout=self.config.timeout)
            self.stats["api_calls_made"] += 1
            
            if response.status_code == 201:
                result = response.json()
                company_id = result["id"]
                self.stats["companies_updated"] += 1
                logger.info("Created new HubSpot company",
                           duns=duns,
                           company_id=company_id)
                return company_id
            else:
                logger.error("Failed to create company",
                           duns=duns,
                           status_code=response.status_code,
                           response=response.text)
                
        except Exception as e:
            logger.error("Failed to create company",
                        duns=duns,
                        error=str(e))
        
        return None
    
    def _process_single_notification(self, company_id: str, notification: Notification):
        """Process a single notification for a company"""
        try:
            notification_type = notification.type.value
            actions = self.config.notification_actions.get(notification_type, [])
            
            for action in actions:
                if action == "create_task":
                    self._create_task(company_id, notification)
                elif action == "create_note":
                    self._create_note(company_id, notification)
                elif action == "update_property":
                    self._update_company_property(company_id, notification)
                elif action == "update_company":
                    self._update_company_info(company_id, notification)
                
        except Exception as e:
            logger.error("Failed to process notification",
                        company_id=company_id,
                        notification_type=notification.type.value,
                        error=str(e))
    
    def _create_task(self, company_id: str, notification: Notification):
        """Create a HubSpot task for the notification"""
        try:
            url = f"{self.config.base_url}/crm/v3/objects/tasks"
            
            is_critical = notification.type in self.critical_types
            priority = "HIGH" if is_critical else "MEDIUM"
            
            task_properties = {
                "hs_task_subject": f"D&B Alert: {notification.type.value} - DUNS {notification.duns}",
                "hs_task_body": self._generate_notification_summary(notification),
                "hs_task_priority": priority,
                "hs_task_status": "NOT_STARTED",
                "hs_task_type": "TODO",
                "hs_timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "hubspot_owner_id": self._get_owner_id() if self.config.task_owner_email else None
            }
            
            # Remove None values
            task_properties = {k: v for k, v in task_properties.items() if v is not None}
            
            task_payload = {
                "properties": task_properties,
                "associations": [
                    {
                        "to": {"id": company_id},
                        "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 2}]
                    }
                ]
            }
            
            response = self.session.post(url, json=task_payload, timeout=self.config.timeout)
            self.stats["api_calls_made"] += 1
            
            if response.status_code == 201:
                self.stats["tasks_created"] += 1
                logger.debug("Created HubSpot task",
                           company_id=company_id,
                           notification_type=notification.type.value)
            else:
                logger.error("Failed to create task",
                           company_id=company_id,
                           status_code=response.status_code,
                           response=response.text)
                
        except Exception as e:
            logger.error("Failed to create task",
                        company_id=company_id,
                        error=str(e))
    
    def _create_note(self, company_id: str, notification: Notification):
        """Create a HubSpot note for the notification"""
        try:
            url = f"{self.config.base_url}/crm/v3/objects/notes"
            
            note_body = self._generate_notification_summary(notification, detailed=True)
            
            note_properties = {
                "hs_note_body": note_body,
                "hs_timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "hubspot_owner_id": self._get_owner_id() if self.config.task_owner_email else None
            }
            
            # Remove None values
            note_properties = {k: v for k, v in note_properties.items() if v is not None}
            
            note_payload = {
                "properties": note_properties,
                "associations": [
                    {
                        "to": {"id": company_id},
                        "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 2}]
                    }
                ]
            }
            
            response = self.session.post(url, json=note_payload, timeout=self.config.timeout)
            self.stats["api_calls_made"] += 1
            
            if response.status_code == 201:
                self.stats["notes_created"] += 1
                logger.debug("Created HubSpot note",
                           company_id=company_id,
                           notification_type=notification.type.value)
            else:
                logger.error("Failed to create note",
                           company_id=company_id,
                           status_code=response.status_code,
                           response=response.text)
                
        except Exception as e:
            logger.error("Failed to create note",
                        company_id=company_id,
                        error=str(e))
    
    def _update_company_property(self, company_id: str, notification: Notification):
        """Update company properties based on notification"""
        try:
            url = f"{self.config.base_url}/crm/v3/objects/companies/{company_id}"
            
            properties = {
                "last_dun_bradstreet_notification": notification.type.value,
                "last_dun_bradstreet_update": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            }
            
            # Add critical flag for critical notifications
            if notification.type in self.critical_types:
                properties["dun_bradstreet_critical_alert"] = "true"
                properties["dun_bradstreet_alert_date"] = datetime.utcnow().strftime("%Y-%m-%d")
            
            update_payload = {"properties": properties}
            
            response = self.session.patch(url, json=update_payload, timeout=self.config.timeout)
            self.stats["api_calls_made"] += 1
            
            if response.status_code == 200:
                self.stats["companies_updated"] += 1
                logger.debug("Updated company properties",
                           company_id=company_id,
                           notification_type=notification.type.value)
            else:
                logger.error("Failed to update company properties",
                           company_id=company_id,
                           status_code=response.status_code,
                           response=response.text)
                
        except Exception as e:
            logger.error("Failed to update company property",
                        company_id=company_id,
                        error=str(e))
    
    def _update_company_info(self, company_id: str, notification: Notification):
        """Update company information from notification elements"""
        try:
            if not notification.elements:
                return
            
            url = f"{self.config.base_url}/crm/v3/objects/companies/{company_id}"
            properties = {}
            
            # Map notification elements to HubSpot properties
            for element in notification.elements:
                if "primaryName" in element.element and element.current:
                    properties["name"] = element.current
                elif "website" in element.element and element.current:
                    properties[self.config.company_domain_property] = element.current
                elif "address" in element.element and element.current:
                    # Parse address components if needed
                    properties["address"] = element.current
                elif "telephone" in element.element and element.current:
                    properties["phone"] = element.current
            
            if properties:
                update_payload = {"properties": properties}
                
                response = self.session.patch(url, json=update_payload, timeout=self.config.timeout)
                self.stats["api_calls_made"] += 1
                
                if response.status_code == 200:
                    self.stats["companies_updated"] += 1
                    logger.debug("Updated company info",
                               company_id=company_id,
                               properties_updated=list(properties.keys()))
                else:
                    logger.error("Failed to update company info",
                               company_id=company_id,
                               status_code=response.status_code,
                               response=response.text)
                
        except Exception as e:
            logger.error("Failed to update company info",
                        company_id=company_id,
                        error=str(e))
    
    def _generate_notification_summary(self, notification: Notification, detailed: bool = False) -> str:
        """Generate a summary of the notification for tasks/notes"""
        lines = []
        lines.append(f"D&B Monitoring Alert: {notification.type.value}")
        lines.append(f"DUNS: {notification.duns}")
        lines.append(f"Timestamp: {notification.delivery_timestamp}")
        
        if notification.type in self.critical_types:
            lines.append("⚠️ CRITICAL ALERT - Immediate attention required")
        
        if detailed and notification.elements:
            lines.append("\nChanges detected:")
            for i, element in enumerate(notification.elements, 1):
                lines.append(f"{i}. {element.element}")
                if element.previous:
                    lines.append(f"   Previous: {element.previous}")
                if element.current:
                    lines.append(f"   Current: {element.current}")
        
        lines.append(f"\nNotification ID: {notification.id}")
        lines.append("Source: TraceOne D&B Monitoring System")
        
        return "\n".join(lines)
    
    def _get_owner_id(self) -> Optional[str]:
        """Get HubSpot owner ID by email"""
        if not self.config.task_owner_email:
            return None
        
        try:
            url = f"{self.config.base_url}/crm/v3/owners"
            params = {"email": self.config.task_owner_email}
            
            response = self.session.get(url, params=params, timeout=self.config.timeout)
            self.stats["api_calls_made"] += 1
            
            if response.status_code == 200:
                results = response.json()
                if results.get("results"):
                    return results["results"][0]["id"]
            
            return None
            
        except Exception as e:
            logger.error("Failed to get owner ID",
                        owner_email=self.config.task_owner_email,
                        error=str(e))
            return None
    
    def test_connection(self) -> bool:
        """Test HubSpot API connection"""
        if not self.enabled:
            logger.warning("HubSpot handler is disabled")
            return False
        
        try:
            url = f"{self.config.base_url}/crm/v3/objects/companies"
            params = {"limit": 1}
            
            response = self.session.get(url, params=params, timeout=self.config.timeout)
            self.stats["api_calls_made"] += 1
            
            if response.status_code == 200:
                logger.info("HubSpot API connection test successful")
                return True
            else:
                logger.error("HubSpot API connection failed",
                           status_code=response.status_code,
                           response=response.text)
                return False
                
        except Exception as e:
            logger.error("HubSpot API connection test failed", error=str(e))
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get HubSpot handler status"""
        return {
            "enabled": self.enabled,
            "base_url": self.config.base_url,
            "duns_property": self.config.duns_property_name,
            "statistics": self.stats.copy()
        }


def create_hubspot_notification_handler(config: HubSpotConfig) -> HubSpotNotificationHandler:
    """
    Factory function to create HubSpot notification handler
    
    Args:
        config: HubSpot configuration
        
    Returns:
        Configured HubSpot notification handler
    """
    return HubSpotNotificationHandler(config)
