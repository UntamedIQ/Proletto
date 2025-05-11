# Proletto Deployment Instructions for Replit

This document provides instructions on how to deploy the Proletto application on Replit.

## Deployment Configuration

The application has been updated to use the correct port (port 80) for deployment. Follow these steps to deploy:

1. On Replit, click on the **Deploy** tab in the sidebar.
2. In the deployment settings, configure the application to:
   - Run command: `./flask_deploy.sh`
   - Port: 80

Either of the following deployment scripts can be used:

- `flask_deploy.sh` (recommended) - This script includes additional database and Redis connection checks, and is specifically designed for Flask applications.
- `deploy.sh` - A simpler script that only sets environment variables.

Both scripts automatically set the necessary environment variables for deployment, including:
- `REPLIT_DEPLOYMENT=1` to indicate the app is running in deployment mode
- `PORT=80` and `API_PORT=80` to ensure both main app and API backend listen on port 80
- Production environment settings

## Deployment Architecture

Proletto uses a two-component architecture:
1. **Main Application**: The Flask web application serving the user interface
2. **API Backend**: The Flask API application providing data services

In development, these run on separate ports (5000 and 5001). In deployment, both are configured to listen on port 80, and routing between them is handled via URL paths (the API is available at `/api/*` endpoints).

## Environment Variables

Ensure these environment variables are set in your Replit environment secrets:

- `DATABASE_URL`: PostgreSQL database connection string
- `REDIS_URL`: Redis connection string
- `STRIPE_SECRET_KEY`: Stripe secret key
- `STRIPE_PUBLIC_KEY`: Stripe publishable key
- `STRIPE_WEBHOOK_SECRET`: Stripe webhook secret
- `SENDGRID_API_KEY`: SendGrid API key
- `API_KEY`: API key for internal services
- `FLASK_SECRET_KEY`: Secret key for Flask sessions

## Deployment Steps

1. Complete the pre-deployment checks in the [Deployment Checklist](./DEPLOYMENT_CHECKLIST.md)

2. Configure your Replit deployment:
   - Set Run Command to: `./flask_deploy.sh`
   - Set Port to: `80`
   - Set Deployment environment variables in Replit Secrets

3. Deploy the application using Replit's deployment features

4. After deployment, test the following endpoints:
   - `/` - Main landing page
   - `/opportunities` - Opportunities page
   - `/api/healthz` - API health check endpoint

5. Complete the post-deployment checks in the [Deployment Checklist](./DEPLOYMENT_CHECKLIST.md)

## Deployment Environment Port Configuration

By default, Proletto detects `REPLIT_DEPLOYMENT=1` and switches to listening on port **80** (`0.0.0.0:80`).

The application has been configured with two port configurations:
- **Development Mode**: Uses port 5000 for the main app and port 5001 for the API backend
- **Production/Deployment Mode**: Both main app and API backend use port 80

### Port Configuration in Different Environments

| Environment | Main App Port | API Backend Port | Controlled By |
|-------------|--------------|------------------|---------------|
| Development | 5000         | 5001             | Default       |
| Deployment  | 80           | 80               | REPLIT_DEPLOYMENT=1 |

> **Note for Local Development:**  
> Running on port 80 locally may require elevated (root/administrator) privileges and can lead to failures in your dev environment.  
> This is expected. In the Replit hosting environment, port 80 is accessible without extra permissions and the app will bind successfully.

If you encounter a permission error when testing locally, you can override back to the default dev port:

```bash
export REPLIT_DEPLOYMENT=0
export PORT=5000
export API_PORT=5001
python main.py
```

## Troubleshooting

If the deployment fails:
1. Check the logs to see if there are any error messages
2. Verify that the application is configured to listen on port 80
3. Ensure all required environment variables are set
4. Confirm the `REPLIT_DEPLOYMENT` environment variable is set to "1"

**Note:** When testing locally, attempting to run on port 80 may fail because this port requires elevated permissions. This is normal behavior and does not indicate a problem with the deployment configuration. In the actual Replit deployment environment, port 80 will be properly accessible.