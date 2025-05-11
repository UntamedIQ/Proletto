#!/usr/bin/env python3
"""
URL Update Script for Scrapers

This script updates the URLs in scrapers based on the current logs,
replacing URLs that are consistently failing with working alternatives.

It reads the most recent logs, identifies patterns of failing URLs,
and applies known fixes to the scraper code.
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
logger = logging.getLogger('url_updater')

# URL mappings for known issues (old URL -> new URL)
URL_MAPPINGS = {
    # Domain not resolving
    'https://www.artmuseum.jobs/': 'https://jobs.museum.org/',
    
    # Pages not found (404 errors)
    'https://www.aam-us.org/job-board/': 'https://careers.aam-us.org/',
    'https://www.collegeart.org/jobs/': 'https://careers.collegeart.org/',
    'https://www.aiga.org/job-board': 'https://designjobs.aiga.org/',
    
    # SSL/TLS issues
    'https://jobs.arteducators.org/': 'http://jobs.arteducators.org/',
    
    # Renamed or restructured sites
    'https://www.nyfa.org/opportunities': 'https://www.nyfa.org/jobs/',
    'https://creative-capital.org/opportunities': 'https://creative-capital.org/open-opportunities/',
    'https://www.artsopportunities.org': 'https://www.artopps.org/index.html',
    'http://artisttrust.org/index.php/for-artists/opportunities': 'https://artisttrust.org/resources/opportunities/'
}

# Additional timeouts for slow sites (URL -> timeout in seconds)
SITE_TIMEOUTS = {
    'https://www.artsthread.com/': 30,
    'https://www.resartis.org/': 40,
    'https://www.submittable.com/': 30,
    'https://jobs.arteducators.org/': 45
}

def analyze_recent_logs():
    """Analyze recent logs to identify failing URLs"""
    logger.info("Analyzing recent logs for URL failures...")
    
    # Log files to check
    log_files = ['bot.log', 'ap_scheduler.log', 'api.log']
    
    # Track failures by URL
    url_failures = {}
    
    for log_file in log_files:
        if not os.path.exists(log_file):
            logger.warning(f"Log file not found: {log_file}")
            continue
            
        with open(log_file, 'r') as f:
            log_content = f.read()
            
        # Look for common error patterns
        error_patterns = [
            r'WARNING.*?(https?://[^\s\'"\)\}]+).*?timed out',
            r'ERROR.*?(https?://[^\s\'"\)\}]+).*?fetch attempts failed',
            r'WARNING.*?(https?://[^\s\'"\)\}]+).*?Page not found',
            r'WARNING.*?(https?://[^\s\'"\)\}]+).*?Connection error'
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, log_content)
            for url in matches:
                if url not in url_failures:
                    url_failures[url] = 0
                url_failures[url] += 1
    
    # Sort by failure count
    sorted_failures = sorted(url_failures.items(), key=lambda x: x[1], reverse=True)
    
    # Log results
    if not sorted_failures:
        logger.info("No URL failures found in logs")
    else:
        logger.info(f"Found {len(sorted_failures)} URLs with failures:")
        for url, count in sorted_failures:
            logger.info(f"  {url}: {count} failures")
            
            # Check if we have a fix for this URL
            if url in URL_MAPPINGS:
                logger.info(f"    -> Known fix available: {URL_MAPPINGS[url]}")
            elif any(url.startswith(domain) for domain in SITE_TIMEOUTS.keys()):
                matching_domain = next(domain for domain in SITE_TIMEOUTS.keys() if url.startswith(domain))
                logger.info(f"    -> Known slow site, increasing timeout to {SITE_TIMEOUTS[matching_domain]}s")
    
    return sorted_failures

def find_scraper_files():
    """Find all Python files that appear to be scrapers"""
    potential_files = []
    
    # Look for files with common scraper naming patterns
    for pattern in ['*engine*.py', '*scraper*.py', 'scrapers/*.py', 'engines/*.py', 'proletto_engine_*.py']:
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

def update_urls_in_file(file_path, url_failures):
    """Update URLs in a specific file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Make a backup of the original file
    backup_path = f"{file_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    with open(backup_path, 'w') as f:
        f.write(content)
    
    # Apply URL mappings
    updates_made = 0
    for old_url, new_url in URL_MAPPINGS.items():
        if old_url in content:
            content = content.replace(old_url, new_url)
            updates_made += 1
            logger.info(f"Updated URL in {file_path}: {old_url} -> {new_url}")
    
    # Update timeouts for slow sites
    for site_url, timeout in SITE_TIMEOUTS.items():
        # Look for requests to this site with default timeout
        patterns = [
            (fr'requests\.get\(\s*[\'"]{site_url}[^\'"]*[\'"]\s*,\s*timeout=\d+', 
             fr'requests.get(\1, timeout={timeout}'),
            (fr'requests\.get\(\s*[\'"]{site_url}[^\'"]*[\'"]\s*\)', 
             fr'requests.get(\1, timeout={timeout})')
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                updates_made += 1
                logger.info(f"Updated timeout in {file_path} for {site_url} to {timeout}s")
    
    # Write updated content only if changes were made
    if updates_made > 0:
        with open(file_path, 'w') as f:
            f.write(content)
        logger.info(f"Made {updates_made} updates to {file_path}")
    else:
        logger.info(f"No updates needed for {file_path}")
        
        # Remove the backup if no changes
        os.remove(backup_path)
    
    return updates_made

def main():
    """Main function to update URLs in scraper files"""
    logger.info("Starting URL update script")
    
    # Analyze logs to identify failing URLs
    url_failures = analyze_recent_logs()
    
    # Find all scraper files
    scraper_files = find_scraper_files()
    
    # Update URLs in each file
    total_updates = 0
    for file_path in scraper_files:
        updates = update_urls_in_file(file_path, url_failures)
        total_updates += updates
    
    if total_updates > 0:
        logger.info(f"Completed with {total_updates} URL updates across {len(scraper_files)} files")
    else:
        logger.info("No URL updates were needed")

if __name__ == "__main__":
    main()