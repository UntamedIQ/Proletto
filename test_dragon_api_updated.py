#!/usr/bin/env python3
"""
Dragon API Tester

This script directly tests the core routes of the Dragon API to diagnose
connection issues between services.
"""

import requests
import sys
import json
from tabulate import tabulate
from typing import Dict, Any, List, Tuple

def colorize(text, color_code):
    """Add color to terminal output"""
    return f"\033[{color_code}m{text}\033[0m"

def red(text):
    return colorize(text, "31")

def green(text):
    return colorize(text, "32")

def yellow(text):
    return colorize(text, "33")

def test_dragon_endpoints(port=5002, timeout=3):
    """Test each Dragon API endpoint and report results"""
    base_url = f"http://localhost:{port}"
    
    # Define endpoints to test (updated with new dragon-health path)
    endpoints = [
        "/",
        "/health",
        "/dragon-health",
        "/opportunities",
        "/admin/dragon-status/",
        "/admin/rescue/restart-scheduler",
        "/admin/rescue/refresh-cache",
        "/static/images/logo.svg",
        "/static/css/styles.css"
    ]
    
    results = []
    success_count = 0
    
    print(f"Testing Dragon API on {base_url}...\n")
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        
        try:
            response = requests.get(url, timeout=timeout)
            status = f"{response.status_code} {response.reason}"
            success = 200 <= response.status_code < 300
            
            if success:
                success_count += 1
                
            # Get response preview
            try:
                if 'application/json' in response.headers.get('Content-Type', ''):
                    # Format JSON for better readability
                    json_content = json.dumps(response.json(), indent=2)
                    preview = json_content[:200] + "..." if len(json_content) > 200 else json_content
                else:
                    preview = response.text[:200] + "..." if len(response.text) > 200 else response.text
            except:
                preview = response.text[:200] + "..." if len(response.text) > 200 else response.text
            
        except requests.exceptions.Timeout:
            status = "Timeout"
            success = False
            preview = "Request timed out"
        except requests.exceptions.RequestException as e:
            status = f"Error"
            success = False
            preview = str(e)
            
        results.append([endpoint, status, "✓" if success else "✗", preview])
    
    # Calculate success rate
    success_rate = (success_count / len(endpoints)) * 100
    
    # Print results in a table
    print("== Dragon API Endpoint Test Results ==\n")
    
    table = tabulate(
        results,
        headers=["Endpoint", "Status", "Success", "Response Preview"],
        tablefmt="grid"
    )
    print(table)
    
    print(f"\nDragon API Success Rate: {success_count}/{len(endpoints)} ({success_rate:.1f}%)\n")
    
    # List failing endpoints
    failing = [endpoint for endpoint, _, success, _ in results if success == "✗"]
    if failing:
        print("Failing endpoints:")
        for endpoint in failing:
            print(f"  - {endpoint}")
        
        print("\nCRITICAL ISSUE: Core API endpoints are not responding.")
        print("Recommendations:")
        print("1. Check if the Dragon server is running on port 5002")
        print("2. Verify blueprint registration in dragon_core.py")
        print("3. Look for errors in startup logs")

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5002
    test_dragon_endpoints(port=port)