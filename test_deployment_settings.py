#!/usr/bin/env python3
"""
Test script for Proletto deployment settings.

This script tests whether the deployment configuration correctly 
detects the environment and sets the appropriate port.
"""

import os
from deployment_config import setup_deployment_env, get_port


def test_deployment_settings():
    """Test the deployment settings in various configurations."""
    
    print("=== Proletto Deployment Settings Test ===\n")
    
    # Test with REPLIT_DEPLOYMENT=1
    original_env = os.environ.get('REPLIT_DEPLOYMENT')
    try:
        # Set deployment environment
        os.environ['REPLIT_DEPLOYMENT'] = '1'
        
        # Get deployment info
        port = get_port()
        flask_env = os.environ.get('FLASK_ENV')
        flask_debug = os.environ.get('FLASK_DEBUG')
        debug = os.environ.get('DEBUG')
        port_var = os.environ.get('PORT')
        api_port = os.environ.get('API_PORT')
        
        print("Testing with REPLIT_DEPLOYMENT=1:")
        print(f"- Port: {port}")
        print(f"- FLASK_ENV: {flask_env}")
        print(f"- FLASK_DEBUG: {flask_debug}")
        print(f"- DEBUG: {debug}")
        print(f"- PORT: {port_var}")
        print(f"- API_PORT: {api_port}")
        
        # Check if port is correctly set to 80 for deployment
        if port == 80:
            print("✅ Deployment configuration loaded correctly.\n")
        else:
            print("❌ Deployment configuration failed. Expected port 80, got {port}.\n")
            
        # Test without REPLIT_DEPLOYMENT
        if original_env:
            os.environ['REPLIT_DEPLOYMENT'] = original_env
        else:
            del os.environ['REPLIT_DEPLOYMENT']
            
        # Get development port
        port = get_port()
        print("Testing without REPLIT_DEPLOYMENT:")
        print(f"- Port: {port}")
        
        # Check if port is correctly set to 5000 for development
        if port == 5000:
            print("✅ Development configuration loaded correctly.\n")
        else:
            print(f"❌ Development configuration failed. Expected port 5000, got {port}.\n")
            
    finally:
        # Restore original environment
        if original_env:
            os.environ['REPLIT_DEPLOYMENT'] = original_env
        elif 'REPLIT_DEPLOYMENT' in os.environ:
            del os.environ['REPLIT_DEPLOYMENT']
            
    print("=== Deployment Settings Test Complete ===")


if __name__ == "__main__":
    test_deployment_settings()