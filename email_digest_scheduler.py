"""
Email Digest Scheduler

This module handles scheduling of weekly digest emails to Proletto Pro subscribers.
It uses APScheduler to manage the schedule and triggers the email_digest module.
"""

import os
import logging
from datetime import datetime, timedelta
import json

# APScheduler imports
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import current_app

from email_digest import run_weekly_digest, test_digest_email

# Set up logging
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None
scheduler_state_file = 'digest_scheduler_state.json'


def initialize_digest_scheduler(app):
    """
    Initialize the email digest scheduler.
    
    Args:
        app: The Flask application context
    """
    global scheduler
    
    if scheduler:
        logger.info("Email digest scheduler already initialized")
        return
    
    try:
        # Don't activate in development mode unless specifically requested
        if os.environ.get('FLASK_ENV') == 'development' and not os.environ.get('FORCE_DIGEST_SCHEDULER'):
            logger.info("Email digest scheduler not activated in development environment")
            return
            
        with app.app_context():
            # Create the scheduler
            scheduler = BackgroundScheduler()
            
            # Add the daily digest job that checks user preferences - runs every day at 7am
            scheduler.add_job(
                run_daily_digest_job,
                trigger=CronTrigger(hour=7, minute=0),
                id='daily_digest',
                name='Daily Digest Emails',
                replace_existing=True,
                args=[app]
            )
            
            # Add job to retry failed digests (checks every 4 hours)
            scheduler.add_job(
                retry_failed_digests_job,
                trigger=CronTrigger(hour='*/4'),
                id='retry_digests',
                name='Retry Failed Digests',
                replace_existing=True,
                args=[app]
            )
            
            # Start the scheduler
            scheduler.start()
            
            # Load and log the scheduler state
            save_scheduler_state()
            
            logger.info("Email digest scheduler initialized successfully with dynamic user preferences")
            
    except Exception as e:
        logger.error(f"Error initializing email digest scheduler: {e}")
        if scheduler:
            scheduler.shutdown()
            scheduler = None


def run_daily_digest_job(app):
    """
    Run the daily digest email job based on user preferences.
    This job checks which users should receive digests today based on their preferences.
    
    Args:
        app: The Flask application
    """
    with app.app_context():
        try:
            # Get the current day of week (0=Monday, 6=Sunday)
            current_day = datetime.utcnow().weekday()
            logger.info(f"Running daily digest job for weekday {current_day}")
            
            # Import inside to avoid circular imports
            from models import db, User
            
            # Get eligible Pro/Premium users whose preferred day matches today
            eligible_users = User.query.filter(
                User.membership_level.in_(['pro', 'premium']),
                User.digest_enabled == True,
                User.digest_day_of_week == current_day,
                User.email.isnot(None),
                # Add other filtering criteria as needed
            ).all()
            
            logger.info(f"Found {len(eligible_users)} users for today's digest (day {current_day})")
            
            # Process each eligible user
            success_count = 0
            error_count = 0
            
            for user in eligible_users:
                try:
                    from email_digest import get_recommendations_for_user, send_weekly_digest
                    
                    # Get recommendations for this user
                    recommendations = get_recommendations_for_user(user.id, limit=5)
                    
                    # Skip if no recommendations
                    if not recommendations:
                        logger.warning(f"No recommendations available for user {user.id}")
                        continue
                    
                    # Send the digest email
                    if send_weekly_digest(user.id, recommendations):
                        success_count += 1
                        # Reset failure count on success
                        user.digest_failure_count = 0
                        user.last_digest_sent = datetime.utcnow()
                    else:
                        error_count += 1
                        # Increment failure count
                        user.digest_failure_count += 1
                        
                    # Save changes
                    db.session.commit()
                        
                except Exception as e:
                    logger.error(f"Error processing digest for user {user.id}: {e}")
                    error_count += 1
                    
                    # Increment failure count
                    try:
                        user.digest_failure_count += 1
                        db.session.commit()
                    except Exception as db_error:
                        logger.error(f"Error updating failure count: {db_error}")
            
            logger.info(f"Daily digest completed - {success_count} successes, {error_count} errors")
            
            # Update the scheduler state
            save_scheduler_state(last_run=datetime.utcnow())
            
        except Exception as e:
            logger.error(f"Error in daily digest job: {e}")
            
            # Update the scheduler state with the error
            save_scheduler_state(
                last_run=datetime.utcnow(),
                error=str(e)
            )


def retry_failed_digests_job(app):
    """
    Retry sending digest emails to users with failed attempts.
    This job runs periodically to retry digests that failed to send.
    
    Args:
        app: The Flask application
    """
    with app.app_context():
        try:
            logger.info("Running retry job for failed digest emails")
            
            # Import inside to avoid circular imports
            from models import db, User
            
            # Get users with failed digest attempts (1-3 failures)
            # We don't retry more than 3 times to avoid spamming users with problematic emails
            retry_users = User.query.filter(
                User.digest_failure_count.between(1, 3),
                User.digest_enabled == True,
                User.email.isnot(None),
                User.membership_level.in_(['pro', 'premium'])
            ).all()
            
            logger.info(f"Found {len(retry_users)} users with failed digests to retry")
            
            # Process each user
            success_count = 0
            error_count = 0
            
            for user in retry_users:
                try:
                    from email_digest import get_recommendations_for_user, send_weekly_digest
                    
                    # Get recommendations
                    recommendations = get_recommendations_for_user(user.id, limit=5)
                    
                    # Skip if no recommendations
                    if not recommendations:
                        logger.warning(f"No recommendations available for retry user {user.id}")
                        continue
                    
                    # Send the digest email
                    if send_weekly_digest(user.id, recommendations):
                        success_count += 1
                        # Reset failure count on success
                        user.digest_failure_count = 0
                        user.last_digest_sent = datetime.utcnow()
                    else:
                        error_count += 1
                        # Increment failure count
                        user.digest_failure_count += 1
                        
                    # Save changes
                    db.session.commit()
                    
                except Exception as e:
                    logger.error(f"Error processing retry digest for user {user.id}: {e}")
                    error_count += 1
            
            logger.info(f"Retry digest job completed - {success_count} successes, {error_count} errors")
            
        except Exception as e:
            logger.error(f"Error in retry digest job: {e}")


def run_digest_job(app):
    """
    Legacy method for backward compatibility.
    Run the digest email job with the Flask app context.
    
    Args:
        app: The Flask application
    """
    with app.app_context():
        try:
            logger.info("Running scheduled email digest job (legacy method)")
            run_weekly_digest()
            
            # Update the scheduler state
            save_scheduler_state(last_run=datetime.utcnow())
            
        except Exception as e:
            logger.error(f"Error in digest email scheduler job: {e}")
            
            # Update the scheduler state with the error
            save_scheduler_state(
                last_run=datetime.utcnow(),
                error=str(e)
            )


def trigger_digest_job_now(app):
    """
    Manually trigger the digest email job immediately.
    
    Args:
        app: The Flask application
        
    Returns:
        True if job was triggered, False otherwise
    """
    if not scheduler:
        logger.error("Cannot trigger digest job - scheduler not initialized")
        return False
        
    with app.app_context():
        try:
            # Add a one-time job to run immediately
            scheduler.add_job(
                run_digest_job,
                trigger='date',
                run_date=datetime.now() + timedelta(seconds=5),
                id='manual_digest',
                name='Manual Digest Emails',
                replace_existing=True,
                args=[app]
            )
            
            logger.info("Manual digest job triggered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error triggering manual digest job: {e}")
            return False


def send_test_digest_email(app, user_id):
    """
    Send a test digest email to a specific user.
    
    Args:
        app: The Flask application
        user_id: The ID of the user to send test email to
        
    Returns:
        True if email was sent successfully, False otherwise
    """
    with app.app_context():
        try:
            logger.info(f"Sending test digest email to user {user_id}")
            result = test_digest_email(user_id)
            return result
        except Exception as e:
            logger.error(f"Error sending test digest email: {e}")
            return False


def get_digest_scheduler_info():
    """
    Get information about the digest scheduler state.
    
    Returns:
        Dictionary with scheduler information
    """
    info = {
        'active': scheduler is not None and scheduler.running,
        'state_file': scheduler_state_file,
        'current_time': datetime.utcnow().isoformat(),
    }
    
    # Try to load state information
    try:
        if os.path.exists(scheduler_state_file):
            with open(scheduler_state_file, 'r') as f:
                state = json.load(f)
                info.update(state)
    except Exception as e:
        info['error'] = f"Error loading state file: {str(e)}"
    
    # Add job information if scheduler is active
    if scheduler and scheduler.running:
        jobs = []
        for job in scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        info['jobs'] = jobs
    
    return info


def save_scheduler_state(last_run=None, error=None):
    """
    Save the current state of the scheduler to the state file.
    
    Args:
        last_run: Last run time (optional)
        error: Error message if any (optional)
    """
    state = {
        'scheduler_active': scheduler is not None and scheduler.running,
        'updated_at': datetime.utcnow().isoformat()
    }
    
    if last_run:
        state['last_run'] = last_run.isoformat()
    
    if error:
        state['last_error'] = error
    
    # Add job information if scheduler is active
    if scheduler and scheduler.running:
        jobs = []
        for job in scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None
            })
        state['jobs'] = jobs
    
    try:
        with open(scheduler_state_file, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving scheduler state: {e}")


def shutdown_scheduler():
    """
    Shutdown the scheduler if it's running.
    """
    global scheduler
    
    if scheduler and scheduler.running:
        try:
            scheduler.shutdown()
            logger.info("Email digest scheduler shutdown successfully")
        except Exception as e:
            logger.error(f"Error shutting down email digest scheduler: {e}")
    
    scheduler = None


if __name__ == "__main__":
    # This section allows testing the scheduler directly
    import flask
    app = flask.Flask(__name__)
    with app.app_context():
        # Initialize scheduler
        initialize_digest_scheduler(app)
        
        # Print scheduler info
        print(json.dumps(get_digest_scheduler_info(), indent=2))
        
        # Test manual trigger
        trigger_digest_job_now(app)