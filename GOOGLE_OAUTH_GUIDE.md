# Google OAuth Setup for Proletto

This guide explains how to configure Google OAuth authentication for Proletto.

## Credentials Setup

The application supports two methods to provide Google OAuth credentials:

1. **Environment Variables (Recommended for Production)**
   - Set `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` environment variables
   - These are automatically used in both CI/CD and local development

2. **JSON Client Secret File (Development Only)**
   - Place a `client_secret.json` file in the root directory
   - This is loaded automatically during development if environment variables are not present
   - This method is NOT recommended for production use

## GitHub Secrets Setup

For CI/CD workflows, add these secrets to your GitHub repository:

- `GOOGLE_OAUTH_CLIENT_ID`: Your Google OAuth Client ID
- `GOOGLE_OAUTH_CLIENT_SECRET`: Your Google OAuth Client Secret

These are then passed to the deployment environment.

## Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project or select an existing one
3. Configure the OAuth consent screen:
   - Select "External" user type
   - Add a name, logo, and developer contact information
   - Add the "profile" and "email" scopes
4. Create OAuth client ID:
   - Select "Web application" as the application type
   - Add authorized JavaScript origins (e.g., `https://your-replit-domain.replit.dev`)
   - Add authorized redirect URIs:
     - `https://your-replit-domain.replit.dev/auth/google/google_login/callback`
     - For development, add localhost entries as well

## Redirect URI Note

The correct redirect URI format is:

```
https://your-domain.example.com/auth/google/google_login/callback
```

Always make sure this exactly matches what's configured in the Google Cloud Console.

## Implementation Details

The OAuth functionality is implemented in:

- `google_auth.py`: Main OAuth blueprint implementation
- `utils/google_auth_helper.py`: Helper module for credential loading
- `deploy_replit.sh`: Ensures credentials are properly available during deployment

The system uses the `oauthlib` and `requests` packages for OAuth authentication.