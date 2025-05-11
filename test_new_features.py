#!/usr/bin/env python3
"""
Test script for the new Instagram Ads Scraper and Maintenance Bot features.
This script tests:
1. The Instagram Ads Scraper (standalone execution)
2. The Maintenance Bot (attaching to a scheduler and handling errors)
"""

import os
import sys
import logging
import time
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.events import EVENT_JOB_ERROR

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_script")

def test_instagram_ads_scraper():
    """Test the Instagram Ads Scraper in standalone mode"""
    logger.info("Testing Instagram Ads Scraper...")
    
    try:
        from scrapers.instagram_ads import run as run_instagram_scraper
        
        # Run the scraper
        result = run_instagram_scraper()
        
        if result:
            logger.info("✅ Instagram Ads Scraper test PASSED")
        else:
            logger.error("❌ Instagram Ads Scraper test FAILED - returned False")
            
    except ImportError as e:
        logger.error(f"❌ Instagram Ads Scraper test FAILED - import error: {e}")
    except Exception as e:
        logger.error(f"❌ Instagram Ads Scraper test FAILED - error: {e}")

def failing_job():
    """A job that fails on purpose for testing the maintenance bot"""
    logger.info("Running failing job for testing...")
    raise ValueError("This job is designed to fail for testing purposes")

def test_maintenance_bot():
    """Test the Maintenance Bot with a failing job"""
    logger.info("Testing Maintenance Bot...")
    
    try:
        # Create a test scheduler
        scheduler = BlockingScheduler()
        
        # Register the maintenance bot
        from maintenance.bot import register_with_scheduler
        register_with_scheduler(scheduler)
        
        # Make sure required environment variables are set for testing
        if not os.environ.get("SLACK_BOT_TOKEN"):
            logger.warning("SLACK_BOT_TOKEN environment variable not set, alerts will fail")
            
        if not os.environ.get("SLACK_CHANNEL_ID"):
            logger.warning("SLACK_CHANNEL_ID environment variable not set, alerts will fail")
        
        if not os.environ.get("GITHUB_REPO") or not os.environ.get("GITHUB_TOKEN"):
            logger.warning("GITHUB_REPO or GITHUB_TOKEN environment variables not set, GitHub issues won't be created")
        
        # Add a failing job to test the bot's retry mechanism
        scheduler.add_job(
            failing_job,
            'interval',
            seconds=5,
            id='test_failing_job',
            max_instances=1
        )
        
        # Start the scheduler (in a separate thread so we can stop it)
        scheduler.start()
        
        # Let it run for 30 seconds to test retry behavior
        logger.info("Running scheduler for 20 seconds to test retry behavior...")
        time.sleep(20)
        
        # Shutdown
        scheduler.shutdown()
        logger.info("✅ Maintenance Bot test completed - check logs for successful retries")
        
    except ImportError as e:
        logger.error(f"❌ Maintenance Bot test FAILED - import error: {e}")
    except Exception as e:
        logger.error(f"❌ Maintenance Bot test FAILED - error: {e}")

def main():
    """Run all tests"""
    logger.info("Starting tests for new Instagram Ads Scraper and Maintenance Bot features")
    
    if "--instagram-only" in sys.argv:
        test_instagram_ads_scraper()
    elif "--maintenance-only" in sys.argv:
        test_maintenance_bot()
    else:
        test_instagram_ads_scraper()
        test_maintenance_bot()
    
    logger.info("All tests completed")

if __name__ == "__main__":
    main()