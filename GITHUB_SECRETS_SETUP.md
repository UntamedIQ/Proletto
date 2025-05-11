# GitHub Secrets Setup for Proletto CI/CD Pipeline

This document explains how to set up the necessary secrets in GitHub for the Proletto CI/CD pipeline.

## Required Secrets

### For All Environments

- `SLACK_WEBHOOK_URL`: The webhook URL for posting deployment notifications to Slack
- `GOOGLE_OAUTH_CLIENT_ID`: Google OAuth Client ID for authentication
- `GOOGLE_OAUTH_CLIENT_SECRET`: Google OAuth Client Secret for authentication

### For Production Environment

- `REPLIT_API_KEY`: API key for Replit API access
- `REPLIT_DEPLOY_KEY`: Deployment key for Replit
- `REPLIT_PROJECT_ID`: The ID of your production Replit project
- `DATABASE_URL`: PostgreSQL database connection string for production
- `REDIS_URL`: Redis connection string for production
- `FLASK_SECRET_KEY`: Secret key for Flask sessions in production
- `STRIPE_SECRET_KEY`: Stripe Secret Key for production
- `STRIPE_PUBLIC_KEY`: Stripe Public Key for production
- `STRIPE_WEBHOOK_SECRET`: Stripe Webhook Secret for production
- `SENDGRID_API_KEY`: SendGrid API Key for sending emails
- `SENDGRID_FROM_EMAIL`: Email address to send from with SendGrid

### For Staging Environment

- `REPLIT_STAGING_API_KEY`: API key for Replit API access (staging)
- `REPLIT_STAGING_DEPLOY_KEY`: Deployment key for Replit (staging)
- `REPLIT_STAGING_PROJECT_ID`: The ID of your staging Replit project
- `STAGING_DATABASE_URL`: PostgreSQL database connection string for staging
- `STAGING_REDIS_URL`: Redis connection string for staging
- `STAGING_FLASK_SECRET_KEY`: Secret key for Flask sessions in staging
- `STAGING_STRIPE_SECRET_KEY`: Stripe Secret Key for staging
- `STAGING_STRIPE_PUBLIC_KEY`: Stripe Public Key for staging

### For Development Environment

- `REPLIT_DEV_API_KEY`: API key for Replit API access (development)
- `REPLIT_DEV_DEPLOY_KEY`: Deployment key for Replit (development)
- `REPLIT_DEV_PROJECT_ID`: The ID of your development Replit project
- `DEV_DATABASE_URL`: PostgreSQL database connection string for development
- `DEV_REDIS_URL`: Redis connection string for development

## Setting Up GitHub Secrets

1. Go to your GitHub repository
2. Click on "Settings"
3. In the left sidebar, click on "Secrets and variables" > "Actions"
4. Click "New repository secret"
5. Enter the name and value for each secret listed above
6. Click "Add secret"

## Setting Up GitHub Environments

The CI/CD pipeline uses GitHub Environments to manage different deployment environments. To set up environments:

1. Go to your GitHub repository
2. Click on "Settings"
3. In the left sidebar, click on "Environments"
4. Click "New environment"
5. Create environments for "production", "staging", and "development"
6. For each environment, you can set up additional protections:
   - Require reviewers for deployments (recommended for production)
   - Add environment-specific secrets if needed
   - Set wait timers or deployment branches

## Verifying Setup

After setting up all secrets, you can verify the CI/CD pipeline is properly configured by:

1. Making a small change to the codebase
2. Pushing the change to the appropriate branch
3. Going to the "Actions" tab in GitHub
4. Watching the workflow run and checking for any errors

## Troubleshooting

If you encounter issues with the CI/CD pipeline:

1. Check the workflow logs in the "Actions" tab
2. Verify all secrets are correctly set up
3. Ensure the Replit API keys and deployment keys are valid
4. Check that the database and Redis connection strings are correct

For additional help, contact the Proletto DevOps team.