#!/bin/bash
# Template for environment variables - Copy to env_vars.sh and fill in values
# This template file is safe to commit to GitHub

# Database and Redis Configuration
export DATABASE_URL="postgresql://username:password@hostname:port/database"
export REDIS_URL="redis://username:password@hostname:port"

# Flask Configuration
export FLASK_SECRET_KEY="your_secret_key_here"
export FLASK_ENV="development"  # development or production

# Google OAuth Configuration
export GOOGLE_OAUTH_CLIENT_ID="your_client_id_here"
export GOOGLE_OAUTH_CLIENT_SECRET="your_client_secret_here"

# Stripe Payment Configuration
export STRIPE_SECRET_KEY="your_stripe_secret_key"
export STRIPE_PUBLIC_KEY="your_stripe_public_key"
export STRIPE_WEBHOOK_SECRET="your_stripe_webhook_secret"
export STRIPE_PRICE_ID="your_stripe_price_id"
export STRIPE_PRICE_ESSENTIALS="your_stripe_price_essentials"
export STRIPE_PRICE_INSIDER="your_stripe_price_insider"
export STRIPE_PRICE_GALLERY="your_stripe_price_gallery"
export STRIPE_PRICE_PAYPERPOST="your_stripe_price_payperpost"

# SendGrid Email Configuration
export SENDGRID_API_KEY="your_sendgrid_api_key"
export SENDGRID_FROM_EMAIL="your_sendgrid_from_email"

# Slack Configuration  
export SLACK_BOT_TOKEN="your_slack_bot_token"
export SLACK_CHANNEL_ID="your_slack_channel_id"

# OpenAI Configuration
export OPENAI_API_KEY="your_openai_api_key"

# API Configuration
export API_KEY="your_api_key"

# Deployment Configuration
export REPLIT_DEV_DOMAIN="your_replit_dev_domain"
export REPLIT_DEPLOYMENT="your_replit_deployment"
export REPLIT_DOMAINS="your_replit_domains"