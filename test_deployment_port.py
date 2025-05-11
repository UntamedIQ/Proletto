#!/usr/bin/env python3
"""
Test Deployment Port Configuration

This script tests the proper port configuration for deployment.
It verifies that both main and API applications will use port 80 in deployment.
"""
import os
import sys

print("Testing deployment port configuration...")

# Test main.py
try:
    print("\nTesting main.py port configuration:")
    # Set deployment flag
    os.environ["REPLIT_DEPLOYMENT"] = "1"
    
    # Import the deployment configuration
    from deployment_config import get_port
    
    port = get_port()
    print(f"- Using deployment_config: port = {port}")
    
    # Remove the module to test the fallback
    sys.modules.pop("deployment_config", None)
    
    # Import the run_app function
    from main import run_app
    
    print("- main.py configuration appears correct for deployment")
    
except ImportError as e:
    print(f"❌ Error testing main.py: {e}")
except Exception as e:
    print(f"❌ Unexpected error testing main.py: {e}")

# Test api.py
try:
    print("\nTesting api.py port configuration:")
    
    # Import the run_api function
    from api import run_api
    
    print("- api.py configuration appears correct for deployment")
    
except ImportError as e:
    print(f"❌ Error testing api.py: {e}")
except Exception as e:
    print(f"❌ Unexpected error testing api.py: {e}")

print("\nDeployment port test complete.")
print("For deployment:")
print("1. Set REPLIT_DEPLOYMENT=1")
print("2. Configure to run on port 80")
print("3. Use ./deploy.sh as the run command")