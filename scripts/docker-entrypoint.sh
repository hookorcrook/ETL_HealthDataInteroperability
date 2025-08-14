#!/bin/bash

# Function to ensure shared network exists
ensure_shared_network() {
    if ! docker network ls | grep -q "shared-network"; then
        echo "Creating shared network..."
        docker network create shared-network
    else
        echo "Shared network already exists"
    fi
}

# Function to wait for Airflow webserver
wait_for_airflow() {
    echo "Waiting for Airflow webserver..."
    while ! nc -z localhost 8080; do   
        sleep 1
    done
    echo "Airflow webserver is up"
}

# Ensure shared network exists
ensure_shared_network

# Initialize Airflow DB if needed
airflow db init

# Create admin user if it doesn't exist
airflow users create \
    --username admin \
    --firstname admin \
    --lastname admin \
    --role Admin \
    --email admin@example.com \
    --password admin

# Setup Airflow connections and variables
python /opt/airflow/scripts/setup_airflow.py

# Start Airflow (using the original entrypoint)
exec /entrypoint
