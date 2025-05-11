#!/bin/bash
# Initialization script for Proletto Flask application

# Create requirements.txt from our template
cat requirements-deploy.txt > requirements.txt
echo "Created requirements.txt"

# Run the Flask application
echo "Starting Flask application..."
python main.py