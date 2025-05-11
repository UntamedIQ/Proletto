# Proletto Deployment Guide

## Issue: Replit is treating this as a static HTML site instead of a Flask application

To fix the deployment issues, follow these steps:

### 1. Update .replit Configuration in Replit UI

1. Go to the "Files" tab in Replit
2. Open the `.replit` file
3. Change these values:
   - `run = "python main.py"`
   - `entrypoint = "main.py"`
   - `language = "python3"`

### 2. Update Deployment Configuration

1. In the `.replit` file, update the deployment section:
   ```
   [deployment]
   run = ["sh", "-c", "./init.sh"]
   ```

2. Make sure your port configuration is correct:
   ```
   [[ports]]
   localPort = 3000
   externalPort = 80
   ```

### 3. Deploy the Application

1. Use the "Deploy" button in Replit
2. Choose "Deployment type: Reserved VM" for better performance
3. Confirm deployment

## Using Replit's Deployment Assistant

We've noticed Replit provides a deployment assistant that can help with the configuration:

1. Click the **Redeploy this App** button in the Deployment tab
2. Follow the Assistant's step-by-step process to:
   - Create the proper requirements.txt file
   - Update the Flask deployment script
   - Set the correct port configuration
   - Deploy the application

The assistant should automatically fix most of the issues with your deployment.

## Troubleshooting

### If "Missing requirements.txt" error persists:

We've already prepared a requirements.txt file for you. If needed, you can regenerate it with:

```
cp requirements-deploy.txt requirements.txt
```

### If port conflicts persist:

Make sure your application listens on the correct port by setting the PORT environment variable in the Replit UI:

1. Go to "Secrets" in the Replit UI
2. Add a new secret with key `PORT` and value `80`

## Key Configuration Files

- **main.py**: Main Flask application entry point
- **init.sh**: Simple deployment script that copies requirements and starts Flask
- **flask_deploy.sh**: Advanced deployment script that handles dependencies and port configuration
- **requirements.txt**: Contains all necessary dependencies for the application
- **.replit**: Replit-specific configuration file (must be updated through the UI)

## Required Environment Variables

Your application needs these environment variables in the Replit "Secrets" tab:

- `DATABASE_URL`: PostgreSQL database connection string
- `FLASK_SECRET_KEY`: Secret key for Flask sessions
- Other API keys for external services (SendGrid, Stripe, etc.)