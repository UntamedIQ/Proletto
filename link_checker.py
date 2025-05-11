#!/usr/bin/env python3
"""
Link Checker

A simplified wrapper script to run link_audit.py with specific parameters.
This script makes it easier to run a complete site audit as requested.

Usage:
  python link_checker.py https://your-domain.com
"""

import sys
import os
import requests
import csv
from datetime import datetime
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import argparse

def is_valid_url(url):
    """Check if the URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def is_internal_link(url, base_domain):
    """Check if a URL is internal to the base domain"""
    parsed_url = urlparse(url)
    return parsed_url.netloc == base_domain or not parsed_url.netloc

def check_url(url, timeout=5):
    """Check if a URL is accessible and return status code"""
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return response.status_code
    except Exception as e:
        print(f"Error checking {url}: {e}", file=sys.stderr)
        return 0  # 0 means connection error

def find_links(url, base_domain, max_depth=2, current_depth=0, visited=None):
    """Find all links on a page up to max_depth"""
    if visited is None:
        visited = set()
    
    if url in visited or current_depth > max_depth:
        return []
    
    visited.add(url)
    links = []
    
    try:
        print(f"Checking {url} (depth {current_depth}/{max_depth})", file=sys.stderr)
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return [(url, "", "internal", response.status_code, "yes" if response.status_code >= 400 else "no")]
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Add the current page
        links.append((url, "", "internal", response.status_code, "no"))
        
        # Find all links on the page
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href', '').strip()
            anchor_text = a_tag.get_text(strip=True) or "[No Text]"
            
            # Skip mailto, tel, javascript and anchor links
            if href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
                continue
            
            # Build full URL
            full_url = urljoin(url, href)
            
            # Remove fragments
            full_url = full_url.split('#')[0]
            
            # Check if it's a valid URL
            if not is_valid_url(full_url):
                continue
            
            # Determine if internal or external
            link_type = "internal" if is_internal_link(full_url, base_domain) else "external"
            
            # Record this link
            if full_url not in [l[0] for l in links]:
                if link_type == "external":
                    # For external links, check status but don't crawl further
                    status_code = check_url(full_url)
                    is_broken = "yes" if status_code >= 400 or status_code == 0 else "no"
                    links.append((full_url, anchor_text, link_type, status_code, is_broken))
                else:
                    # For internal links, add to list and crawl if within depth limit
                    links.append((full_url, anchor_text, link_type, None, None))
                    if current_depth < max_depth:
                        links.extend(find_links(full_url, base_domain, max_depth, current_depth + 1, visited))
    
    except Exception as e:
        print(f"Error processing {url}: {e}", file=sys.stderr)
        links.append((url, "", "internal", 0, "yes"))
    
    return links

def main():
    parser = argparse.ArgumentParser(description="Website Link Checker")
    parser.add_argument("url", help="The URL to check")
    parser.add_argument("--depth", type=int, default=2, help="Maximum crawl depth (default: 2)")
    parser.add_argument("--output", help="Output CSV file (default: link_audit_{datetime}.csv)")
    
    args = parser.parse_args()
    
    if not is_valid_url(args.url):
        print(f"Error: '{args.url}' is not a valid URL", file=sys.stderr)
        return 1
    
    # Get base domain for internal link checking
    base_domain = urlparse(args.url).netloc
    
    # Get output filename
    if not args.output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"link_audit_{timestamp}.csv"
    else:
        output_file = args.output
        
    # Ensure we're not overriding a redirect if stdout is already being redirected
    stdout_is_redirected = not sys.stdout.isatty() if hasattr(sys.stdout, 'isatty') else False
    use_stdout = stdout_is_redirected and args.output is None
    
    print(f"Starting link check for {args.url} with max depth {args.depth}", file=sys.stderr)
    print(f"Results will be saved to {output_file}", file=sys.stderr)
    
    # Find all links
    links = find_links(args.url, base_domain, args.depth)
    
    # Update any internal links with None status code
    print("\nChecking status of internal links with unknown status...", file=sys.stderr)
    for i, (url, anchor, link_type, status, broken) in enumerate(links):
        if link_type == "internal" and status is None:
            status_code = check_url(url)
            is_broken = "yes" if status_code >= 400 or status_code == 0 else "no"
            links[i] = (url, anchor, link_type, status_code, is_broken)
    
    # Write results to CSV
    if use_stdout:
        # Write to stdout if it's being redirected
        writer = csv.writer(sys.stdout)
        writer.writerow(["URL", "Anchor Text", "Type", "Status Code", "Broken"])
        for url, anchor, link_type, status, broken in links:
            writer.writerow([url, anchor, link_type, status or "", broken or ""])
    else:
        # Write to file
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["URL", "Anchor Text", "Type", "Status Code", "Broken"])
            
            for url, anchor, link_type, status, broken in links:
                writer.writerow([url, anchor, link_type, status or "", broken or ""])
    
    # Count broken links
    broken_count = sum(1 for _, _, _, _, broken in links if broken == "yes")
    total_count = len(links)
    
    print(f"\nAudit complete. Found {total_count} links, {broken_count} broken.", file=sys.stderr)
    if use_stdout:
        print(f"Results written to standard output", file=sys.stderr)
    else:
        print(f"Results saved to {output_file}", file=sys.stderr)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())