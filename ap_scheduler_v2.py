#!/usr/bin/env python3
"""
Proletto AP Scheduler V2

A streamlined, improved scheduler for Proletto's opportunity scrapers.
This version follows a more modular approach with direct imports and cleaner structure.

Key improvements:
1. Direct imports of scraper functions instead of dynamic imports
2. Cleaner job configuration 
3. Health check endpoint for monitoring
4. Maintenance bot integration for error handling
5. Persistent SQLAlchemy job store
"""

import os
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from sqlalchemy import create_engine

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("proletto_scheduler")

# Import scraper run functions
# State-specific engines
try:
    from proletto_engine_california import run as scrape_california
    from proletto_engine_newyork import run as scrape_newyork
    from proletto_engine_texas import run as scrape_texas
    from proletto_engine_florida import run as scrape_florida
    from proletto_engine_illinois import run as scrape_illinois
    from proletto_engine_massachusetts import run as scrape_massachusetts
    from proletto_engine_washington import run as scrape_washington
    from proletto_engine_colorado import run as scrape_colorado
    from proletto_engine_oregon import run as scrape_oregon
    from proletto_engine_pennsylvania import run as scrape_pennsylvania
    from proletto_engine_social import run as scrape_social
except ImportError as e:
    logger.warning(f"Failed to import one or more state engines: {e}")

# Import special scrapers
try:
    # Updated Instagram scraper that finds both ads and regular art opportunity posts
    from scrapers.instagram_ads import run as scrape_instagram_ads
except ImportError as e:
    logger.warning(f"Failed to import Instagram scraper: {e}")

# Import maintenance bot for auto error handling and GitHub issue creation
try:
    import maintenance.bot
    maintenance_bot_available = True
except ImportError:
    logger.warning("Maintenance bot not available - error handling will be limited")
    maintenance_bot_available = False

# Configuration
STATE_FILE = "scheduler_state.json"
DEFAULT_STATE = {
    "last_successful_run": None,
    "consecutive_failures": 0,
    "total_runs": 0,
    "total_successes": 0,
    "total_failures": 0,
    "last_run": None,
    "created_at": datetime.now().isoformat(),
}

# Scheduler categories for organization
premium_states = ["california", "newyork", "texas"]
supporter_states = ["florida", "illinois", "massachusetts", "washington"]
other_states = ["colorado", "oregon", "pennsylvania"]
free_tier = ["social"]
special_tier = ["instagram_ads"]
all_engines = premium_states + supporter_states + other_states + free_tier + special_tier

# Global variables
scheduler = None
current_state = DEFAULT_STATE.copy()
app = Flask(__name__)

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
        job.metadata = job.kwargs['metadata']
    
    if event.code == EVENT_JOB_EXECUTED:
        logger.info(f"Job {event.job_id} executed successfully")
        
        # Update global state
        current_state["last_successful_run"] = now
        current_state["consecutive_failures"] = 0
        current_state["total_runs"] = current_state.get("total_runs", 0) + 1
        current_state["total_successes"] = current_state.get("total_successes", 0) + 1
        current_state["last_run"] = now
        
        # Update job-specific metadata
        if job:
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
    
    elif event.code == EVENT_JOB_ERROR:
        logger.error(f"Job {event.job_id} failed with exception: {event.exception}")
        
        # Update global state
        current_state["consecutive_failures"] = current_state.get("consecutive_failures", 0) + 1
        current_state["total_runs"] = current_state.get("total_runs", 0) + 1
        current_state["total_failures"] = current_state.get("total_failures", 0) + 1
        current_state["last_run"] = now
        
        # Update job-specific metadata
        if job:
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

def get_scrape_function(engine_name: str):
    """Get the appropriate scrape function based on engine name"""
    scraper_map = {
        # State engines
        "california": scrape_california,
        "newyork": scrape_newyork,
        "texas": scrape_texas,
        "florida": scrape_florida,
        "illinois": scrape_illinois,
        "massachusetts": scrape_massachusetts,
        "washington": scrape_washington,
        "colorado": scrape_colorado,
        "oregon": scrape_oregon,
        "pennsylvania": scrape_pennsylvania,
        # Special engines
        "social": scrape_social,
        "instagram_ads": scrape_instagram_ads,
    }
    
    return scraper_map.get(engine_name)

def run_scraper_job(engine_name: str) -> bool:
    """Run a specific scraper engine"""
    start_time = time.time()
    logger.info(f"Running scraper job for {engine_name}")
    
    # Get the appropriate scrape function
    run_func = get_scrape_function(engine_name)
    if not run_func:
        logger.error(f"No scrape function found for engine {engine_name}")
        return False
    
    # Run the engine and track results
    try:
        result = run_func()
        success = result if isinstance(result, bool) else True
        
        duration = time.time() - start_time
        logger.info(f"Scraper job for {engine_name} completed in {duration:.2f} seconds with {'success' if success else 'failure'}")
        
        # Send alert on success if needed
        if success:
            try:
                from alerts import alert_scraper_success
                alert_scraper_success(
                    scraper_name=engine_name,
                    opportunities_count=-1,  # We don't know how many, the engine doesn't return this currently
                    duration=duration
                )
            except ImportError:
                logger.warning("Could not import alert_scraper_success from alerts module")
        
        return success
    except Exception as e:
        logger.error(f"Error running scraper {engine_name}: {e}")
        
        # Send alert on error
        try:
            from alerts import alert_scraper_error
            alert_scraper_error(
                scraper_name=engine_name,
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

def aggregate_metrics():
    """Aggregate metrics from all scrapers for reporting"""
    logger.info("Aggregating scraper metrics")
    # Implementation would depend on what metrics you want to track
    # For example, success rates, average run times, opportunity counts, etc.
    try:
        from scraper_health import aggregate_all
        aggregate_all()
    except ImportError:
        logger.warning("Could not import aggregate_all from scraper_health module")

def init_scheduler(app) -> BackgroundScheduler:
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
            engine = create_engine(database_url)
            
            # Create the SQLAlchemy job store which will create tables as needed
            job_store = SQLAlchemyJobStore(url=database_url)
            
            # Set up the job store with the database connection
            jobstores = {
                'default': SQLAlchemyJobStore(url=database_url)
            }
            
            # Create scheduler with persistent job store
            scheduler = BackgroundScheduler(jobstores=jobstores)
            logger.info("Scheduler initialized with SQLAlchemy persistence")
        except Exception as e:
            logger.error(f"Failed to initialize SQLAlchemyJobStore: {e}")
            logger.warning("Falling back to in-memory job store")
            scheduler = BackgroundScheduler()
    else:
        # Fall back to in-memory job store if no database URL is available
        logger.warning("No DATABASE_URL found, using in-memory job store (jobs will be lost on restart)")
        scheduler = BackgroundScheduler()
    
    # Add listener for job events
    scheduler.add_listener(
        job_listener,
        EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
    )
    
    # Register maintenance bot if available
    if maintenance_bot_available:
        try:
            from maintenance.bot import register_with_scheduler
            logger.info("Registering maintenance bot with scheduler")
            register_with_scheduler(scheduler)
            logger.info("Maintenance bot registered successfully")
        except Exception as e:
            logger.error(f"Failed to register maintenance bot: {e}")
    
    # In development mode, don't actually run the jobs
    is_production = os.environ.get("REPLIT_DEPLOYMENT") == "true" or os.environ.get("ENABLE_SCHEDULER") == "true"
    if not is_production:
        logger.info("Running in development mode - jobs will be scheduled but not executed")
        scheduler.start()
        return scheduler
    
    # Schedule premium tier state scrapers (3 times per week - Monday, Wednesday, Friday at 11am)
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
            'cron',
            day_of_week="mon,wed,fri",
            hour=11,
            minute=0,
            id=f"premium_{state}",
            args=[state],
            kwargs=initial_kwargs,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=3600,  # 1 hour grace time for misfires
        )
    
    # Schedule supporter tier state scrapers (2 times per week - Tuesday, Thursday at 11am)
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
            'cron',
            day_of_week="tue,thu",
            hour=11,
            minute=0,
            id=f"supporter_{state}",
            args=[state],
            kwargs=initial_kwargs,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=3600,
        )
    
    # Schedule other state scrapers (1 time per week - Saturday at 11am)
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
            'cron',
            day_of_week="sat",
            hour=11,
            minute=0,
            id=f"other_{state}",
            args=[state],
            kwargs=initial_kwargs,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=3600,
        )
    
    # Schedule social media scraper (every 6 hours)
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
        'interval',
        hours=6,
        id="free_social",
        args=["social"],
        kwargs=social_kwargs,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    
    # Schedule Instagram Ads scraper (hourly)
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
        'interval',
        hours=1,
        id="instagram_ads",
        args=["instagram_ads"],
        kwargs=instagram_kwargs,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    
    # Schedule weekly comprehensive run (all engines) - Sunday at 1am
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
        'cron',
        day_of_week="sun",
        hour=1,
        minute=0,
        id="weekly_all",
        kwargs=weekly_kwargs,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=7200,  # 2 hour grace time for the big job
    )
    
    # Schedule metrics aggregation job - every day at 00:05
    scheduler.add_job(
        aggregate_metrics,
        'cron',
        hour=0,
        minute=5,
        id="aggregate_metrics",
        max_instances=1,
        coalesce=True,
    )
    
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
            trigger='date',
            run_date=datetime.now(),
            max_instances=1,
            coalesce=True,
        )
    
    return scheduler

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

# Flask routes for monitoring and management
@app.route('/healthz')
def healthz():
    """Health check endpoint for monitoring"""
    if not scheduler or not scheduler.running:
        return 'Scheduler not running', 500
    return 'OK', 200

@app.route('/admin/api/scheduler-status')
def scheduler_status():
    """Get detailed scheduler status"""
    return get_scheduler_info()

@app.route('/admin/api/scheduler/jobs/<job_id>/pause')
def pause_job(job_id):
    """Pause a job"""
    if not scheduler:
        return {"error": "Scheduler not initialized"}, 500
    
    job = scheduler.get_job(job_id)
    if not job:
        return {"error": f"Job {job_id} not found"}, 404
    
    job.pause()
    return {"status": "paused", "job_id": job_id}

@app.route('/admin/api/scheduler/jobs/<job_id>/resume')
def resume_job(job_id):
    """Resume a paused job"""
    if not scheduler:
        return {"error": "Scheduler not initialized"}, 500
    
    job = scheduler.get_job(job_id)
    if not job:
        return {"error": f"Job {job_id} not found"}, 404
    
    job.resume()
    return {"status": "resumed", "job_id": job_id}

@app.route('/admin/api/scheduler/jobs/<job_id>/run-now')
def run_job_now(job_id):
    """Run a job immediately"""
    if not scheduler:
        return {"error": "Scheduler not initialized"}, 500
    
    job = scheduler.get_job(job_id)
    if not job:
        return {"error": f"Job {job_id} not found"}, 404
    
    scheduler.add_job(
        job.func,
        args=job.args,
        kwargs=job.kwargs,
        id=f"{job_id}_manual_{int(time.time())}",
        trigger='date',
        run_date=datetime.now(),
        max_instances=1,
        coalesce=True,
    )
    return {"status": "triggered", "job_id": job_id}

@app.route('/admin/api/scheduler/run-all')
def run_all_jobs():
    """Run all scraper jobs immediately"""
    if not scheduler:
        return {"error": "Scheduler not initialized"}, 500
    
    scheduler.add_job(
        run_all_scrapers,
        trigger='date',
        run_date=datetime.now(),
        id=f"run_all_manual_{int(time.time())}",
        max_instances=1,
        coalesce=True,
    )
    return {"status": "triggered", "job_id": "all_jobs"}

def main():
    """Main entry point for the application"""
    # Initialize the scheduler
    init_scheduler(app)
    
    # Start the Flask app
    port = int(os.environ.get('PORT', 5001))
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()