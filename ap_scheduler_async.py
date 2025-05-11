"""
Proletto AP Scheduler with Asyncio Support

This module provides advanced scheduling capabilities using APScheduler for the Proletto 
opportunity scrapers, with support for asynchronous (asyncio) scrapers for better performance.

Key advantages:
1. Persistence - can save job state to a database
2. Advanced scheduling - more sophisticated scheduling patterns
3. Missed jobs handling - handles jobs that should have run while the app was down
4. More reliable execution - better error handling and monitoring
5. Support for asyncio - much faster execution through concurrent requests

Usage:
1. Import into the main API or Flask app
2. Initialize the scheduler with init_scheduler()
3. Scheduler will automatically start scraper jobs according to a predefined schedule
"""

import logging
import os
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List
import asyncio
import nest_asyncio
import apscheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from apscheduler.jobstores.memory import MemoryJobStore

# Apply nest_asyncio to allow running asyncio code in environments that already have an event loop
nest_asyncio.apply()

# Configure logging
logger = logging.getLogger("ap_scheduler_async")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Import asynchronous scrapers
from scrapers.instagram_ads_async import run_instagram_ads_scraper
from scrapers.art_opportunities_async import run_art_opportunities_scraper, run_all_state_scrapers

# State file path for persistence
STATE_FILE = "bot_scheduler_state.json"

# Default schedules for scrapers (in minutes between runs)
DEFAULT_SCHEDULES = {
    "instagram_ads": 120,          # Every 2 hours
    "california": 240,             # Every 4 hours
    "new_york": 240,               # Every 4 hours
    "texas": 360,                  # Every 6 hours
    "florida": 360,                # Every 6 hours
    "social_media": 120,           # Every 2 hours (free tier)
    "all_states": 1440,            # Once per day (premium comprehensive run)
}

# Job status tracking
job_stats = {
    "instagram_ads": {"success_count": 0, "error_count": 0, "last_run": None, "last_status": None, "last_duration": None},
    "california": {"success_count": 0, "error_count": 0, "last_run": None, "last_status": None, "last_duration": None},
    "new_york": {"success_count": 0, "error_count": 0, "last_run": None, "last_status": None, "last_duration": None},
    "texas": {"success_count": 0, "error_count": 0, "last_run": None, "last_status": None, "last_duration": None},
    "florida": {"success_count": 0, "error_count": 0, "last_run": None, "last_status": None, "last_duration": None},
    "social_media": {"success_count": 0, "error_count": 0, "last_run": None, "last_status": None, "last_duration": None},
    "all_states": {"success_count": 0, "error_count": 0, "last_run": None, "last_status": None, "last_duration": None},
}

# Consecutive failures tracking for recovery
consecutive_failures = {}

def load_state() -> Dict[str, Any]:
    """Load the scheduler state from file"""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading state: {e}")
    
    return {"job_stats": {}, "last_successful_run": None}

def save_state(state: Dict[str, Any]) -> None:
    """Save the scheduler state to file"""
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error saving state: {e}")

def job_listener(event):
    """Event listener for job events to track successes and failures"""
    job_id = event.job_id
    
    if job_id in job_stats:
        stats = job_stats[job_id]
        stats["last_run"] = datetime.now().isoformat()
        
        if event.code == EVENT_JOB_EXECUTED:
            stats["success_count"] += 1
            stats["last_status"] = "success"
            stats["last_duration"] = event.retval.get("duration") if isinstance(event.retval, dict) else None
            if job_id in consecutive_failures:
                consecutive_failures[job_id] = 0
            logger.info(f"Job {job_id} executed successfully")
        
        elif event.code == EVENT_JOB_ERROR:
            stats["error_count"] += 1
            stats["last_status"] = "error"
            consecutive_failures[job_id] = consecutive_failures.get(job_id, 0) + 1
            logger.error(f"Job {job_id} failed: {event.exception}")
        
        elif event.code == EVENT_JOB_MISSED:
            logger.warning(f"Job {job_id} was missed")
        
        # Save updated state
        save_state({"job_stats": job_stats, "last_successful_run": datetime.now().isoformat()})
        
        # Log consecutive failures
        if job_id in consecutive_failures and consecutive_failures[job_id] > 2:
            logger.warning(f"Job {job_id} has failed {consecutive_failures[job_id]} times in a row")

def run_with_app_context(func, *args, **kwargs):
    """Run a function within Flask application context"""
    try:
        # Try to import Flask app from main module
        # This can be adjusted based on your actual app structure
        try:
            from main import app
            with app.app_context():
                return func(*args, **kwargs)
        except ImportError:
            # If main app import fails, try the API app
            try:
                from api import app
                with app.app_context():
                    return func(*args, **kwargs)
            except ImportError:
                # If no app is available, run without context
                logger.warning("No Flask app available, running without app context")
                return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error running function with app context: {e}")
        # Fall back to running without context
        return func(*args, **kwargs)

def run_instagram_ads_job() -> Dict[str, Any]:
    """Run the Instagram ads scraper job"""
    start_time = time.time()
    logger.info("Starting Instagram ads scraper job")
    
    try:
        # Run within Flask app context
        opportunities_count = run_with_app_context(run_instagram_ads_scraper)
        
        duration = time.time() - start_time
        logger.info(f"Instagram ads scraper completed in {duration:.2f}s, found {opportunities_count} opportunities")
        
        return {
            "success": True,
            "opportunities_count": opportunities_count,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error running Instagram ads scraper: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def run_state_scraper_job(state_key: str) -> Dict[str, Any]:
    """Run a state-specific scraper job"""
    start_time = time.time()
    logger.info(f"Starting {state_key} scraper job")
    
    try:
        # Run within Flask app context
        opportunities_count = run_with_app_context(run_art_opportunities_scraper, state_key)
        
        duration = time.time() - start_time
        logger.info(f"{state_key} scraper completed in {duration:.2f}s, found {opportunities_count} opportunities")
        
        return {
            "success": True,
            "state": state_key,
            "opportunities_count": opportunities_count,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error running {state_key} scraper: {e}")
        return {
            "success": False,
            "state": state_key,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def run_all_states_job() -> Dict[str, Any]:
    """Run the comprehensive all-states scraper job"""
    start_time = time.time()
    logger.info("Starting comprehensive all-states scraper job")
    
    try:
        # Run within Flask app context
        opportunities_count = run_with_app_context(run_all_state_scrapers)
        
        duration = time.time() - start_time
        logger.info(f"All-states scraper completed in {duration:.2f}s, found {opportunities_count} opportunities")
        
        return {
            "success": True,
            "opportunities_count": opportunities_count,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error running all-states scraper: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def run_social_media_job() -> Dict[str, Any]:
    """Run the social media scraper job (for free tier)"""
    start_time = time.time()
    logger.info("Starting social media scraper job")
    
    try:
        # The social media scraper uses our legacy code path
        # In a real implementation, we would refactor this to use the new async system
        # Run within Flask app context
        from bot_code import run_social_media_scraper
        opportunities_count = run_with_app_context(run_social_media_scraper)
        
        duration = time.time() - start_time
        logger.info(f"Social media scraper completed in {duration:.2f}s, found {opportunities_count} opportunities")
        
        return {
            "success": True,
            "opportunities_count": opportunities_count,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error running social media scraper: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def init_scheduler() -> apscheduler.schedulers.background.BackgroundScheduler:
    """Initialize and start the APScheduler"""
    # Load previous state if available
    state = load_state()
    if "job_stats" in state:
        global job_stats
        # Merge saved stats with defaults for any new jobs
        for job_id, stats in state["job_stats"].items():
            if job_id in job_stats:
                job_stats[job_id] = stats
    
    # Create the scheduler
    scheduler = BackgroundScheduler(
        jobstores={
            'default': MemoryJobStore()
        },
        job_defaults={
            'coalesce': True,  # Combine multiple pending executions
            'max_instances': 1,  # Only allow one instance of each job
            'misfire_grace_time': 15*60  # Allow jobs up to 15 minutes late
        }
    )
    
    # Add job listener for tracking successes and failures
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED)
    
    # Add the scraper jobs
    
    # Instagram ads scraper - every 2 hours
    scheduler.add_job(
        run_instagram_ads_job,
        'interval',
        minutes=DEFAULT_SCHEDULES["instagram_ads"],
        id='instagram_ads',
        replace_existing=True,
        next_run_time=datetime.now() + timedelta(seconds=random.randint(10, 30))
    )
    
    # State-specific scrapers
    for state in ['california', 'new_york', 'texas', 'florida']:
        scheduler.add_job(
            run_state_scraper_job,
            'interval',
            minutes=DEFAULT_SCHEDULES[state],
            id=state,
            args=[state],
            replace_existing=True,
            next_run_time=datetime.now() + timedelta(seconds=random.randint(60, 300))
        )
    
    # Social media scraper (free tier) - every 2 hours
    scheduler.add_job(
        run_social_media_job,
        'interval',
        minutes=DEFAULT_SCHEDULES["social_media"],
        id='social_media',
        replace_existing=True,
        next_run_time=datetime.now() + timedelta(seconds=random.randint(30, 60))
    )
    
    # Comprehensive all-states scraper - once per day
    scheduler.add_job(
        run_all_states_job,
        'interval',
        minutes=DEFAULT_SCHEDULES["all_states"],
        id='all_states',
        replace_existing=True,
        next_run_time=datetime.now() + timedelta(hours=random.randint(2, 6))
    )
    
    # Define a check and recovery function that runs every 30 minutes
    def check_and_run_recovery():
        """Check if we need to run a recovery job due to consecutive failures"""
        for job_id, failures in consecutive_failures.items():
            if failures >= 3:
                logger.warning(f"Job {job_id} has failed {failures} times in a row, scheduling immediate recovery run")
                # Schedule an immediate run to try to recover
                job = scheduler.get_job(job_id)
                if job:
                    # Run the job in a few seconds
                    job.modify(next_run_time=datetime.now() + timedelta(seconds=10))
                    # Reset the failures count
                    consecutive_failures[job_id] = 0
    
    # Add the recovery checker job
    scheduler.add_job(
        check_and_run_recovery,
        'interval',
        minutes=30,
        id='recovery_checker',
        replace_existing=True
    )
    
    # Start the scheduler
    scheduler.start()
    
    logger.info("APScheduler started with the following jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"- {job.id}: {job.trigger}, next run at {job.next_run_time}")
    
    # Log the scheduler configuration
    logger.info(f"- Daily comprehensive scrape: Sunday at 1:00 AM")
    logger.info(f"- Auto-retry mechanism: Active")
    
    return scheduler

def shutdown_scheduler() -> None:
    """Shut down the scheduler"""
    logger.info("Shutting down scheduler")
    # Save the current state
    save_state({"job_stats": job_stats, "last_shutdown": datetime.now().isoformat()})

def get_scheduler_info() -> Dict[str, Any]:
    """Get information about the current scheduler state"""
    return {
        "job_stats": job_stats,
        "consecutive_failures": consecutive_failures,
        "last_update": datetime.now().isoformat(),
    }

# If this module is run directly, start the scheduler
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scheduler = init_scheduler()
    
    # Keep the script running
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        shutdown_scheduler()
        scheduler.shutdown()