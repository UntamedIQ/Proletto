#!/usr/bin/env python3
"""
Simple Link Audit Tool

This script crawls a website and creates a CSV report of all links found,
including their HTTP status codes and whether they're broken.

Usage:
  python simple_link_audit.py > audit_results.csv
"""

import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import csv
import sys
import argparse
import time

def parse_args():
    parser = argparse.ArgumentParser(description="Website Link Audit Tool")
    parser.add_argument("--url", 
                      default="https://myproletto.replit.app",
                      help="The base URL to crawl")
    parser.add_argument("--delay", 
                      type=float, 
                      default=0.5,
                      help="Delay between requests in seconds")
    parser.add_argument("--max-pages", 
                      type=int, 
                      default=50,
                      help="Maximum number of pages to crawl")
    return parser.parse_args()

def is_internal(url, base_domain):
    """Check if a URL is internal (same domain as base_domain)"""
    host = urlparse(url).netloc
    return host == base_domain or not host

def fetch(url, timeout=10):
    """Fetch a URL and return status code and content"""
    try:
        resp = requests.get(url, timeout=timeout, allow_redirects=True)
        return resp.status_code, resp.text
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None, ""

def check_content_type(url, timeout=5):
    """Check if URL returns HTML content"""
    try:
        resp = requests.head(url, timeout=timeout)
        content_type = resp.headers.get('Content-Type', '')
        return 'text/html' in content_type
    except Exception:
        return False

def main():
    args = parse_args()
    BASE = args.url
    DELAY = args.delay
    
    # Get the base domain for internal link checking
    base_domain = urlparse(BASE).netloc
    
    VISITED = set()
    TO_VISIT = {BASE}
    RESULTS = []
    
    print(f"Starting crawl at {BASE}", file=sys.stderr)
    print(f"Delay between requests: {DELAY} seconds", file=sys.stderr)
    
    # Set a max page limit for practical testing
    max_pages = args.max_pages
    crawled_count = 0
    
    while TO_VISIT and crawled_count < max_pages:
        url = TO_VISIT.pop()
        if url in VISITED:
            continue
            
        VISITED.add(url)
        crawled_count += 1
        print(f"Processing: {url} (Visited: {len(VISITED)}, Queued: {len(TO_VISIT)}, Max: {max_pages})", file=sys.stderr)
        
        status, html = fetch(url)
        
        # Record this URL's status
        broken = "yes" if (status is None or status >= 400) else "no"
        RESULTS.append({
            "url": url,
            "anchor_text": "",  # Root URL has no anchor text
            "type": "internal",  # Root URL is always internal
            "status_code": status or "ERR",
            "broken": broken
        })
        
        # Parse links only if HTML and status is OK
        if status and html and status < 400 and check_content_type(url):
            try:
                soup = BeautifulSoup(html, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a['href'].strip()
                    
                    # Skip certain link types
                    if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                        continue
                        
                    # Build full URL
                    full = urljoin(url, href)
                    
                    # Normalize (remove fragment)
                    full = full.split('#')[0]
                    
                    # Get anchor text
                    anchor = a.get_text(strip=True) or "[No Text]"
                    if len(anchor) > 100:
                        anchor = anchor[:97] + "..."
                    
                    # Determine if internal or external
                    internal = is_internal(full, base_domain)
                    link_type = "internal" if internal else "external"
                    
                    # Schedule internal links for crawling if not visited
                    if internal and full not in VISITED and full not in TO_VISIT:
                        TO_VISIT.add(full)
                    
                    # Record the link
                    RESULTS.append({
                        "url": full,
                        "anchor_text": anchor,
                        "type": link_type,
                        "status_code": None,  # Will be checked later for external links
                        "broken": None
                    })
            except Exception as e:
                print(f"Error parsing {url}: {e}", file=sys.stderr)
        
        # Respect crawl delay
        time.sleep(DELAY)
    
    # Check status of external links
    print("\nChecking status of external links...", file=sys.stderr)
    for result in RESULTS:
        if result["status_code"] is None:
            status, _ = fetch(result["url"])
            result["status_code"] = status or "ERR"
            result["broken"] = "yes" if (status is None or status >= 400) else "no"
    
    # Sort results: internal first, then by URL
    sorted_results = sorted(RESULTS, key=lambda r: (0 if r["type"] == "internal" else 1, r["url"]))
    
    # Write CSV to stdout
    fieldnames = ["url", "anchor_text", "type", "status_code", "broken"]
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    for row in sorted_results:
        writer.writerow(row)
    
    # Print summary
    total = len(sorted_results)
    broken = sum(1 for r in sorted_results if r["broken"] == "yes")
    print(f"\nSummary:", file=sys.stderr)
    print(f"Total URLs found: {total}", file=sys.stderr)
    print(f"Broken links: {broken} ({broken/total*100:.1f}%)", file=sys.stderr)

if __name__ == "__main__":
    main()