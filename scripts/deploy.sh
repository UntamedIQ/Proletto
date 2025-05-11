#!/bin/bash
# Enhanced Deployment Script for Proletto CI/CD Pipeline
# This script handles the deployment process with additional safety checks

set -e  # Exit on error

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse arguments
ENVIRONMENT="production"
SKIP_MIGRATION=false
SKIP_CACHE_WARMUP=false

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --env=*)
      ENVIRONMENT="${1#*=}"
      ;;
    --skip-migration)
      SKIP_MIGRATION=true
      ;;
    --skip-cache-warmup)
      SKIP_CACHE_WARMUP=true
      ;;
    *)
      echo -e "${RED}Error: Unknown option $1${NC}"
      exit 1
      ;;
  esac
  shift
done

# Configuration based on environment
case $ENVIRONMENT in
  development)
    PORT=5000
    WORKERS=2
    FLASK_ENV=development
    ;;
  staging)
    PORT=5000
    WORKERS=4
    FLASK_ENV=production
    ;;
  production)
    PORT=5000
    WORKERS=8
    FLASK_ENV=production
    ;;
  *)
    echo -e "${RED}Error: Unknown environment '$ENVIRONMENT'${NC}"
    exit 1
    ;;
esac

echo -e "${GREEN}===== Proletto Deployment Script =====${NC}"
echo -e "${GREEN}Deploying to ${YELLOW}$ENVIRONMENT${GREEN} environment${NC}"

# Make scripts executable
chmod +x scripts/*.py
chmod +x scripts/*.sh
chmod +x *.py
chmod +x *.sh 2>/dev/null || true

# Set environment variables
export PORT=$PORT
export FLASK_ENV=$FLASK_ENV
export FLASK_APP=main.py
export REPLIT_DEPLOYMENT=1
export DEPLOYMENT_ENVIRONMENT=$ENVIRONMENT

echo -e "${GREEN}📣 PORT=$PORT - This will be forwarded to external port 80${NC}"
echo -e "${GREEN}📣 FLASK_ENV=$FLASK_ENV${NC}"
echo -e "${GREEN}📣 DEPLOYMENT_ENVIRONMENT=$DEPLOYMENT_ENVIRONMENT${NC}"

# Database migration
if [ "$SKIP_MIGRATION" = false ]; then
  echo -e "${GREEN}Running database migrations...${NC}"
  python scripts/migrate_db.py
  if [ $? -ne 0 ]; then
    echo -e "${RED}Database migration failed! Aborting deployment.${NC}"
    exit 1
  fi
  echo -e "${GREEN}✅ Database migration completed successfully${NC}"
else
  echo -e "${YELLOW}⚠️ Skipping database migration${NC}"
fi

# Pre-warm cache (for production/staging only)
if [ "$SKIP_CACHE_WARMUP" = false ] && [ "$ENVIRONMENT" != "development" ]; then
  echo -e "${GREEN}Pre-warming cache...${NC}"
  python -c "
import os, sys
sys.path.insert(0, os.path.abspath('.'))
try:
    from cache_utils import warm_cache
    with open('main.py') as f:
        app_module = type('module', (), {})
        app_module.__file__ = 'main.py'
        exec(f.read(), app_module.__dict__)
    warm_cache(app_module.app)
    print('✅ Cache warmed up successfully')
except Exception as e:
    print(f'⚠️ Cache warm-up failed: {e}')
    # Non-critical, continue deployment
  "
fi

# Health check function
perform_health_check() {
  echo -e "${GREEN}Performing health check...${NC}"
  # Wait for server to be responsive
  for i in {1..30}; do
    curl -s http://localhost:$PORT/api/health > /dev/null
    if [ $? -eq 0 ]; then
      echo -e "${GREEN}✅ Health check passed${NC}"
      return 0
    fi
    echo -e "${YELLOW}Waiting for server to become responsive (attempt $i/30)${NC}"
    sleep 2
  done
  
  echo -e "${RED}❌ Health check failed after 30 attempts${NC}"
  return 1
}

echo -e "${GREEN}Starting Gunicorn server with $WORKERS workers...${NC}"

# Start Gunicorn in the background
if [ "$ENVIRONMENT" = "development" ]; then
  # In development, use Flask's built-in server
  python main.py &
  SERVER_PID=$!
else
  # In staging/production, use Gunicorn
  gunicorn --bind 0.0.0.0:$PORT --workers $WORKERS --threads 2 --timeout 60 main:app &
  SERVER_PID=$!
fi

# Perform health check
sleep 3  # Give the server a moment to start
perform_health_check
if [ $? -ne 0 ]; then
  # Kill the server process if health check fails
  kill $SERVER_PID 2>/dev/null || true
  echo -e "${RED}Deployment failed: Server did not pass health check${NC}"
  exit 1
fi

# If we get here during CI/CD, we're good to go
if [ -n "$CI" ]; then
  # Kill the background server (CI/CD just needs to verify it starts)
  kill $SERVER_PID 2>/dev/null || true
  echo -e "${GREEN}✅ Deployment verification completed successfully${NC}"
  exit 0
fi

# For direct running, wait for the server process
echo -e "${GREEN}✅ Deployment completed successfully${NC}"
echo -e "${GREEN}Server is running with PID $SERVER_PID${NC}"
echo -e "${GREEN}Press Ctrl+C to stop${NC}"

wait $SERVER_PID