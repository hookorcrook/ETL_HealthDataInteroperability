#!/bin/bash

# Create required directories
mkdir -p logs
mkdir -p include/temp_data
mkdir -p data

# Set permissions
chmod -R 777 logs
chmod -R 777 include/temp_data
chmod -R 777 data

echo "Created and set permissions for required directories"
