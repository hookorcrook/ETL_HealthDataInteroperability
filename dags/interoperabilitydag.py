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

        openmrs_url = "http://openmrs-referenceapplication:8080/openmrs/ws/rest/v1/person"
        auth = ("admin", "Admin123")

        all_results = []
        url = f"{openmrs_url}?q=&v=default"

        while url:
            response = requests.get(url, auth=auth)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            all_results.extend(results)
            print(f"Fetched {len(results)} records, total so far: {len(all_results)}")

            # Pagination: get next link
            next_url = None
            for link in data.get("links", []):
                if link.get("rel") == "next":
                    next_url = link.get("uri")
                    break
            url = next_url

        # Save all persons to file
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            json.dump({"results": all_results}, f, indent=2)

        print(f"✅ Total persons fetched: {len(all_results)}")
        return filename

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
        skip_file = "patients_all.json"

        if os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                if filename == skip_file:
                    continue  # skip this file
                file_path = os.path.join(temp_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"✅ Removed {file_path}")
                    elif os.path.isdir(file_path):
                        # Remove directories recursively
                        shutil.rmtree(file_path)
                        print(f"✅ Removed directory {file_path}")
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
