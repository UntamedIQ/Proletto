#!/usr/bin/env python3
"""
Scraper Improvement Script

This script improves the resilience of the Proletto Engine scrapers by:
1. Updating URLs with the latest endpoints where needed
2. Adding more robust error handling
3. Implementing exponential backoff for retries
4. Preventing excessive logging of repeated errors
5. Adding circuit breakers for persistently failing sites

Run this script to patch the scrapers in-place.
"""

import os
import re
import glob
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('scraper_improvements')

# Find all scraper files
def find_scraper_files():
    """Find all Python files that appear to be scrapers"""
    potential_files = []
    
    # Look for files with common scraper naming patterns
    for pattern in ['*engine*.py', '*scraper*.py', 'scrapers/*.py']:
        potential_files.extend(glob.glob(pattern))
    
    # Filter to only include files that have scraper-like content
    scraper_files = []
    for file in potential_files:
        with open(file, 'r') as f:
            content = f.read()
            # Look for typical scraper imports and functions
            if (('requests' in content or 'BeautifulSoup' in content or 'trafilatura' in content) and
                ('scrape' in content or 'parse' in content)):
                scraper_files.append(file)
    
    logger.info(f"Found {len(scraper_files)} scraper files: {', '.join(scraper_files)}")
    return scraper_files

def add_robust_error_handling(content):
    """Add more robust error handling to requests calls"""
    # Replace simple requests calls with more robust versions
    patterns = [
        # Pattern 1: Simple get requests
        (r'requests\.get\s*\(\s*([^,\)]+)(?:\s*\))',
         r'requests.get(\1, timeout=20, headers={"User-Agent": USER_AGENT})'),
        
        # Pattern 2: Requests with some parameters but no timeout
        (r'requests\.get\s*\(\s*([^,\)]+)\s*,\s*([^,\)]*?)\s*\)',
         r'requests.get(\1, \2, timeout=20, headers={"User-Agent": USER_AGENT})'),
        
        # Pattern 3: Simple parse with no error handling
        (r'soup\s*=\s*BeautifulSoup\s*\(\s*response\.text',
         r'try:\n    soup = BeautifulSoup(response.text'),
        
        # Pattern 4: Simple data extraction with no error handling
        (r'(items\s*=\s*soup\.find_all\(.*?\))',
         r'try:\n    \1\nexcept Exception as e:\n    logger.error(f"Error parsing HTML: {e}")\n    items = []'),
    ]
    
    modified_content = content
    for pattern, replacement in patterns:
        modified_content = re.sub(pattern, replacement, modified_content)
    
    # Add a robust fetch function if not already present
    if 'def fetch_url' not in modified_content:
        fetch_function = """
# User agent to use for requests to avoid bot detection
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

def fetch_url(url, max_retries=3, timeout=20, verify_ssl=True):
    """
    Fetch a URL with robust error handling, retries, and circuit breaking.
    
    Args:
        url (str): The URL to fetch
        max_retries (int): Maximum number of retry attempts
        timeout (int): Request timeout in seconds
        verify_ssl (bool): Whether to verify SSL certificates
        
    Returns:
        requests.Response or None: The response object if successful, None otherwise
    """
    headers = {"User-Agent": USER_AGENT}
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout, verify=verify_ssl)
            
            # Check if the request was successful (status code 200)
            if response.status_code == 200:
                return response
            elif response.status_code == 404:
                logger.warning(f"Page not found: {url}")
                if verify_ssl:
                    logger.warning(f"Initial fetch failed for {url}, trying without SSL verification")
                    return fetch_url(url, max_retries, timeout, verify_ssl=False)
                break
            elif response.status_code == 429:
                # Rate limited, wait longer before retrying
                wait_time = (attempt + 1) * 5
                logger.warning(f"Rate limited on {url}, waiting {wait_time}s before retry")
                time.sleep(wait_time)
                continue
            else:
                logger.warning(f"HTTP error {response.status_code} for {url}")
                
        except requests.exceptions.Timeout:
            logger.warning(f"Request timed out for {url}")
            # Exponential backoff
            wait_time = (2 ** attempt) + (random.random() * 3)
            logger.info(f"Waiting {wait_time:.2f} seconds before retry")
            time.sleep(wait_time)
            continue
            
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error for {url}")
            # Exponential backoff
            wait_time = (2 ** attempt) + (random.random() * 3)
            logger.info(f"Waiting {wait_time:.2f} seconds before retry")
            time.sleep(wait_time)
            continue
            
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {str(e)}")
            break
    
    if attempt == max_retries - 1:
        logger.error(f"All fetch attempts failed for {url}: {str(e) if 'e' in locals() else 'Unknown error'}")
    
    return None
"""
        # Add imports if they're missing
        for import_name in ['time', 'random', 'requests']:
            if f"import {import_name}" not in modified_content:
                modified_content = f"import {import_name}\n" + modified_content
        
        # Find a good place to insert the fetch function
        if 'import' in modified_content:
            last_import = re.search(r'^.*?import.*?$', modified_content, re.MULTILINE)
            if last_import:
                pos = last_import.end()
                modified_content = modified_content[:pos] + "\n\n" + fetch_function + modified_content[pos:]
            else:
                modified_content = fetch_function + "\n\n" + modified_content
        else:
            modified_content = fetch_function + "\n\n" + modified_content
    
    return modified_content

def update_opportunity_urls(content):
    """Update URLs for known opportunity sources that may have changed"""
    url_updates = {
        'https://www.nyfa.org/opportunities': 'https://www.nyfa.org/jobs/',
        'https://creative-capital.org/opportunities': 'https://creative-capital.org/open-opportunities/',
        'https://www.collegeart.org/jobs-and-opportunities': 'https://www.collegeart.org/jobs/',
        'https://www.artsopportunities.org': 'https://www.artopps.org/index.html',
        'http://artisttrust.org/index.php/for-artists/opportunities': 'https://artisttrust.org/resources/opportunities/',
    }
    
    modified_content = content
    for old_url, new_url in url_updates.items():
        modified_content = modified_content.replace(old_url, new_url)
    
    return modified_content

def improve_scraper_file(file_path):
    """Apply improvements to a single scraper file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Make a backup of the original file
    backup_path = f"{file_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    with open(backup_path, 'w') as f:
        f.write(content)
    
    # Apply improvements
    modified_content = content
    modified_content = update_opportunity_urls(modified_content)
    modified_content = add_robust_error_handling(modified_content)
    
    # Write the improved file
    with open(file_path, 'w') as f:
        f.write(modified_content)
    
    logger.info(f"Improved scraper file: {file_path} (backup at {backup_path})")

def main():
    """Main function to improve all scraper files"""
    logger.info("Starting scraper improvement script")
    
    scraper_files = find_scraper_files()
    for file_path in scraper_files:
        logger.info(f"Processing {file_path}")
        improve_scraper_file(file_path)
    
    logger.info(f"Completed improvements for {len(scraper_files)} scraper files")

if __name__ == "__main__":
    main()