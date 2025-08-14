#!/bin/bash

# Function to check service health
check_service() {
    local service=$1
    local url=$2
    local max_retries=${3:-30}
    local retry_interval=${4:-5}
    
    echo "Checking $service..."
    for ((i=1; i<=$max_retries; i++)); do
        if curl -s -f "$url" > /dev/null; then
            echo "✅ $service is healthy"
            return 0
        else
            echo "⏳ Waiting for $service (attempt $i/$max_retries)..."
            sleep $retry_interval
        fi
    done
    echo "❌ $service health check failed"
    return 1
}

# Check OpenMRS
check_service "OpenMRS" "http://openmrs:8080/openmrs/ws/rest/v1/session" || exit 1

# Check DHIS2
check_service "DHIS2" "http://dhis2:8080/api/system/info" || exit 1

# Check Spark Master
check_service "Spark Master" "http://spark-master:8081/" || exit 1

# Check Airflow
check_service "Airflow" "http://airflow-webserver:8080/health" || exit 1

echo "✅ All services are healthy"
