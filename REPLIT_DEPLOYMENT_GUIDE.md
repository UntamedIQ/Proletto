# Proletto Deployment Guide for Replit

## Overview

This guide outlines the process for properly deploying Proletto on Replit. It covers the required port configuration, environment setup, and steps to ensure a successful deployment.

## Important Port Configuration

For successful deployment on Replit, the application **must** bind to port 5000, which Replit forwards to external port 80. This is a critical requirement for all Replit deployments.

## Pre-Deployment Checklist

1. Ensure Redis authentication is configured correctly
   - Run `python fix_redis_auth.py` to test and fix Redis connections
   - Verify Redis connection in logs: "Successfully connected to Redis cache"

2. Verify port configuration is correct
   - `gunicorn_config.py` should use port 5000, not port 80
   - `flask_deploy.sh` should set PORT=5000 
   - Deployment should bind to "0.0.0.0:5000"

3. Ensure all scripts have executable permissions
   - Run `chmod +x *.sh` to make all shell scripts executable

## Deployment Process

### Option 1: Using the Replit Deployments UI

1. Click the "Deploy" button in the Replit UI
2. This will execute the deployment command defined in the .replit file
3. Verify the application binds to port 5000
4. Monitor the deployment logs for any errors

### Option 2: Using the Simplified Deployment Script

We've created a simplified deployment script that ensures proper port configuration:

```bash
./deploy_replit.sh
```

This script:
- Sets PORT=5000 explicitly
- Configures the production environment
- Starts Gunicorn with the correct port binding
- Uses the gunicorn_config.py if available

## Troubleshooting

### Port Configuration Issues

If you see the error: "The application is not binding to port 5000 which is being forwarded to external port 80"

1. Run our port configuration fixer:
   ```bash
   python fix_deployment_port.py
   ```

2. Verify the gunicorn_config.py is using port 5000:
   ```python
   # Should be this:
   PORT = os.getenv("PORT", "5000")
   bind = f"0.0.0.0:{PORT}"
   ```

3. Use the simplified deployment script:
   ```bash
   ./deploy_replit.sh
   ```

### Redis Connection Issues

If Redis connection fails:

1. Run the Redis connection fixer:
   ```bash
   python fix_redis_connection.py
   ```

2. Verify proper Redis URL format:
   ```
   redis://:{password}@host:port
   ```

## Environment Variables

The following environment variables are essential for deployment:

- `PORT=5000` - Critical for Replit deployment
- `FLASK_ENV=production` - Sets production mode
- `REDIS_URL` - Redis connection string with proper authentication
- `DATABASE_URL` - PostgreSQL connection string

## After Deployment

1. Verify the application is accessible via the external URL
2. Check Redis cache health using the health endpoints
3. Monitor logs for any errors or warnings

## Additional Resources

- `PORT_CONFIGURATION.md` - Detailed port configuration guide
- `REDIS_CONFIGURATION.md` - Redis connection setup guide
- `REPLIT_DEPLOYMENT_UPDATE.md` - Latest deployment updates