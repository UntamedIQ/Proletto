"""
Proletto Initialization Script
This file explicitly identifies this as a Flask application for Replit
"""

import os
import sys
import json

# Application type identifier
APP_CONFIG = {
    "type": "flask",
    "framework": "flask",
    "main_file": "main.py",
    "port": int(os.environ.get("PORT", 3000)),
    "production_port": 80
}

def create_config_file():
    """Create a configuration file to identify this as a Flask app"""
    with open("replit.app.json", "w") as f:
        json.dump({
            "app_type": "flask",
            "entry_point": "main.py",
            "run_command": "python main.py",
            "port": 80,
            "dependencies": [
                "flask",
                "flask-sqlalchemy",
                "flask-login",
                "psycopg2-binary"
            ]
        }, f, indent=2)
    print("Created Replit app configuration file")

def check_requirements():
    """Check if requirements.txt exists and create if needed"""
    if not os.path.exists("requirements.txt"):
        if os.path.exists("requirements-deploy.txt"):
            os.system("cp requirements-deploy.txt requirements.txt")
            print("Created requirements.txt from requirements-deploy.txt")
        else:
            print("WARNING: No requirements.txt file found")
    
def main():
    """Main initialization function"""
    print("Initializing Proletto Flask application")
    create_config_file()
    check_requirements()
    print("Initialization complete")

if __name__ == "__main__":
    main()