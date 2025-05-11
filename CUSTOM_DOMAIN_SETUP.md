# Setting Up api.myproletto.com on Replit

This guide explains how to set up the api.myproletto.com domain to point to your Replit backend for the Proletto platform.

## Domain Architecture Overview

The Proletto platform uses a multi-domain architecture:

- **www.myproletto.com**: Main website (Vercel)
- **app.myproletto.com**: Core application (Vercel)
- **dashboard.myproletto.com**: User dashboards (Vercel)
- **digest.myproletto.com**: Weekly digests (Vercel)
- **api.myproletto.com**: Backend API (Replit)
- **assets.myproletto.com**: Static assets (CDN)
- **status.myproletto.com**: System status (Status page service)
- **payments.myproletto.com**: Payment processing (Stripe)

## Prerequisites

1. Domain ownership and DNS access for myproletto.com
2. Replit account with your API backend project

## Setting Up the API Domain

### 1. Configure Environment Variables in Replit

Add the following environment variables to your Replit project:

```
CUSTOM_DOMAIN=api.myproletto.com
CORS_ALLOWED_ORIGINS=https://www.myproletto.com,https://app.myproletto.com,https://dashboard.myproletto.com,https://digest.myproletto.com
```

### 2. Update DNS Settings

In your domain provider's DNS settings:

1. Add a `CNAME` record:
   - Name/Host: `api`
   - Value/Target: Your Replit domain (e.g., `proletto-api.replit.app`)
   - TTL: 3600 (or as recommended by your provider)

2. Wait for DNS propagation (usually takes 24-48 hours)

### 3. Configure Domain in Replit

1. Go to your Replit project
2. Navigate to the "Settings" tab
3. Scroll down to "Custom Domains" section
4. Enter `api.myproletto.com` and click "Add"
5. Wait for Replit to verify the domain (this may take a few minutes)
6. Once verified, Replit will automatically provision SSL certificates

### 4. Verify CORS Configuration

The API backend has been configured with CORS settings to accept requests only from authorized Proletto domains:

1. www.myproletto.com
2. app.myproletto.com
3. dashboard.myproletto.com
4. digest.myproletto.com

In development environments, the following are also allowed:
- localhost:3000 (for frontend development)
- localhost:5000 (for local testing)
- Your Replit dev domain

## Testing the Configuration

After making these changes:

1. Restart the Replit workflows
2. Test that api.myproletto.com resolves correctly:
   ```
   curl https://api.myproletto.com/
   ```
   
   Should return:
   ```json
   {
     "service": "Proletto API",
     "status": "healthy",
     "version": "1.0.0",
     "timestamp": "..."
   }
   ```

3. Test CORS by making a request from one of the allowed domains

## Production Checklist

Before going live, ensure:

1. Environment variables are correctly set
2. Domain verification is complete
3. SSL certificates are properly provisioned
4. CORS settings are restrictive (only allowing Proletto domains)
5. Rate limiting is configured (recommended for production APIs)
6. Monitoring and error logging are set up

## Troubleshooting

- **Domain not working**: Make sure DNS propagation has completed (can take up to 48 hours)
- **CORS errors**: Verify that the origin making the request is in the allowed list
- **SSL issues**: Replit should handle SSL certificates automatically, but if you're seeing certificate warnings, contact Replit support
