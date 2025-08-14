#!/bin/bash

# Sleep for a while to ensure the webserver is ready
sleep 30
echo "Starting connection setup..."

# Create OpenMRS connection
airflow connections add 'openmrs_api' \
    --conn-type 'http' \
    --conn-host "${OPENMRS_URL:-http://openmrs:8080/openmrs}" \
    --conn-login "${OPENMRS_USERNAME:-admin}" \
    --conn-password "${OPENMRS_PASSWORD:-Admin123}"

# Create DHIS2 connection
airflow connections add 'dhis2_api' \
    --conn-type 'http' \
    --conn-host "${DHIS2_URL:-http://dhis2:8080}" \
    --conn-password "${DHIS2_API_TOKEN:-admin}"

# Create Spark connection
airflow connections add 'my_spark_conn' \
    --conn-type 'spark' \
    --conn-host 'spark://spark-master' \
    --conn-port '7077' \
    --conn-extra '{
        "spark-binary": "spark-submit",
        "deploy-mode": "client",
        "namespace": "airflow",
        "queue": "default"
    }'

echo "Connections created successfully"
