# Google OAuth Configuration Guide

This guide explains how to set up Google OAuth authentication for Proletto.

## Step 1: Create or Update a Google OAuth Client ID

1. Go to the [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new OAuth 2.0 Client ID or update an existing one
3. Add the following URL to the "Authorized redirect URIs":
   ```
   https://22e42364-079d-4ee7-8480-16ca0c045811-00-2tx98zwt5azo.riker.replit.dev/auth/google/google_login/callback
   ```
   
   Note: When deploying to production, you'll need to update this with your production domain.

## Step 2: Set Environment Variables

In your Replit environment, set the following environment variables:

1. `GOOGLE_OAUTH_CLIENT_ID`: Your OAuth client ID from Google Cloud Console
2. `GOOGLE_OAUTH_CLIENT_SECRET`: Your OAuth client secret from Google Cloud Console

## Step 3: Testing the Integration

Once your configuration is complete:

1. Visit the home page and click "Continue with Google"
2. You should be redirected to Google's authentication page
3. After logging in, you should be redirected back to the application

## Troubleshooting

If you get an "Access blocked: This app's request is invalid" error:

1. Verify that the exact redirect URI is added in Google Cloud Console
2. Check that the OAuth client ID and secret are correctly set in environment variables
3. Make sure you're using the latest URI structure: `/auth/google/google_login/callback`

## Important Notes

- The redirect URI must exactly match what's configured in Google Cloud Console
- Any time you change domains or URL structures, you'll need to update the authorized redirect URIs
- Local development and production environments need separate redirect URIs in the Google Console