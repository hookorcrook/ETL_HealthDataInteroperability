from airflow.decorators import dag, task
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime
import json
import os
import shutil

@dag(
    schedule_interval="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["etl", "openmrs", "dhis2"]
)
def load_openmrs_to_dhis2():
    
    @task()
    def extract_patient() -> str:
        import requests
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"./include/temp_data/patients_raw_{timestamp}.json"

        url = "http://openmrs-referenceapplication:8080/openmrs/ws/rest/v1/person?q=&v=default"
        auth = ("admin", "Admin123")

        response = requests.get(url, auth=auth)
        response.raise_for_status()

        with open(filename, "w") as f:
            f.write(response.text)

        return filename  # Return path to use in next step

    transform = SparkSubmitOperator(
        task_id="transform_with_spark",
        application="./include/scripts/transform_patient.py",
        conn_id="my_spark_conn",
        application_args=[],  # Use XCom or env if needed
        verbose=True
    )

    load = SparkSubmitOperator(
        task_id="load_with_spark",
        application="./include/scripts/load_to_dhis2.py",
        conn_id="my_spark_conn",
        application_args=[],  # Use XCom or env if needed
        verbose=True
    )

    def cleanup_temp_data():
        temp_dir = "./include/temp_data"
        if os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"✅ Removed {file_path}")
                except Exception as e:
                    print(f"⚠️ Failed to remove {file_path}: {e}")
        else:
            print("ℹ️ Temp directory does not exist")

    cleanup = PythonOperator(
        task_id="cleanup_temp_data",
        python_callable=cleanup_temp_data
    )

    # DAG structure
    raw_path = extract_patient()
    raw_path >> transform >> load >> cleanup

dag = load_openmrs_to_dhis2()
