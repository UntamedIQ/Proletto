#!/usr/bin/env python3
"""
Test Asynchronous Scrapers

This script tests the new asynchronous scraper implementation with a small sample
of URLs to verify correct functionality.
"""

import os
import sys
import time
import asyncio
import logging
import argparse
import nest_asyncio
from datetime import datetime

# Apply nest_asyncio to allow running asyncio code in environments that already have an event loop
nest_asyncio.apply()

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_async")

# Test URL sets
TEST_URLS = {
    "instagram": [
        "https://www.instagram.com/explore/tags/artopportunity/",
        "https://www.instagram.com/explore/tags/artgrant/"
    ],
    "california": [
        "https://www.cac.ca.gov/opportunities/",
        "https://www.artjobs.com/california/"
    ],
    "new_york": [
        "https://www.nyfa.org/opportunities/",
        "https://www.artjobs.com/new-york/"
    ],
    "general": [
        "https://www.callforentry.org/",
        "https://artistsnetwork.org/art-competitions/",
        "https://www.artquest.org.uk/opportunities/"
    ]
}

async def test_instagram_ads_async():
    """Test the Instagram Ads async scraper"""
    logger.info("Testing Instagram Ads async scraper...")
    
    try:
        from scrapers.instagram_ads_async import InstagramAdsAsyncScraper
        
        # Create scraper instance
        scraper = InstagramAdsAsyncScraper()
        
        # Run with test URLs
        start_time = time.time()
        result = await scraper.run_scraper(TEST_URLS["instagram"])
        duration = time.time() - start_time
        
        logger.info(f"Instagram Ads async scraper completed in {duration:.2f}s")
        logger.info(f"Found {result} opportunities")
        
        return {
            "name": "Instagram Ads",
            "urls_tested": len(TEST_URLS["instagram"]),
            "duration": duration,
            "opportunities": result,
            "success": True
        }
    
    except Exception as e:
        logger.error(f"Error testing Instagram Ads async scraper: {e}")
        return {
            "name": "Instagram Ads",
            "urls_tested": len(TEST_URLS["instagram"]),
            "duration": 0,
            "opportunities": 0,
            "success": False,
            "error": str(e)
        }

async def test_art_opportunities_async(state=None, urls=None):
    """Test the Art Opportunities async scraper"""
    name = state.capitalize() if state else "General"
    logger.info(f"Testing {name} Art Opportunities async scraper...")
    
    try:
        from scrapers.art_opportunities_async import ArtOpportunitiesAsyncScraper
        
        # Determine which URLs to use
        test_urls = urls or TEST_URLS.get(state.lower() if state else "general")
        
        # Create scraper instance
        scraper = ArtOpportunitiesAsyncScraper(
            engine_name=state or "test",
            urls=test_urls,
            state=state
        )
        
        # Run the scraper
        start_time = time.time()
        result = await scraper.run_scraper(test_urls)
        duration = time.time() - start_time
        
        logger.info(f"{name} Art Opportunities async scraper completed in {duration:.2f}s")
        logger.info(f"Found {result} opportunities")
        
        return {
            "name": f"{name} Art Opportunities",
            "urls_tested": len(test_urls),
            "duration": duration,
            "opportunities": result,
            "success": True
        }
    
    except Exception as e:
        logger.error(f"Error testing {name} Art Opportunities async scraper: {e}")
        return {
            "name": f"{name} Art Opportunities",
            "urls_tested": len(urls or TEST_URLS.get(state.lower() if state else "general")),
            "duration": 0,
            "opportunities": 0,
            "success": False,
            "error": str(e)
        }

async def run_all_tests():
    """Run all scraper tests"""
    results = []
    
    # Test Instagram Ads scraper
    results.append(await test_instagram_ads_async())
    
    # Test California scraper
    results.append(await test_art_opportunities_async("california"))
    
    # Test New York scraper
    results.append(await test_art_opportunities_async("new_york"))
    
    # Test general Art Opportunities scraper
    results.append(await test_art_opportunities_async())
    
    return results

def print_results(results):
    """Print test results in a user-friendly format"""
    print("\n" + "=" * 80)
    print(" ASYNC SCRAPER TEST RESULTS ".center(80, "="))
    print("=" * 80 + "\n")
    
    for result in results:
        status = "✓ PASS" if result["success"] else "✗ FAIL"
        print(f"{result['name']} Scraper: {status}")
        print(f"  URLs tested: {result['urls_tested']}")
        if result["success"]:
            print(f"  Duration: {result['duration']:.2f}s")
            print(f"  Opportunities found: {result['opportunities']}")
        else:
            print(f"  Error: {result.get('error', 'Unknown')}")
        print()
    
    # Overall assessment
    success_count = sum(1 for r in results if r["success"])
    print(f"Overall: {success_count}/{len(results)} tests passed")
    
    if success_count == len(results):
        print("\nAll async scrapers are functioning correctly!")
        print("Ready to activate the async scheduler system.")
    else:
        print("\nSome async scrapers have issues that need to be fixed.")
        print("Please check the error messages and update the implementation.")

def main():
    parser = argparse.ArgumentParser(description="Test Asynchronous Scrapers")
    parser.add_argument("--instagram", action="store_true", help="Test only Instagram Ads scraper")
    parser.add_argument("--california", action="store_true", help="Test only California scraper")
    parser.add_argument("--new-york", action="store_true", help="Test only New York scraper")
    parser.add_argument("--general", action="store_true", help="Test only general Art Opportunities scraper")
    parser.add_argument("--url", type=str, help="Test with a specific URL")
    parser.add_argument("--all", action="store_true", help="Test all scrapers")
    
    args = parser.parse_args()
    
    # If no arguments provided, run all tests
    if not (args.instagram or args.california or args.new_york or args.general or args.url or args.all):
        args.all = True
    
    print("=" * 80)
    print(" PROLETTO ASYNC SCRAPER TESTS ".center(80, "="))
    print("=" * 80)
    print("Testing the new asynchronous scraper implementation...\n")
    
    try:
        results = []
        loop = asyncio.get_event_loop()
        
        if args.instagram or args.all:
            results.append(loop.run_until_complete(test_instagram_ads_async()))
        
        if args.california or args.all:
            results.append(loop.run_until_complete(test_art_opportunities_async("california")))
        
        if args.new_york or args.all:
            results.append(loop.run_until_complete(test_art_opportunities_async("new_york")))
        
        if args.general or args.all:
            results.append(loop.run_until_complete(test_art_opportunities_async()))
        
        if args.url:
            results.append(loop.run_until_complete(test_art_opportunities_async(
                state=None, urls=[args.url])))
        
        print_results(results)
        
        # Return success if all tests passed
        return all(r["success"] for r in results)
    
    except Exception as e:
        logger.error(f"Error during tests: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)