# Configuration Guide

This document describes the configuration system for the Health Data Interoperability ETL pipeline.

## Environment Variables

The following environment variables must be set:

```bash
# OpenMRS Configuration
OPENMRS_URL=http://openmrs-host:8080/openmrs
OPENMRS_USERNAME=your_username
OPENMRS_PASSWORD=your_password

# DHIS2 Configuration
DHIS2_URL=http://dhis2-host:8080
DHIS2_API_TOKEN=your_api_token

# Spark Configuration
SPARK_MASTER=local[*]  # or your Spark master URL
```

## Configuration Files

The configuration system uses YAML files located in the `config/` directory:

- `default.yaml`: Base configuration, contains default values
- `development.yaml`: Development environment settings
- `production.yaml`: Production environment settings

### Loading Configuration

The configuration system automatically:
1. Loads the base configuration from `default.yaml`
2. Overlays environment-specific configuration
3. Resolves environment variables

### Using Configuration

```python
from include.framework.config import Config

# Load configuration
config = Config()

# Get specific values
openmrs_url = config.get('openmrs', 'base_url')
spark_config = config.spark

# Get nested values
person_endpoint = config.get('openmrs', 'api')['person_endpoint']
```

## Airflow Integration

The configuration system integrates with Airflow through:
- Connections (for OpenMRS, DHIS2, and Spark)
- Variables (for paths and other settings)

### Setting Up Airflow

Run the setup script to configure Airflow:

```bash
python scripts/setup_airflow.py
```

This will create:
- OpenMRS API connection
- DHIS2 API connection
- Spark connection
- Required Airflow variables

## Environment-Specific Settings

### Development
- Local Spark instance
- Debug logging
- Minimal resource allocation
- Immediate temp file cleanup

### Production
- Clustered Spark
- Info-level logging
- Optimized resource allocation
- Retention-based cleanup
- Monitoring and alerting
- Error retry mechanisms

## Security Notes

- Never commit `.env` files
- Use `.env.example` as a template
- Rotate API tokens regularly
- Use appropriate file permissions
