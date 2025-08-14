from typing import Dict, Any, List, Optional
import requests
import logging

class AttributeManager:
    """Manages DHIS2 tracked entity attributes"""
    
    def __init__(self, session: requests.Session, base_url: str, headers: Dict[str, str]):
        self.session = session
        self.base_url = base_url
        self.headers = headers
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get_attribute(self, attribute_id: str) -> Optional[Dict[str, Any]]:
        """Get attribute by ID"""
        url = f"{self.base_url}/api/trackedEntityAttributes/{attribute_id}"
        response = self.session.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def create_attribute(self, data: Dict[str, Any]) -> str:
        """Create a new tracked entity attribute
        
        Args:
            data: Attribute data including name, valueType, etc.
            
        Returns:
            str: ID of the created attribute
        """
        url = f"{self.base_url}/api/trackedEntityAttributes"
        response = self.session.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()["response"]["uid"]
    
    def create_option_set(self, name: str, options: List[Dict[str, str]]) -> str:
        """Create an option set for an attribute
        
        Args:
            name: Name of the option set
            options: List of options with code and name
            
        Returns:
            str: ID of the created option set
        """
        # Create option set
        option_set_data = {
            "name": name,
            "valueType": "TEXT"
        }
        url = f"{self.base_url}/api/optionSets"
        response = self.session.post(url, headers=self.headers, json=option_set_data)
        response.raise_for_status()
        option_set_id = response.json()["response"]["uid"]
        
        # Create options
        option_ids = []
        for option in options:
            option_data = {
                "code": option["code"],
                "name": option["name"],
                "optionSet": {"id": option_set_id}
            }
            url = f"{self.base_url}/api/options"
            response = self.session.post(url, headers=self.headers, json=option_data)
            response.raise_for_status()
            option_ids.append(response.json()["response"]["uid"])
        
        return option_set_id
    
    def setup_attributes(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Set up tracked entity attributes from configuration
        
        Args:
            config: Attribute configuration dictionary
            
        Returns:
            Dict[str, str]: Mapping of attribute names to their IDs
        """
        attributes = {}
        
        for entity_type, attrs in config.items():
            for attr_name, attr_config in attrs.get("attributes", {}).items():
                # Check if attribute has options
                option_set_id = None
                if "optionSet" in attr_config:
                    option_set_name = f"{attr_name} Options"
                    option_set_id = self.create_option_set(
                        option_set_name,
                        attr_config["optionSet"]["options"]
                    )
                
                # Create attribute
                attr_data = {
                    "name": attr_name,
                    "shortName": attr_name[:50],
                    "valueType": attr_config["valueType"],
                    "aggregationType": "NONE",
                    "unique": attr_config.get("unique", False),
                    "confidential": attr_config.get("confidential", False),
                    "optionSet": {"id": option_set_id} if option_set_id else None,
                    "orgunitScope": attr_config.get("orgunitScope", False),
                    "displayInListNoProgram": True,
                    "displayOnVisitSchedule": False,
                    "searchable": True
                }
                
                attr_id = self.create_attribute(attr_data)
                attributes[attr_name] = attr_id
        
        return attributes
    
    def validate_attributes(self, attribute_ids: List[str]) -> bool:
        """Validate that all attributes exist and are correctly configured
        
        Args:
            attribute_ids: List of attribute IDs to validate
            
        Returns:
            bool: True if all attributes are valid
        """
        try:
            for attr_id in attribute_ids:
                attr = self.get_attribute(attr_id)
                if not attr:
                    self.logger.error(f"Attribute {attr_id} not found")
                    return False
                
                # Check if attribute has required properties
                required_props = ["name", "valueType", "unique"]
                for prop in required_props:
                    if prop not in attr:
                        self.logger.error(f"Attribute {attr_id} missing required property: {prop}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating attributes: {str(e)}")
            return False
