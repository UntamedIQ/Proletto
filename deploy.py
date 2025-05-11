#!/usr/bin/env python3
"""
Proletto Deployment Helper Script
This script prepares the environment for deployment and starts the Flask application
"""

import os
import sys
import subprocess
import shutil
import importlib.util

# Set up environment for deployment
os.environ["PORT"] = "80"  # Production port
os.environ["FLASK_ENV"] = "production"
os.environ["FLASK_DEBUG"] = "0"
os.environ["DEPLOYMENT"] = "true"

# Copy requirements file if it doesn't exist
if not os.path.exists("requirements.txt"):
    if os.path.exists("requirements-deploy.txt"):
        shutil.copy("requirements-deploy.txt", "requirements.txt")
        print("Created requirements.txt from requirements-deploy.txt")

# Print Python version information
print(f"Python version: {sys.version}")
print(f"Python path: {sys.executable}")

# Print deployment information
print("======== DEPLOYMENT INFORMATION ========")
print(f"Port: {os.environ.get('PORT', '(not set)')}")
print(f"FLASK_ENV: {os.environ.get('FLASK_ENV', '(not set)')}")
print(f"FLASK_DEBUG: {os.environ.get('FLASK_DEBUG', '(not set)')}")
print("========================================")

# Import and run the Flask application programmatically
print("Starting Flask application on port 80...")

# Import main module
spec = importlib.util.spec_from_file_location("main", "main.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

# Run the application with our deployment settings
if hasattr(main, "run_app"):
    main.run_app()
else:
    # Fallback in case run_app is not defined
    print("WARNING: run_app function not found, using direct app.run()")
    if hasattr(main, "app"):
        main.app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 80)), debug=False)
    else:
        print("ERROR: Could not find Flask app instance")
        sys.exit(1)