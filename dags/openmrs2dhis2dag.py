from airflow.decorators import dag, task
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.operators.python import PythonOperator
from datetime import datetime
import requests,json,os

@dag(schedule_interval="@daily", start_date=datetime(2025, 1, 1), catchup=False)
def sync_openmrs_to_dhis2():

    def extract_patient():  
        base_url = "http://openmrs-referenceapplication:8080/openmrs/ws/rest/v1/person"
        params = {"v": "full", "q":""}
        auth = ("admin", "Admin123")
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"./include/temp_data/patients_raw_{timestamp}.json"

        all_results = []
        start_index = 0
        page_size = 50  # OpenMRS default
        while True:
            paged_url = f"{base_url}?startIndex={start_index}"
            response = requests.get(paged_url, auth=auth, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            if not results:
                break

            all_results.extend(results)
            print(f"Fetched {len(results)} records, total so far: {len(all_results)}")
            
            # If no "next" link in response, stop
            links = data.get("links", [])
            next_link = next((link for link in links if link.get("rel") == "next"), None)
            if not next_link:
                break

            start_index += len(results)

        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            json.dump({"results": all_results}, f, indent=2)
        
        print(f"✅ Total persons fetched: {len(all_results)}")



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
        output_filename = f"./include/temp_data/patients_ready_{timestamp}.json"
        with open(output_filename) as f:
            patients = json.load(f)

        url = "http://web:8080/api/trackedEntityInstances"
        headers = {
            "Authorization": "ApiToken d2p_afc0zYTgYyGErraPlIv83JFiKv0Vyh7nHHu8mG8fFzoJ2dXRgT",
            "Content-Type": "application/json"
        }

        for patient in patients:
            print(f"Posting patient {patient['patient_id']} to DHIS2 using url: {url}")
            r = requests.post(url, json=patient, headers=headers)
            print(f"Posted Successfully for patient : {patient['patient_id']}.  {r.status_code} - {r.text}")
            if r.status_code >= 400:
                raise Exception(f"Failed to load data to DHIS2: {r.status_code} - {r.text}")

    load = PythonOperator(
        task_id="load_to_dhis2",
        python_callable=load_to_dhis2
    )

    extract >> transform >> load

dag = sync_openmrs_to_dhis2()
