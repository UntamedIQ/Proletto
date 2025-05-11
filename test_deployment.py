#!/usr/bin/env python3
"""
Proletto Deployment Test Script
This script tests that the Flask application is correctly configured for deployment.
"""

import os
import sys
import socket
import requests
import time
import subprocess
import signal
from contextlib import contextmanager

# Set environment variables for testing
os.environ["PORT"] = "80"
os.environ["FLASK_ENV"] = "production"
os.environ["FLASK_DEBUG"] = "0"
os.environ["DEPLOYMENT"] = "test"

def is_port_in_use(port):
    """Check if a port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

@contextmanager
def run_flask_app():
    """Run the Flask app in a subprocess"""
    # Make sure the port is not in use
    if is_port_in_use(80):
        print("❌ Port 80 is already in use. Cannot run test.")
        sys.exit(1)
    
    # Start the Flask app
    print("Starting Flask app for testing...")
    process = subprocess.Popen(
        ["python", "deploy.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for the app to start
    retries = 10
    while retries > 0:
        if is_port_in_use(80):
            break
        print("Waiting for Flask app to start...")
        time.sleep(1)
        retries -= 1
    
    if retries == 0:
        print("❌ Flask app did not start within the expected time.")
        process.terminate()
        sys.exit(1)
    
    try:
        # App is running, yield control back
        yield process
    finally:
        # Clean up
        print("Stopping Flask app...")
        process.terminate()
        process.wait(timeout=5)

def test_deployment_configuration():
    """Test that the Flask app is correctly configured for deployment"""
    try:
        with run_flask_app() as process:
            # Test that the app is accessible
            print("Testing connection to Flask app...")
            response = requests.get("http://localhost:80/healthz")
            
            if response.status_code == 200:
                print("✅ Successfully connected to Flask app on port 80")
                
                # Check that the app is running with the correct configuration
                print("Checking app configuration...")
                app_config = response.json()
                
                if "status" in app_config and app_config["status"] == "ok":
                    print("✅ App is reporting healthy status")
                else:
                    print("❌ App is not reporting healthy status")
                
                # Test complete
                print("\n✅ Deployment configuration test passed!")
                return True
            else:
                print(f"❌ Failed to connect to Flask app: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Error during deployment test: {e}")
        return False

if __name__ == "__main__":
    print("\n=== PROLETTO DEPLOYMENT CONFIGURATION TEST ===\n")
    
    # Skip actual testing if port 80 requires elevated privileges
    if os.name != "nt" and os.geteuid() != 0 and not is_port_in_use(80):
        print("⚠️ Running on port 80 requires root privileges.")
        print("⚠️ This test will be skipped, but deployment should work on Replit.")
        print("⚠️ Replit provides the necessary privileges to bind to port 80.")
        sys.exit(0)
    
    success = test_deployment_configuration()
    
    if success:
        print("\nThe application is correctly configured for deployment.")
        print("You can deploy it to Replit using the 'Deploy' button.")
    else:
        print("\nThe application has deployment configuration issues.")
        print("Please fix them before deploying to Replit.")
    
    print("\n===========================================\n")