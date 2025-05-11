"""
Proletto AP Scheduler

This module provides advanced scheduling capabilities using APScheduler for the Proletto 
opportunity scrapers. It enables reliable execution of scrapers at scheduled intervals
in a "serverless" environment like Replit Always-On.

Key advantages over the previous schedule library:
1. Persistence - can save job state to a database
2. Advanced scheduling - more sophisticated scheduling patterns
3. Missed jobs handling - handles jobs that should have run while the app was down
4. More reliable execution - better error handling and monitoring

Usage:
1. Import into the main API or Flask app
2. Initialize the scheduler with init_scheduler()
3. Scheduler will automatically start scraper jobs according to a predefined schedule
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import apscheduler.schedulers.background
import apscheduler.triggers.interval
import apscheduler.triggers.cron
import apscheduler.triggers.combining
import apscheduler.events
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ap_scheduler.log"),
    ],
)
logger = logging.getLogger("ap_scheduler")

# Constants
STATE_FILE = "ap_scheduler_state.json"
DEFAULT_STATE = {
    "last_successful_run": None,
    "consecutive_failures": 0,
    "total_runs": 0,
    "total_successes": 0,
    "total_failures": 0,
    "last_run": None,
    "created_at": datetime.now().isoformat(),
}

# Global variables
scheduler = None
current_state = DEFAULT_STATE.copy()

# Scraper engine groups by membership tier
premium_states = ["california", "newyork", "texas"]
supporter_states = ["florida", "illinois", "massachusetts", "washington"]
other_states = ["colorado", "oregon", "pennsylvania"]
free_tier = ["social"]
# New special tier for Instagram ads scraper
special_tier = ["instagram_ads"]
all_engines = premium_states + supporter_states + other_states + free_tier + special_tier


def load_state() -> Dict[str, Any]:
    """Load the scheduler state from file"""
    if not Path(STATE_FILE).exists():
        logger.info(f"State file {STATE_FILE} not found, using default state")
        return DEFAULT_STATE.copy()
    
    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
            logger.info(f"Loaded state: {state}")
            return state
    except Exception as e:
        logger.error(f"Error loading state file: {e}")
        return DEFAULT_STATE.copy()


def save_state(state: Dict[str, Any]) -> None:
    """Save the scheduler state to file"""
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
            logger.info(f"Saved state: {state}")
    except Exception as e:
        logger.error(f"Error saving state file: {e}")


def job_listener(event):
    """Event listener for job events to track successes and failures"""
    global current_state, scheduler
    
    now = datetime.now().isoformat()
    job = scheduler.get_job(event.job_id) if scheduler and event.job_id else None
    
    # Initialize job metadata if needed
    if job:
        # For SQLAlchemyJobStore persistence, we use job.kwargs for metadata
        # as it gets stored in the database between restarts
        if not hasattr(job, 'metadata'):
            job.metadata = {}
        
        # Initialize metadata dictionary if not present in kwargs
        if 'metadata' not in job.kwargs:
            job.kwargs['metadata'] = {
                'consecutive_failures': 0,
                'total_runs': 0,
                'total_successes': 0,
                'total_failures': 0,
            }
        
        # Sync metadata between the in-memory attribute and persistent kwargs
        # This ensures we have access to metadata both ways and it persists properly
        job.metadata = job.kwargs['metadata']
    
    if event.code == apscheduler.events.EVENT_JOB_EXECUTED:
        logger.info(f"Job {event.job_id} executed successfully")
        
        # Update global state
        current_state["last_successful_run"] = now
        current_state["consecutive_failures"] = 0
        current_state["total_runs"] = current_state.get("total_runs", 0) + 1
        current_state["total_successes"] = current_state.get("total_successes", 0) + 1
        current_state["last_run"] = now
        
        # Update job-specific metadata
        if job:
            if not hasattr(job, 'metadata'):
                job.metadata = {}
            
            # Update the in-memory metadata
            job.metadata['last_run'] = now
            job.metadata['last_success'] = now
            job.metadata['consecutive_failures'] = 0
            # Ensure numeric values are stored as integers
            current_runs = int(job.metadata.get('total_runs', 0))
            current_successes = int(job.metadata.get('total_successes', 0))
            job.metadata['total_runs'] = current_runs + 1
            job.metadata['total_successes'] = current_successes + 1
            
            # Also update the persistent kwargs metadata for database storage
            job.kwargs['metadata'] = job.metadata.copy()
            
            # Ensure the job is updated in the job store
            scheduler.modify_job(job_id=job.id, kwargs=job.kwargs)
    
    elif event.code == apscheduler.events.EVENT_JOB_ERROR:
        logger.error(f"Job {event.job_id} failed with exception: {event.exception}")
        
        # Update global state
        current_state["consecutive_failures"] = current_state.get("consecutive_failures", 0) + 1
        current_state["total_runs"] = current_state.get("total_runs", 0) + 1
        current_state["total_failures"] = current_state.get("total_failures", 0) + 1
        current_state["last_run"] = now
        
        # Update job-specific metadata
        if job:
            if not hasattr(job, 'metadata'):
                job.metadata = {}
            
            # Update the in-memory metadata
            job.metadata['last_run'] = now
            job.metadata['last_failure'] = now
            job.metadata['last_error'] = str(event.exception)
            # Ensure numeric values are stored as integers
            current_failures = int(job.metadata.get('consecutive_failures', 0))
            current_runs = int(job.metadata.get('total_runs', 0))
            current_total_failures = int(job.metadata.get('total_failures', 0))
            job.metadata['consecutive_failures'] = current_failures + 1
            job.metadata['total_runs'] = current_runs + 1
            job.metadata['total_failures'] = current_total_failures + 1
            
            # Also update the persistent kwargs metadata for database storage
            job.kwargs['metadata'] = job.metadata.copy()
            
            # Ensure the job is updated in the job store
            scheduler.modify_job(job_id=job.id, kwargs=job.kwargs)
        
        # Import here to avoid circular imports
        try:
            from alerts import alert_scheduler_error
            alert_scheduler_error(
                scheduler_name="APScheduler",
                error_message=str(event.exception),
                job_id=event.job_id,
                next_run=str(job.next_run_time) if job and job.next_run_time else "unknown"
            )
        except ImportError:
            logger.warning("Could not import alert_scheduler_error from alerts module")
    
    save_state(current_state)


def run_scraper_job(scraper_name: str) -> bool:
    """Generic function to run a specific scraper engine"""
    start_time = time.time()
    logger.info(f"Running scraper job for {scraper_name}")
    
    # Attempt to import the specific engine module
    try:
        if scraper_name == "social":
            from proletto_engine_social import run
        elif scraper_name == "instagram_ads":
            # Import from the new scrapers package
            from scrapers.instagram_ads import run
        else:
            # Import the specific state engine dynamically
            module_name = f"proletto_engine_{scraper_name}"
            engine_module = __import__(module_name, fromlist=["run"])
            run = engine_module.run
    except ImportError as e:
        logger.error(f"Failed to import engine {scraper_name}: {e}")
        return False
    
    # Run the engine and track results
    try:
        result = run()
        success = result if isinstance(result, bool) else True
        
        duration = time.time() - start_time
        logger.info(f"Scraper job for {scraper_name} completed in {duration:.2f} seconds with {'success' if success else 'failure'}")
        
        # Send alert on success if needed
        if success:
            try:
                from alerts import alert_scraper_success
                alert_scraper_success(
                    scraper_name=scraper_name,
                    opportunities_count=-1,  # We don't know how many, the engine doesn't return this currently
                    duration=duration
                )
            except ImportError:
                logger.warning("Could not import alert_scraper_success from alerts module")
        
        return success
    except Exception as e:
        logger.error(f"Error running scraper {scraper_name}: {e}")
        
        # Send alert on error
        try:
            from alerts import alert_scraper_error
            alert_scraper_error(
                scraper_name=scraper_name,
                error_message=str(e),
                url=None,
                attempts=1
            )
        except ImportError:
            logger.warning("Could not import alert_scraper_error from alerts module")
        
        return False


def run_all_scrapers() -> bool:
    """Run all available scraper engines"""
    logger.info("Running all scraper engines")
    
    results = []
    for engine in all_engines:
        result = run_scraper_job(engine)
        results.append(result)
    
    success_rate = sum(results) / len(results) if results else 0
    logger.info(f"All scraper jobs completed with {success_rate:.0%} success rate")
    return success_rate > 0.5  # Consider overall success if more than half succeeded


def init_scheduler() -> apscheduler.schedulers.background.BackgroundScheduler:
    """Initialize and start the APScheduler"""
    global scheduler, current_state
    
    # Load state from file
    current_state = load_state()
    
    # Set up database URL for job persistence
    database_url = os.environ.get("DATABASE_URL")
    
    if database_url:
        try:
            # Configure the SQLAlchemy job store
            logger.info(f"Setting up SQLAlchemyJobStore for job persistence")
            
            # Create the schema for APScheduler tables if needed
            from sqlalchemy import create_engine
            engine = create_engine(database_url)
            
            # Import SQLAlchemyJobStore schema creation function
            from apscheduler.jobstores.sqlalchemy import create_tables
            
            # Create the tables (this is safe to call even if tables already exist)
            create_tables(engine, True)
            
            # Set up the job store with the database connection
            jobstores = {
                'default': SQLAlchemyJobStore(url=database_url)
            }
            
            # Create scheduler with persistent job store
            scheduler = apscheduler.schedulers.background.BackgroundScheduler(jobstores=jobstores)
            logger.info("Scheduler initialized with SQLAlchemy persistence")
        except Exception as e:
            logger.error(f"Failed to initialize SQLAlchemyJobStore: {e}")
            logger.warning("Falling back to in-memory job store")
            scheduler = apscheduler.schedulers.background.BackgroundScheduler()
    else:
        # Fall back to in-memory job store if no database URL is available
        logger.warning("No DATABASE_URL found, using in-memory job store (jobs will be lost on restart)")
        scheduler = apscheduler.schedulers.background.BackgroundScheduler()
    
    # Add listener for job events
    scheduler.add_listener(
        job_listener,
        apscheduler.events.EVENT_JOB_EXECUTED | apscheduler.events.EVENT_JOB_ERROR
    )
    
    # In development mode, don't actually run the jobs
    is_production = os.environ.get("REPLIT_DEPLOYMENT") == "true" or os.environ.get("ENABLE_SCHEDULER") == "true"
    if not is_production:
        logger.info("Running in development mode - jobs will be scheduled but not executed")
        scheduler.start()
        return scheduler
    
    # Premium tier state scrapers (3 times per week - Monday, Wednesday, Friday at 11am)
    premium_trigger = apscheduler.triggers.cron.CronTrigger(
        day_of_week="mon,wed,fri", hour=11, minute=0
    )
    for state in premium_states:
        # Initialize with empty metadata in kwargs for persistence
        initial_kwargs = {
            'metadata': {
                'consecutive_failures': 0,
                'total_runs': 0,
                'total_successes': 0,
                'total_failures': 0,
                'tier': 'premium'
            }
        }
        scheduler.add_job(
            run_scraper_job,
            premium_trigger,
            id=f"premium_{state}",
            args=[state],
            kwargs=initial_kwargs,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=3600,  # 1 hour grace time for misfires
        )
    
    # Supporter tier state scrapers (2 times per week - Tuesday, Thursday at 11am)
    supporter_trigger = apscheduler.triggers.cron.CronTrigger(
        day_of_week="tue,thu", hour=11, minute=0
    )
    for state in supporter_states:
        # Initialize with empty metadata in kwargs for persistence
        initial_kwargs = {
            'metadata': {
                'consecutive_failures': 0,
                'total_runs': 0,
                'total_successes': 0,
                'total_failures': 0,
                'tier': 'supporter'
            }
        }
        scheduler.add_job(
            run_scraper_job,
            supporter_trigger,
            id=f"supporter_{state}",
            args=[state],
            kwargs=initial_kwargs,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=3600,
        )
    
    # Other state scrapers (1 time per week - Saturday at 11am)
    other_trigger = apscheduler.triggers.cron.CronTrigger(
        day_of_week="sat", hour=11, minute=0
    )
    for state in other_states:
        # Initialize with empty metadata in kwargs for persistence
        initial_kwargs = {
            'metadata': {
                'consecutive_failures': 0,
                'total_runs': 0,
                'total_successes': 0,
                'total_failures': 0,
                'tier': 'free'
            }
        }
        scheduler.add_job(
            run_scraper_job,
            other_trigger,
            id=f"other_{state}",
            args=[state],
            kwargs=initial_kwargs,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=3600,
        )
    
    # Free tier social media scraper (every 6 hours)
    social_trigger = apscheduler.triggers.interval.IntervalTrigger(hours=6)
    # Initialize with empty metadata in kwargs for persistence
    social_kwargs = {
        'metadata': {
            'consecutive_failures': 0,
            'total_runs': 0,
            'total_successes': 0,
            'total_failures': 0,
            'tier': 'free'
        }
    }
    scheduler.add_job(
        run_scraper_job,
        social_trigger,
        id="free_social",
        args=["social"],
        kwargs=social_kwargs,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    
    # Instagram Ads scraper (hourly)
    instagram_trigger = apscheduler.triggers.interval.IntervalTrigger(hours=1)
    # Initialize with empty metadata in kwargs for persistence
    instagram_kwargs = {
        'metadata': {
            'consecutive_failures': 0,
            'total_runs': 0,
            'total_successes': 0,
            'total_failures': 0,
            'tier': 'special'
        }
    }
    scheduler.add_job(
        run_scraper_job,
        instagram_trigger,
        id="instagram_ads",
        args=["instagram_ads"],
        kwargs=instagram_kwargs,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    
    # Weekly comprehensive run (all engines) - Sunday at 1am
    weekly_trigger = apscheduler.triggers.cron.CronTrigger(
        day_of_week="sun", hour=1, minute=0
    )
    # Initialize with empty metadata in kwargs for persistence
    weekly_kwargs = {
        'metadata': {
            'consecutive_failures': 0,
            'total_runs': 0,
            'total_successes': 0,
            'total_failures': 0,
            'tier': 'system',
            'job_type': 'comprehensive'
        }
    }
    scheduler.add_job(
        run_all_scrapers,
        weekly_trigger,
        id="weekly_all",
        kwargs=weekly_kwargs,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=7200,  # 2 hour grace time for the big job
    )
    
    # Recovery job - when consecutive failures reach a threshold
    def check_and_run_recovery():
        """Check if we need to run a recovery job due to consecutive failures"""
        global current_state
        if current_state.get("consecutive_failures", 0) >= 3:
            logger.warning(f"Detected {current_state.get('consecutive_failures')} consecutive failures, running recovery job")
            # Run the social engine only for recovery to avoid overloading
            run_scraper_job("social")
    
    recovery_trigger = apscheduler.triggers.interval.IntervalTrigger(hours=1)
    # Initialize recovery job with metadata
    recovery_kwargs = {
        'metadata': {
            'consecutive_failures': 0,
            'total_runs': 0,
            'total_successes': 0,
            'total_failures': 0,
            'tier': 'system',
            'job_type': 'recovery'
        }
    }
    scheduler.add_job(
        check_and_run_recovery,
        recovery_trigger,
        id="recovery_check",
        kwargs=recovery_kwargs,
        max_instances=1,
        coalesce=True,
    )
    
    # Register the maintenance bot listener
    try:
        from maintenance.bot import register_with_scheduler
        logger.info("Registering maintenance bot with scheduler")
        register_with_scheduler(scheduler)
        logger.info("Maintenance bot registered successfully")
    except ImportError as e:
        logger.error(f"Failed to import maintenance bot: {e}")
        logger.warning("Maintenance bot will not be active - auto-retry and GitHub issue creation disabled")
    
    # Start the scheduler
    logger.info("Starting APScheduler for Proletto engines in production mode")
    scheduler.start()
    
    # Run social engine immediately on startup for quick feedback
    if os.environ.get("RUN_ON_STARTUP", "true").lower() == "true":
        # Initialize startup job with metadata
        startup_kwargs = {
            'metadata': {
                'consecutive_failures': 0,
                'total_runs': 0,
                'total_successes': 0,
                'total_failures': 0,
                'tier': 'system',
                'job_type': 'startup'
            }
        }
        scheduler.add_job(
            run_scraper_job,
            args=["social"],
            kwargs=startup_kwargs,
            id="startup_job",
            trigger=apscheduler.triggers.interval.IntervalTrigger(seconds=5),
            next_run_time=datetime.now(),
            max_instances=1,
            coalesce=True,
        )
    
    return scheduler


def shutdown_scheduler() -> None:
    """Shut down the scheduler"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        logger.info("APScheduler shut down")


def get_scheduler_info() -> Dict[str, Any]:
    """Get information about the current scheduler state"""
    global scheduler, current_state
    
    if not scheduler:
        return {"status": "not_initialized"}
    
    jobs = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time.isoformat() if job.next_run_time else None
        
        # Get job metadata if available
        job_metadata = {}
        # First check the in-memory metadata
        if hasattr(job, 'metadata'):
            job_metadata = job.metadata
        # Then check the persistent kwargs metadata as a fallback
        elif 'metadata' in job.kwargs:
            job_metadata = job.kwargs['metadata']
        
        jobs.append({
            "id": job.id,
            "next_run": next_run,
            "state": "scheduled" if next_run else "paused",
            "func": str(job.func.__name__ if hasattr(job.func, '__name__') else job.func),
            "args": str(job.args),
            "kwargs": str(job.kwargs),
            "last_run": job_metadata.get('last_run', None),
            "last_success": job_metadata.get('last_success', None),
            "last_failure": job_metadata.get('last_failure', None),
            "consecutive_failures": job_metadata.get('consecutive_failures', 0),
            "total_runs": job_metadata.get('total_runs', 0),
        })
    
    return {
        "status": "running" if scheduler.running else "stopped",
        "jobs_count": len(scheduler.get_jobs()),
        "jobs": jobs,
        "state": current_state,
        "is_production": os.environ.get("REPLIT_DEPLOYMENT") == "true" or os.environ.get("ENABLE_SCHEDULER") == "true",
        "started_at": getattr(scheduler, 'start_time', None),
        "timezone": str(getattr(scheduler, 'timezone', 'UTC')),
    }