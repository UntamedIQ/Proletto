#!/usr/bin/env python3
"""
Setup script for deploying Proletto on Replit.

This script configures the environment variables needed for deploying
the Proletto application on Replit, and performs essential checks 
to ensure a successful deployment.
"""

import os
import sys
import logging
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("proletto-deploy")

def check_environment_variables():
    """Check if all required environment variables are set."""
    required_variables = [
        "DATABASE_URL",
        "FLASK_SECRET_KEY",
        "API_KEY"
    ]
    
    recommended_variables = [
        "REDIS_URL",
        "STRIPE_SECRET_KEY",
        "STRIPE_PUBLIC_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "SENDGRID_API_KEY",
        "SENDGRID_FROM_EMAIL",
        "GOOGLE_OAUTH_CLIENT_ID",
        "GOOGLE_OAUTH_CLIENT_SECRET"
    ]
    
    missing_required = []
    missing_recommended = []
    
    for var in required_variables:
        if not os.environ.get(var):
            missing_required.append(var)
    
    for var in recommended_variables:
        if not os.environ.get(var):
            missing_recommended.append(var)
    
    if missing_required:
        logger.error("The following required environment variables are missing:")
        for var in missing_required:
            logger.error(f"  - {var}")
        return False
    
    if missing_recommended:
        logger.warning("The following recommended environment variables are missing:")
        for var in missing_recommended:
            logger.warning(f"  - {var}")
    
    logger.info("All required environment variables are set.")
    return True

def check_database_connection():
    """Check if the database connection is valid."""
    try:
        import psycopg2
        
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            logger.error("DATABASE_URL environment variable is not set.")
            return False
        
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        
        logger.info("Database connection is valid.")
        return True
    except ImportError:
        logger.error("psycopg2 is not installed. Cannot check database connection.")
        return False
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        return False

def check_redis_connection():
    """Check if the Redis connection is valid."""
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        logger.warning("REDIS_URL environment variable is not set. Using SimpleCache instead.")
        return True
    
    try:
        import redis
        
        r = redis.from_url(redis_url)
        r.ping()
        
        logger.info("Redis connection is valid.")
        return True
    except ImportError:
        logger.error("redis-py is not installed. Cannot check Redis connection.")
        return False
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {str(e)}")
        logger.warning("Falling back to SimpleCache.")
        return True

def normalize_environment_variables():
    """Normalize environment variables to expected formats."""
    # Format REDIS_URL to include proper protocol prefix if needed
    if 'REDIS_URL' in os.environ:
        redis_url = os.environ['REDIS_URL']
        if redis_url and not (redis_url.startswith('redis://') or 
                             redis_url.startswith('rediss://') or 
                             redis_url.startswith('unix://')):
            os.environ['REDIS_URL'] = f"redis://{redis_url}"
            logger.info(f"Normalized REDIS_URL to include redis:// prefix: {os.environ['REDIS_URL']}")
    
    # Make sure Stripe keys are properly formatted
    for key in ['STRIPE_SECRET_KEY', 'STRIPE_PUBLIC_KEY', 'STRIPE_WEBHOOK_SECRET']:
        if key in os.environ and os.environ[key]:
            # Remove any whitespace that might have been added
            os.environ[key] = os.environ[key].strip()
            logger.info(f"Normalized {key} format")
    
    # Set FLASK_ENV for production
    os.environ['FLASK_ENV'] = 'production'
    logger.info("FLASK_ENV set to production for deployment")
    
    return True

def setup_deployment_env():
    """Set up environment for deployment."""
    # Set REPLIT_DEPLOYMENT environment variable
    os.environ["REPLIT_DEPLOYMENT"] = "1"
    logger.info("REPLIT_DEPLOYMENT environment variable set to 1.")
    
    # Note: We don't set PORT explicitly, as Replit will provide the correct port
    # This allows Replit to control port assignment for proper external mapping
    logger.info("Using Replit-provided PORT environment variable for deployment.")
    
    # Check for previous deployment
    deployment_flag = Path(".deployment_flag")
    if deployment_flag.exists():
        logger.info("Previous deployment found. Updating deployment.")
    else:
        logger.info("First-time deployment. Creating deployment flag.")
        deployment_flag.touch()
        
    # Normalize environment variables
    normalize_environment_variables()
    
    return True

def main():
    """Main function to set up deployment environment."""
    logger.info("Setting up Proletto deployment environment...")
    
    # Set up deployment environment
    setup_deployment_env()
    
    # Check environment variables
    if not check_environment_variables():
        logger.error("Deployment setup failed: Missing required environment variables.")
        sys.exit(1)
    
    # Check database connection
    if not check_database_connection():
        logger.error("Deployment setup failed: Invalid database connection.")
        sys.exit(1)
    
    # Check Redis connection
    check_redis_connection()
    
    # Set executable permissions for deployment scripts
    try:
        subprocess.run(["chmod", "+x", "deploy.sh"], check=True)
        subprocess.run(["chmod", "+x", "flask_deploy.sh"], check=True)
        logger.info("Set executable permissions for deployment scripts.")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to set executable permissions: {str(e)}")
    
    logger.info("Proletto deployment environment setup complete.")
    logger.info("You can now run the application with the following command:")
    logger.info("  ./flask_deploy.sh")
    
    # Try to restart workflow in Replit environment
    try:
        from replit import db
        logger.info("Replit environment detected. Restarting workflow...")
        subprocess.run(["kill", "-HUP", "1"], check=False)
    except ImportError:
        logger.info("Not running in Replit environment. Manual restart required.")

if __name__ == "__main__":
    main()