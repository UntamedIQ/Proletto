#!/usr/bin/env python3
"""
Quick Link Test for Proletto

This script performs a quick check of the most important links on both the main Proletto app
and the Dragon feature, and compares the results.
"""

import sys
import requests
from tabulate import tabulate
from urllib.parse import urljoin

# Define the base URLs
MAIN_APP_URL = "http://localhost:5000"
DRAGON_URL = "http://localhost:5002"

# Define important routes to check
IMPORTANT_ROUTES = [
    "/",                        # Home page
    "/how-it-works",            # How it works page
    "/login",                   # Login page
    "/register",                # Register page
    "/membership",              # Membership page
    "/opportunities",           # Opportunities page
    "/search",                  # Search page
    "/dashboard",               # Dashboard page
    "/portfolio",               # Portfolio page
    "/static/images/logo.svg",  # Logo image
    "/static/css/styles.css",   # Main CSS
    "/static/assets/hero-image.svg",  # Hero image
    "/api/v2/health",           # API health endpoint
]

def check_url(base_url, path):
    """Check if a URL is accessible."""
    url = urljoin(base_url, path)
    try:
        response = requests.get(url, timeout=2)
        return response.status_code, response.status_code < 400
    except Exception as e:
        return f"Error: {str(e)}", False

def compare_links():
    """Compare links between main app and dragon feature."""
    results = []
    main_app_success = 0
    dragon_success = 0
    
    for route in IMPORTANT_ROUTES:
        main_status, main_success = check_url(MAIN_APP_URL, route)
        dragon_status, dragon_success = check_url(DRAGON_URL, route)
        
        if main_success:
            main_app_success += 1
        if dragon_success:
            dragon_success += 1
        
        results.append([
            route,
            f"{main_status} ({'✓' if main_success else '✗'})",
            f"{dragon_status} ({'✓' if dragon_success else '✗'})"
        ])
    
    # Calculate success percentages
    main_percentage = (main_app_success / len(IMPORTANT_ROUTES)) * 100
    dragon_percentage = (dragon_success / len(IMPORTANT_ROUTES)) * 100
    
    # Print the results
    print("\n== Link Comparison: Main App vs Dragon Feature ==\n")
    print(tabulate(results, headers=["Route", "Main App", "Dragon Feature"], tablefmt="grid"))
    
    print(f"\nMain App Success: {main_app_success}/{len(IMPORTANT_ROUTES)} ({main_percentage:.1f}%)")
    print(f"Dragon Feature Success: {dragon_success}/{len(IMPORTANT_ROUTES)} ({dragon_percentage:.1f}%)")
    
    if main_percentage > dragon_percentage:
        print("\nRECOMMENDATION: The main app has better link health than the Dragon feature.")
    elif dragon_percentage > main_percentage:
        print("\nRECOMMENDATION: The Dragon feature has better link health than the main app.")
    else:
        print("\nRECOMMENDATION: Both applications have equivalent link health.")
    
    # List common broken links
    broken_links = []
    for route in IMPORTANT_ROUTES:
        _, main_success = check_url(MAIN_APP_URL, route)
        _, dragon_success = check_url(DRAGON_URL, route)
        
        if not main_success and not dragon_success:
            broken_links.append(route)
    
    if broken_links:
        print("\nCommon broken links in both applications:")
        for link in broken_links:
            print(f"  - {link}")

if __name__ == "__main__":
    compare_links()