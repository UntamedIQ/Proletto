#!/usr/bin/env python3
"""
Proletto Engine Test Script

This script tests the enhanced scraper functionality with various configurations
and test cases to ensure reliability and resilience.
"""

import sys
import json
import time
import logging
import argparse
from scrapers_improvement import scrape_opportunities, generate_health_report, get_site_health_metrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_scraper')

# Test cases for different scenarios
TEST_CASES = [
    {
        "name": "Standard HTTP Site",
        "url": "https://www.callforentry.org/",
        "keywords": ["grant", "opportunity", "residency", "fellowship"]
    },
    {
        "name": "SSL Certificate Issues",
        "url": "https://self-signed-cert.example.com",
        "keywords": ["art", "job", "opportunity"],
        "expect_failure": True
    },
    {
        "name": "JavaScript-Heavy Site",
        "url": "https://www.submittable.com/discover/",
        "keywords": ["grant", "opportunity", "residency"],
        "use_headless": True
    },
    {
        "name": "Rate Limited Site",
        "url": "https://www.nyfa.org/opportunities/",
        "keywords": ["grant", "opportunity", "residency"],
        "rapid_requests": 5
    },
    {
        "name": "DNS Failure Test",
        "url": "https://nonexistent-domain-12345.com/",
        "keywords": ["art"],
        "expect_failure": True
    }
]

def load_config():
    """Load configuration from file"""
    try:
        with open('scraper_config.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning("Config file not found or invalid, using defaults")
        return {}

def run_test_case(test_case, config=None):
    """Run a single test case"""
    name = test_case.get("name", "Unnamed Test")
    url = test_case.get("url")
    keywords = test_case.get("keywords", [])
    expect_failure = test_case.get("expect_failure", False)
    rapid_requests = test_case.get("rapid_requests", 1)
    use_headless = test_case.get("use_headless", False)
    
    logger.info(f"Running test: {name}")
    logger.info(f"URL: {url}")
    logger.info(f"Keywords: {keywords}")
    
    start_time = time.time()
    success = False
    opportunities = []
    
    try:
        # For rapid request testing
        for i in range(rapid_requests):
            if i > 0:
                logger.info(f"Making rapid request {i+1}/{rapid_requests}")
                time.sleep(0.5)  # Small delay between rapid requests
                
            opportunities = scrape_opportunities(url, keywords, try_headless=use_headless)
            
            if opportunities:
                success = True
                logger.info(f"Found {len(opportunities)} opportunities")
                break
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        success = False
    
    duration = time.time() - start_time
    
    # Determine if test passed based on expectations
    if expect_failure:
        passed = not success
        outcome = "PASSED (Expected Failure)" if passed else "FAILED (Unexpected Success)"
    else:
        passed = success
        outcome = "PASSED" if passed else "FAILED"
    
    logger.info(f"Test {outcome}")
    logger.info(f"Duration: {duration:.2f} seconds")
    
    return {
        "name": name,
        "url": url,
        "passed": passed,
        "outcome": outcome,
        "duration": duration,
        "opportunities_found": len(opportunities) if opportunities else 0
    }

def run_all_tests():
    """Run all test cases"""
    config = load_config()
    results = []
    
    logger.info("Starting scraper test suite")
    start_time = time.time()
    
    for test_case in TEST_CASES:
        result = run_test_case(test_case, config)
        results.append(result)
        # Add a small delay between tests
        time.sleep(1)
    
    duration = time.time() - start_time
    
    # Calculate summary statistics
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    
    logger.info("=" * 50)
    logger.info("TEST SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total Tests: {total}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Success Rate: {(passed/total)*100:.1f}%")
    logger.info(f"Total Duration: {duration:.2f} seconds")
    
    # Print site health metrics
    logger.info("=" * 50)
    logger.info("SITE HEALTH METRICS")
    logger.info("=" * 50)
    
    health_metrics = get_site_health_metrics()
    for domain, metrics in health_metrics.items():
        circuit_status = "OPEN" if metrics.get("circuit_open", False) else "CLOSED"
        success_count = metrics.get("success_count", 0)
        failure_count = metrics.get("failure_count", 0)
        
        logger.info(f"Domain: {domain}")
        logger.info(f"  Circuit Status: {circuit_status}")
        logger.info(f"  Success Count: {success_count}")
        logger.info(f"  Failure Count: {failure_count}")
        
        if "last_success" in metrics and metrics["last_success"]:
            logger.info(f"  Last Success: {metrics['last_success']}")
        
        logger.info("-" * 30)
    
    return results

def custom_test(url, keywords):
    """Run a custom test with user-provided URL and keywords"""
    logger.info(f"Running custom test for URL: {url}")
    
    if not keywords:
        keywords = ["grant", "opportunity", "residency", "fellowship", "job"]
        
    logger.info(f"Using keywords: {keywords}")
    
    test_case = {
        "name": "Custom Test",
        "url": url,
        "keywords": keywords
    }
    
    return run_test_case(test_case)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Test Proletto Engine Scrapers')
    parser.add_argument('--url', help='Test a specific URL')
    parser.add_argument('--keywords', nargs='+', help='Keywords to use for custom test')
    parser.add_argument('--test-all', action='store_true', help='Run all test cases')
    parser.add_argument('--report', action='store_true', help='Generate health report')
    
    args = parser.parse_args()
    
    if args.report:
        report = generate_health_report()
        print(report)
        filename = f"health_report_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        with open(filename, 'w') as f:
            f.write(report)
        logger.info(f"Health report written to {filename}")
    elif args.url:
        custom_test(args.url, args.keywords)
    elif args.test_all:
        run_all_tests()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()