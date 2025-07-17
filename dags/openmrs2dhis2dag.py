from airflow.decorators import dag, task
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.operators.python import PythonOperator
from datetime import datetime

@dag(schedule_interval="@daily", start_date=datetime(2025, 1, 1), catchup=False)
def sync_openmrs_to_dhis2():

    def extract_patient():
        import requests
        url = "http://openmrs-referenceapplication:8080/openmrs/ws/rest/v1/person?q=&v=default"
        params = {"v": "full"}
        auth = ("admin", "Admin123")
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"./include/temp_data/patients_raw_{timestamp}.json"

        response = requests.get(url, auth=auth, params=params)
        response.raise_for_status()

        with open(filename, "w") as f:
            f.write(response.text)

    extract = PythonOperator(
        task_id="extract_patient",
        python_callable=extract_patient
    )

    transform = SparkSubmitOperator(
        task_id="transform_with_spark",
        application="./include/scripts/transform_patient.py",
        conn_id="my_spark_conn",  # make sure this connection exists in Airflow
        application_args=[],
        verbose=True
    )

    def load_to_dhis2():
        import requests, json
        timestamp = datetime.now().strftime("%Y%m%d")
        output_filename = "./include/temp_data/patients_ready_{timestamp}.json"
        with open(output_filename) as f:
            patients = json.load(f)

        url = "http://web:8080/api/trackedEntityInstances"
        auth = ("admin", "district")

        for patient in patients:
            r = requests.post(url, json=patient, auth=auth)
            print(f"Posted: {r.status_code} - {r.text}")

    load = PythonOperator(
        task_id="load_to_dhis2",
        python_callable=load_to_dhis2
    )

    extract >> transform >> load
dag = sync_openmrs_to_dhis2()
