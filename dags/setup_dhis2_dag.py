from airflow.decorators import dag, task
from datetime import datetime
from include.framework.config import Config
from include.framework.loaders.dhis2.setup import SetupManager

# Load configuration
config = Config()

@dag(
    schedule_interval=None,  # Manual trigger only
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["setup", "dhis2"]
)
def setup_dhis2_system():
    """DAG for setting up DHIS2 system configuration"""
    
    # Create a custom XCom key for tracking setup completion
    SETUP_COMPLETION_KEY = "dhis2_setup_completed"
    
    @task()
    def setup_organization_hierarchy():
        """Setup organization units hierarchy"""
        setup_manager = SetupManager(config.config)
        entity_config = setup_manager.load_entity_config()
        setup_manager.setup_organization_units(entity_config)
        return setup_manager.created_entities["organization_units"]
    
    @task()
    def setup_tracked_entity_attributes():
        """Setup tracked entity attributes"""
        setup_manager = SetupManager(config.config)
        entity_config = setup_manager.load_entity_config()
        setup_manager.setup_attributes(entity_config)
        return setup_manager.created_entities["attributes"]
    
    @task()
    def setup_programs():
        """Setup programs and program stages"""
        setup_manager = SetupManager(config.config)
        entity_config = setup_manager.load_entity_config()
        setup_manager.setup_programs(entity_config)
        return setup_manager.created_entities["programs"]

    @task()
    def validate_setup(org_units: dict, attributes: dict, programs: dict):
        """Validate the complete setup"""
        setup_manager = SetupManager(config.config)
        
        # Validate organization hierarchy
        root_id = org_units.get("root")
        if root_id and not setup_manager.org_manager.validate_hierarchy(root_id):
            raise ValueError("Organization hierarchy validation failed")
        
        # Validate attributes
        if not setup_manager.attr_manager.validate_attributes(list(attributes.values())):
            raise ValueError("Attributes validation failed")
        
        # Validate programs
        for program_details in programs.values():
            if not setup_manager.program_manager.validate_program(program_details["id"]):
                raise ValueError(f"Program {program_details['id']} validation failed")
        
        setup_result = {
            "organization_units": org_units,
            "attributes": attributes,
            "programs": programs,
            "setup_completed": True,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store setup completion status in XCom
        return {SETUP_COMPLETION_KEY: setup_result}
    
    # Define task dependencies
    org_units = setup_organization_hierarchy()
    attributes = setup_tracked_entity_attributes()
    programs = setup_programs()
    validation = validate_setup(org_units, attributes, programs)
    
    # Set up the pipeline
    [org_units, attributes] >> programs >> validation

# Create the DAG
dag = setup_dhis2_system()
