from pyspark.sql import SparkSession
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import explode, col
import requests
import json


def main():
    spark = SparkSession.builder \
        .appName("OpenMRS Connect") \
        .getOrCreate()
    
    # Replace with your actual credentials and URL
    username = "admin"
    password = "Admin123"
    url = "http://openmrs-referenceapplication:8080/openmrs/ws/rest/v1/encounter?patient=50d012b9-e5ba-4fe7-9e6d-018a40d303be"

    response = requests.get(url, auth=(username, password))

    # Check for successful response
    if response.status_code == 200:
        json_data = response.json()
    else:
        raise Exception(f"API request failed with status {response.status_code}: {response.text}")
    
    # --- Step 2: Convert JSON data to string and parallelize as RDD ---
    json_str = json.dumps(json_data)
    rdd = spark.sparkContext.parallelize([json_str])

# --- Step 3: Load JSON into DataFrame ---
    df = spark.read.json(rdd)

# --- Step 4: Parse and flatten ---
# Explode 'results' (encounters)
    df_encounters = df.select(explode(col("results")).alias("encounter"))

# Explode 'obs' inside encounters
    df_obs = df_encounters.select(
    col("encounter.uuid").alias("encounter_uuid"),
    col("encounter.encounterDatetime").alias("encounter_datetime"),
    col("encounter.patient.uuid").alias("patient_uuid"),
    col("encounter.patient.display").alias("patient_display"),
    explode(col("encounter.obs")).alias("observation"),
    col("encounter.visit.uuid").alias("visit_uuid"),
    col("encounter.visit.display").alias("visit_display")
    )

# Select and flatten obs fields
    df_obs_flat = df_obs.select(
    "patient_uuid",
    "patient_display",
    "encounter_uuid",
    "encounter_datetime",
    "visit_uuid",
    "visit_display",
    col("observation.uuid").alias("obs_uuid"),
    col("observation.display").alias("obs_display"),
    col("observation.obsDatetime").alias("obs_datetime"),
    col("observation.concept.display").alias("concept_name"),
    col("observation.value").alias("value")
)

# Show parsed observations
    df_obs_flat.show(truncate=False)
    
    spark.stop()

if __name__ == "__main__":
    main()