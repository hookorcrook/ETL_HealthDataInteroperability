from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from datetime import datetime
import os
import requests
import json
import glob
import shutil

# Config
timestamp = datetime.now().strftime("%Y%m%d")
input_path = f"./include/temp_data/patients_raw_{timestamp}.json"
transition_path = f"./include/temp_data/patients_tmp_{timestamp}.json"
output_path = f"./include/temp_data/patients_ready_{timestamp}.json"

# temp dir no longer needed for final write, keep just in case
all_patients_dir = "./include/temp_data/patients_all_tmp"
all_patients_path = f"./include/temp_data/patients_all.json"

openmrs_url = "http://openmrs-referenceapplication:8080/openmrs/ws/rest/v1/patient"
auth = ("admin", "Admin123")

# Check if raw data exists
if not os.path.exists(input_path):
    print(f"Input file not found: {input_path}")
    exit(1)

# Start Spark
spark = SparkSession.builder.appName("ValidateOpenMRSPatients").getOrCreate()

# Load raw JSON
with open(input_path, "r") as f:
    data = json.load(f)

results = data.get("results", [])

# Save standalone JSON for Spark
os.makedirs(os.path.dirname(transition_path), exist_ok=True)
with open(transition_path, "w") as f:
    json.dump(results, f, indent=2)

df_raw = spark.read.json(transition_path, multiLine=True)

df_patients = df_raw.select(
    "uuid",
    "display",
    "gender",
    "age",
    col("birthdate").alias("dob"),
    col("preferredName.display").alias("name"),
    col("preferredAddress.display").alias("address")
)

df_patients.show()

# Load or create patients_all.json (driver-side read)
if os.path.exists(all_patients_path):
    try:
        df_all = spark.read.json(all_patients_path, multiLine=True)
        if "uuid" in df_all.columns:
            df_all = df_all.withColumnRenamed("uuid", "patient_id")
    except Exception:
        # fallback to empty schema
        df_all = spark.createDataFrame([], df_patients.select("uuid", "name", "dob", "gender").schema).withColumnRenamed("uuid", "patient_id")
else:
    df_all = spark.createDataFrame([], df_patients.select("uuid", "name", "dob", "gender").schema).withColumnRenamed("uuid", "patient_id")

# Identify delta patients
df_delta = df_patients.join(df_all, df_patients.uuid == df_all.patient_id, how="left_anti")
delta_count = df_delta.count()
print(f"Processing {delta_count} new patients (delta)")

valid_patients = []

for row in df_delta.collect():
    uuid = row["uuid"]
    try:
        url = f"{openmrs_url}/{uuid}"
        response = requests.get(url, auth=auth, timeout=5)
        if response.status_code == 200:
            patient_data = response.json()
            person_data = patient_data.get("person", {})

            if not person_data:
                print(f"No person data for UUID: {uuid}")
                continue

            full_name = patient_data.get("display", "")
            dob = person_data.get("birthdate").split("T")[0] if person_data.get("birthdate") else None
            gender = person_data.get("gender")
            name = full_name.split(" - ", 1)[-1] if " - " in full_name else full_name

            valid_patients.append((uuid, name, dob, gender))
        else:
            print(f"Invalid UUID {uuid} - Status: {response.status_code}")
    except Exception as e:
        print(f"Error processing UUID {uuid}: {str(e)}")

# Write delta output
if valid_patients:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([{"patient_id": u, "name": n, "dob": d, "gender": g} for u, n, d, g in valid_patients], f, indent=2)
    print(f"Saved {len(valid_patients)} valid new patients to {output_path}")
else:
    print("No new valid patients found.")

# ---------- SAFE single-file update (driver-side) ----------
if valid_patients:
    # Build a combined list of existing patients + new valid patients (avoid collecting entire large df_all if huge)
    # Read existing patients_all.json on driver if exists
    existing = []
    if os.path.exists(all_patients_path):
        try:
            with open(all_patients_path, "r", encoding="utf-8") as f:
                existing = json.load(f)  # expects a JSON array
        except Exception:
            # graceful fallback if file malformed
            existing = []

    # Convert existing to dict keyed by patient_id to avoid duplicates
    existing_by_id = {p.get("patient_id") or p.get("uuid"): p for p in existing if (p.get("patient_id") or p.get("uuid"))}

    # Add/overwrite with new valid patients
    for u, n, d, g in valid_patients:
        existing_by_id[u] = {"patient_id": u, "name": n, "dob": d, "gender": g}

    # Final list sorted optionally
    final_list = list(existing_by_id.values())

    # Write single JSON file atomically: write to temp file then move
    tmp_file = f"{all_patients_path}.tmp"
    os.makedirs(os.path.dirname(all_patients_path), exist_ok=True)
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(final_list, f, indent=2)
    os.replace(tmp_file, all_patients_path)  # atomic on POSIX
    print(f"Updated {all_patients_path} with total {len(final_list)} patients")

spark.stop()
