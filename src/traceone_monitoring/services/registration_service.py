"""
Registration Management Service
Handles D&B monitoring registration lifecycle
"""

import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import structlog

from ..api.client import DNBApiClient
from ..models.registration import (
    Registration,
    RegistrationConfig,
    RegistrationStatus,
    RegistrationSummary,
    DunsSubject,
    RegistrationOperation
)


logger = structlog.get_logger(__name__)


class RegistrationError(Exception):
    """Registration management errors"""
    pass


class RegistrationManager:
    """
    Service for managing D&B monitoring registrations
    """
    
    def __init__(self, api_client: DNBApiClient):
        """
        Initialize registration manager
        
        Args:
            api_client: D&B API client
        """
        self.client = api_client
        self._registrations: Dict[str, Registration] = {}
    
    def create_registration_from_config(self, config: RegistrationConfig) -> Registration:
        """
        Create a new monitoring registration from configuration
        
        Args:
            config: Registration configuration
            
        Returns:
            Created registration
            
        Raises:
            RegistrationError: If registration creation fails
        """
        logger.info("Creating registration",
                   reference=config.reference,
                   data_blocks=config.data_blocks,
                   duns_count=len(config.duns_list))
        
        try:
            # Create registration object
            registration = Registration(
                reference=config.reference,
                config=config,
                total_duns_monitored=len(config.duns_list)
            )
            
            # Note: In a real implementation, this would make an API call to D&B
            # to create the registration. For now, we'll simulate it.
            # response = self.client.post('/v1/monitoring/registrations', json=config.to_dict())
            
            # Store registration
            self._registrations[config.reference] = registration
            
            logger.info("Registration created successfully",
                       reference=config.reference,
                       registration_id=str(registration.id))
            
            return registration
            
        except Exception as e:
            logger.error("Failed to create registration",
                        reference=config.reference,
                        error=str(e))
            raise RegistrationError(f"Failed to create registration: {e}")
    
    def create_registration_from_file(self, config_file_path: str) -> Registration:
        """
        Create registration from YAML configuration file
        
        Args:
            config_file_path: Path to YAML configuration file
            
        Returns:
            Created registration
        """
        config_path = Path(config_file_path)
        if not config_path.exists():
            raise RegistrationError(f"Configuration file not found: {config_file_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            # Create configuration object
            config = RegistrationConfig(**config_data)
            
            # Create registration
            return self.create_registration_from_config(config)
            
        except yaml.YAMLError as e:
            raise RegistrationError(f"Invalid YAML configuration: {e}")
        except Exception as e:
            raise RegistrationError(f"Failed to load configuration: {e}")
    
    def add_duns_to_monitoring(
        self, 
        registration_reference: str, 
        duns_list: List[str],
        batch_mode: bool = True
    ) -> RegistrationOperation:
        """
        Add DUNS to monitoring registration
        
        Args:
            registration_reference: Registration reference
            duns_list: List of DUNS to add
            batch_mode: Whether to add in batch or individually
            
        Returns:
            Operation result
        """
        logger.info("Adding DUNS to monitoring",
                   registration=registration_reference,
                   duns_count=len(duns_list),
                   batch_mode=batch_mode)
        
        registration = self.get_registration(registration_reference)
        if not registration:
            raise RegistrationError(f"Registration not found: {registration_reference}")
        
        operation = RegistrationOperation(
            registration_id=registration.id,
            operation_type="ADD_DUNS",
            duns_affected=duns_list
        )
        
        try:
            if batch_mode and len(duns_list) > 1:
                # Add DUNS in batch
                self._add_duns_batch(registration_reference, duns_list)
            else:
                # Add DUNS individually
                for duns in duns_list:
                    self._add_single_duns(registration_reference, duns)
            
            # Update registration statistics
            registration.total_duns_monitored += len(duns_list)
            
            logger.info("Successfully added DUNS to monitoring",
                       registration=registration_reference,
                       duns_count=len(duns_list))
            
            return operation
            
        except Exception as e:
            operation.success = False
            operation.error_message = str(e)
            
            logger.error("Failed to add DUNS to monitoring",
                        registration=registration_reference,
                        error=str(e))
            
            raise RegistrationError(f"Failed to add DUNS: {e}")
    
    def remove_duns_from_monitoring(
        self,
        registration_reference: str,
        duns_list: List[str],
        batch_mode: bool = True
    ) -> RegistrationOperation:
        """
        Remove DUNS from monitoring registration
        
        Args:
            registration_reference: Registration reference
            duns_list: List of DUNS to remove
            batch_mode: Whether to remove in batch or individually
            
        Returns:
            Operation result
        """
        logger.info("Removing DUNS from monitoring",
                   registration=registration_reference,
                   duns_count=len(duns_list),
                   batch_mode=batch_mode)
        
        registration = self.get_registration(registration_reference)
        if not registration:
            raise RegistrationError(f"Registration not found: {registration_reference}")
        
        operation = RegistrationOperation(
            registration_id=registration.id,
            operation_type="REMOVE_DUNS",
            duns_affected=duns_list
        )
        
        try:
            if batch_mode and len(duns_list) > 1:
                # Remove DUNS in batch
                self._remove_duns_batch(registration_reference, duns_list)
            else:
                # Remove DUNS individually
                for duns in duns_list:
                    self._remove_single_duns(registration_reference, duns)
            
            # Update registration statistics
            registration.total_duns_monitored = max(0, registration.total_duns_monitored - len(duns_list))
            
            logger.info("Successfully removed DUNS from monitoring",
                       registration=registration_reference,
                       duns_count=len(duns_list))
            
            return operation
            
        except Exception as e:
            operation.success = False
            operation.error_message = str(e)
            
            logger.error("Failed to remove DUNS from monitoring",
                        registration=registration_reference,
                        error=str(e))
            
            raise RegistrationError(f"Failed to remove DUNS: {e}")
    
    def activate_monitoring(self, registration_reference: str) -> bool:
        """
        Activate monitoring for a registration
        
        Args:
            registration_reference: Registration reference
            
        Returns:
            True if activation successful
        """
        logger.info("Activating monitoring",
                   registration=registration_reference)
        
        registration = self.get_registration(registration_reference)
        if not registration:
            raise RegistrationError(f"Registration not found: {registration_reference}")
        
        try:
            # Call D&B API to activate monitoring
            # DELETE /v1/monitoring/registrations/{RegistrationID}/suppress
            endpoint = f"/v1/monitoring/registrations/{registration_reference}/suppress"
            response = self.client.delete(endpoint)
            
            # Update registration status
            registration.activate()
            
            logger.info("Monitoring activated successfully",
                       registration=registration_reference)
            
            return True
            
        except Exception as e:
            logger.error("Failed to activate monitoring",
                        registration=registration_reference,
                        error=str(e))
            raise RegistrationError(f"Failed to activate monitoring: {e}")
    
    def get_registration(self, registration_reference: str) -> Optional[Registration]:
        """
        Get registration by reference
        
        Args:
            registration_reference: Registration reference
            
        Returns:
            Registration if found, None otherwise
        """
        return self._registrations.get(registration_reference)
    
    def list_registrations(self) -> List[RegistrationSummary]:
        """
        List all registrations
        
        Returns:
            List of registration summaries
        """
        summaries = []
        for registration in self._registrations.values():
            summary = RegistrationSummary(
                id=registration.id,
                reference=registration.reference,
                status=registration.status,
                total_duns_monitored=registration.total_duns_monitored,
                total_notifications_received=registration.total_notifications_received,
                created_at=registration.created_at,
                activated_at=registration.activated_at,
                last_pull_timestamp=registration.last_pull_timestamp
            )
            summaries.append(summary)
        
        return summaries
    
    def export_monitored_duns(self, registration_reference: str) -> List[str]:
        """
        Export list of DUNS under monitoring
        
        Args:
            registration_reference: Registration reference
            
        Returns:
            List of DUNS numbers
        """
        logger.info("Exporting monitored DUNS list",
                   registration=registration_reference)
        
        try:
            # Call D&B API to export DUNS list
            endpoint = f"/v1/monitoring/registrations/export/{registration_reference}/subjects"
            response = self.client.get(endpoint)
            
            # Parse response (actual format depends on D&B API response)
            # This is a simplified implementation
            data = response.json()
            duns_list = data.get('subjects', [])
            
            logger.info("DUNS list exported successfully",
                       registration=registration_reference,
                       duns_count=len(duns_list))
            
            return duns_list
            
        except Exception as e:
            logger.error("Failed to export DUNS list",
                        registration=registration_reference,
                        error=str(e))
            raise RegistrationError(f"Failed to export DUNS list: {e}")
    
    def check_duns_status(self, registration_reference: str, duns: str) -> Dict[str, Any]:
        """
        Check status of a specific DUNS in registration
        
        Args:
            registration_reference: Registration reference
            duns: DUNS number to check
            
        Returns:
            DUNS status information
        """
        try:
            endpoint = f"/v1/monitoring/registrations/{registration_reference}/duns/{duns}"
            response = self.client.get(endpoint)
            
            return response.json()
            
        except Exception as e:
            logger.error("Failed to check DUNS status",
                        registration=registration_reference,
                        duns=duns,
                        error=str(e))
            raise RegistrationError(f"Failed to check DUNS status: {e}")
    
    def _add_duns_batch(self, registration_reference: str, duns_list: List[str]):
        """Add DUNS in batch mode"""
        endpoint = f"/v1/monitoring/registrations/{registration_reference}/subjects"
        
        # Prepare CSV data - each DUNS on a new line
        csv_data = "\n".join(duns_list)
        
        headers = {
            "Content-Type": "text/csv"
        }
        
        logger.debug("Sending DUNS batch add request",
                    endpoint=endpoint,
                    duns_count=len(duns_list),
                    csv_preview=csv_data[:100] + "..." if len(csv_data) > 100 else csv_data)
        
        response = self.client.patch(endpoint, data=csv_data, headers=headers)
        
        # Log success
        logger.debug("DUNS batch added successfully",
                    registration=registration_reference,
                    duns_count=len(duns_list))
    
    def _add_single_duns(self, registration_reference: str, duns: str):
        """Add single DUNS"""
        endpoint = f"/v1/monitoring/registrations/{registration_reference}/subjects/{duns}"
        params = {"subject": "duns"}
        
        
        response = self.client.post(endpoint, params=params)
        
        logger.debug("Single DUNS added successfully",
                    registration=registration_reference,
                    duns=duns)
    
    def _remove_duns_batch(self, registration_reference: str, duns_list: List[str]):
        """Remove DUNS in batch mode"""
        endpoint = f"/v1/monitoring/registrations/{registration_reference}/subjects"
        
        # Prepare CSV data - each DUNS on a new line
        csv_data = "\n".join(duns_list)
        
        headers = {
            "Content-Type": "text/csv"
        }
        
        logger.debug("Sending DUNS batch remove request",
                    endpoint=endpoint,
                    duns_count=len(duns_list),
                    csv_preview=csv_data[:100] + "..." if len(csv_data) > 100 else csv_data)
        
        response = self.client.delete(endpoint, data=csv_data, headers=headers)
        
        logger.debug("DUNS batch removed successfully",
                    registration=registration_reference,
                    duns_count=len(duns_list))
    
    def _remove_single_duns(self, registration_reference: str, duns: str):
        """Remove single DUNS"""
        endpoint = f"/v1/monitoring/registrations/{registration_reference}/subjects/{duns}"
        
        response = self.client.delete(endpoint)
        
        logger.debug("Single DUNS removed successfully",
                    registration=registration_reference,
                    duns=duns)


def create_registration_manager(api_client: DNBApiClient) -> RegistrationManager:
    """
    Factory function to create registration manager
    
    Args:
        api_client: D&B API client
        
    Returns:
        Configured registration manager
    """
    return RegistrationManager(api_client)
