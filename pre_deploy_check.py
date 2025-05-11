#!/usr/bin/env python3
"""
Proletto Pre-Deployment Check Script

This script runs a series of checks before deployment to ensure the environment is
properly configured and the code is ready for deployment.

Usage:
  python pre_deploy_check.py [--env=<environment>]

Options:
  --env=<environment>    Target environment (development, staging, production)
                         [default: production]
"""

import os
import sys
import argparse
import logging
import importlib
import subprocess
from typing import Dict, List, Optional, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('pre-deploy')

# Color codes for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Pre-deployment checks for Proletto')
    parser.add_argument('--env', choices=['development', 'staging', 'production'],
                      default='production', help='Target environment')
    return parser.parse_args()

class DeploymentCheck:
    """Base class for deployment checks."""
    
    def __init__(self, environment: str):
        self.environment = environment
        self.status = {}
        
    def print_status(self, check_name: str, status: bool, warning: bool = False) -> bool:
        """Print the status of a check."""
        if status:
            logger.info(f"{GREEN}✓ {check_name} check passed{RESET}")
            return True
        elif warning:
            logger.warning(f"{YELLOW}⚠️ {check_name} check has warnings{RESET}")
            return True
        else:
            logger.error(f"{RED}✗ {check_name} check failed{RESET}")
            return False

    def log_check(self, check_key: str, status: bool) -> None:
        """Log a check result."""
        self.status[check_key] = status

    def run_all_checks(self) -> bool:
        """Run all checks."""
        raise NotImplementedError("Subclasses must implement run_all_checks()")

class ProlettoDeploy(DeploymentCheck):
    """Proletto deployment checks."""
    
    def __init__(self, environment: str):
        super().__init__(environment)
        logger.info(f"{BLUE}Running pre-deployment checks for {environment} environment{RESET}")
        
    def check_required_files(self) -> bool:
        """Check if all required files exist."""
        logger.info(f"{BLUE}Checking required files...{RESET}")
        
        required_files = [
            'main.py',
            'requirements.txt',
            'deploy_replit.sh',
            'flask_deploy.sh'
        ]
        
        # Environment-specific required files
        if self.environment == 'production':
            required_files.append('README.md')
            required_files.append('DEPLOYMENT_GUIDE.md')
            
        missing_files = [f for f in required_files if not os.path.exists(f)]
        
        if missing_files:
            logger.error(f"{RED}Missing required files: {', '.join(missing_files)}{RESET}")
            self.log_check("required_files", False)
            return False
            
        logger.info(f"{GREEN}All required files are present{RESET}")
        self.log_check("required_files", True)
        return True
    
    def check_python_imports(self) -> bool:
        """Check if all required Python modules can be imported."""
        logger.info(f"{BLUE}Checking Python imports...{RESET}")
        
        core_modules = [
            'flask',
            'sqlalchemy',
            'gunicorn'
        ]
        
        if self.environment in ['staging', 'production']:
            core_modules.extend([
                'redis',
                'stripe',
                'sendgrid'
            ])
            
        missing_modules = []
        for module in core_modules:
            try:
                importlib.import_module(module)
            except ImportError:
                missing_modules.append(module)
                
        if missing_modules:
            logger.error(f"{RED}Missing required Python modules: {', '.join(missing_modules)}{RESET}")
            logger.error(f"{YELLOW}Try running: pip install -r requirements.txt{RESET}")
            self.log_check("python_imports", False)
            return False
            
        logger.info(f"{GREEN}All required Python modules are available{RESET}")
        self.log_check("python_imports", True)
        return True
    
    def check_environment_variables(self) -> bool:
        """Check if required environment variables are set."""
        logger.info(f"{BLUE}Checking environment variables...{RESET}")
        
        # Base required variables
        required_vars = [
            'FLASK_SECRET_KEY'
        ]
        
        # Environment-specific variables
        if self.environment == 'development':
            pass  # Development might use defaults or SQLite
        else:
            required_vars.extend([
                'DATABASE_URL',
                'REDIS_URL'
            ])
            
        if self.environment == 'production':
            required_vars.extend([
                'STRIPE_SECRET_KEY',
                'STRIPE_PUBLIC_KEY',
                'SENDGRID_API_KEY'
            ])
            
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        # Special case: For CI/CD we might get secrets at runtime
        if len(sys.argv) > 1 and "--ci" in sys.argv:
            if missing_vars:
                logger.warning(f"{YELLOW}⚠️ Some variables missing, but running in CI mode. They should be provided by CI secrets.{RESET}")
                self.log_check("environment_variables", True)
                return True
            
        if missing_vars:
            logger.error(f"{RED}Missing required environment variables: {', '.join(missing_vars)}{RESET}")
            self.log_check("environment_variables", False)
            return False
            
        logger.info(f"{GREEN}All required environment variables are set{RESET}")
        self.log_check("environment_variables", True)
        return True
    
    def check_deployment_scripts(self) -> bool:
        """Check if deployment scripts are executable."""
        logger.info(f"{BLUE}Checking deployment scripts...{RESET}")
        
        deployment_scripts = [
            'deploy_replit.sh',
            'flask_deploy.sh'
        ]
        
        if self.environment == 'production':
            deployment_scripts.append('deploy.sh')
            
        non_executable = []
        for script in deployment_scripts:
            if os.path.exists(script) and not os.access(script, os.X_OK):
                non_executable.append(script)
                
        if non_executable:
            logger.warning(f"{YELLOW}⚠️ Some scripts are not executable: {', '.join(non_executable)}{RESET}")
            logger.warning(f"{YELLOW}Running: chmod +x {' '.join(non_executable)}{RESET}")
            
            for script in non_executable:
                os.chmod(script, 0o755)
                
            logger.info(f"{GREEN}Made scripts executable{RESET}")
            
        logger.info(f"{GREEN}All deployment scripts are executable{RESET}")
        self.log_check("deployment_scripts", True)
        return True
    
    def check_database_connection(self) -> bool:
        """Check if database connection is working."""
        logger.info(f"{BLUE}Checking database connection...{RESET}")
        
        # Skip for development environment or CI environment
        if self.environment == 'development' or (len(sys.argv) > 1 and "--ci" in sys.argv):
            logger.info(f"{YELLOW}⚠️ Skipping database connection check for {self.environment} environment{RESET}")
            self.log_check("database_connection", True)
            return True
            
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            logger.warning(f"{YELLOW}⚠️ DATABASE_URL not set, skipping database connection check{RESET}")
            self.log_check("database_connection", True)
            return True
            
        try:
            # Check if we can connect to the database
            if 'postgresql' in db_url:
                try:
                    import psycopg2
                    conn = psycopg2.connect(db_url)
                    conn.close()
                    logger.info(f"{GREEN}PostgreSQL database connection successful{RESET}")
                except ImportError:
                    logger.warning(f"{YELLOW}⚠️ psycopg2 not installed, skipping database connection check{RESET}")
                except Exception as e:
                    logger.error(f"{RED}PostgreSQL database connection failed: {str(e)}{RESET}")
                    self.log_check("database_connection", False)
                    return False
            elif 'sqlite' in db_url:
                try:
                    import sqlite3
                    db_path = db_url.replace('sqlite:///', '')
                    conn = sqlite3.connect(db_path)
                    conn.close()
                    logger.info(f"{GREEN}SQLite database connection successful{RESET}")
                except Exception as e:
                    logger.error(f"{RED}SQLite database connection failed: {str(e)}{RESET}")
                    self.log_check("database_connection", False)
                    return False
            else:
                logger.warning(f"{YELLOW}⚠️ Unsupported database type in DATABASE_URL, skipping connection check{RESET}")
                
            self.log_check("database_connection", True)
            return True
        except Exception as e:
            logger.error(f"{RED}Database connection check failed with unexpected error: {str(e)}{RESET}")
            self.log_check("database_connection", False)
            return False
    
    def check_redis_connection(self) -> bool:
        """Check if Redis connection is working."""
        logger.info(f"{BLUE}Checking Redis connection...{RESET}")
        
        # Skip for development environment or CI environment
        if self.environment == 'development' or (len(sys.argv) > 1 and "--ci" in sys.argv):
            logger.info(f"{YELLOW}⚠️ Skipping Redis connection check for {self.environment} environment{RESET}")
            self.log_check("redis_connection", True)
            return True
            
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            logger.warning(f"{YELLOW}⚠️ REDIS_URL not set, skipping Redis connection check{RESET}")
            logger.warning(f"{YELLOW}The app will use SimpleCache as a fallback.{RESET}")
            self.log_check("redis_connection", True)
            return True
            
        try:
            import redis
            r = redis.from_url(redis_url)
            r.ping()
            logger.info(f"{GREEN}Redis connection successful{RESET}")
            self.log_check("redis_connection", True)
            return True
        except ImportError:
            logger.warning(f"{YELLOW}⚠️ redis package not installed, skipping Redis connection check{RESET}")
            self.log_check("redis_connection", True)
            return True
        except Exception as e:
            logger.warning(f"{YELLOW}⚠️ Redis connection failed: {str(e)}{RESET}")
            logger.warning(f"{YELLOW}The app will use SimpleCache as a fallback.{RESET}")
            self.log_check("redis_connection", True)  # Not critical, app can use SimpleCache
            return True
    
    def run_all_checks(self) -> bool:
        """Run all deployment checks."""
        checks = [
            self.check_required_files,
            self.check_python_imports,
            self.check_environment_variables,
            self.check_deployment_scripts,
            self.check_database_connection,
            self.check_redis_connection
        ]
        
        results = []
        for check in checks:
            results.append(check())
            
        # Print overall status
        if all(results):
            logger.info(f"{GREEN}========================================{RESET}")
            logger.info(f"{GREEN}✓ All pre-deployment checks passed!{RESET}")
            logger.info(f"{GREEN}Ready to deploy to {self.environment} environment{RESET}")
            logger.info(f"{GREEN}========================================{RESET}")
            return True
        else:
            logger.error(f"{RED}========================================{RESET}")
            logger.error(f"{RED}✗ Some pre-deployment checks failed!{RESET}")
            logger.error(f"{RED}Please fix the issues before deploying{RESET}")
            logger.error(f"{RED}========================================{RESET}")
            return False

def main():
    """Main entry point."""
    args = parse_args()
    checker = ProlettoDeploy(args.env)
    success = checker.run_all_checks()
    
    if not success:
        sys.exit(1)
        
if __name__ == '__main__':
    main()