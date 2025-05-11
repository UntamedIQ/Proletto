#!/bin/bash
# Enhanced Replit Deployment Script for Proletto
# This script is specifically designed to ensure proper port binding for Replit deployments
# Supports multiple environments (development, staging, production)

set -e  # Exit on error

# Parse command line arguments
ENVIRONMENT="production"  # Default to production

while [ "$#" -gt 0 ]; do
  case "$1" in
    --env=*)
      ENVIRONMENT="${1#*=}"
      ;;
    --staging)
      ENVIRONMENT="staging"
      ;;
    --development)
      ENVIRONMENT="development"
      ;;
    *)
      echo "Unknown parameter: $1"
      exit 1
      ;;
  esac
  shift
done

echo "===== Proletto Replit Deployment Script ====="
echo "Setting up deployment environment: $ENVIRONMENT"
echo "Setting up proper port binding..."

# CRITICAL: Set PORT environment variable explicitly
# This is required for Replit deployments to work properly
export PORT=5000
echo "PORT=$PORT"

# Ensure all scripts are executable
chmod +x *.sh 2>/dev/null || true
chmod +x *.py 2>/dev/null || true

# Configure environment
export FLASK_APP=main.py
export REPLIT_DEPLOYMENT=1

case "$ENVIRONMENT" in
  production)
    export FLASK_ENV=production
    export PROLETTO_ENV=production
    echo "🚀 Deploying to PRODUCTION environment"
    ;;
  staging)
    export FLASK_ENV=production  # Still use production Flask mode
    export PROLETTO_ENV=staging
    echo "🚀 Deploying to STAGING environment"
    ;;
  development)
    export FLASK_ENV=development
    export PROLETTO_ENV=development
    echo "🚀 Deploying to DEVELOPMENT environment"
    ;;
  *)
    echo "⚠️ Unknown environment: $ENVIRONMENT. Defaulting to production."
    export FLASK_ENV=production
    export PROLETTO_ENV=production
    ;;
esac

echo "📣 PORT=$PORT - This will be forwarded to external port 80"
echo "📣 FLASK_ENV=$FLASK_ENV"
echo "📣 PROLETTO_ENV=$PROLETTO_ENV"
echo "📣 FLASK_APP=$FLASK_APP"

# Load environment-specific settings if available
ENV_CONFIG_FILE=".env.$PROLETTO_ENV"
if [ -f "$ENV_CONFIG_FILE" ]; then
  echo "📣 Loading environment-specific settings from $ENV_CONFIG_FILE"
  # shellcheck disable=SC1090
  source "$ENV_CONFIG_FILE"
fi

# Load custom environment variables if available
ENV_VARS_FILE="env_vars.sh"
if [ -f "$ENV_VARS_FILE" ]; then
  echo "📣 Loading custom environment variables from $ENV_VARS_FILE"
  # shellcheck disable=SC1090
  source "$ENV_VARS_FILE"
fi

# Verify critical environment variables
echo "📣 Checking critical environment variables..."

# Check Google OAuth credentials
if [ -z "$GOOGLE_OAUTH_CLIENT_ID" ] || [ -z "$GOOGLE_OAUTH_CLIENT_SECRET" ]; then
  echo "⚠️ Warning: Google OAuth credentials not found in environment"
  
  # Try to find credentials file
  if [ -f "client_secret.json" ] || [ -f "credentials.json" ]; then
    echo "🔑 Google OAuth credentials file found"
  else
    echo "⚠️ Warning: Google OAuth credentials file not found"
    echo "🔍 Google OAuth login may not work properly"
  fi
else
  echo "✅ Google OAuth credentials found in environment"
fi

# Run pre-deployment tasks if needed
PRE_DEPLOY_SCRIPT="pre_deploy_$PROLETTO_ENV.sh"
if [ -f "$PRE_DEPLOY_SCRIPT" ]; then
  echo "📣 Running pre-deployment script: $PRE_DEPLOY_SCRIPT"
  bash "$PRE_DEPLOY_SCRIPT"
fi

# Launch Gunicorn with explicit port binding
# We're not using gunicorn_config.py here to ensure the port binding is explicit
echo "🚀 Starting Gunicorn WSGI server..."
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 60 main:app