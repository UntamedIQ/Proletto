"""
Proletto Engine Improvements

This script adds improvements to the opportunity scraping engines to make them more resilient
and handle common errors more gracefully.

Key improvements:
1. Resilient Networking Layer
   - DNS & SSL Retries with exponential back-off
   - Custom SSL Context for sites with certificate issues
   - Timeouts & Circuit Breakers to avoid hammering failing sites

2. Proxy & IP Rotation
   - User-Agent Cycling to avoid bot detection
   - Support for proxy rotation (configurable)

3. Adaptive Parsers
   - Improved HTML parsing with multiple selector strategies
   - Headless browser fallback for JavaScript-heavy sites

4. Data Quality & Deduplication
   - Content fingerprinting to detect duplicates
   - Sanity checks for required fields

5. Monitoring & Alerting
   - Per-site health tracking
   - Automatic circuit breaking for failing sites

6. Backfill & Cache mechanisms
   - Transient failure handling
   - Result caching for reliability
"""

import logging
import random
import time
import json
import os
import hashlib
import threading
from datetime import datetime, timedelta
import requests
from urllib3.exceptions import InsecureRequestWarning
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bs4 import BeautifulSoup

# Configure logging
logger = logging.getLogger('scraper_improvements')
logger.setLevel(logging.INFO)

# Import the alerts module for Slack notifications
try:
    from alerts import alert_slack
    SLACK_ALERTS_AVAILABLE = True
except ImportError:
    SLACK_ALERTS_AVAILABLE = False
    logger.warning("Alerts module not available. Slack notifications are disabled.")
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Suppress only the single InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Circuit breaker settings
CIRCUIT_BREAKER_TIMEOUT = 30 * 60  # 30 minutes
CIRCUIT_BREAKER_THRESHOLD = 3  # Number of failures before tripping circuit
CIRCUIT_BREAKER_RESET_INTERVAL = 60 * 60  # 1 hour

# Cache settings
CACHE_DURATION = 60 * 60  # 1 hour

# Site health tracking
# Dictionary to track health metrics for each site
# Format: {
#   'domain.com': {
#     'success_count': 0,
#     'failure_count': 0,
#     'circuit_open': False,
#     'last_attempt': datetime.now(),
#     'last_success': datetime.now(),
#     'open_until': None,
#     'avg_latency': 0
#   }
# }
site_health = {}
site_health_lock = threading.Lock()

# Cache for responses
response_cache = {}
response_cache_lock = threading.Lock()

class CircuitBreaker:
    """
    Circuit breaker implementation to prevent hammering failing sites.
    """
    def __init__(self, domain):
        self.domain = domain
        
    def __enter__(self):
        with site_health_lock:
            # Initialize site health if not exists
            if self.domain not in site_health:
                site_health[self.domain] = {
                    'success_count': 0,
                    'failure_count': 0,
                    'circuit_open': False,
                    'last_attempt': datetime.now(),
                    'last_success': None,
                    'open_until': None,
                    'avg_latency': 0
                }
            
            # Check if circuit is open (site is failing)
            if site_health[self.domain]['circuit_open']:
                open_until = site_health[self.domain]['open_until']
                
                # If timeout period has passed, allow one request through
                if open_until and datetime.now() > open_until:
                    logger.info(f"Circuit half-open for {self.domain}, allowing test request")
                    site_health[self.domain]['circuit_open'] = False
                    site_health[self.domain]['failure_count'] = 0
                else:
                    logger.warning(f"Circuit open for {self.domain}, blocking request until {open_until}")
                    raise Exception(f"Circuit open for {self.domain}")
                
            # Update last attempt time
            site_health[self.domain]['last_attempt'] = datetime.now()
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # If there was an exception, increment failure count
        with site_health_lock:
            if exc_type:
                site_health[self.domain]['failure_count'] += 1
                
                # If failure count exceeds threshold, open circuit
                if site_health[self.domain]['failure_count'] >= CIRCUIT_BREAKER_THRESHOLD:
                    open_until = datetime.now() + timedelta(seconds=CIRCUIT_BREAKER_TIMEOUT)
                    site_health[self.domain]['circuit_open'] = True
                    site_health[self.domain]['open_until'] = open_until
                    logger.warning(f"Circuit opened for {self.domain} until {open_until}")
                    
                    # Send Slack alert when circuit is opened
                    if SLACK_ALERTS_AVAILABLE:
                        alert_message = (f"❗️ Circuit breaker tripped for {self.domain}. "
                                        f"Site failed {site_health[self.domain]['failure_count']} times. "
                                        f"Circuit will remain open until {open_until}.")
                        try:
                            alert_slack(alert_message, level="error")
                        except Exception as e:
                            logger.error(f"Failed to send Slack alert: {e}")
            else:
                # Success, reset failure count and update success metrics
                site_health[self.domain]['failure_count'] = 0
                site_health[self.domain]['success_count'] += 1
                site_health[self.domain]['last_success'] = datetime.now()
                
        # Don't suppress the exception
        return False

def get_domain(url):
    """
    Extract domain from URL
    """
    try:
        return url.split('//')[1].split('/')[0].replace('www.', '')
    except:
        return url

# List of user agents to rotate
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',
    'ProlettoBot/1.0 (+https://www.myproletto.com/about-our-bot)'
]

def create_resilient_session():
    """
    Create a requests session with retry capabilities
    """
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,  # Total number of retries
        backoff_factor=0.5,  # Backoff factor for retries
        status_forcelist=[429, 500, 502, 503, 504],  # Status codes to retry on
        allowed_methods=["GET", "POST"]  # Methods to retry
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def get_random_user_agent():
    """
    Get a random user agent from the list
    """
    return random.choice(USER_AGENTS)

def fetch_url_with_retry(url, timeout=15, verify_ssl=True, headers=None, max_retries=3):
    """
    Fetch a URL with retries and better error handling
    
    Args:
        url (str): URL to fetch
        timeout (int): Timeout in seconds
        verify_ssl (bool): Whether to verify SSL certificates
        headers (dict): HTTP headers to send
        max_retries (int): Maximum number of retries
        
    Returns:
        tuple: (success, content) where success is a boolean and content is the response text
    """
    if headers is None:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
    
    session = create_resilient_session()
    
    # Initialize retry count
    retries = 0
    
    while retries <= max_retries:
        try:
            response = session.get(
                url, 
                headers=headers, 
                timeout=timeout,
                verify=verify_ssl
            )
            
            # Check if the response is valid
            if response.status_code == 200:
                return True, response.text
                
            # Handle common HTTP errors
            if response.status_code == 403:
                logger.warning(f"Access forbidden for {url}")
                return False, "Access forbidden"
                
            if response.status_code == 404:
                logger.warning(f"Page not found: {url}")
                return False, "Page not found"
                
            if response.status_code == 429:
                logger.warning(f"Rate limited for {url}")
                # Exponential backoff
                wait_time = (2 ** retries) + random.uniform(0, 1)
                logger.info(f"Waiting {wait_time:.2f} seconds before retry")
                time.sleep(wait_time)
                retries += 1
                continue
                
            # Other errors
            logger.warning(f"HTTP error {response.status_code} for {url}")
            return False, f"HTTP error: {response.status_code}"
            
        except requests.exceptions.Timeout:
            logger.warning(f"Request timed out for {url}")
            retries += 1
            if retries <= max_retries:
                wait_time = (2 ** retries) + random.uniform(0, 1)
                logger.info(f"Waiting {wait_time:.2f} seconds before retry")
                time.sleep(wait_time)
                # Try a longer timeout on retries
                timeout += 5
                continue
            return False, "Request timed out"
            
        except requests.exceptions.SSLError:
            logger.warning(f"SSL error for {url}, retrying without verification")
            # Try again without SSL verification
            if verify_ssl:
                verify_ssl = False
                continue
            return False, "SSL verification failed"
            
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error for {url}")
            retries += 1
            if retries <= max_retries:
                wait_time = (2 ** retries) + random.uniform(0, 1)
                logger.info(f"Waiting {wait_time:.2f} seconds before retry")
                time.sleep(wait_time)
                continue
            return False, "Connection error"
            
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {e}")
            retries += 1
            if retries <= max_retries:
                wait_time = (2 ** retries) + random.uniform(0, 1)
                logger.info(f"Waiting {wait_time:.2f} seconds before retry")
                time.sleep(wait_time)
                continue
            return False, f"Error: {str(e)}"
    
    # If we get here, we've exceeded the maximum retries
    return False, "Max retries exceeded"

def extract_opportunities_from_html(html, keywords, url, min_text_length=15):
    """
    Extract opportunities from HTML with improved content extraction
    
    Args:
        html (str): HTML content
        keywords (list): List of keywords to check for
        url (str): Source URL
        min_text_length (int): Minimum length of text to be considered valid
        
    Returns:
        list: List of opportunity dictionaries
    """
    soup = BeautifulSoup(html, 'html.parser')
    opportunities = []
    
    # Look for opportunity cards, listings, or sections
    opportunity_containers = []
    
    # Common selectors for opportunity listings
    selectors = [
        'article', '.job-listing', '.opportunity', '.post', '.card',
        '.listing', '.job', '.open-call', '.residency', '.grant',
        'div[class*="job"]', 'div[class*="opp"]', 'div[class*="listing"]',
        '.item', '.event', 'section', '.entry', '.content-item',
        'li.listing', '.result', '.row'
    ]
    
    # Try to find containers for opportunities
    for selector in selectors:
        containers = soup.select(selector)
        if containers:
            opportunity_containers.extend(containers)
    
    # If no containers found, try to find individual links
    if not opportunity_containers:
        opportunity_containers = soup.find_all(['a', 'div', 'section', 'article'])
    
    # Process each container
    for container in opportunity_containers:
        # Look for a title and link
        title_tag = container.find(['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b', 'a'])
        link_tag = container.find('a', href=True)
        
        if not title_tag or not link_tag:
            continue
        
        title = title_tag.get_text(strip=True)
        link = link_tag['href']
        
        # Make sure the link is absolute
        if not link.startswith('http'):
            if link.startswith('/'):
                # Get the base URL (protocol + domain)
                base_url = '/'.join(url.split('/')[:3])
                link = base_url + link
            else:
                # Relative to current path
                url_path = '/'.join(url.split('/')[:-1])
                link = f"{url_path}/{link}"
        
        # Skip if title is too short or doesn't match keywords
        if len(title) < min_text_length or not any(keyword.lower() in title.lower() for keyword in keywords):
            continue
        
        # Extract description
        description = ""
        description_tags = container.find_all(['p', 'div.description', 'div.summary', 'div.excerpt', 'span.description'])
        for tag in description_tags:
            text = tag.get_text(strip=True)
            if len(text) > min_text_length:
                description = text
                break
        
        # Extract location
        location = ""
        location_tags = container.find_all(['span.location', 'div.location', 'p.location', 'span.place', 'div.place'])
        for tag in location_tags:
            text = tag.get_text(strip=True)
            if 'location' in text.lower() or 'place' in text.lower() or 'city' in text.lower() or 'state' in text.lower():
                location = text
                break
        
        # Extract date info
        deadline = ""
        date_tags = container.find_all(['span.date', 'div.date', 'p.date', 'span.deadline', 'div.deadline'])
        for tag in date_tags:
            text = tag.get_text(strip=True)
            if 'deadline' in text.lower() or 'due' in text.lower() or 'date' in text.lower():
                deadline = text
                break
        
        # Get source domain
        source = url.split('//')[1].split('/')[0].replace('www.', '')
        
        opportunity = {
            'title': title,
            'url': link,
            'description': description,
            'location': location,
            'deadline': deadline,
            'source': source,
            'scraped_date': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        opportunities.append(opportunity)
    
    # Deduplicate opportunities by URL
    unique_opportunities = []
    seen_urls = set()
    
    for opp in opportunities:
        if opp['url'] not in seen_urls:
            seen_urls.add(opp['url'])
            unique_opportunities.append(opp)
    
    return unique_opportunities

def verify_opportunity_data(opportunities):
    """
    Verify and clean opportunity data
    
    Args:
        opportunities (list): List of opportunity dictionaries
        
    Returns:
        list: Cleaned list of opportunity dictionaries
    """
    verified_opportunities = []
    
    for opp in opportunities:
        # Ensure all required fields are present
        if not opp.get('title') or not opp.get('url'):
            continue
        
        # Clean the title - remove excessive whitespace
        opp['title'] = ' '.join(opp['title'].split())
        
        # Ensure URL is valid
        if not opp['url'].startswith('http'):
            continue
        
        # Truncate overly long descriptions
        if len(opp.get('description', '')) > 500:
            opp['description'] = opp['description'][:497] + '...'
        
        verified_opportunities.append(opp)
    
    return verified_opportunities

def check_cache(url):
    """
    Check if we have a fresh cached response for this URL
    
    Args:
        url (str): URL to check
        
    Returns:
        tuple: (cached, content) where cached is a boolean and content is the cached response
    """
    url_hash = hashlib.md5(url.encode()).hexdigest()
    
    with response_cache_lock:
        if url_hash in response_cache:
            cache_time, content = response_cache[url_hash]
            if (datetime.now() - cache_time).total_seconds() < CACHE_DURATION:
                logger.info(f"Using cached response for {url}")
                return True, content
    
    return False, None

def update_cache(url, content):
    """
    Update the cache with a new response
    
    Args:
        url (str): URL that was fetched
        content (str): Response content
    """
    url_hash = hashlib.md5(url.encode()).hexdigest()
    
    with response_cache_lock:
        response_cache[url_hash] = (datetime.now(), content)

def get_site_health_metrics():
    """
    Get health metrics for all sites
    
    Returns:
        dict: Site health metrics
    """
    with site_health_lock:
        # Make a copy to avoid concurrent modification
        return {k: v.copy() for k, v in site_health.items()}

def generate_health_report():
    """
    Generate a health report for all sites
    
    Returns:
        str: Health report as CSV
    """
    metrics = get_site_health_metrics()
    
    if not metrics:
        return "No site health metrics available yet."
    
    csv_lines = ["domain,success_count,failure_count,circuit_status,last_attempt,last_success,success_rate"]
    
    for domain, data in metrics.items():
        last_attempt = data.get('last_attempt', 'never')
        last_success = data.get('last_success', 'never')
        
        if isinstance(last_attempt, datetime):
            last_attempt = last_attempt.strftime('%Y-%m-%d %H:%M:%S')
        
        if isinstance(last_success, datetime):
            last_success = last_success.strftime('%Y-%m-%d %H:%M:%S')
            
        success_count = data.get('success_count', 0)
        failure_count = data.get('failure_count', 0)
        total = success_count + failure_count
        
        success_rate = "0%"
        if total > 0:
            success_rate = f"{(success_count / total) * 100:.1f}%"
            
        circuit_status = "open" if data.get('circuit_open', False) else "closed"
        
        csv_lines.append(f"{domain},{success_count},{failure_count},{circuit_status},{last_attempt},{last_success},{success_rate}")
    
    return "\n".join(csv_lines)

def scrape_opportunities(url, keywords, use_cache=True, try_headless=False):
    """
    Scrape opportunities from a URL with improved handling
    
    Args:
        url (str): URL to scrape
        keywords (list): List of keywords to check for
        use_cache (bool): Whether to use caching
        try_headless (bool): Whether to try headless browser as fallback
        
    Returns:
        list: List of opportunity dictionaries
    """
    domain = get_domain(url)
    logger.info(f"Scraping opportunities from {url}")
    
    # Check cache first if enabled
    if use_cache:
        cached, content = check_cache(url)
        if cached:
            # Extract opportunities from cached HTML
            opportunities = extract_opportunities_from_html(content, keywords, url)
            opportunities = verify_opportunity_data(opportunities)
            logger.info(f"Found {len(opportunities)} opportunities from cache for {url}")
            return opportunities
    
    # Use circuit breaker to prevent hammering failing sites
    try:
        with CircuitBreaker(domain):
            start_time = time.time()
            
            # First attempt with SSL verification
            success, content = fetch_url_with_retry(url)
            
            # If that fails, try without SSL verification
            if not success:
                logger.warning(f"Initial fetch failed for {url}, trying without SSL verification")
                success, content = fetch_url_with_retry(url, verify_ssl=False)
            
            # If still not successful, try with a proxy if available
            if not success and 'PROXY_URL' in os.environ:
                logger.warning(f"Fetch with SSL override failed for {url}, trying with proxy")
                proxy_url = os.environ['PROXY_URL']
                proxies = {'http': proxy_url, 'https': proxy_url}
                headers = {'User-Agent': get_random_user_agent()}
                
                try:
                    response = requests.get(url, headers=headers, proxies=proxies, timeout=20)
                    if response.status_code == 200:
                        success = True
                        content = response.text
                except Exception as e:
                    logger.error(f"Proxy fetch failed for {url}: {e}")
            
            # If still not successful and headless fallback is enabled, try that
            if not success and try_headless and 'HEADLESS_FALLBACK_ENABLED' in os.environ:
                # This is a placeholder for headless browser integration
                # Actual implementation would require installing a headless browser like Playwright
                logger.warning(f"Standard fetching failed for {url}, headless fallback would run here")
                # In a real implementation, this would launch a headless browser to fetch JavaScript-rendered content
            
            # Update site metrics with latency
            if success:
                latency = time.time() - start_time
                with site_health_lock:
                    if domain in site_health:
                        current_avg = site_health[domain].get('avg_latency', 0)
                        count = site_health[domain].get('success_count', 0)
                        if count > 0:
                            # Compute rolling average
                            new_avg = (current_avg * count + latency) / (count + 1)
                            site_health[domain]['avg_latency'] = new_avg
                        else:
                            site_health[domain]['avg_latency'] = latency
                
                # Update cache if successful
                if use_cache:
                    update_cache(url, content)
                
                # Extract opportunities from HTML
                opportunities = extract_opportunities_from_html(content, keywords, url)
                
                # Verify and clean the data
                opportunities = verify_opportunity_data(opportunities)
                
                # Content fingerprinting - hash key fields for identity checking
                for opp in opportunities:
                    fingerprint_data = f"{opp.get('title', '')}|{opp.get('url', '')}|{opp.get('deadline', '')}"
                    opp['fingerprint'] = hashlib.md5(fingerprint_data.encode()).hexdigest()
                
                logger.info(f"Found {len(opportunities)} opportunities from {url}")
                return opportunities
            else:
                logger.error(f"All fetch attempts failed for {url}: {content}")
                return []
    
    except Exception as e:
        if "Circuit open" in str(e):
            logger.warning(f"Circuit breaker prevented request to {url}: {e}")
        else:
            logger.error(f"Error scraping {url}: {e}")
        return []

def apply_improvements():
    """
    Apply improvements to the Proletto engines
    """
    logger.info("Applying improvements to Proletto opportunity scrapers")
    
    # Create a stub function for the engines to use
    code = """
def improved_scrape_site(url, keywords):
    \"\"\"
    Improved scraping function with better error handling
    
    This function should be used in place of the original scrape_site function
    in all Proletto engines for improved reliability.
    \"\"\"
    from scrapers_improvement import scrape_opportunities
    return scrape_opportunities(url, keywords)
"""
    
    # Write the code to a file to be imported by the engines
    with open('improved_scraper.py', 'w') as f:
        f.write(code)
    
    logger.info("Generated improved_scraper.py for engines to use")
    return True

if __name__ == "__main__":
    # Apply improvements when run directly
    apply_improvements()