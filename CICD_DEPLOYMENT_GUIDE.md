# Proletto CI/CD Pipeline Guide

This document explains the Continuous Integration and Continuous Deployment (CI/CD) pipeline for Proletto.

## Overview

The Proletto CI/CD pipeline automates testing, building, and deploying the application across different environments. The pipeline is designed to ensure code quality, run tests, and deploy safely to various environments.

## Pipeline Structure

The CI/CD pipeline consists of the following stages:

1. **Lint**: Checks code quality using flake8, pylint, and black
2. **Test**: Runs unit, API, and end-to-end tests
3. **Build**: Packages the application for deployment
4. **Deploy**: Deploys the application to the appropriate environment

## Environments

Proletto uses three deployment environments:

- **Development (dev)**: For ongoing development work
- **Staging**: For pre-production testing and verification
- **Production**: The live environment used by customers

## Workflow Triggers

The CI/CD pipeline can be triggered in several ways:

- **Push to development branch**: Runs lint, test, and deploys to development
- **Push to main/master branch**: Runs lint, test, and deploys to staging
- **Manual trigger**: Can deploy to any environment with approval

## Setup Instructions

### Prerequisites

- GitHub account with repository access
- Replit account with deployment access
- Required secrets configured in the GitHub repository

### Required Secrets

Add the following secrets to your GitHub repository settings:

- `REPLIT_DEPLOY_KEY`: API key for Replit deployment
- `SLACK_WEBHOOK`: Webhook URL for Slack notifications (optional)
- `DATABASE_URL`: Database connection string for each environment
- `REDIS_URL`: Redis connection string (if applicable)

### Branch Protection Rules

To ensure code quality, set up branch protection rules:

1. Go to your repository settings
2. Navigate to "Branches"
3. Add rule for `main` and `master` branches
4. Require status checks to pass before merging
5. Require pull request reviews

## Deployment Process

### Automatic Deployments

- Code pushed to the `development` branch is automatically deployed to the development environment
- Code pushed to the `main` or `master` branch is automatically deployed to the staging environment
- Production deployments require manual approval through the GitHub workflow

### Manual Deployments

To manually deploy to any environment:

1. Go to the "Actions" tab in your GitHub repository
2. Select "Proletto CI/CD Pipeline" workflow
3. Click "Run workflow"
4. Select the desired branch and environment
5. Click "Run workflow"

### Rollbacks

To roll back to a previous version:

1. Find the previous successful deployment in GitHub Actions
2. Re-run that workflow to deploy the previous version

## Local Development Integration

The CI/CD scripts can also be used for local development:

### Running Tests Locally

```bash
# Run all tests
python scripts/run_tests.py

# Run only unit tests
python scripts/run_tests.py --unit

# Run only API tests
python scripts/run_tests.py --api

# Run with verbose output
python scripts/run_tests.py --verbose
```

### Local Deployment Testing

```bash
# Deploy to development environment locally
./scripts/deploy.sh --env=development

# Skip database migration
./scripts/deploy.sh --env=development --skip-migration

# Skip cache warm-up
./scripts/deploy.sh --env=development --skip-cache-warmup
```

## Monitoring Deployments

### Deployment Logs

Deployment logs are available in the GitHub Actions interface:

1. Go to the "Actions" tab in your GitHub repository
2. Select the relevant workflow run
3. View the logs for each step

### Health Checks

The CI/CD pipeline includes health checks to verify successful deployments:

- API health endpoint (`/api/health`) is checked after each deployment
- Additional validation can be added in the workflow configuration

## Troubleshooting

### Common Issues

- **Failed tests**: Check the test logs in GitHub Actions for details on which tests failed
- **Deployment failures**: Check the deployment logs for error messages
- **Database migration errors**: Ensure the database is accessible and migrations are valid

### Support

For CI/CD pipeline support, contact the Proletto DevOps team at devops@proletto.com