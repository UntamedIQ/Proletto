#!/usr/bin/env python3
"""
Broken Link Checker for Proletto

This script crawls the Proletto website and reports any broken links.
It checks both internal and external links and provides a summary report.
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

# Disable SSL warnings for development testing
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set up logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("link-checker")

class LinkChecker:
    def __init__(self, base_url, max_pages=50, check_external=True, output_file=None):
        self.base_url = base_url
        self.max_pages = max_pages
        self.check_external = check_external
        self.output_file = output_file
        self.visited_urls = set()
        self.broken_links = []
        self.external_links = set()
        self.internal_links = set()
        self.visited_count = 0
        self.session = requests.Session()
        # Set a user agent to avoid being blocked
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; ProlettoBotLinkChecker/1.0; +https://www.myproletto.com/bot)'
        })
        
    def is_valid_url(self, url):
        """Check if url is a valid URL format."""
        parsed = urlparse(url)
        return bool(parsed.netloc) and bool(parsed.scheme)
    
    def is_internal_link(self, url):
        """Check if a URL is internal."""
        parsed_url = urlparse(url)
        parsed_base = urlparse(self.base_url)
        return parsed_url.netloc == parsed_base.netloc or not parsed_url.netloc
    
    def normalize_url(self, url, parent_url):
        """Normalize URL and handle relative URLs."""
        if not url:
            return None
            
        # Skip certain URLs
        if url.startswith(('javascript:', 'mailto:', 'tel:', '#')):
            return None
            
        # Handle relative URLs
        if not self.is_valid_url(url):
            url = urljoin(parent_url, url)
            
        # Remove fragments
        parsed_url = urlparse(url)
        url = parsed_url._replace(fragment='').geturl()
        
        return url
    
    def check_link(self, url):
        """Check if a link is broken."""
        try:
            if self.is_internal_link(url):
                self.internal_links.add(url)
                response = self.session.head(url, allow_redirects=True, timeout=10, verify=False)
                if response.status_code >= 400:
                    # Try with GET if HEAD doesn't work
                    response = self.session.get(url, timeout=10, verify=False)
            else:
                if not self.check_external:
                    return True
                self.external_links.add(url)
                response = self.session.head(url, allow_redirects=True, timeout=15, verify=False)
                if response.status_code >= 400:
                    # Some sites don't like HEAD requests, try GET
                    response = self.session.get(url, timeout=15, verify=False)
                    
            return response.status_code < 400
        except Exception as e:
            logger.debug(f"Error checking {url}: {str(e)}")
            return False
    
    def extract_links(self, url):
        """Extract all links from a webpage."""
        links = set()
        try:
            response = self.session.get(url, timeout=10, verify=False)
            if response.status_code >= 400:
                return links
                
            soup = BeautifulSoup(response.text, 'html.parser')
            for a_tag in soup.find_all('a', href=True):
                link = self.normalize_url(a_tag['href'], url)
                if link:
                    links.add(link)
                    
            # Also check CSS and script links
            for tag in soup.find_all(['link', 'script', 'img'], src=True):
                link = self.normalize_url(tag.get('src'), url)
                if link:
                    links.add(link)
                    
            for tag in soup.find_all('link', href=True):
                link = self.normalize_url(tag.get('href'), url)
                if link:
                    links.add(link)
                    
        except Exception as e:
            logger.warning(f"Error extracting links from {url}: {str(e)}")
            
        return links
    
    def crawl(self, url=None):
        """Crawl the website and check all links."""
        if url is None:
            url = self.base_url
            
        if url in self.visited_urls:
            return
            
        self.visited_urls.add(url)
        self.visited_count += 1
        
        if self.visited_count > self.max_pages:
            logger.info(f"Reached maximum pages limit ({self.max_pages})")
            return
            
        logger.info(f"Checking: {url} ({self.visited_count}/{self.max_pages})")
        
        links = self.extract_links(url)
        logger.info(f"Found {len(links)} links on {url}")
        
        for link in links:
            if not self.check_link(link):
                logger.warning(f"Broken link: {link} (found on {url})")
                self.broken_links.append({
                    'url': link,
                    'parent': url,
                    'timestamp': datetime.now().isoformat()
                })
            
            # Only crawl internal links
            if (self.is_internal_link(link) and 
                link not in self.visited_urls and 
                self.visited_count < self.max_pages):
                time.sleep(0.5)  # Be nice to the server
                self.crawl(link)
    
    def generate_report(self):
        """Generate a report of broken links."""
        report = {
            'base_url': self.base_url,
            'scan_date': datetime.now().isoformat(),
            'pages_checked': self.visited_count,
            'internal_links_count': len(self.internal_links),
            'external_links_count': len(self.external_links),
            'broken_links_count': len(self.broken_links),
            'broken_links': self.broken_links
        }
        
        if self.output_file:
            with open(self.output_file, 'w') as f:
                json.dump(report, f, indent=2)
        
        return report
    
    def print_summary(self, report=None):
        """Print a summary of the link checking results."""
        if report is None:
            report = self.generate_report()
            
        logger.info("\n================= LINK CHECKER SUMMARY =================")
        logger.info(f"Base URL: {report['base_url']}")
        logger.info(f"Scan Date: {report['scan_date']}")
        logger.info(f"Pages Checked: {report['pages_checked']}")
        logger.info(f"Internal Links: {report['internal_links_count']}")
        logger.info(f"External Links: {report['external_links_count']}")
        logger.info(f"Broken Links: {report['broken_links_count']}")
        
        if report['broken_links_count'] > 0:
            logger.info("\n================= BROKEN LINKS =================")
            for link in report['broken_links']:
                logger.info(f"Link: {link['url']}")
                logger.info(f"Found on: {link['parent']}")
                logger.info("-" * 50)
                
        logger.info("\n================= END OF REPORT =================")
        
def main():
    parser = argparse.ArgumentParser(description='Check for broken links on a website.')
    parser.add_argument('--url', required=True, help='The base URL to check')
    parser.add_argument('--max-pages', type=int, default=50, help='Maximum pages to check')
    parser.add_argument('--no-external', action='store_true', help='Skip external links')
    parser.add_argument('--output', help='Output file for JSON report')
    
    args = parser.parse_args()
    
    checker = LinkChecker(
        base_url=args.url,
        max_pages=args.max_pages,
        check_external=not args.no_external,
        output_file=args.output
    )
    
    logger.info(f"Starting link checker for {args.url}")
    logger.info(f"Checking up to {args.max_pages} pages")
    
    checker.crawl()
    report = checker.generate_report()
    checker.print_summary(report)
    
    if args.output:
        logger.info(f"Report saved to {args.output}")
        
    return report['broken_links_count']

if __name__ == "__main__":
    sys.exit(main())