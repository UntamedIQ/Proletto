#!/usr/bin/env python3
"""
Auth Route Verification Script - Development Utility
===================================================
STANDALONE DEVELOPMENT UTILITY - Not used in production

This script verifies all auth endpoints are properly registered and accessible in the Proletto app.
It provides a quick way to check for 404s or other routing issues.

Usage:
  python scripts/verify_auth.py [base_url]

Example:
  python scripts/verify_auth.py https://proletto.com
  python scripts/verify_auth.py  # Uses REPLIT_DOMAINS or localhost:5000 by default
"""
import requests
import sys
import os

# Get the base URL from command line, environment, or use default
if len(sys.argv) > 1:
    BASE = sys.argv[1]
else:
    REPLIT_DOMAIN = os.environ.get('REPLIT_DEV_DOMAIN', '')
    if REPLIT_DOMAIN:
        BASE = f"https://{REPLIT_DOMAIN}"
    else:
        BASE = "http://localhost:5000"

# Define the auth endpoints to check
ENDPOINTS = [
    "/auth/login",
    "/auth/register",
    "/auth/logout",
    "/auth/reset-password",
    "/auth/reset-password-request",
    "/auth/confirm-email",
    "/opportunities",
    "/portfolio",
    "/get-started",
    "/sign-up",
    "/sign-in",
    "/upgrade",
    "/start-trial",
    "/login.html",
    "/signup.html"
]

def check(url):
    """Check if a URL is accessible and return the status code"""
    try:
        print(f"Checking {url}...")
        r = requests.head(url, allow_redirects=True, timeout=5)
        return r.status_code
    except Exception as e:
        return f"ERR: {e}"

if __name__ == '__main__':
    print(f"\n🔍 Verifying routes on {BASE}\n")
    
    # Try to get the routes from Flask directly
    try:
        print("\n📋 Testing Key Endpoints:")
        for ep in ENDPOINTS:
            url = BASE + ep
            status = check(url)
            # Consider 200, 201, 302 and 303 as success
            if status in [200, 201, 302, 303]:
                mark = "✅"
            else:
                mark = f"❌ {status}"
            print(f"  {ep.ljust(30)} -> {mark}")
    except Exception as e:
        print(f"❌ Error checking routes: {e}")
    
    print("\nTips:")
    print("- 405 error usually means endpoint exists but only accepts POST")
    print("- 404 error means endpoint isn't registered at all")
    print("- If you see SSLError, your URL might be incorrect")
    print("\nNEXT STEPS:")
    print("1. If any routes 404, check blueprint registration order in main.py")
    print("2. Make sure templates exist in the correct location")
    print("3. Ensure blueprints are registered before any routes that reference them")
    print("4. Verify that catch-all route is registered AFTER all other routes")