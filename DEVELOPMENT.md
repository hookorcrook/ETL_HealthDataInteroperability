# Development Guide

This guide provides detailed instructions for setting up a development environment and working on the ETL_HealthDataInteroperability project.

## Development Environment Setup

### 1. Python Environment

```bash
# Create a virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate
# On Unix/MacOS:
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
```

### 2. Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually (recommended before committing)
pre-commit run --all-files
```

### 3. IDE Setup

#### VS Code
Install the following extensions:
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Docker (ms-azuretools.vscode-docker)
- YAML (redhat.vscode-yaml)
- Apache Airflow (astronomer.airflow)

Recommended `settings.json` configurations:
```json
{
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "editor.formatOnSave": true,
    "editor.rulers": [88],
    "files.trimTrailingWhitespace": true
}
```

### 4. Local Development Database Setup

For local development without Docker:

1. **OpenMRS Database**:
   ```bash
   # Install MySQL
   mysql -u root -p
   CREATE DATABASE openmrs;
   CREATE USER 'openmrs'@'localhost' IDENTIFIED BY 'Admin123';
   GRANT ALL PRIVILEGES ON openmrs.* TO 'openmrs'@'localhost';
   FLUSH PRIVILEGES;
   ```

2. **DHIS2 Database**:
   ```bash
   # Install PostgreSQL
   createdb dhis2
   createuser -P dhis2 # Use 'district' as password
   psql -d dhis2 -c "GRANT ALL PRIVILEGES ON DATABASE dhis2 TO dhis2;"
   ```

## Development Workflow

### 1. Branch Management

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Keep branch up to date
git fetch origin
git rebase origin/main

# Push changes
git push origin feature/your-feature-name
```

### 2. Code Style

We follow these conventions:
- Black for code formatting (max line length: 88)
- Flake8 for code linting
- Google style docstrings
- Type hints for function arguments and return values

Example:
```python
def transform_patient_data(
    patient: Dict[str, Any],
    org_unit: str
) -> Dict[str, Any]:
    """Transform patient data to DHIS2 format.

    Args:
        patient: Raw patient data from OpenMRS
        org_unit: Organization unit ID in DHIS2

    Returns:
        Transformed patient data ready for DHIS2

    Raises:
        ValueError: If required fields are missing
    """
    ...
```

### 3. Testing

#### Unit Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_transformers.py

# Run with coverage
pytest --cov=include

# Run tests in parallel
pytest -n auto
```

#### Integration Tests
```bash
# Start required services
make start

# Run integration tests
pytest tests/integration/

# Stop services
make stop
```

### 4. DAG Development

1. **Local DAG Testing**:
   ```bash
   # Start Airflow in standalone mode
   export AIRFLOW_HOME=$(pwd)
   airflow standalone
   ```

2. **DAG File Structure**:
   ```python
   from airflow import DAG
   from airflow.utils.dates import days_ago

   default_args = {
       'owner': 'airflow',
       'depends_on_past': False,
       'start_date': days_ago(1),
       'email_on_failure': False,
       'email_on_retry': False,
       'retries': 1
   }

   with DAG(
       'your_dag_id',
       default_args=default_args,
       schedule_interval=None
   ) as dag:
       # Your tasks here
       ...
   ```

3. **Testing DAGs**:
   ```bash
   # Test DAG syntax
   python -c "from dags.your_dag import dag"

   # Test task dependencies
   airflow tasks list your_dag_id --tree
   ```

### 5. Debugging

#### Airflow Tasks
```bash
# Get task logs
airflow tasks test your_dag_id task_id 2025-01-01

# Debug with ipdb
import ipdb; ipdb.set_trace()
```

#### Docker Containers
```bash
# View container logs
docker compose -f docker-compose.all.yml logs -f [service_name]

# Access container shell
docker compose -f docker-compose.all.yml exec [service_name] bash

# Check container health
docker compose -f docker-compose.all.yml ps
```

### 6. Common Development Tasks

#### Adding New Dependencies
1. Add to `requirements.txt`
2. Rebuild containers:
   ```bash
   make clean
   make start
   ```

#### Updating Database Schema
1. Create migration file in `migrations/`
2. Test migration locally
3. Update documentation

#### Adding New ETL Component
1. Create classes in appropriate directories:
   - Extractors: `include/framework/extractors/`
   - Transformers: `include/framework/transformers/`
   - Loaders: `include/framework/loaders/`
2. Add unit tests
3. Update DAG to use new component

## Troubleshooting

### Common Issues

1. **Permission Issues**
   ```bash
   # Fix log permissions
   sudo chown -R $(id -u):$(id -g) logs/
   ```

2. **Database Connection Issues**
   ```bash
   # Check database connectivity
   nc -zv localhost 3306  # MySQL
   nc -zv localhost 5432  # PostgreSQL
   ```

3. **Container Issues**
   ```bash
   # Remove all containers and volumes
   make clean

   # Rebuild specific service
   docker compose -f docker-compose.all.yml up -d --build [service_name]
   ```

### Getting Help

1. Check the logs:
   ```bash
   make logs
   ```

2. Debug specific service:
   ```bash
   docker compose -f docker-compose.all.yml logs [service_name]
   ```

3. Open an issue on GitHub with:
   - Description of the problem
   - Steps to reproduce
   - Relevant logs
   - Environment details

## Performance Tips

1. Use batch processing where possible
2. Implement proper error handling and retries
3. Use connection pooling for databases
4. Cache frequently accessed data
5. Monitor memory usage in Spark transformations

## Documentation

### Adding Documentation

1. Update relevant README files
2. Add docstrings to new classes and functions
3. Update API documentation if needed
4. Add comments for complex logic

### Building Documentation
```bash
# Install documentation dependencies
pip install sphinx sphinx-rtd-theme

# Build documentation
cd docs
make html
```
