# Health Data Interoperability ETL Pipeline

This project implements an ETL (Extract, Transform, Load) pipeline that enables health data interoperability between OpenMRS and DHIS2 health information management systems using Apache Airflow and Apache Spark.

## Prerequisites

- Docker and Docker Compose (version 2.x or higher)
- Git
- At least 8GB RAM available for containers
- 20GB free disk space
- Python 3.9 or higher (for local development)

## System Architecture

The system consists of several containerized services:

1. **Apache Airflow** (Port 8080)
   - Webserver
   - Scheduler
   - Workers
   - PostgreSQL database
   - Redis message broker

2. **OpenMRS** (Port 8081)
   - OpenMRS web application
   - MySQL database

3. **DHIS2** (Port 8082)
   - DHIS2 core application
   - PostgreSQL database

4. **Apache Spark** (Port 8085)
   - Spark master
   - Web UI

## Project Structure

```
├── apps/                  # Application specific code
├── config/               # Configuration files
│   ├── default.yaml     # Default configuration
│   ├── development.yaml # Development environment config
│   └── production.yaml  # Production environment config
├── dags/                # Airflow DAG definitions
├── include/             # ETL framework code
│   ├── framework/      # Core framework components
│   └── scripts/        # ETL scripts
├── HMISTools/          # HMIS system configurations
│   ├── DHIS2/         # DHIS2 Docker setup
│   └── openMRS/       # OpenMRS Docker setup
└── docker-compose.yaml  # Main Docker Compose configuration
```

## Setup Instructions

### 1. Initial Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/hookorcrook/ETL_HealthDataInteroperability.git
   cd ETL_HealthDataInteroperability
   ```

2. Environment Setup:
   ```bash
   # Copy the environment file
   cp .env.example .env
   
   # Review and edit if needed
   notepad .env  # or use your preferred editor
   ```

   The default credentials in `.env.example` are:
   - OpenMRS: admin/Admin123
   - DHIS2: admin/district
   - Airflow: airflow/airflow

3. Check Docker Configuration:
   ```bash
   # Verify Docker and Docker Compose installation
   docker --version
   docker compose version
   
   # Ensure Docker has enough resources (minimum 8GB RAM)
   ```

4. Directory Permissions:
   ```bash
   # Create and set permissions for Airflow logs
   mkdir -p ./logs
   chmod -R 777 ./logs  # On Unix systems
   
   # Create data directories
   mkdir -p ./include/temp_data
   ```
   ```
   # OpenMRS Configuration
   OPENMRS_URL=http://openmrs-referenceapplication:8080/openmrs
   OPENMRS_USERNAME=admin
   OPENMRS_PASSWORD=Admin123

   # DHIS2 Configuration
   DHIS2_URL=http://web:8080
   DHIS2_API_TOKEN=your_api_token

   # Spark Configuration
   SPARK_MASTER=local[*]
   ```

### 2. Start the System

#### Quick Start (Recommended)
Start all services with a single command:
```bash
# First time setup
docker compose -f docker-compose.all.yml up airflow-init

# Start all services
docker compose -f docker-compose.all.yml up -d
```

The services will be available at:
- Airflow: http://localhost:8080 (login: airflow/airflow)
- OpenMRS: http://localhost:8081 (login: admin/Admin123)
- DHIS2: http://localhost:8082 (login: admin/district)
- Spark Master UI: http://localhost:8085

#### Monitor Startup
```bash
# View logs of all services
docker compose -f docker-compose.all.yml logs -f

# View logs of a specific service
docker compose -f docker-compose.all.yml logs -f [service-name]
```

#### Check Service Health
```bash
# List running containers
docker compose -f docker-compose.all.yml ps

# Check service health
docker compose -f docker-compose.all.yml ps --format "table {{.Service}}\t{{.Status}}"
```

#### Stopping the System
```bash
# Stop all services
docker compose -f docker-compose.all.yml down

# Stop and remove volumes (clean start)
docker compose -f docker-compose.all.yml down -v
```

#### Option 2: Start Services Individually
If you need more control, you can start each system separately:

1. Start OpenMRS:
   ```bash
   cd HMISTools/openMRS
   docker-compose up -d
   cd ../..
   ```

2. Start DHIS2:
   ```bash
   cd HMISTools/DHIS2
   docker-compose up -d
   cd ../..
   ```

3. Start Airflow:
   ```bash
   docker-compose up -d
   ```

### 3. System Verification

#### Initial System Check
1. Verify all services are running:
   ```bash
   docker compose -f docker-compose.all.yml ps
   ```

2. Check service logs for errors:
   ```bash
   docker compose -f docker-compose.all.yml logs | grep -i error
   ```

#### Access Web Interfaces

1. **Airflow Dashboard**
   - URL: http://localhost:8080
   - Username: airflow
   - Password: airflow
   - Verify: DAGs are listed and scheduler is running

2. **OpenMRS**
   - URL: http://localhost:8081/openmrs
   - Username: admin
   - Password: Admin123
   - Verify: Can access patient records

3. **DHIS2**
   - URL: http://localhost:8082
   - Username: admin
   - Password: district
   - Verify: Can access dashboard

4. **Spark Master UI**
   - URL: http://localhost:8085
   - Verify: Worker nodes are connected

## Running the ETL Pipeline

### 1. Initial DHIS2 Setup

1. Access the Airflow web interface
2. Locate the `setup_dhis2_system` DAG
3. Click "Trigger DAG" to run the setup
4. Wait for setup completion (monitor in Airflow UI)

### 2. Run Data Synchronization

1. After setup is complete, locate the `load_openmrs_to_dhis2` DAG
2. Trigger the DAG manually or wait for scheduled execution
3. Monitor the execution in Airflow UI

## DAG Descriptions

1. `setup_dhis2_system`:
   - Sets up DHIS2 organization units
   - Creates tracked entity attributes
   - Configures programs and stages
   - Must be run successfully before data sync

2. `load_openmrs_to_dhis2`:
   - Extracts patient data from OpenMRS
   - Transforms data using Spark
   - Loads data into DHIS2
   - Runs daily by default

## Monitoring and Maintenance

### Logs
- Airflow logs: `./logs/`
- OpenMRS logs: `HMISTools/openMRS/logs/`
- DHIS2 logs: `HMISTools/DHIS2/logs/`

### Temporary Data
- ETL temporary files: `./include/temp_data/`
- Cleaned up automatically after successful DAG runs

### Configuration Updates
1. Modify files in `./config/`
2. Re-run setup DAG if DHIS2 configuration changes
3. Changes to ETL logic only require DAG restart

## Troubleshooting

### Common Issues

1. Container Connection Issues:
   ```bash
   # Check container status
   docker ps
   # Check container logs
   docker logs <container_id>
   ```

2. DAG Failures:
   - Check Airflow logs in web UI
   - Verify system connectivity
   - Ensure setup DAG completed successfully

3. Data Synchronization Issues:
   - Verify OpenMRS connectivity
   - Check DHIS2 API token validity
   - Review transformation logs

### Support

For issues and support:
1. Check the logs
2. Review configuration
3. Open an issue on GitHub

## Development

For detailed information about setting up a development environment, coding standards, testing procedures, and best practices, please refer to our [Development Guide](DEVELOPMENT.md).

Quick start for developers:

1. Setup development environment:
   ```bash
   make setup
   ```

2. Start the services:
   ```bash
   make start
   ```

3. View logs:
   ```bash
   make logs
   ```

4. Run tests:
   ```bash
   make test
   ```

For more detailed instructions and advanced development topics, please consult the [Development Guide](DEVELOPMENT.md).

## License

[Add your license information here]