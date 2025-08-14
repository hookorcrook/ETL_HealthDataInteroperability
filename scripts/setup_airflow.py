from airflow import settings
from airflow.models import Connection, Variable
import os
import yaml
from pathlib import Path

def load_config():
    """Load configuration from YAML file based on environment"""
    env = os.getenv('AIRFLOW_ENV', 'development')
    config_path = Path('/opt/airflow/config') / f'{env}.yaml'
    
    if not config_path.exists():
        config_path = Path('/opt/airflow/config/default.yaml')
    
    if not config_path.exists():
        raise FileNotFoundError(f"No configuration file found at {config_path}")
    
    with open(config_path) as f:
        return yaml.safe_load(f)

def setup_airflow_configs():
    """Set up Airflow connections and variables from environment"""
    # Load configuration
    config = load_config()
    
    # Create session
    session = settings.Session()
    
    try:
        # Delete existing connections if they exist
        session.query(Connection).filter(
            Connection.conn_id.in_(['openmrs_api', 'dhis2_api', 'my_spark_conn'])
        ).delete(synchronize_session=False)
        session.commit()
        
        # Setup OpenMRS Connection
        openmrs_conn = Connection(
            conn_id="openmrs_api",
            conn_type="http",
            host=os.getenv("OPENMRS_URL", config['openmrs']['base_url']),
            login=os.getenv("OPENMRS_USERNAME", config['openmrs']['username']),
            password=os.getenv("OPENMRS_PASSWORD", config['openmrs']['password'])
        )
        
        # Setup DHIS2 Connection
        dhis2_conn = Connection(
            conn_id="dhis2_api",
            conn_type="http",
            host=os.getenv("DHIS2_URL"),
            password=os.getenv("DHIS2_API_TOKEN")  # Using password field for API token
        )
        
        # Setup Spark Connection
        spark_conn = Connection(
            conn_id="my_spark_conn",
            conn_type="spark",
            host=os.getenv("SPARK_MASTER", "local[*]"),
            port=7077
        )
        
        # Store connections
        for conn in [openmrs_conn, dhis2_conn, spark_conn]:
            existing_conn = session.query(Connection).filter_by(conn_id=conn.conn_id).first()
            if existing_conn:
                session.delete(existing_conn)
            session.add(conn)
        
        # Setup Variables
        variables = {
            "OPENMRS_API_VERSION": "v1",
            "DHIS2_API_VERSION": "api",
            "TEMP_DATA_PATH": "./include/temp_data"
        }
        
        for key, value in variables.items():
            Variable.set(key, value, serialize_json=True)
        
        session.commit()
        print("✅ Successfully set up Airflow connections and variables")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error setting up Airflow configs: {str(e)}")
        raise
    
    finally:
        session.close()

if __name__ == "__main__":
    setup_airflow_configs()
