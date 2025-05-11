# Proletto Deployment Guide

This guide provides detailed instructions for deploying the Proletto application on Replit.

## Deployment Architecture

Proletto has a multi-component architecture consisting of:

1. **Main Flask App** (port 5000 in dev, port 80 in production)
   - Handles web page rendering
   - Serves static files
   - Proxies API requests to the API backend

2. **API Backend** (port 5001)
   - Provides JSON API endpoints
   - Handles data operations
   - Manages authentication via JWT

3. **Bot Scheduler**
   - Runs opportunity scrapers
   - Scheduled job execution

## Prerequisites

Before deployment, make sure:

1. All required environment variables are set in the Replit Secrets
   - `DATABASE_URL`: PostgreSQL connection string
   - `REDIS_URL`: Redis connection string (optional, app will use SimpleCache fallback if unavailable)
   - `REDIS_PASSWORD`: Redis password for authentication (if required)
   - `REDIS_DISABLED`: Set to "1" to completely disable Redis and force SimpleCache usage
   - `API_BACKEND_URL`: URL of the API backend (e.g., `https://myproletto-api.replit.app`)
   - `STRIPE_SECRET_KEY`, `STRIPE_PUBLIC_KEY`, `STRIPE_WEBHOOK_SECRET`: For payment processing
   - `SENDGRID_API_KEY`: For email sending
   - `FLASK_SECRET_KEY`: For securing session cookies
   - Additional API keys as needed for various features
2. Database connection is properly configured
3. External services (Stripe, SendGrid, etc.) are set up correctly
4. Static assets are properly organized

## Deployment Steps

### 1. Prepare the Application

```sh
# Run deployment configuration check
python deployment_config.py --check

# Make sure your code is up to date
git pull
```

### 2. Deploy with Replit

1. Click the **Deploy** button in Replit UI
2. Replit will execute the command specified in `.replit`:
   ```
   [deployment]
   run = ["sh", "-c", "python deploy.py"]
   ```
3. The `deploy.py` script will:
   - Set environment variables for production
   - Start the Flask application on port 80
   - Configure the application for production use

### 3. Verify Deployment

After deployment:

1. Check the application is accessible via the deployment URL
2. Verify all functionality works correctly
3. Monitor for any errors in the logs

## Port Configuration

Replit production environment expects:

- The main application to listen on port 80
- Binding to all network interfaces (`0.0.0.0`) 

## Troubleshooting

### Common Issues

1. **Application not starting**
   - Check the deployment logs
   - Verify PORT environment variable is set correctly
   - Make sure the application is binding to `0.0.0.0`

2. **API connectivity issues**
   - Verify the API backend is running
   - Check `API_BACKEND_URL` environment variable is set correctly
   - Make sure the API proxy in main.py is using the environment variable, not a hardcoded URL
   - Check CORS settings in both the main app and API backend
   - If using Replit for both frontend and API backend, ensure both are deployed

3. **Database connection issues**
   - Verify DATABASE_URL environment variable
   - Check PostgreSQL is running correctly

4. **Redis connection issues**
   - The application is designed to automatically fall back to SimpleCache if Redis is unavailable
   - Check REDIS_URL and REDIS_PASSWORD are correctly set if Redis functionality is desired
   - Verify that the Redis server allows connections from your IP address
   - Use one of these scripts to troubleshoot or resolve Redis issues:
     ```bash
     # Test different Redis connection formats
     python fix_redis_url.py --test-only
     
     # More comprehensive testing with special character handling
     python fix_redis_connection.py
     
     # Completely disable Redis and use SimpleCache
     python disable_redis.py
     ```
   - To permanently disable Redis and always use SimpleCache, set environment variable REDIS_DISABLED=1
   - Redis is optional for Proletto functionality, but improves performance under high load
   - You can confirm cache status by querying one of these endpoints:
     ```bash
     # Web app cache health
     curl http://localhost:5000/cache-utils/health
     
     # API backend cache health
     curl http://localhost:5001/api/cache-utils/health
     ```

### Deployment Logs

To view deployment logs:

1. Go to the Replit Console
2. Run `tail -f /var/log/nix/deploy.log`

## Additional Resources

- [Replit Deployment Docs](https://docs.replit.com/hosting/deployments/about-deployments)
- [Flask Deployment Guide](https://flask.palletsprojects.com/en/2.0.x/deploying/)
- [PostgreSQL on Replit](https://docs.replit.com/database/postgresql-database)

## Related Documentation

For more specific topics related to Proletto deployment, see:

- [REDIS_CONFIGURATION.md](REDIS_CONFIGURATION.md) - Detailed Redis setup and troubleshooting
- [CACHE_MONITORING.md](CACHE_MONITORING.md) - How to monitor cache health and performance