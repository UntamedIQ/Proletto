# API Backend Configuration

This document explains how to configure the API backend connection for Proletto.

## Overview

Proletto uses a two-service architecture:

1. **Main Application** - Serves the web UI and handles user sessions
2. **API Backend** - Provides data and business logic through JSON APIs

These services need to communicate with each other. The main application proxies API requests to the backend service.

## Configuration

### Setting API Backend URL

The `API_BACKEND_URL` environment variable controls where API requests are sent. This should be set to the full URL of your API backend service.

```
API_BACKEND_URL=https://myproletto-api.replit.app  # For production
API_BACKEND_URL=http://0.0.0.0:5001                # For local development
```

### How It Works

When a request is made to `/api/*` in the main application:

1. The request is captured by the `api_proxy` function in `main.py`
2. The URL is constructed using `API_BACKEND_URL` (or fallback to `http://0.0.0.0:5001`)
3. Headers and parameters are forwarded to preserve the request
4. The response is relayed back to the client

This architecture allows:
- Frontend and backend to be deployed separately
- Different scaling characteristics for each service
- Independent development and testing

### Deployment Considerations

For production deployment:

1. Deploy the API backend service first
2. Note the URL of the deployed API service
3. Set `API_BACKEND_URL` environment variable in the main application
4. Deploy the main application

When developing locally:
- The main app typically runs on port 5000
- The API backend typically runs on port 5001
- Use `http://0.0.0.0:5001` as the API backend URL

## Troubleshooting

If API requests are failing, check:

1. Is the API backend service running?
2. Is the `API_BACKEND_URL` environment variable set correctly?
3. Can the main application reach the API backend? (networking/firewall issues)
4. Are CORS headers properly configured on the API backend?
5. Are authentication tokens being properly forwarded?

You can test connectivity with:

```bash
curl -v "$(API_BACKEND_URL)/api/healthz"
```

This should return a 200 OK response with basic service information.