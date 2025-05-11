#!/usr/bin/env python3
"""
Dragon API Tester

This script directly tests the core routes of the Dragon API to diagnose
connection issues between services.
"""

import os
import sys
import json
import requests
from tabulate import tabulate

# Define Dragon API endpoints to test
DRAGON_API_ENDPOINTS = [
    "/",                        # Root route (not defined, should 404)
    "/health",                  # Health endpoint
    "/opportunities",           # Opportunities endpoint
    "/admin/dragon-status/",    # Admin dashboard (should 302 redirect if not logged in)
    "/admin/rescue/restart-scheduler",  # Admin rescue action
    "/admin/rescue/refresh-cache",      # Admin rescue action
    "/static/images/logo.svg",  # Static files
    "/static/css/styles.css",   # Static files
]

def colorize(text, color_code):
    """Add color to terminal output"""
    return f"\033[{color_code}m{text}\033[0m"

def red(text):
    return colorize(text, "91")

def green(text):
    return colorize(text, "92")

def yellow(text):
    return colorize(text, "93")

def test_dragon_endpoints(port=5002, timeout=3):
    """Test each Dragon API endpoint and report results"""
    base_url = f"http://localhost:{port}"
    
    results = []
    success_count = 0
    
    print(f"Testing Dragon API on {base_url}...")
    
    for endpoint in DRAGON_API_ENDPOINTS:
        url = base_url + endpoint
        
        try:
            response = requests.get(url, timeout=timeout)
            code = response.status_code
            
            # Check if successful (any 2XX or redirect 3XX)
            success = code < 400
            
            if success:
                success_count += 1
                
            # Handle special status codes
            if code == 200:
                status = green(f"{code} OK")
            elif 300 <= code < 400:
                status = yellow(f"{code} Redirect")
            elif code == 404:
                status = yellow(f"{code} Not Found")
            else:
                status = red(f"{code} Error")
                
            # Try to extract JSON for API endpoints
            content_type = response.headers.get('Content-Type', '')
            response_preview = "N/A"
            
            if 'application/json' in content_type:
                try:
                    data = response.json()
                    response_preview = json.dumps(data, indent=2)[:100] + "..." if len(json.dumps(data)) > 100 else json.dumps(data)
                except:
                    response_preview = response.text[:100] + "..." if len(response.text) > 100 else response.text
            else:
                response_preview = response.text[:100] + "..." if len(response.text) > 100 else response.text
                
        except requests.exceptions.Timeout:
            status = red("Timeout")
            success = False
            response_preview = "Request timed out"
        except requests.exceptions.ConnectionError:
            status = red("Connection Error")
            success = False
            response_preview = "Failed to connect to server"
        except Exception as e:
            status = red(f"Error: {type(e).__name__}")
            success = False
            response_preview = str(e)
            
        results.append([
            endpoint,
            status,
            success,
            response_preview
        ])
    
    # Calculate success percentage
    success_percentage = (success_count / len(DRAGON_API_ENDPOINTS)) * 100
    
    # Print results table
    headers = ["Endpoint", "Status", "Success", "Response Preview"]
    table_data = [[row[0], row[1], "✓" if row[2] else "✗", row[3]] for row in results]
    
    print("\n== Dragon API Endpoint Test Results ==\n")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    print(f"\nDragon API Success Rate: {success_count}/{len(DRAGON_API_ENDPOINTS)} ({success_percentage:.1f}%)")
    
    # Provide recommendations based on test results
    failing_endpoints = [row[0] for row in results if not row[2]]
    if failing_endpoints:
        print("\nFailing endpoints:")
        for endpoint in failing_endpoints:
            print(f"  - {endpoint}")
            
        # Check specific patterns
        if "/health" in failing_endpoints and "/opportunities" in failing_endpoints:
            print("\nCRITICAL ISSUE: Core API endpoints are not responding.")
            print("Recommendations:")
            print("1. Check if the Dragon server is running on port 5002")
            print("2. Verify blueprint registration in dragon_core.py")
            print("3. Look for errors in startup logs")
        elif "/opportunities" in failing_endpoints and "/health" not in failing_endpoints:
            print("\nISSUE: Opportunities endpoint not working, but health endpoint is.")
            print("Recommendations:")
            print("1. Check database connection and opportunity data loading")
            print("2. Verify cache configuration")
            print("3. Look for errors in the opportunity loading logic")
    else:
        print("\nAll Dragon API endpoints are working correctly!")
                
if __name__ == "__main__":
    # Get port from command line argument or use default
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5002
    test_dragon_endpoints(port=port)