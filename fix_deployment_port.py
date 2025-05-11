#!/usr/bin/env python3
"""
Proletto Deployment Port Configuration Fixer

This script ensures proper port configuration for Replit deployment.
It modifies all necessary files to ensure the application binds to port 5000,
which is required for Replit deployments.
"""

import os
import re
import sys
import logging
import fileinput
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("deploy-port-fixer")

def fix_replit_config():
    """Fix .replit configuration file."""
    replit_updated = False
    replit_path = '.replit'
    
    if not os.path.exists(replit_path):
        logger.error("❌ .replit file not found")
        return False
    
    # Read the file
    with open(replit_path, 'r') as f:
        content = f.read()
    
    # Check and fix deployment command
    if 'run = ["sh", "-c", "./flask_deploy.sh"]' in content:
        content = content.replace(
            'run = ["sh", "-c", "./flask_deploy.sh"]',
            'run = ["sh", "-c", "./deploy_replit.sh"]'
        )
        replit_updated = True
        logger.info("✅ Updated .replit to use deploy_replit.sh")
    
    # Check and fix waitForPort
    if 'waitForPort = 80' in content:
        content = content.replace(
            'waitForPort = 80',
            'waitForPort = 5000'
        )
        replit_updated = True
        logger.info("✅ Updated .replit waitForPort from 80 to 5000")
    
    # Add buildCommand if missing
    if '[deployment]' in content and 'buildCommand' not in content:
        content = content.replace(
            '[deployment]',
            '[deployment]\n# No special build step needed for this application\nbuildCommand = "echo \'No build command needed, using runtime deployment\'"'
        )
        replit_updated = True
        logger.info("✅ Added buildCommand to .replit")
    
    # Write updated content if changes were made
    if replit_updated:
        with open(replit_path, 'w') as f:
            f.write(content)
        logger.info("✅ Updated .replit configuration")
    else:
        logger.info("✓ No changes needed to .replit configuration")
    
    return replit_updated

def fix_flask_deploy():
    """Fix flask_deploy.sh script."""
    deploy_path = 'flask_deploy.sh'
    
    if not os.path.exists(deploy_path):
        logger.error("❌ flask_deploy.sh file not found")
        return False
    
    # Check if file is executable and make it so
    if not os.access(deploy_path, os.X_OK):
        os.chmod(deploy_path, 0o755)
        logger.info("✅ Made flask_deploy.sh executable")
    
    # Read the file
    with open(deploy_path, 'r') as f:
        content = f.read()
    
    deploy_updated = False
    
    # Check for PORT variable
    if 'export PORT=5000' not in content:
        # Find the right spot to insert the PORT variable
        if '# Production Flask settings' in content:
            content = content.replace(
                '# Production Flask settings',
                '# Production Flask settings\nexport PORT=5000\n# Critical for Replit deployment'
            )
        elif 'export FLASK_ENV=production' in content:
            content = content.replace(
                'export FLASK_ENV=production',
                'export FLASK_ENV=production\nexport PORT=5000'
            )
        else:
            # Add it near the top if we can't find a good spot
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('echo "====='):
                    lines.insert(i+1, 'export PORT=5000  # Critical for Replit deployment')
                    content = '\n'.join(lines)
                    break
        
        deploy_updated = True
        logger.info("✅ Added PORT=5000 to flask_deploy.sh")
    
    # Make sure we're binding to 0.0.0.0:5000
    if '--bind 0.0.0.0:5000' not in content and '--bind 0.0.0.0:${PORT:-5000}' not in content:
        if 'exec gunicorn -c gunicorn_config.py main:app' in content:
            content = content.replace(
                'exec gunicorn -c gunicorn_config.py main:app',
                'exec gunicorn --bind 0.0.0.0:${PORT:-5000} -c gunicorn_config.py main:app'
            )
            deploy_updated = True
            logger.info("✅ Added explicit binding to flask_deploy.sh gunicorn command")
    
    if deploy_updated:
        with open(deploy_path, 'w') as f:
            f.write(content)
        logger.info("✅ Updated flask_deploy.sh")
    else:
        logger.info("✓ No changes needed to flask_deploy.sh")
    
    return deploy_updated

def create_deploy_replit():
    """Create deploy_replit.sh script."""
    deploy_path = 'deploy_replit.sh'
    
    # Content for the deployment script
    content = """#!/bin/bash
# Enhanced Replit Deployment Script for Proletto
# This script is specifically designed to ensure proper port binding for Replit deployments

set -e  # Exit on error

echo "===== Proletto Replit Deployment Script ====="
echo "Setting up deployment environment with proper port binding..."

# CRITICAL: Set PORT environment variable explicitly
# This is required for Replit deployments to work properly
export PORT=5000
echo "PORT=$PORT"

# Ensure all scripts are executable
chmod +x *.sh
chmod +x *.py

# Configure production environment
export FLASK_ENV=production 
export FLASK_APP=main.py
export REPLIT_DEPLOYMENT=1

echo "📣 PORT=$PORT - This will be forwarded to external port 80"
echo "📣 FLASK_ENV=$FLASK_ENV"
echo "📣 FLASK_APP=$FLASK_APP"

# Launch Gunicorn with explicit port binding
# We're not using gunicorn_config.py here to ensure the port binding is explicit
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 60 main:app
"""
    
    # Write the file
    with open(deploy_path, 'w') as f:
        f.write(content)
    
    # Make it executable
    os.chmod(deploy_path, 0o755)
    
    logger.info("✅ Created deploy_replit.sh script")
    return True

def fix_gunicorn_config():
    """Fix gunicorn_config.py file."""
    config_path = 'gunicorn_config.py'
    
    if not os.path.exists(config_path):
        logger.warning("⚠️ gunicorn_config.py file not found, creating it")
        content = """\"\"\"
Gunicorn Configuration for Proletto Production Deployment

This file contains configuration settings for running the Proletto app
with Gunicorn in production environments.

Usage:
    gunicorn -c gunicorn_config.py main:app
\"\"\"

import os
import multiprocessing

# Bind to port provided by Replit or default to 5000
# Replit deployment typically sets PORT=5000 (maps to external port 80)
# It's critical to use the PORT environment variable Replit provides
PORT = os.getenv("PORT", "5000")

# Force port to 5000 for Replit deployment to ensure port forwarding works
if PORT != "5000":
    print(f"⚠️ WARNING: PORT is set to {PORT}, but Replit requires port 5000.")
    print("⚠️ Overriding to PORT=5000 to ensure external port 80 mapping works.")
    PORT = "5000"
    os.environ["PORT"] = PORT
    
bind = f"0.0.0.0:{PORT}"

# Log the port being used to help with debugging
print(f"✅ Gunicorn binding to: 0.0.0.0:{PORT} (will forward to external port 80 in deployment)")

# Dynamic worker count based on CPU cores
workers = max(2, (os.cpu_count() or 1) * 2)

# Use 2 threads per worker for handling concurrent requests
# This helps improve throughput when there are blocking I/O operations
threads = 2

# Timeout for worker processes (60 seconds)
# This prevents workers from hanging indefinitely
timeout = 60

# Access log configuration
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"

# Preload the application to save memory
preload_app = True

# Recommended settings for Replit environments
worker_class = "sync"  # Use sync workers since we have threading enabled
worker_connections = 1000
max_requests = 1000  # Restart workers after handling this many requests
max_requests_jitter = 100  # Add jitter to avoid all workers restarting at once

# Process naming
proc_name = "proletto_gunicorn"

# Security settings
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
"""
        with open(config_path, 'w') as f:
            f.write(content)
        logger.info("✅ Created gunicorn_config.py")
        return True
    
    config_updated = False
    
    # Read the file
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Check for proper port binding
    port_fixed = False
    if 'PORT = os.getenv("PORT", "5000")' not in content:
        # Try to fix the PORT assignment
        port_pattern = re.compile(r'PORT\s*=\s*os\.getenv\([\'"]PORT[\'"],\s*[\'"](\d+)[\'"]\)')
        if port_pattern.search(content):
            content = port_pattern.sub('PORT = os.getenv("PORT", "5000")', content)
            port_fixed = True
            config_updated = True
    
    # Check for force port to 5000 logic
    if 'Force port to 5000' not in content and 'if PORT != "5000":' not in content:
        # Add the force port section
        force_port_code = """
# Force port to 5000 for Replit deployment to ensure port forwarding works
if PORT != "5000":
    print(f"⚠️ WARNING: PORT is set to {PORT}, but Replit requires port 5000.")
    print("⚠️ Overriding to PORT=5000 to ensure external port 80 mapping works.")
    PORT = "5000"
    os.environ["PORT"] = PORT
    """
        
        # Find a good place to insert it
        if 'PORT = os.getenv' in content:
            content = content.replace(
                'PORT = os.getenv',
                'PORT = os.getenv'
            )
            # Insert after the PORT line
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'PORT = os.getenv' in line:
                    lines.insert(i+1, force_port_code)
                    content = '\n'.join(lines)
                    break
            config_updated = True
    
    # Make sure binding is correct
    if 'bind = f"0.0.0.0:{PORT}"' not in content:
        bind_pattern = re.compile(r'bind\s*=.*')
        if bind_pattern.search(content):
            content = bind_pattern.sub('bind = f"0.0.0.0:{PORT}"', content)
            config_updated = True
    
    if config_updated:
        with open(config_path, 'w') as f:
            f.write(content)
        logger.info("✅ Updated gunicorn_config.py")
    else:
        logger.info("✓ No changes needed to gunicorn_config.py")
    
    return config_updated

def fix_env_vars_script():
    """Fix fix_env_vars.py script to ensure it sets PORT=5000."""
    env_vars_path = 'fix_env_vars.py'
    
    if not os.path.exists(env_vars_path):
        logger.warning("⚠️ fix_env_vars.py file not found")
        return False
    
    # Read the file
    with open(env_vars_path, 'r') as f:
        content = f.read()
    
    env_vars_updated = False
    
    # Check for set_prod_env function and PORT setting
    if 'def set_prod_env():' in content and 'PORT' not in content:
        if 'os.environ[\'REPLIT_DEPLOYMENT\'] = \'1\'' in content:
            content = content.replace(
                'os.environ[\'REPLIT_DEPLOYMENT\'] = \'1\'',
                'os.environ[\'REPLIT_DEPLOYMENT\'] = \'1\'\n    \n    # Critical for Replit deployment: set PORT=5000 for correct port forwarding\n    os.environ[\'PORT\'] = \'5000\'\n    logger.info("Set PORT=5000 (critical for Replit deployment forwarding to port 80)")\n    print("export PORT=\'5000\'")'
            )
            env_vars_updated = True
            logger.info("✅ Added PORT=5000 to fix_env_vars.py")
    
    if env_vars_updated:
        with open(env_vars_path, 'w') as f:
            f.write(content)
        logger.info("✅ Updated fix_env_vars.py")
    else:
        logger.info("✓ No changes needed to fix_env_vars.py")
    
    return env_vars_updated

def main():
    """Main function."""
    print("===============================================")
    print("Proletto Deployment Port Configuration Fixer")
    print("===============================================")
    print("This script ensures proper port configuration for Replit deployment.")
    print()
    
    # Track if any changes were made
    changes_made = False
    
    # Make fixes
    changes_made |= fix_replit_config()
    changes_made |= fix_flask_deploy()
    changes_made |= create_deploy_replit()
    changes_made |= fix_gunicorn_config()
    changes_made |= fix_env_vars_script()
    
    # Summary
    print("\nSummary:")
    if changes_made:
        print("✅ Deployment configuration has been updated successfully.")
        print("✅ Your application should now correctly bind to port 5000 during deployment.")
        print("\nImportant Notes:")
        print("1. Port 5000 will be forwarded to external port 80 by Replit")
        print("2. Use ./deploy_replit.sh for the most reliable deployment")
        print("3. The .replit file has been updated to use the new deployment script")
    else:
        print("✓ No changes were necessary. Your deployment configuration looks good.")
    
    print("\nYou can now deploy your application through the Replit interface or by running:")
    print("./deploy_replit.sh")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())