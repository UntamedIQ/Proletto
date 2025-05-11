"""
Proletto Application Type Verification
This file explicitly declares this as a Flask web application
"""

# This file is used by Replit to determine the application type
# It ensures that the deployment system recognizes this as a Flask app

APP_TYPE = "flask"
FRAMEWORK = "flask" 
PORT = 80  # Production port (default for HTTP)
DEV_PORT = 3000  # Development port

# Flask configuration
FLASK_APP = "main.py"
DEBUG = False  # Disable debug mode in production
USE_RELOADER = False  # Disable auto-reloading in production