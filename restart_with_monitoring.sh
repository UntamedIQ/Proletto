#!/bin/bash

# Backup original main.py if not already backed up
if [ ! -f main.py.bak ]; then
    echo "Creating backup of original main.py as main.py.bak"
    cp main.py main.py.bak
fi

# Replace main.py with our updated version
echo "Replacing main.py with monitoring-enabled version"
cp main_updated.py main.py

# Restart the Proletto App workflow
echo "Restarting Proletto App workflow..."
restart_workflow_cmd="restart_workflow 'Proletto App'"
python3 -c "import os; os.system('$restart_workflow_cmd')"

echo "Monitoring system is now active!"
echo "Access the monitoring dashboard at: /admin/monitoring"
echo "Check logs in the logs directory for monitoring data."
echo ""
echo "To revert back to the original main.py:"
echo "  cp main.py.bak main.py && python3 -c \"import os; os.system('restart_workflow \\'Proletto App\\'')\"" 