#!/bin/bash
# Proletto Flask Deployment Script
# This script sets up the necessary environment for deploying Proletto on Replit
# and starts the Flask application using Gunicorn WSGI server for production.

set -e  # Exit on error

echo "===== Proletto Flask Deployment Script ====="
echo "Setting up deployment environment..."

# Ensure this script is executable
chmod +x "$0"

# Verify Python 3 is available - try multiple commands to be robust
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    # Check if python is Python 3
    PY_VERSION=$(python --version 2>&1)
    if [[ $PY_VERSION == *"Python 3"* ]]; then
        PYTHON_CMD="python"
    else
        echo "❌ Python version 3 is required but found: $PY_VERSION"
        exit 1
    fi
else
    echo "❌ Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

echo "✅ Using Python command: $PYTHON_CMD ($(${PYTHON_CMD} --version 2>&1))"

# Verify Gunicorn is installed
if ! ${PYTHON_CMD} -c "import gunicorn" &> /dev/null; then
    echo "🔄 Gunicorn not found. Installing..."
    ${PYTHON_CMD} -m pip install gunicorn
fi

# Run any setup steps (migrations, env fixes, etc.)
echo "🔧 Running deployment setup..."
${PYTHON_CMD} setup_deployment.py

# Fix environment variables
echo "🔧 Sourcing environment variables..."
${PYTHON_CMD} fix_env_vars.py > env_vars.sh
chmod +x env_vars.sh
source ./env_vars.sh

# Production Flask settings
export FLASK_ENV=production
export FLASK_APP=main.py
export PORT=5000

# Explicitly log PORT setting for debugging
echo "📣 Setting PORT=$PORT for deployment (will forward to external port 80)"

# Test Redis connection if URL is provided
if [ -n "$REDIS_URL" ]; then
    echo "🔍 Testing Redis connection..."
    REDIS_TEST=$(${PYTHON_CMD} - << 'EOF'
import redis, os, sys
url = os.getenv("REDIS_URL")
try:
    r = redis.from_url(url, decode_responses=True)
    r.ping()
    sys.stdout.write("SUCCESS")
except redis.exceptions.AuthenticationError:
    sys.stdout.write("AUTH_REQUIRED")
except Exception as e:
    sys.stdout.write(f"ERROR:{e}")
EOF
)
    case "$REDIS_TEST" in
        SUCCESS)
            echo "✅ Redis connection successful."
            ;;
        AUTH_REQUIRED)
            echo "⚠️ Redis requires authentication—falling back to SimpleCache."
            ;;
        ERROR:*)
            echo "⚠️ Redis error (${REDIS_TEST#ERROR:})—falling back to SimpleCache."
            ;;
    esac
else
    echo "⚠️ REDIS_URL not set—using in-memory SimpleCache."
fi

# In production, Replit will provide $PORT (should be 5000 for local→80 mapping)
echo "📋 Starting Gunicorn on port ${PORT:-5000}..."

# Launch Gunicorn
if [ -f "gunicorn_config.py" ]; then
    # With config file, PORT will be read from environment by gunicorn_config.py
    exec gunicorn -c gunicorn_config.py main:app
else
    # Fallback: bind directly to the PORT provided by Replit, or 5000 if not set
    echo "⚠️ gunicorn_config.py not found. Using command line parameters."
    exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 4 --threads 2 --timeout 60 main:app
fi

