#!/usr/bin/env python3
"""
Link Audit Tool

This script crawls a website and creates a CSV report of all links found,
including their HTTP status codes and whether they're broken.

Usage:
  python link_audit.py --url https://your-domain.com --output links.csv
"""

import argparse
import csv
import logging
import re
import sys
import time
import urllib.parse
from collections import deque
from datetime import datetime
from typing import Dict, List, Set, Tuple

import requests
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning

# Suppress only the specific InsecureRequestWarning
try:
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except (AttributeError, ImportError):
    # If packages is not available, try alternate approach
    import urllib3
    urllib3.disable_warnings(InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Constants
USER_AGENT = "Mozilla/5.0 (Proletto Link Audit Bot; contact@proletto.com)"
REQUEST_TIMEOUT = 15  # seconds
REQUEST_DELAY = 0.5  # seconds between requests
MAX_RETRIES = 3


class LinkAuditor:
    """
    Crawls a website and audits all internal and external links.
    """

    def __init__(self, base_url: str):
        """
        Initialize the LinkAuditor with a base URL.
        
        Args:
            base_url: The root URL to start crawling from
        """
        # Normalize the base URL
        self.base_url = base_url.rstrip("/")
        self.base_domain = urllib.parse.urlparse(self.base_url).netloc
        
        # Initialize collections
        self.visited_urls: Set[str] = set()
        self.queue: deque = deque()
        self.results: List[Dict] = []
        
        # Initialize session
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        
        logger.info(f"Initialized link auditor for {self.base_url}")
        logger.info(f"Base domain: {self.base_domain}")

    def is_internal_url(self, url: str) -> bool:
        """
        Check if a URL is internal (on the same domain).
        
        Args:
            url: The URL to check
            
        Returns:
            bool: True if internal, False if external
        """
        parsed_url = urllib.parse.urlparse(url)
        return parsed_url.netloc == self.base_domain or not parsed_url.netloc

    def normalize_url(self, url: str, parent_url: str = None) -> str | None:
        """
        Normalize a URL, resolving relative URLs and removing fragments.
        
        Args:
            url: The URL to normalize
            parent_url: The URL where this link was found
            
        Returns:
            str: The normalized URL, or None if the URL should be skipped
        """
        # Skip special URLs
        if not url or url.startswith(("mailto:", "tel:", "javascript:", "#")):
            return None
        
        # Remove fragments
        url = url.split("#")[0]
        
        # Handle relative URLs
        if not urllib.parse.urlparse(url).netloc:
            if parent_url:
                url = urllib.parse.urljoin(parent_url, url)
            else:
                url = urllib.parse.urljoin(self.base_url, url)
        
        # Ensure http/https protocol
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        return url

    def fetch_url(self, url: str) -> Tuple[int, str, str]:
        """
        Fetch a URL and return its status code and content.
        
        Args:
            url: The URL to fetch
            
        Returns:
            tuple: (status_code, final_url, content)
        """
        attempts = 0
        while attempts < MAX_RETRIES:
            try:
                response = self.session.get(
                    url, 
                    timeout=REQUEST_TIMEOUT, 
                    allow_redirects=True,
                    verify=False  # Skip SSL verification
                )
                final_url = response.url
                return response.status_code, final_url, response.text
            except requests.RequestException as e:
                attempts += 1
                if attempts < MAX_RETRIES:
                    logger.warning(f"Error fetching {url}: {e}. Retrying ({attempts}/{MAX_RETRIES})...")
                    time.sleep(REQUEST_DELAY * 2)
                else:
                    logger.error(f"Failed to fetch {url} after {MAX_RETRIES} attempts: {e}")
                    return 0, url, ""

    def extract_links(self, content: str, parent_url: str) -> List[Tuple[str, str]]:
        """
        Extract all links from HTML content.
        
        Args:
            content: HTML content
            parent_url: The URL of the page where links are extracted from
            
        Returns:
            list: List of (url, anchor_text) tuples
        """
        links = []
        try:
            soup = BeautifulSoup(content, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag.get("href", "").strip()
                anchor_text = a_tag.get_text(strip=True) or "[No Text]"
                
                # Limit anchor text length
                if len(anchor_text) > 100:
                    anchor_text = anchor_text[:97] + "..."
                
                normalized_url = self.normalize_url(href, parent_url)
                if normalized_url:
                    links.append((normalized_url, anchor_text))
        except Exception as e:
            logger.error(f"Error parsing content from {parent_url}: {e}")
        
        return links

    def crawl(self):
        """
        Crawl the website starting from the base URL.
        """
        logger.info(f"Starting crawl at {self.base_url}")
        self.queue.append(self.base_url)
        
        while self.queue:
            current_url = self.queue.popleft()
            
            # Skip if already visited
            if current_url in self.visited_urls:
                continue
            
            self.visited_urls.add(current_url)
            logger.info(f"Processing: {current_url} ({len(self.visited_urls)} visited, {len(self.queue)} queued)")
            
            # Fetch the URL
            status_code, final_url, content = self.fetch_url(current_url)
            is_broken = status_code >= 400 or status_code == 0
            is_internal = self.is_internal_url(current_url)
            
            # Record the result
            self.results.append({
                "url": current_url,
                "anchor_text": "",  # Will be filled from the referring page
                "type": "internal" if is_internal else "external",
                "status_code": status_code,
                "broken": "yes" if is_broken else "no",
                "final_url": final_url
            })
            
            # Only crawl further if it's an internal HTML page
            content_type = self.session.headers.get('Content-Type', '')
            if is_internal and status_code == 200 and content_type and isinstance(content_type, str) and 'text/html' in content_type:
                # Extract links and add to queue
                links = self.extract_links(content, current_url)
                for link_url, anchor_text in links:
                    # For each link, record where it was found with its anchor text
                    self.results.append({
                        "url": link_url,
                        "anchor_text": anchor_text,
                        "type": "internal" if self.is_internal_url(link_url) else "external",
                        "status_code": None,  # Will be verified when this URL is processed
                        "broken": None,
                        "final_url": None,
                        "source_url": current_url
                    })
                    
                    # Only add internal links to the crawl queue
                    if self.is_internal_url(link_url) and link_url not in self.visited_urls:
                        self.queue.append(link_url)
            
            # Respect crawl delay
            time.sleep(REQUEST_DELAY)
        
        logger.info(f"Crawl completed. Visited {len(self.visited_urls)} URLs.")

    def process_results(self) -> List[Dict]:
        """
        Process raw results into a final report format.
        
        Returns:
            list: Processed results
        """
        url_results = {}
        
        # First pass: Create entries for all unique URLs
        for entry in self.results:
            url = entry["url"]
            if url not in url_results:
                url_results[url] = {
                    "url": url,
                    "anchor_texts": set(),
                    "type": entry["type"],
                    "status_code": entry.get("status_code"),
                    "broken": entry.get("broken"),
                    "sources": set()
                }
            
            # Add anchor text if present
            if entry.get("anchor_text"):
                url_results[url]["anchor_texts"].add(entry["anchor_text"])
            
            # Add source URL if present
            if entry.get("source_url"):
                url_results[url]["sources"].add(entry["source_url"])
        
        # Second pass: Fill in status codes and broken flags
        for url, entry in url_results.items():
            # If status code is None, we need to check the URL
            if entry["status_code"] is None:
                status_code, _, _ = self.fetch_url(url)
                entry["status_code"] = status_code
                entry["broken"] = "yes" if status_code >= 400 or status_code == 0 else "no"
        
        # Convert sets to strings for CSV output
        final_results = []
        for url, entry in url_results.items():
            anchor_text = " | ".join(entry["anchor_texts"]) if entry["anchor_texts"] else "[No Text]"
            final_results.append({
                "url": url,
                "anchor_text": anchor_text,
                "type": entry["type"],
                "status_code": entry["status_code"] or 0,
                "broken": entry["broken"] or "unknown"
            })
        
        # Sort by type (internal first) then URL
        final_results.sort(key=lambda x: (0 if x["type"] == "internal" else 1, x["url"]))
        
        return final_results

    def export_csv(self, output_file: str):
        """
        Export results to a CSV file.
        
        Args:
            output_file: Path to the output CSV file
        """
        fieldnames = ["url", "anchor_text", "type", "status_code", "broken"]
        results = self.process_results()
        
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                writer.writerow({k: result[k] for k in fieldnames})
        
        logger.info(f"Results exported to {output_file}")
        logger.info(f"Found {len(results)} unique URLs")
        broken_count = sum(1 for r in results if r["broken"] == "yes")
        logger.info(f"Found {broken_count} broken links")


def main():
    """
    Main function to run the link audit tool.
    """
    parser = argparse.ArgumentParser(description="Website Link Audit Tool")
    parser.add_argument("--url", required=True, help="The base URL to crawl")
    parser.add_argument(
        "--output",
        default=f"link_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        help="Output CSV file path"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    try:
        # Create and run the auditor
        auditor = LinkAuditor(args.url)
        auditor.crawl()
        auditor.export_csv(args.output)
        logger.info("Link audit completed successfully!")
        return 0
    except KeyboardInterrupt:
        logger.warning("Audit interrupted by user.")
        return 1
    except Exception as e:
        logger.exception(f"Error during link audit: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())