#!/usr/bin/env python3
"""
Auth Route Verification Script
Checks all auth endpoints to make sure they're accessible in the Proletto app
"""
import requests
import sys
import os

# Get the base URL from the environment or use default
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
    "/debug/auth-routes",
    "/direct-login",
    "/direct-register"
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
    print(f"\n🔍 Verifying auth routes on {BASE}\n")
    
    # Try to get the debug route first to see all auth routes
    try:
        debug_url = f"{BASE}/debug/auth-routes"
        print(f"Fetching route debug info from {debug_url}...")
        r = requests.get(debug_url, timeout=5)
        if r.status_code == 200:
            routes = r.json()
            print("\n📋 Registered Auth Routes from Flask:")
            for route in routes:
                print(f"  {route['path'].ljust(30)} -> {route['endpoint']} {route['methods']}")
        else:
            print(f"❌ Could not fetch debug info: {r.status_code}")
    except Exception as e:
        print(f"❌ Error fetching debug routes: {e}")
    
    print("\n📋 Testing Auth Endpoints:")
    for ep in ENDPOINTS:
        url = BASE + ep
        status = check(url)
        mark = "✅" if status == 200 else f"❌ {status}"
        print(f"  {ep.ljust(30)} -> {mark}")
    
    print("\nTips:")
    print("- 405 error usually means endpoint exists but only accepts POST")
    print("- 404 error means endpoint isn't registered at all")
    print("- If you see SSLError, your URL might be incorrect")
    print("\nNEXT STEPS:")
    print("1. If any routes 404, check blueprint registration order")
    print("2. Make sure your templates exist in the correct location")
    print("3. Try direct template routes to bypass blueprint issues")