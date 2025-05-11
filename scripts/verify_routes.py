#!/usr/bin/env python3
"""
Route Verification Script - Smoke Test

This script tests all the critical routes in the Proletto application 
to ensure they are properly configured and responding.
"""

import os
import sys
import requests
import json
from pprint import pprint
from urllib.parse import urljoin

# Use the provided base URL or default to localhost
BASE_URL = os.environ.get('REPLIT_URL', 'https://website-builder-myproletto.replit.app')

# List of routes to test
ROUTES = [
    '/',
    '/opportunities',
    '/portfolio',
    '/auth/login',
    '/auth/register',
    '/auth/logout',
    '/get-started',
    '/sign-up',
    '/sign-in',
    '/upgrade',
    '/start-trial',
    '/login.html',
    '/signup.html',
]

def test_route(route):
    """Test a route and return its status code and response type"""
    url = urljoin(BASE_URL, route)
    try:
        response = requests.get(url, allow_redirects=True)
        status_code = response.status_code
        content_type = response.headers.get('Content-Type', '').split(';')[0].strip()
        final_url = response.url  # Where we ended up after redirects
        
        return {
            'route': route,
            'url': url,
            'status_code': status_code,
            'content_type': content_type,
            'final_url': final_url,
            'redirected': final_url != url,
            'success': 200 <= status_code < 400  # 2xx or 3xx is success
        }
    except Exception as e:
        return {
            'route': route,
            'url': url,
            'status_code': None,
            'content_type': None,
            'final_url': None,
            'redirected': False,
            'success': False,
            'error': str(e)
        }

def main():
    """Main function to run the tests"""
    results = []
    success_count = 0
    failure_count = 0
    
    print(f"🔍 Testing routes on {BASE_URL}...")
    
    for route in ROUTES:
        result = test_route(route)
        results.append(result)
        
        if result['success']:
            success_count += 1
            status = '✅'
        else:
            failure_count += 1
            status = '❌'
            
        redirect_info = ''
        if result.get('redirected'):
            redirect_info = f" → {result['final_url']}"
            
        print(f"{status} {route} - {result.get('status_code')}{redirect_info}")
    
    print("\n=== Summary ===")
    print(f"Total Routes: {len(ROUTES)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {failure_count}")
    
    # Output detailed results
    print("\n=== Detailed Results ===")
    for result in results:
        if not result['success']:
            print(f"\nRoute: {result['route']}")
            pprint(result)
    
    return 0 if failure_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())