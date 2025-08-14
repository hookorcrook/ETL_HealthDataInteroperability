from typing import Dict, Any, List, Optional
import requests
from datetime import datetime
import logging

class OrganizationManager:
    """Manages DHIS2 organization units"""
    
    def __init__(self, session: requests.Session, base_url: str, headers: Dict[str, str]):
        self.session = session
        self.base_url = base_url
        self.headers = headers
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def get_org_unit(self, org_unit_id: str) -> Optional[Dict[str, Any]]:
        """Get organization unit by ID"""
        url = f"{self.base_url}/api/organisationUnits/{org_unit_id}"
        response = self.session.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def create_org_unit(self, data: Dict[str, Any]) -> str:
        """Create a new organization unit
        
        Args:
            data: Organization unit data including name, code, etc.
            
        Returns:
            str: ID of the created organization unit
        """
        url = f"{self.base_url}/api/organisationUnits"
        response = self.session.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()["response"]["uid"]
    
    def update_org_unit(self, org_unit_id: str, data: Dict[str, Any]) -> None:
        """Update an existing organization unit"""
        url = f"{self.base_url}/api/organisationUnits/{org_unit_id}"
        response = self.session.put(url, headers=self.headers, json=data)
        response.raise_for_status()
    
    def create_hierarchy(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Create organization unit hierarchy from configuration
        
        Args:
            config: Organization hierarchy configuration
            
        Returns:
            Dict[str, str]: Mapping of org unit levels to their IDs
        """
        org_units = {}
        
        # Create root org unit if specified
        root_config = config.get("root")
        if root_config:
            root_data = {
                "name": root_config["name"],
                "code": root_config["code"],
                "openingDate": root_config.get("openingDate", datetime.now().strftime("%Y-%m-%d")),
                "closedDate": root_config.get("closedDate")
            }
            root_id = self.create_org_unit(root_data)
            org_units["root"] = root_id
        
        # Create hierarchy levels
        hierarchy = config.get("default_hierarchy", [])
        parent_id = org_units.get("root")
        
        for level in hierarchy:
            level_data = {
                "name": f"Default {level['type']}",
                "code": f"DEF_{level['type'].upper()}",
                "openingDate": datetime.now().strftime("%Y-%m-%d"),
                "parent": {"id": parent_id} if parent_id else None,
                "level": level["level"]
            }
            
            level_id = self.create_org_unit(level_data)
            org_units[f"level_{level['level']}"] = level_id
            parent_id = level_id
        
        return org_units
    
    def validate_hierarchy(self, root_id: str) -> bool:
        """Validate organization unit hierarchy
        
        Args:
            root_id: ID of the root organization unit
            
        Returns:
            bool: True if hierarchy is valid
        """
        try:
            root = self.get_org_unit(root_id)
            if not root:
                self.logger.error(f"Root organization unit {root_id} not found")
                return False
            
            # Check if root has required properties
            required_props = ["name", "code", "level"]
            for prop in required_props:
                if prop not in root:
                    self.logger.error(f"Root org unit missing required property: {prop}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating hierarchy: {str(e)}")
            return False
