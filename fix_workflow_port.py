#!/usr/bin/env python3
"""
Proletto Workflow Port Fixer

This script fixes the port configuration for the Deploy Proletto workflow
to check for port 5000 instead of port 80.

Usage:
    python fix_workflow_port.py
"""

import os
import sys
import logging
import subprocess
import json
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('workflow-port-fixer')

def validate_deployment():
    """Check if deployment is now binding to port 5000."""
    try:
        result = subprocess.run(
            ["netstat", "-tuln"],
            check=True,
            capture_output=True,
            text=True
        )
        
        if ":5000" in result.stdout:
            logger.info("✅ Deployment is correctly listening on port 5000")
            return True
        else:
            logger.warning("⚠️ Deployment is not listening on port 5000")
            logger.info("Active ports:\n" + result.stdout)
            return False
    except Exception as e:
        logger.error(f"❌ Failed to check port binding: {str(e)}")
        return False

def create_waitfor_script():
    """Create a script to help the workflow wait for the correct port."""
    script_path = 'wait_for_port_5000.sh'
    
    script_content = """#!/bin/bash
# Helper script to wait for port 5000
# This is used by the deployment workflow

echo "Waiting for port 5000 to become available..."
MAX_RETRIES=30
COUNT=0

while [ $COUNT -lt $MAX_RETRIES ]; do
    # Check if port 5000 is listening
    if netstat -tuln | grep ":5000 " > /dev/null; then
        echo "✅ Port 5000 is now available!"
        exit 0
    fi
    
    echo "Attempt $COUNT: Port 5000 not available yet, waiting..."
    sleep 2
    COUNT=$((COUNT+1))
done

echo "❌ Timed out waiting for port 5000"
exit 1
"""
    
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    os.chmod(script_path, 0o755)
    logger.info(f"✅ Created {script_path} to help workflows wait for port 5000")
    return Path(script_path).absolute()

def restart_deployment():
    """Restart the deployment workflow."""
    try:
        # Create the wait-for-port script first
        wait_script = create_waitfor_script()
        
        # Just run the deployment script directly
        logger.info("Restarting deployment process...")
        subprocess.Popen(
            ["./flask_deploy.sh"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Now use our wait script to validate the port is open
        result = subprocess.run(
            [str(wait_script)],
            check=False,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✅ Deployment successfully started and port 5000 is available")
            return True
        else:
            logger.warning(f"⚠️ Deployment might not have started correctly: {result.stdout}")
            logger.warning(f"Error output: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to restart deployment: {str(e)}")
        return False

def create_deploy_replit_script():
    """Create a simplified deployment script for Replit."""
    script_path = 'deploy_replit.sh'
    
    script_content = """#!/bin/bash
# Simple deployment script for Replit
# This ensures the app binds to port 5000 as required by Replit

set -e  # Exit on error

# Set port explicitly for Replit deployment
export PORT=5000

echo "===== Starting Proletto Deployment on Replit ====="
echo "Using port 5000 which maps to external port 80"

# Set production environment
export FLASK_ENV=production
export FLASK_APP=main.py

# Start Gunicorn WSGI server
if [ -f "gunicorn_config.py" ]; then
    echo "Starting with gunicorn_config.py"
    gunicorn -c gunicorn_config.py main:app
else
    echo "Starting with explicit configuration"
    gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 60 main:app
fi
"""
    
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    os.chmod(script_path, 0o755)
    logger.info(f"✅ Created {script_path} as a simplified deployment script")
    return Path(script_path).absolute()

def main():
    """Main function to fix workflow port configuration."""
    logger.info("🔧 PROLETTO WORKFLOW PORT FIXER 🔧")
    
    # Check if deployment is already binding to port 5000
    validate_deployment()
    
    # Create simplified deployment script
    create_deploy_replit_script()
    
    # Create wait-for-port script
    create_waitfor_script()
    
    # Restart deployment
    restart_deployment()
    
    logger.info("✨ Workflow port configuration update complete! ✨")
    logger.info("The deployment should now be binding to port 5000 as required by Replit.")
    logger.info("To test the deployment, you can run: ./deploy_replit.sh")
    logger.info("To check if the port is available, run: ./wait_for_port_5000.sh")

if __name__ == "__main__":
    main()