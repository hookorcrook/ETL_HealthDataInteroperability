from pyspark.sql import SparkSession
from pyspark.sql.functions import explode
from datetime import datetime
import os
import requests
import json

# Config
timestamp = datetime.now().strftime("%Y%m%d")
input_path = f"./include/temp_data/patients_raw_{timestamp}.json"
transition_path = f"./include/temp_data/patients_tmp_{timestamp}.json"
output_path = f"./include/temp_data/patients_ready_{timestamp}.json"

openmrs_url = "http://openmrs-referenceapplication:8080/openmrs/ws/rest/v1/patient"
auth = ("admin", "Admin123")

# Check if raw data exists
if not os.path.exists(input_path):
    print(f"Input file not found: {input_path}")
    exit(1)

# Start Spark
spark = SparkSession.builder.appName("ValidateOpenMRSPatients").getOrCreate()


# Load original JSON
with open(input_path, "r") as f:
    data = json.load(f)

results = data.get("results", [])

# Save results as a standalone JSON array
with open(transition_path, "w") as f:
    json.dump(results, f, indent=2)

# Read raw JSON
df_raw = spark.read.json(transition_path, multiLine=True)
df_raw.show()

df_patients = df_raw.select(explode("results").alias("patient")).select("patient.uuid")


# Collect UUIDs to driver
uuids = [row["uuid"] for row in df_patients.collect()]

print(f"Found {len(uuids)} UUIDs in raw data")

valid_patients = []

# Validate each UUID with API call
for uuid in uuids:
    try:
        url = f"{openmrs_url}/{uuid}"
        print(f"Checking for: {uuid} with URL: {url}")
        response = requests.get(url, auth=auth, timeout=5)
        if response.status_code == 200:
            patient_data = response.json()
            valid_patients.append({
                "patient_id": uuid,
                "name": patient_data.get("display"),
                "dob": patient_data.get("birthdate"),
                "gender": patient_data.get("gender")
            })
        else:
            print(f"Invalid patient UUID: {uuid} and url {url}- Status: {response.status_code}")
    except Exception as e:
        print(f"Error checking UUID {uuid}: {str(e)}")

# Write output
if valid_patients:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(valid_patients, f, indent=2)
    print(f"Saved {len(valid_patients)} valid patients to {output_path}")
else:
    print("No valid patients found.")

spark.stop()
