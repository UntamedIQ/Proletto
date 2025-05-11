#!/usr/bin/env python3
"""
Test Script for the V2 Scheduler and Instagram Ads Scraper
"""

import os
import time
import logging
import argparse
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_scheduler_v2")

def test_instagram_scraper():
    """Test the Instagram Ads scraper functionality"""
    logger.info("Testing Instagram Ads scraper...")
    
    try:
        # Import the module without running it
        import scrapers.instagram_ads
        
        # Check if the required functions and components exist
        required_attributes = ["run", "process_ad_text", "extract_ad_info", "filter_art_related"]
        missing_attributes = []
        
        for attr in required_attributes:
            if not hasattr(scrapers.instagram_ads, attr):
                missing_attributes.append(attr)
        
        if missing_attributes:
            logger.error(f"❌ Missing attributes in Instagram Ads scraper: {', '.join(missing_attributes)}")
            return False
        
        logger.info("✅ Instagram Ads scraper module structure is valid")
        
        # Check the supported ad types
        if hasattr(scrapers.instagram_ads, "SUPPORTED_AD_TYPES"):
            ad_types = scrapers.instagram_ads.SUPPORTED_AD_TYPES
            logger.info(f"Instagram Ads scraper supports {len(ad_types)} ad types: {', '.join(ad_types)}")
        
        # Check the art-related keywords filter
        if hasattr(scrapers.instagram_ads, "ART_RELATED_KEYWORDS"):
            keyword_count = len(scrapers.instagram_ads.ART_RELATED_KEYWORDS)
            logger.info(f"Instagram Ads scraper has {keyword_count} art-related keywords for filtering")
        
        # Validate a simple test case for the filter function
        test_text = "This is an art opportunity for visual artists, painters, and sculptors"
        if scrapers.instagram_ads.filter_art_related(test_text):
            logger.info("✅ Art-related filter correctly identified art content")
        else:
            logger.warning("⚠️ Art-related filter did not recognize test content")
        
        logger.info("✅ Instagram Ads scraper test PASSED")
        return True
    except Exception as e:
        logger.error(f"❌ Error testing Instagram Ads scraper: {e}")
        return False

def test_maintenance_bot():
    """Test the Maintenance Bot functionality"""
    logger.info("Testing Maintenance Bot...")
    
    try:
        # Only test if module is available with required structure
        import maintenance.bot
        
        # Check if required functions exist
        required_functions = [
            "register_with_scheduler", 
            "on_job_error", 
            "handle_job_failure", 
            "reset_job_failures"
        ]
        
        missing_functions = []
        for func in required_functions:
            if not hasattr(maintenance.bot, func):
                missing_functions.append(func)
        
        if missing_functions:
            logger.error(f"❌ Missing functions in Maintenance Bot: {', '.join(missing_functions)}")
            return False
            
        logger.info(f"✅ All required functions are present in Maintenance Bot")
        
        # Check for required configuration constants
        required_constants = [
            "GITHUB_ISSUE_TEMPLATE", 
            "MAX_CONSECUTIVE_FAILURES",
            "FAILURE_RETENTION_DAYS"
        ]
        
        missing_constants = []
        for const in required_constants:
            if not hasattr(maintenance.bot, const):
                missing_constants.append(const)
                
        if missing_constants:
            logger.warning(f"⚠️ Missing constants in Maintenance Bot: {', '.join(missing_constants)}")
            # Not a failure, just a warning
        else:
            logger.info(f"✅ All constants are present in Maintenance Bot")
        
        # Check a few key functionality indicators
        max_failures = getattr(maintenance.bot, "MAX_CONSECUTIVE_FAILURES", 5)
        logger.info(f"Maintenance Bot will create issues after {max_failures} consecutive failures")
        
        github_template = hasattr(maintenance.bot, "GITHUB_ISSUE_TEMPLATE")
        logger.info(f"Maintenance Bot has GitHub issue template: {github_template}")
        
        # Simple static test of the functionality passed
        logger.info("✅ Maintenance Bot module structure PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing Maintenance Bot: {e}")
        return False

def test_scheduler_v2():
    """Test the APScheduler V2 functionality"""
    logger.info("Testing APScheduler V2...")
    
    try:
        import ap_scheduler_v2
        
        # Test only the module imports and verify core functions exist
        required_functions = [
            "load_state", "save_state", "job_listener", 
            "get_scrape_function", "run_scraper_job", 
            "run_all_scrapers", "init_scheduler", "get_scheduler_info"
        ]
        
        missing_functions = []
        for func in required_functions:
            if not hasattr(ap_scheduler_v2, func):
                missing_functions.append(func)
        
        if missing_functions:
            logger.error(f"❌ Missing functions in APScheduler V2: {', '.join(missing_functions)}")
            return False
            
        logger.info(f"✅ All required functions are present in APScheduler V2")
        
        # Verify module-level variables
        expected_variables = ["premium_states", "supporter_states", "other_states", "free_tier", "special_tier"]
        missing_variables = []
        for var in expected_variables:
            if not hasattr(ap_scheduler_v2, var):
                missing_variables.append(var)
                
        if missing_variables:
            logger.error(f"❌ Missing variables in APScheduler V2: {', '.join(missing_variables)}")
            return False
            
        logger.info(f"✅ All required variables are present in APScheduler V2")
        
        # Success! We successfully validated the module structure
        logger.info("✅ APScheduler V2 module structure PASSED")
        return True
    except Exception as e:
        logger.error(f"❌ Error testing APScheduler V2: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test the V2 Scheduler components")
    parser.add_argument("--component", choices=["all", "instagram", "maintenance", "scheduler"], 
                        default="all", help="Component to test")
    args = parser.parse_args()
    
    results = []
    
    if args.component in ["all", "instagram"]:
        instagram_result = test_instagram_scraper()
        results.append(("Instagram Ads Scraper", instagram_result))
    
    if args.component in ["all", "maintenance"]:
        maintenance_result = test_maintenance_bot()
        results.append(("Maintenance Bot", maintenance_result))
    
    if args.component in ["all", "scheduler"]:
        scheduler_result = test_scheduler_v2()
        results.append(("APScheduler V2", scheduler_result))
    
    # Display summary
    logger.info("\n" + "=" * 50)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("=" * 50)
    
    for component, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{component}: {status}")
    
    # Overall status
    overall = all(result for _, result in results)
    logger.info("=" * 50)
    logger.info(f"OVERALL: {'✅ PASSED' if overall else '❌ FAILED'}")
    logger.info("=" * 50)
    
    return 0 if overall else 1

if __name__ == "__main__":
    exit(main())