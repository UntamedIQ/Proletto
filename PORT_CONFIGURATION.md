# Proletto Port Configuration Guide

## Overview

This document outlines the port configuration setup for deploying Proletto on Replit. Understanding the correct port setup is essential for successful deployment.

## Port Configuration Requirements

For Replit Deployments, the application **must** listen on port `5000`, which is forwarded to external port `80`. This is a requirement of the Replit platform.

## Key Files and Configurations

### 1. .replit

The `.replit` file contains port forwarding rules:

```
[[ports]]
localPort = 5000
externalPort = 80
```

This maps local port 5000 to external port 80. **Your application must bind to port 5000**.

### 2. gunicorn_config.py

This file configures the Gunicorn WSGI server:

```python
# Bind to port 5000 for Replit deployment or dynamic PORT from environment
PORT = os.getenv("PORT", "5000")
bind = f"0.0.0.0:{PORT}"
```

### 3. flask_deploy.sh

This script sets up the deployment environment:

```bash
# Set default port to 5000 for Replit deployment
PORT=5000
export PORT
```

### 4. setup_deployment.py

This script sets environment variables for deployment:

```python
# Set PORT explicitly to 5000 for Replit deployment
os.environ["PORT"] = "5000"
```

## Troubleshooting

If you encounter the error:

```
The application is not binding to port 5000 which is being forwarded to external port 80
```

Check the following:

1. Verify `gunicorn_config.py` is using port 5000 (not 80)
2. Ensure environment variable `PORT` is set to 5000 in flask_deploy.sh
3. Run `python fix_deployment_port.py` to automatically fix port configuration

## Manual Fix

If needed, you can manually fix the port configuration:

```bash
# Run the deployment port fixer
python fix_deployment_port.py

# Restart the deployment workflow
workflows restart "Deploy Proletto"
```

## Notes

- Never hard-code port 80 for Replit deployments
- Always use port 5000 which will be mapped to external port 80
- For local development, port 5008 is used and mapped to 3003
- The API backend uses port 5001 mapped to 3000