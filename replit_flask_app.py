#!/usr/bin/env python
"""
Proletto Replit Flask Deployment Helper
This file exists specifically to help Replit identify this as a Flask application

To deploy:
1. Run this file to verify configuration
2. Use the "Deploy" button in Replit
"""

import os
import sys
import importlib.util
import subprocess

def check_environment():
    """Check if the environment is properly set up for Flask deployment"""
    print("Proletto Flask Application Deployment Helper")
    print("============================================")
    
    # Check Python version
    print(f"Python version: {sys.version}")
    
    # Check Flask
    try:
        import flask
        print(f"Flask version: {flask.__version__}")
    except ImportError:
        print("Flask is not installed. This might cause deployment issues.")
    
    # Check Flask-Login
    try:
        import flask_login
        print(f"Flask-Login version: {flask_login.__version__}")
    except ImportError:
        print("Flask-Login is not installed. This is required for authentication.")
        
    # Check main.py
    if os.path.exists("main.py"):
        print(f"Found main.py: {os.path.abspath('main.py')}")
        
        # Import the file as a module to check for Flask app
        try:
            spec = importlib.util.spec_from_file_location("main", "main.py")
            main_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(main_module)
            
            # Check for a Flask app
            if hasattr(main_module, 'app'):
                print("Found Flask app in main.py")
            else:
                print("WARNING: No Flask app found in main.py")
        except Exception as e:
            print(f"Error importing main.py: {e}")
    else:
        print("ERROR: main.py not found. This is required for Flask deployment.")
    
    # Check for .htaccess
    if os.path.exists(".htaccess"):
        print("WARNING: .htaccess exists, which might be causing static HTML configuration.")
        print("Consider removing it for Flask deployment.")
    
    # Check deployed port
    print(f"PORT environment variable: {os.environ.get('PORT', 'Not set (default: 3000)')}")
    
    # Additional checks
    check_port_bindings()
    
    print("\nDeployment Recommendation:")
    print("1. Ensure there is no .htaccess file (rename or remove it)")
    print("2. Make sure the Flask app in main.py binds to 0.0.0.0 and PORT env var")
    print("3. Use the Replit 'Deploy' button in the interface")

def check_port_bindings():
    """Check if any port bindings might conflict"""
    print("\nChecking port bindings:")
    
    try:
        result = subprocess.run(['grep', '-r', 'app.run', '.', '--include="*.py"'], 
                               capture_output=True, text=True)
        
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                print(f"  - {line}")
        else:
            print("  No explicit port bindings found")
    except Exception as e:
        print(f"  Error checking port bindings: {e}")

if __name__ == "__main__":
    check_environment()
    print("\nIf everything looks good, deploy your Flask application using the Replit interface")