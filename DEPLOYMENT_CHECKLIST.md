# Proletto Deployment Checklist

Use this checklist to ensure you've properly configured Proletto for deployment.

## Pre-Deployment Checks

- [ ] All required environment variables are set in Replit Secrets
  - [ ] DATABASE_URL: PostgreSQL database connection string
  - [ ] REDIS_URL: Redis connection string (optional, will use SimpleCache if not available)
  - [ ] STRIPE_SECRET_KEY: Stripe secret key
  - [ ] STRIPE_PUBLIC_KEY: Stripe publishable key
  - [ ] STRIPE_WEBHOOK_SECRET: Stripe webhook secret
  - [ ] SENDGRID_API_KEY: SendGrid API key
  - [ ] API_KEY: API key for internal services
  - [ ] FLASK_SECRET_KEY: Secret key for Flask sessions
  - [ ] GOOGLE_OAUTH_CLIENT_ID: Google OAuth client ID (if using Google auth)
  - [ ] GOOGLE_OAUTH_CLIENT_SECRET: Google OAuth client secret (if using Google auth)

- [ ] Database is properly migrated and accessible
  - [ ] Run database connectivity test: `python -c "import os, psycopg2; conn = psycopg2.connect(os.environ.get('DATABASE_URL')); print('Database connection successful!'); conn.close()"`

- [ ] Redis is properly configured (if using)
  - [ ] Run Redis connectivity test: `python -c "import os, redis; r = redis.from_url(os.environ.get('REDIS_URL')); r.ping() and print('Redis connection successful!')"`

- [ ] Deployment scripts are executable
  - [ ] `chmod +x deploy.sh`
  - [ ] `chmod +x flask_deploy.sh`

## Deployment Configuration

- [ ] Deployment run command set to `./flask_deploy.sh`
- [ ] Deployment port set to 80
- [ ] Custom domains configured (if applicable)

## Post-Deployment Checks

- [ ] Main application endpoints are accessible
  - [ ] Home page: `/`
  - [ ] Opportunities page: `/opportunities`
  - [ ] Authentication pages: `/sign-in` and `/sign-up`

- [ ] API endpoints are accessible
  - [ ] Health check: `/api/healthz`
  - [ ] Authentication: `/api/auth/test`

- [ ] Background services are running
  - [ ] Bot scheduler
  - [ ] API backend

## Troubleshooting Steps

If deployment fails:

1. Check the logs for error messages
2. Verify port configuration is set to 80
3. Ensure all required environment variables are set
4. Check database and Redis connectivity
5. Restart the deployment with `REPLIT_DEPLOYMENT=1`