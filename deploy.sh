#!/bin/bash

# Proletto Deployment Script
# This script prepares the environment for deployment

# Set deployment flag
export REPLIT_DEPLOYMENT=1

# Set production environment
export FLASK_ENV=production
export FLASK_DEBUG=0

# Disable debug mode
export DEBUG=False

# Ensure we use port 80 for both main and API
export PORT=80
export API_PORT=80

echo "✅ Environment configured for deployment"
echo "🔍 Port set to 80 for both main app and API backend"

# Run the application
echo "🚀 Starting Proletto application"
python main.py