#!/usr/bin/env python3
"""
Test script to generate site health metrics for our monitoring dashboard
This will scrape a few sites and ensure metrics are recorded
"""

import time
import logging
from datetime import datetime
from scrapers_improvement import (
    scrape_opportunities, 
    CircuitBreaker, 
    get_site_health_metrics,
    get_domain,
    generate_health_report
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_site_health')

# Test sites with expected behaviors
TEST_SITES = [
    {
        "url": "https://www.callforentry.org/",
        "keywords": ["grant", "opportunity", "residency"],
        "expect_success": True
    },
    {
        "url": "https://www.nyfa.org/opportunities/",
        "keywords": ["grant", "opportunity", "residency"],
        "expect_success": True
    },
    {
        "url": "https://nonexistent-domain-12345.com/",
        "keywords": ["art"],
        "expect_success": False
    },
    {
        "url": "https://www.submittable.com/discover/",
        "keywords": ["grant", "opportunity", "residency"],
        "expect_success": True
    }
]

def test_site_directly(site_info):
    """
    Test a site directly using the CircuitBreaker to ensure metrics are recorded
    """
    url = site_info["url"]
    domain = get_domain(url)
    keywords = site_info["keywords"]
    success = False
    
    logger.info(f"Testing site: {url}")
    
    try:
        # Use circuit breaker directly to ensure metrics are recorded
        with CircuitBreaker(domain):
            # Track start time for latency
            start_time = time.time()
            
            # Attempt to scrape the site
            opportunities = scrape_opportunities(url, keywords)
            
            # Record success if opportunities found or expected failure
            success = len(opportunities) > 0
            
            # Track latency
            latency = time.time() - start_time
            logger.info(f"Request completed in {latency:.2f} seconds")
            logger.info(f"Found {len(opportunities)} opportunities")
            
    except Exception as e:
        logger.error(f"Error testing {url}: {e}")
        success = False
        
    return {
        "url": url,
        "domain": domain,
        "success": success,
        "expected_success": site_info["expect_success"],
        "matches_expectation": success == site_info["expect_success"]
    }

def run_all_tests():
    """
    Run tests for all sites
    """
    results = []
    
    for site in TEST_SITES:
        result = test_site_directly(site)
        results.append(result)
        # Add a small delay between tests
        time.sleep(2)
        
    return results

def main():
    """
    Main function
    """
    logger.info("Starting site health test")
    
    # Run tests to generate metrics
    results = run_all_tests()
    
    # Display test results
    logger.info("=" * 50)
    logger.info("TEST RESULTS")
    logger.info("=" * 50)
    
    success_count = 0
    for result in results:
        status = "PASS" if result["matches_expectation"] else "FAIL"
        logger.info(f"{status} - {result['url']} - Success: {result['success']}")
        if result["matches_expectation"]:
            success_count += 1
            
    logger.info(f"Success rate: {success_count}/{len(results)}")
    
    # Display site health metrics
    logger.info("=" * 50)
    logger.info("SITE HEALTH METRICS")
    logger.info("=" * 50)
    
    health_metrics = get_site_health_metrics()
    if not health_metrics:
        logger.info("No site health metrics available yet.")
    else:
        for domain, metrics in health_metrics.items():
            circuit_status = "OPEN" if metrics.get("circuit_open", False) else "CLOSED"
            success_count = metrics.get("success_count", 0)
            failure_count = metrics.get("failure_count", 0)
            
            logger.info(f"Domain: {domain}")
            logger.info(f"  Circuit Status: {circuit_status}")
            logger.info(f"  Success Count: {success_count}")
            logger.info(f"  Failure Count: {failure_count}")
            
            if "last_success" in metrics and metrics["last_success"]:
                last_success = metrics["last_success"]
                if isinstance(last_success, datetime):
                    last_success = last_success.strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"  Last Success: {last_success}")
            
            logger.info("-" * 30)
    
    # Generate and save health report
    report = generate_health_report()
    report_file = f"scraper_health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(report_file, 'w') as f:
        f.write(report)
    
    logger.info(f"Health report written to {report_file}")
    
if __name__ == "__main__":
    main()