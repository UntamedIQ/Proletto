# Proletto Deployment Configuration Update

## Overview
This document outlines the updated deployment configuration for Proletto on Replit, focusing on proper port configuration and deployment settings.

## Key Changes

### 1. Port Configuration

Proletto is now properly configured to:
- Bind to port 5000 internally
- Map to external port 80 (the standard HTTP port)
- Use the PORT environment variable from Replit for automatic configuration

### 2. Deployment Script (flask_deploy.sh)

- Removed manual PORT export to allow Replit to provide the correct port
- Added exec directive for Gunicorn to ensure proper process handling
- Improved error handling and logging
- Simplified deployment process

```bash
# Key section from flask_deploy.sh
# In production, Replit will provide $PORT (should be 5000 for local→80 mapping)
echo "Launching Gunicorn on port ${PORT:-5000}..."
exec gunicorn -c gunicorn_config.py main:app
```

### 3. Gunicorn Configuration (gunicorn_config.py)

```python
# Bind to port 5000 for Replit deployment or dynamic PORT from environment
PORT = os.getenv("PORT", "5000")
bind = f"0.0.0.0:{PORT}"

# Dynamic worker count based on CPU cores
workers = max(2, (os.cpu_count() or 1) * 2)
```

### 4. Replit Configuration (.replit)

The .replit file should be manually updated to include:

```
[[ports]]
localPort = 5000
externalPort = 80

# Wait for your app to open THIS port before marking the repl as up:
waitForPort = 5000

[deployment]
run = ["bash", "flask_deploy.sh"]
deploymentTarget = "cloudrun"
```

## Deployment Process

1. Commit all changes to the deployment configuration files
2. Click the "Deploy" button in Replit's interface
3. Replit will run flask_deploy.sh, which will:
   - Set up the deployment environment
   - Configure Redis and other services
   - Start Gunicorn on port 5000, which will be mapped to port 80 externally

## Troubleshooting

If you encounter deployment issues:

1. Check the logs for specific error messages
2. Verify that PORT is not being overridden in any scripts
3. Ensure Gunicorn is binding to 0.0.0.0:5000
4. Check that .replit has the correct port configuration
5. Verify that the deploy workflow is properly configured to wait for port 5000

## Next Steps

- Monitor the deployment to ensure it's stable
- Set up continuous integration for automated testing
- Consider implementing deployment health checks

## IMPORTANT: Manual .replit Configuration

You must manually edit the `.replit` file since it is not accessible through the normal editor. Update it with the following configuration:

```
[[ports]]
localPort = 5000
externalPort = 80

# Wait for your app to open THIS port before marking the repl as up:
waitForPort = 5000

[deployment]
run = ["bash", "flask_deploy.sh"]
deploymentTarget = "cloudrun"
```

This configuration is critical because:

1. The workflow is currently failing with "didn't open port 80" because it's expecting port 80 but our app is binding to 5000
2. Changing `waitForPort = 5000` will fix this mismatch
3. Without this change, deployments will continue to fail even though the app is actually running correctly

You can edit the `.replit` file by using the Replit shell and running:
```
nano .replit
```