"""
Proletto Deployment Configuration

This module provides functions to detect whether the application is running in
a deployment environment and sets the necessary environment variables.
"""
import os
import logging

logger = logging.getLogger(__name__)

def setup_deployment_env():
    """
    Set up environment variables for deployment.
    
    This function detects if the application is running in a Replit deployment
    environment and sets the appropriate environment variables.
    """
    # Check if running in Replit deployment
    is_replit = os.environ.get("REPLIT_DB_URL") is not None
    is_deployment = os.environ.get("REPLIT_DEPLOYMENT") == "1"
    
    # If running in Replit but REPLIT_DEPLOYMENT isn't set, set it
    if is_replit and not is_deployment:
        os.environ["REPLIT_DEPLOYMENT"] = "1"
        logger.info("REPLIT_DEPLOYMENT environment variable set to 1")
        
    # Get domain information for proper CORS configuration
    domain = os.environ.get("REPLIT_SLUG") or os.environ.get("REPLIT_APP_NAME")
    if domain:
        # Ensure CORS is set for this domain
        logger.info(f"Running on Replit domain: {domain}")
        
    return {
        "is_replit": is_replit,
        "is_deployment": is_deployment,  # Only use explicit deployment flag
        "domain": domain
    }

def get_port():
    """
    Determine the correct port to use based on environment.
    
    Returns:
        int: Port number to use (80 for deployments, environment PORT or 5000 for development)
    """
    deployment_info = setup_deployment_env()
    
    # If PORT is explicitly set in the environment, use that value
    if "PORT" in os.environ:
        port_str = os.environ.get("PORT", "80")
        port = int(port_str)
        logger.info(f"Using explicitly set PORT from environment: {port}")
        return port
    # Otherwise use 80 for deployments or 5000 for development
    elif deployment_info["is_deployment"]:
        logger.info("Deployment environment detected, using port 80")
        return 80
    else:
        logger.info("Development environment detected, using port 5000")
        return 5000