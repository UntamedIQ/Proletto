#!/usr/bin/env python3
"""
Proletto Site Checker

A focused tool to check key pages on the Proletto site and identify any broken links.
This doesn't crawl the entire site but focuses on specific important pages.
"""

import sys
import requests
import csv
from urllib.parse import urljoin, urlparse
from datetime import datetime
from bs4 import BeautifulSoup

# Base URL
BASE_URL = "https://myproletto.replit.app"

# Key pages to check
KEY_PAGES = [
    "/",  # Home page
    "/dashboard",
    "/opportunities",
    "/portfolio",
    "/profile",
    "/simple-admin/",
    "/get-started",
    "/upgrade",
    "/auth/login",
    "/auth/register",
    "/referral/",
    "/workspace"
]

def is_internal_link(url):
    """Check if a link is internal to our site"""
    base_netloc = urlparse(BASE_URL).netloc
    url_netloc = urlparse(url).netloc
    return not url_netloc or url_netloc == base_netloc

def check_page(url):
    """Check if a page exists and return status code"""
    try:
        print(f"Checking: {url}", file=sys.stderr)
        response = requests.get(url, timeout=5)
        return url, response.status_code, response.status_code < 400, response.text if response.status_code < 400 else None
    except Exception as e:
        print(f"Error checking {url}: {e}", file=sys.stderr)
        return url, 0, False, None

def extract_links(url, html_content):
    """Extract all links from a page"""
    links = []
    try:
        if not html_content:
            return links
            
        soup = BeautifulSoup(html_content, 'html.parser')
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href', '').strip()
            anchor_text = a_tag.get_text(strip=True) or "[No Text]"
            
            # Skip mailto, tel, javascript and anchor links
            if href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
                continue
                
            # Build full URL
            full_url = urljoin(url, href)
            
            # Only keep internal links for our site
            if is_internal_link(full_url):
                links.append((full_url, anchor_text))
    except Exception as e:
        print(f"Error extracting links from {url}: {e}", file=sys.stderr)
        
    return links

def main():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"proletto_check_{timestamp}.csv"
    
    page_results = []
    link_results = []
    checked_urls = set()
    
    # Check each key page
    for page in KEY_PAGES:
        full_url = urljoin(BASE_URL, page)
        if full_url in checked_urls:
            continue
            
        url, status, is_ok, html = check_page(full_url)
        checked_urls.add(url)
        page_results.append((url, status, "OK" if is_ok else "BROKEN"))
        
        # Extract links from working pages
        if is_ok and html:
            links = extract_links(url, html)
            print(f"  Found {len(links)} links on {url}", file=sys.stderr)
            
            # Check each extracted link if not already checked
            for link_url, anchor in links:
                if link_url in checked_urls:
                    continue
                    
                link_url, link_status, link_ok, _ = check_page(link_url)
                checked_urls.add(link_url)
                link_results.append((link_url, anchor, link_status, "OK" if link_ok else "BROKEN"))
    
    # Write page results to CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["URL", "Status Code", "Status", "Type"])
        
        # Write main pages
        for url, status, is_ok in page_results:
            writer.writerow([url, status, is_ok, "Page"])
            
        # Write links
        for url, anchor, status, is_ok in link_results:
            writer.writerow([url, status, is_ok, "Link"])
    
    # Count broken links
    broken_pages = sum(1 for _, _, status in page_results if status == "BROKEN")
    broken_links = sum(1 for _, _, _, status in link_results if status == "BROKEN")
    total_pages = len(page_results)
    total_links = len(link_results)
    
    print(f"\nCheck complete.", file=sys.stderr)
    print(f"Pages: {total_pages} total, {broken_pages} broken", file=sys.stderr)
    print(f"Links: {total_links} total, {broken_links} broken", file=sys.stderr)
    print(f"Results saved to {output_file}", file=sys.stderr)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())