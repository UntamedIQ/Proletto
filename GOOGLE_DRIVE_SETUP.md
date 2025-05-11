# Setting Up Google Drive Integration for Proletto

This guide explains how to set up the Google Drive integration for Proletto to store opportunities and user portfolios.

## 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Make note of the project ID

## 2. Enable the Google Drive API

1. In your project, navigate to "APIs & Services" > "Library"
2. Search for "Google Drive API" and enable it
3. Wait for the API to be enabled

## 3. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" and select "OAuth client ID"
3. Configure the OAuth consent screen if prompted
4. For application type, select "Desktop application"
5. Name your client ID (e.g., "Proletto Drive Integration")
6. Click "Create"
7. You'll see a client ID and client secret - download the JSON file

## 4. Set Up the Credentials in Proletto

1. Rename the downloaded JSON file to `credentials.json`
2. Place this file in the root directory of your Proletto project
3. The first time the application runs with Google Drive integration, it will open a browser window asking for permission to access your Google Drive
4. After granting permission, a `token.pickle` file will be created to store the access token

## 5. Folder Structure in Google Drive

The Google Drive integration will automatically create the following folder structure:

- Proletto (root folder)
  - Opportunities (for storing scraped opportunities)
  - Portfolios (for storing user portfolios)
  - Applications (for storing user applications)
  - Backups (for storing backups of important data)

## 6. Important Notes

- The integration requires internet access to authenticate with Google Drive
- If the `credentials.json` file is not present, the integration will fall back to local file storage
- To revoke access, you can delete the `token.pickle` file and authenticate again
- You can also revoke access through the [Google Account permissions page](https://myaccount.google.com/permissions)

## 7. Technical Details

The Google Drive integration uses the following Python packages:
- google-api-python-client
- google-auth
- google-auth-oauthlib
- google-auth-httplib2

If you're experiencing issues with the integration, check the log files:
- api.log (for API-related logs)
- bot.log (for scraper-related logs)