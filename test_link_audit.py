#!/usr/bin/env python3
"""
Test Link Audit - Simple version
This is a simplified version of the link audit tool that does basic checking of URLs.
"""

import requests
import csv
import sys

def check_url(url):
    """Check if a URL is accessible"""
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        return response.status_code < 400
    except Exception:
        return False

# List of URLs to check
urls = [
    "https://myproletto.replit.app",
    "https://myproletto.replit.app/login",
    "https://myproletto.replit.app/nonexistent",
    "https://example.com",
    "https://httpbin.org/status/404",
    "https://httpbin.org/status/200",
]

# Write results to CSV
writer = csv.writer(sys.stdout)
writer.writerow(["URL", "Status"])

# Check each URL
for url in urls:
    status = "OK" if check_url(url) else "BROKEN"
    writer.writerow([url, status])
    print(f"Checked {url}: {status}", file=sys.stderr)

print("\nAudit complete. Results written to CSV.", file=sys.stderr)