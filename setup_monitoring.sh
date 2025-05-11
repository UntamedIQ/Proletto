#!/bin/bash

# Script to setup monitoring infrastructure for Proletto

# Create logs directory
mkdir -p logs

# Ensure proper permissions
chmod 755 logs

# Create log files with proper permissions
touch logs/proletto.log
touch logs/proletto_error.log
touch logs/proletto_structured.json
chmod 644 logs/proletto.log logs/proletto_error.log logs/proletto_structured.json

# Create empty database directory
mkdir -p logs/db_backups

echo "Monitoring infrastructure setup complete."
echo "Log files are available in the logs directory:"
echo " - logs/proletto.log - General application logs"
echo " - logs/proletto_error.log - Error logs only"
echo " - logs/proletto_structured.json - Structured logs in JSON format"
echo ""
echo "To enable the monitoring system:"
echo "1. Use main_updated.py instead of main.py"
echo "2. Access the monitoring dashboard at /admin/monitoring"
echo ""