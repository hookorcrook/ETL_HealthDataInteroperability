from typing import Dict, Any, List, Optional
import requests
import logging

class ProgramManager:
    """Manages DHIS2 programs and program stages"""
    
    def __init__(self, session: requests.Session, base_url: str, headers: Dict[str, str]):
        self.session = session
        self.base_url = base_url
        self.headers = headers
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get_program(self, program_id: str) -> Optional[Dict[str, Any]]:
        """Get program by ID"""
        url = f"{self.base_url}/api/programs/{program_id}"
        response = self.session.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def create_program(self, data: Dict[str, Any]) -> str:
        """Create a new program
        
        Args:
            data: Program data including name, type, etc.
            
        Returns:
            str: ID of the created program
        """
        url = f"{self.base_url}/api/programs"
        response = self.session.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()["response"]["uid"]
    
    def create_program_stage(self, program_id: str, data: Dict[str, Any]) -> str:
        """Create a new program stage
        
        Args:
            program_id: ID of the program
            data: Program stage data
            
        Returns:
            str: ID of the created program stage
        """
        # Add program reference to stage data
        data["program"] = {"id": program_id}
        
        url = f"{self.base_url}/api/programStages"
        response = self.session.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()["response"]["uid"]
    
    def create_stage_data_element(self, stage_id: str, element_data: Dict[str, Any]) -> str:
        """Create a new data element for a program stage
        
        Args:
            stage_id: ID of the program stage
            element_data: Data element configuration
            
        Returns:
            str: ID of the created data element
        """
        # First create the data element
        url = f"{self.base_url}/api/dataElements"
        de_data = {
            "name": element_data["name"],
            "shortName": element_data["name"][:50],
            "domainType": "TRACKER",
            "valueType": element_data["valueType"],
            "aggregationType": "NONE",
            "zeroIsSignificant": True
        }
        
        response = self.session.post(url, headers=self.headers, json=de_data)
        response.raise_for_status()
        element_id = response.json()["response"]["uid"]
        
        # Then add it to the program stage
        url = f"{self.base_url}/api/programStages/{stage_id}/dataElements"
        psd_data = {
            "dataElement": {"id": element_id},
            "compulsory": element_data.get("mandatory", False),
            "allowProvidedElsewhere": False,
            "displayInReports": True
        }
        
        response = self.session.post(url, headers=self.headers, json=psd_data)
        response.raise_for_status()
        
        return element_id
    
    def setup_program(self, name: str, config: Dict[str, Any], 
                     tracked_entity_type_id: str,
                     org_unit_ids: List[str]) -> Dict[str, Any]:
        """Set up a complete program with stages and data elements
        
        Args:
            name: Program name
            config: Program configuration
            tracked_entity_type_id: ID of the tracked entity type
            org_unit_ids: List of organization unit IDs
            
        Returns:
            Dict[str, Any]: Created program IDs and details
        """
        # Create program
        program_data = {
            "name": config["name"],
            "shortName": config["shortName"],
            "programType": config["programType"],
            "trackedEntityType": {"id": tracked_entity_type_id},
            "organisationUnits": [{"id": id} for id in org_unit_ids],
            "accessLevel": config.get("accessLevel", "OPEN"),
            "enrollmentDateLabel": config.get("enrollmentDateLabel", "Enrollment Date"),
            "incidentDateLabel": config.get("incidentDateLabel", "Incident Date"),
            "displayFrontPageList": True,
            "displayIncidentDate": True,
            "ignoreOverdueEvents": False,
            "onlyEnrollOnce": False,
            "selectEnrollmentDatesInFuture": True,
            "selectIncidentDatesInFuture": True
        }
        
        program_id = self.create_program(program_data)
        result = {
            "id": program_id,
            "stages": {}
        }
        
        # Create program stages
        for stage_config in config.get("stages", []):
            stage_data = {
                "name": stage_config["name"],
                "description": stage_config.get("description", ""),
                "repeatable": stage_config.get("repeatable", False),
                "displayGenerateEventBox": True,
                "standardInterval": 0,
                "autoGenerateEvent": False,
                "openAfterEnrollment": True,
                "reportDateToUse": "false",
                "minDaysFromStart": 0,
                "generatedByEnrollmentDate": False
            }
            
            stage_id = self.create_program_stage(program_id, stage_data)
            
            # Create data elements for the stage
            elements = {}
            for element_config in stage_config.get("elements", []):
                element_id = self.create_stage_data_element(stage_id, element_config)
                elements[element_config["name"]] = element_id
            
            result["stages"][stage_config["name"]] = {
                "id": stage_id,
                "elements": elements
            }
        
        return result
    
    def validate_program(self, program_id: str) -> bool:
        """Validate program configuration
        
        Args:
            program_id: ID of the program to validate
            
        Returns:
            bool: True if program is valid
        """
        try:
            program = self.get_program(program_id)
            if not program:
                self.logger.error(f"Program {program_id} not found")
                return False
            
            # Check required properties
            required_props = ["name", "programType", "trackedEntityType"]
            for prop in required_props:
                if prop not in program:
                    self.logger.error(f"Program missing required property: {prop}")
                    return False
            
            # Check program stages
            url = f"{self.base_url}/api/programs/{program_id}/programStages"
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            stages = response.json().get("programStages", [])
            
            if not stages:
                self.logger.error(f"Program {program_id} has no stages")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating program: {str(e)}")
            return False
