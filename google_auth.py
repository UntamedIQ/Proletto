# Use this Flask blueprint for Google authentication. Do not use flask-dance.

import json
import os
from functools import wraps

import requests
from flask import Blueprint, redirect, request, url_for, current_app
from flask_login import login_required, login_user, logout_user
from oauthlib.oauth2 import WebApplicationClient

# Create blueprint with consistent URL prefix under /auth
google_auth = Blueprint("google_auth", __name__, url_prefix='/auth/google')

# Import models inside functions to avoid circular imports
def get_user_model():
    from models import User
    return User

def get_db():
    from models import db
    return db

# Get Google OAuth credentials from environment variables
# These will need to be set up in the Replit environment
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Make sure to use this redirect URL. It has to match the one in the whitelist
# First check if there's a custom domain set
CUSTOM_DOMAIN = os.environ.get('CUSTOM_DOMAIN')
# Get the current Replit domain
REPLIT_DOMAIN = os.environ.get("REPLIT_DOMAINS", "").split(',')[0] if os.environ.get("REPLIT_DOMAINS") else os.environ.get("REPLIT_DEV_DOMAIN", "")

if CUSTOM_DOMAIN:
    DEV_REDIRECT_URL = f'https://{CUSTOM_DOMAIN}/auth/google/google_login/callback'
else:
    DEV_REDIRECT_URL = f'https://{REPLIT_DOMAIN}/auth/google/google_login/callback'

# ALWAYS display setup instructions to the user:
print(f"""To make Google authentication work:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new OAuth 2.0 Client ID
3. Add {DEV_REDIRECT_URL} to Authorized redirect URIs

For detailed instructions, see:
https://docs.replit.com/additional-resources/google-auth-in-flask#set-up-your-oauth-app--client
""")

client = None
if GOOGLE_CLIENT_ID:
    client = WebApplicationClient(GOOGLE_CLIENT_ID)


@google_auth.route("/google_login")
def login():
    if not client:
        return "Google OAuth client ID not configured", 500
        
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        # Replacing http:// with https:// is important as the external
        # protocol must be https to match the URI whitelisted
        redirect_uri=request.base_url.replace("http://", "https://") + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)


@google_auth.route("/google_login/callback")
def callback():
    if not client:
        return "Google OAuth client ID not configured", 500
        
    code = request.args.get("code")
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    token_endpoint = google_provider_cfg["token_endpoint"]

    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        # Replacing http:// with https:// is important as the external
        # protocol must be https to match the URI whitelisted
        authorization_response=request.url.replace("http://", "https://"),
        redirect_url=request.base_url.replace("http://", "https://"),
        code=code,
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    userinfo = userinfo_response.json()
    if userinfo.get("email_verified"):
        users_email = userinfo["email"]
        users_name = userinfo.get("given_name", "")
    else:
        return "User email not available or not verified by Google.", 400

    # Check if user exists in our database
    User = get_user_model()
    db = get_db()
    
    user = User.query.filter_by(email=users_email).first()
    if not user:
        # Create new user
        user = User(email=users_email, name=users_name, membership_level="free")
        db.session.add(user)
        db.session.commit()

    login_user(user)

    # Redirect to opportunities page after successful login
    return redirect(url_for("opportunities"))


@google_auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))