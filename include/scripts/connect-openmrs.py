from pyspark.sql import SparkSession
import requests
import json
import logging

def main():
    # Initialize Spark session
    spark = SparkSession.builder \
        .appName("OpenMRS Connect") \
        .getOrCreate()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    username = "admin"
    password = "Admin123"
    url = "http://openmrs-referenceapplication:8080/openmrs/ws/rest/v1/patient/daf4ba64-b046-4776-a929-449cad441e73"

    response = requests.get(url, auth=(username, password))

    if response.status_code == 200:
        json_data = response.json()
        # Log the JSON response prettily
        logging.info("Received JSON response:\n%s", json.dumps(json_data, indent=2))
    else:
        logging.error(f"API request failed with status {response.status_code}: {response.text}")

    # Stop Spark session
    spark.stop()

if __name__ == "__main__":
    main()
