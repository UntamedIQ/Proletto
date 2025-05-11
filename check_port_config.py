#!/usr/bin/env python3
"""
Proletto Deployment Port Configuration Checker

This script checks and validates that the application is properly configured
to listen on port 5000, which is essential for Replit deployments.
"""

import os
import sys
import logging
import subprocess
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("port-checker")

def check_env_var():
    """Check if PORT environment variable is set correctly."""
    port_var = os.environ.get('PORT')
    if not port_var:
        logger.warning("❌ PORT environment variable is not set")
        print("Setting PORT=5000 now...")
        os.environ['PORT'] = '5000'
        return False
    elif port_var != '5000':
        logger.warning(f"❌ PORT is set to {port_var}, but Replit requires port 5000")
        print(f"Changing PORT from {port_var} to 5000...")
        os.environ['PORT'] = '5000'
        return False
    else:
        logger.info("✅ PORT environment variable is correctly set to 5000")
        return True

def check_gunicorn_config():
    """Check if gunicorn_config.py is properly configured."""
    if not os.path.exists('gunicorn_config.py'):
        logger.warning("❌ gunicorn_config.py file does not exist")
        return False
    
    with open('gunicorn_config.py', 'r') as f:
        content = f.read()
    
    # Check for port binding
    if 'bind = f"0.0.0.0:{PORT}"' in content:
        logger.info("✅ gunicorn_config.py contains proper port binding")
        
        # Check for PORT variable assignment
        port_match = re.search(r'PORT\s*=\s*os\.getenv\([\'"]PORT[\'"],\s*[\'"](\d+)[\'"]\)', content)
        if port_match:
            default_port = port_match.group(1)
            if default_port == '5000':
                logger.info("✅ gunicorn_config.py sets default PORT to 5000")
                return True
            else:
                logger.warning(f"❌ gunicorn_config.py sets default PORT to {default_port}, not 5000")
                return False
        else:
            logger.warning("❌ Could not find PORT variable assignment in gunicorn_config.py")
            return False
    else:
        logger.warning("❌ gunicorn_config.py does not contain proper port binding")
        return False

def check_deployment_script():
    """Check if flask_deploy.sh contains proper port setting."""
    if not os.path.exists('flask_deploy.sh'):
        logger.warning("❌ flask_deploy.sh file does not exist")
        return False
    
    with open('flask_deploy.sh', 'r') as f:
        content = f.read()
    
    if 'export PORT=5000' in content:
        logger.info("✅ flask_deploy.sh explicitly sets PORT=5000")
        return True
    else:
        logger.warning("❌ flask_deploy.sh does not explicitly set PORT=5000")
        return False

def check_replit_config():
    """Check if .replit file has correct port configuration."""
    if not os.path.exists('.replit'):
        logger.warning("❌ .replit file does not exist")
        return False
    
    with open('.replit', 'r') as f:
        content = f.read()
    
    # Check for port mapping
    if re.search(r'localPort\s*=\s*5000', content) and re.search(r'externalPort\s*=\s*80', content):
        logger.info("✅ .replit file maps port 5000 to external port 80")
        
        # Check for waitForPort in deploy workflow
        if re.search(r'name\s*=\s*"Deploy Proletto".*?waitForPort\s*=\s*5000', content, re.DOTALL):
            logger.info("✅ .replit deploy workflow correctly waits for port 5000")
            return True
        else:
            logger.warning("❌ .replit deploy workflow does not wait for port 5000")
            return False
    else:
        logger.warning("❌ .replit file does not map port 5000 to external port 80")
        return False

def main():
    """Main function to check port configuration."""
    print("===============================================")
    print("Proletto Deployment Port Configuration Checker")
    print("===============================================")
    
    # Perform checks
    env_check = check_env_var()
    gunicorn_check = check_gunicorn_config()
    deploy_script_check = check_deployment_script()
    replit_check = check_replit_config()
    
    # Count passed checks
    checks_passed = sum([env_check, gunicorn_check, deploy_script_check, replit_check])
    
    print("\nSummary:")
    print(f"✅ Environment variable check: {'PASSED' if env_check else 'FAILED'}")
    print(f"✅ Gunicorn config check: {'PASSED' if gunicorn_check else 'FAILED'}")
    print(f"✅ Deployment script check: {'PASSED' if deploy_script_check else 'FAILED'}")
    print(f"✅ Replit config check: {'PASSED' if replit_check else 'FAILED'}")
    print(f"\nOverall result: {checks_passed}/4 checks passed")
    
    if checks_passed == 4:
        print("\n✅ All port configuration checks passed! Your app should bind correctly to port 5000.")
        print("   Replit will forward this to external port 80 for production deployment.")
        return True
    else:
        print("\n⚠️ Some port configuration checks failed. Please fix the issues mentioned above.")
        print("   For Replit deployments, your app MUST bind to port 5000.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)