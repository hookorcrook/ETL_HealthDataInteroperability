from airflow.decorators import dag, task
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.models import DagRun, TaskInstance
from airflow.utils.session import provide_session
from airflow.exceptions import AirflowException
from datetime import datetime
from include.framework.config import Config
from include.framework.connectors.openmrs import OpenMRSExtractor
from include.framework.connectors.dhis2 import DHIS2Loader
from sqlalchemy import desc

# Load configuration
config = Config()

# Constants
SETUP_DAG_ID = "setup_dhis2_system"
SETUP_COMPLETION_KEY = "dhis2_setup_completed"

@provide_session
def check_setup_completion(session=None) -> bool:
    """Check if DHIS2 setup has been completed successfully"""
    # Get the latest successful run of the setup DAG
    latest_setup_run = session.query(DagRun).filter(
        DagRun.dag_id == SETUP_DAG_ID,
        DagRun.state == 'success'
    ).order_by(desc(DagRun.execution_date)).first()
    
    if not latest_setup_run:
        raise AirflowException(
            f"DHIS2 setup has not been completed. Please run the {SETUP_DAG_ID} DAG first."
        )
    
    # Get the validation task instance
    validation_task = session.query(TaskInstance).filter(
        TaskInstance.dag_id == SETUP_DAG_ID,
        TaskInstance.task_id == "validate_setup",
        TaskInstance.run_id == latest_setup_run.run_id,
        TaskInstance.state == 'success'
    ).first()
    
    if not validation_task:
        raise AirflowException("DHIS2 setup validation task not found or not successful")
    
    # Check XCom for setup completion
    setup_result = validation_task.xcom_pull(key=SETUP_COMPLETION_KEY)
    if not setup_result or not setup_result.get("setup_completed"):
        raise AirflowException("DHIS2 setup validation did not complete successfully")
    
    return True

@dag(
    schedule_interval="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["etl", "openmrs", "dhis2"]
)
def load_openmrs_to_dhis2():
    
    @task()
    def verify_setup():
        """Verify that DHIS2 setup has been completed"""
        return check_setup_completion()
    
    @task()
    def extract_patient() -> str:
        """Extract patient data from OpenMRS"""
        with OpenMRSExtractor(config.config, entity_type='person') as extractor:
            return extractor.extract()

    @task
    def prepare_transform_args(extracted_path: str) -> list:
        """Prepare arguments for the transform task"""
        return [extracted_path, config.get('temp_data', 'base_path')]

    # Transform task using Spark
    transform = SparkSubmitOperator(
        task_id="transform_with_spark",
        application="/opt/airflow/include/scripts/transform_patient.py",
        conn_id="my_spark_conn",
        conf={
            "spark.master": config.get('spark', 'master'),
            "spark.driver.memory": "1g",
            "spark.executor.memory": "1g"
        },
        application_args=["{{ task_instance.xcom_pull(task_ids='prepare_transform_args')[0] }}", 
                         "{{ task_instance.xcom_pull(task_ids='prepare_transform_args')[1] }}"],
        verbose=True
    )

    @task()
    def load_to_dhis2(task_instance=None) -> None:
        """Load transformed data to DHIS2"""
        # Get the output path from transform task context
        transformed_path = task_instance.xcom_pull(task_ids='transform_with_spark')
        
        with DHIS2Loader(config.config) as loader:
            # Load data from file
            data = loader.load_data(transformed_path)
            
            # Process data in batches
            results = loader.process_batch(data)
            
            # Validate results
            if not loader.validate_load(results):
                raise Exception("Data load validation failed")

    @task()
    def cleanup_temp_data():
        """Cleanup temporary data files"""
        import os
        temp_path = config.get('temp_data', 'base_path')
        if os.path.exists(temp_path):
            for filename in os.listdir(temp_path):
                file_path = os.path.join(temp_path, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"✅ Removed {file_path}")
                except Exception as e:
                    print(f"⚠️ Failed to remove {file_path}: {e}")
        else:
            print("ℹ️ Temp directory does not exist")

    # Define task dependencies
    setup_check = verify_setup()
    extracted_path = extract_patient()
    transform_args = prepare_transform_args(extracted_path)
    transform.set_upstream(transform_args)
    load_task = load_to_dhis2()
    cleanup = cleanup_temp_data()

    # Set up the pipeline with setup verification
    setup_check >> extracted_path >> transform_args >> transform >> load_task >> cleanup

# Create the DAG
dag = load_openmrs_to_dhis2()
