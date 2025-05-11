"""
Google OAuth Helper

This module provides utilities for loading Google OAuth credentials
either from a local file or from environment variables.
"""

import os
import json
from typing import Dict, Any, Optional

def load_google_credentials() -> Optional[Dict[str, Any]]:
    """
    Load Google OAuth credentials from environment variables or local file.
    
    In production, credentials should be provided via environment variables:
    - GOOGLE_OAUTH_CLIENT_ID
    - GOOGLE_OAUTH_CLIENT_SECRET
    
    In development, credentials can be loaded from a client_secret file.
    
    Returns:
        Dict containing the credentials or None if credentials couldn't be loaded
    """
    # First try to load from environment variables (preferred for production)
    client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
    
    if client_id and client_secret:
        return {
            'web': {
                'client_id': client_id,
                'client_secret': client_secret,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
                'project_id': 'proletto-site'  # This is generally not sensitive
            }
        }
    
    # If environment variables are not set, try to load from file (development only)
    if os.environ.get('FLASK_ENV') != 'production':
        # Look for client secret file in several common locations
        client_secret_paths = [
            'client_secret.json',
            'credentials.json',
            'client_secret_*.json',  # Will be expanded using glob
        ]
        
        import glob
        for path_pattern in client_secret_paths:
            for path in glob.glob(path_pattern):
                try:
                    with open(path, 'r') as f:
                        return json.load(f)
                except (IOError, json.JSONDecodeError):
                    pass
    
    # If we get here, we couldn't load credentials
    if os.environ.get('FLASK_ENV') == 'production':
        # In production, this is a critical error
        raise ValueError("Google OAuth credentials not found. Please set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET environment variables.")
    else:
        # In development, we'll just warn
        print("WARNING: Google OAuth credentials not found. OAuth login will not work.")
        return None

def get_client_id() -> Optional[str]:
    """Get the Google OAuth client ID."""
    credentials = load_google_credentials()
    if credentials and 'web' in credentials:
        return credentials['web'].get('client_id')
    return None

def get_client_secret() -> Optional[str]:
    """Get the Google OAuth client secret."""
    credentials = load_google_credentials()
    if credentials and 'web' in credentials:
        return credentials['web'].get('client_secret')
    return None