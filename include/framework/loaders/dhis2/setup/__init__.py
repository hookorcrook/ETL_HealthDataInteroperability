from typing import Dict, Any, Optional
import requests
import yaml
import logging
from pathlib import Path
from .organization import OrganizationManager
from .attributes import AttributeManager
from .program import ProgramManager

class SetupManager:
    """Manages DHIS2 system setup"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Create session with retry logic
        self.session = requests.Session()
        
        # Setup base URL and headers
        self.base_url = config["dhis2"]["base_url"]
        self.headers = {
            "Authorization": f"ApiToken {config['dhis2']['api_token']}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Initialize managers
        self.org_manager = OrganizationManager(self.session, self.base_url, self.headers)
        self.attr_manager = AttributeManager(self.session, self.base_url, self.headers)
        self.program_manager = ProgramManager(self.session, self.base_url, self.headers)
        
        # Store IDs of created entities
        self.created_entities = {
            "organization_units": {},
            "attributes": {},
            "programs": {}
        }
    
    def load_entity_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load entity configuration from YAML file
        
        Args:
            config_path: Path to configuration file. If None, uses default path.
            
        Returns:
            Dict[str, Any]: Loaded configuration
        """
        if config_path is None:
            config_path = Path(__file__).parent / "entity_config.yaml"
        
        with open(config_path) as f:
            return yaml.safe_load(f)
    
    def setup_organization_units(self, config: Dict[str, Any]) -> None:
        """Setup organization units"""
        self.logger.info("Setting up organization units...")
        try:
            org_units = self.org_manager.create_hierarchy(config["organization_units"])
            self.created_entities["organization_units"].update(org_units)
            
            # Validate hierarchy
            root_id = org_units.get("root")
            if root_id and not self.org_manager.validate_hierarchy(root_id):
                raise ValueError("Organization unit hierarchy validation failed")
                
            self.logger.info("Organization units setup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error setting up organization units: {str(e)}")
            raise
    
    def setup_attributes(self, config: Dict[str, Any]) -> None:
        """Setup tracked entity attributes"""
        self.logger.info("Setting up tracked entity attributes...")
        try:
            for entity_type, type_config in config["tracked_entity_types"].items():
                attributes = self.attr_manager.setup_attributes({
                    entity_type: type_config
                })
                self.created_entities["attributes"].update(attributes)
            
            # Validate attributes
            if not self.attr_manager.validate_attributes(list(self.created_entities["attributes"].values())):
                raise ValueError("Attribute validation failed")
                
            self.logger.info("Attributes setup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error setting up attributes: {str(e)}")
            raise
    
    def setup_programs(self, config: Dict[str, Any]) -> None:
        """Setup programs and their stages"""
        self.logger.info("Setting up programs...")
        try:
            org_unit_ids = list(self.created_entities["organization_units"].values())
            
            for program_name, program_config in config["programs"].items():
                # Get the tracked entity type ID
                entity_type = program_config["trackedEntityType"]
                if entity_type not in config["tracked_entity_types"]:
                    raise ValueError(f"Tracked entity type {entity_type} not found in configuration")
                
                # Create program with stages
                program_details = self.program_manager.setup_program(
                    program_name,
                    program_config,
                    self.created_entities["tracked_entity_types"][entity_type],
                    org_unit_ids
                )
                
                # Store program details
                self.created_entities["programs"][program_name] = program_details
                
                # Validate program
                if not self.program_manager.validate_program(program_details["id"]):
                    raise ValueError(f"Program {program_name} validation failed")
                
            self.logger.info("Programs setup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error setting up programs: {str(e)}")
            raise

    def run_setup(self, config_path: Optional[str] = None) -> Dict[str, Dict[str, str]]:
        """Run complete setup process
        
        Args:
            config_path: Path to configuration file. If None, uses default path.
            
        Returns:
            Dict[str, Dict[str, str]]: Mapping of created entity IDs
        """
        try:
            # Load configuration
            entity_config = self.load_entity_config(config_path)
            
            # Setup components in order
            self.setup_organization_units(entity_config)
            self.setup_attributes(entity_config)
            self.setup_programs(entity_config)
            
            return self.created_entities
            
        except Exception as e:
            self.logger.error(f"Setup process failed: {str(e)}")
            raise
