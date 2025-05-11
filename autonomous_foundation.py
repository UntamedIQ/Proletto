# autonomous_foundation.py
"""
Autonomous Foundation Module for Proletto Dragon Core

This module provides the foundation for autonomous operation, including:
- Job scheduling and monitoring
- Snapshot management for data persistence
- Health and rescue endpoints via Flask Blueprints
"""

import os
import threading
import json
from functools import wraps
from datetime import datetime
from flask import Blueprint, jsonify, current_app

# Initialize blueprints
health_bp = Blueprint('health', __name__)
rescue_bp = Blueprint('rescue', __name__)

# Initialize global scheduler
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
except ImportError:
    print("APScheduler not available - some functionality will be limited")
    scheduler = None

# Snapshot management functions
def load_snapshot():
    """Load opportunity data from snapshot file"""
    try:
        if os.path.exists('data/snapshot.json'):
            with open('data/snapshot.json', 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error loading snapshot: {e}")
        return []

def write_snapshot(opportunities):
    """Write opportunity data to snapshot file"""
    try:
        # Ensure the directory exists
        os.makedirs('data', exist_ok=True)
        with open('data/snapshot.json', 'w') as f:
            json.dump(opportunities, f)
        print(f"Snapshot updated with {len(opportunities)} opportunities")
        return True
    except Exception as e:
        print(f"Error writing snapshot: {e}")
        return False

# Job monitoring decorator
def monitored_job(max_retries=3):
    """Decorator for jobs that should be monitored for failures and retried"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    result = func(*args, **kwargs)
                    # Reset fail count on success
                    wrapper.fail_count = 0 if hasattr(wrapper, 'fail_count') else 0
                    return result
                except Exception as e:
                    retries += 1
                    # Track failures
                    wrapper.fail_count = getattr(wrapper, 'fail_count', 0) + 1
                    print(f"Job {func.__name__} failed (attempt {retries}/{max_retries}): {e}")
                    
                    # If we've exhausted retries, log and alert
                    if retries >= max_retries:
                        error_msg = f"Job {func.__name__} failed after {max_retries} attempts: {str(e)}"
                        print(error_msg)
                        try:
                            # Try to alert if available
                            from alerts import alert_scheduler_error
                            alert_scheduler_error(
                                func.__name__, 
                                str(e), 
                                job_id=getattr(func, 'job_id', None)
                            )
                        except Exception as alert_error:
                            print(f"Could not send alert: {alert_error}")
            return None
        
        # Track failures
        wrapper.fail_count = 0
        wrapper.__monitored__ = True
        return wrapper
    return decorator

# Watchdog thread to monitor job health
def monitor_jobs():
    """
    Monitor health of scheduled jobs and restart the scheduler if needed.
    This runs as a separate thread.
    """
    if not scheduler:
        print("Scheduler not available - watchdog disabled")
        return
        
    print("Starting scheduler watchdog thread")
    while True:
        import time
        # Check every 5 minutes
        time.sleep(300)
        
        # Check if scheduler is running
        if not scheduler.running:
            print("Scheduler stopped - attempting to restart")
            try:
                scheduler.start()
                print("Scheduler restarted successfully")
            except Exception as e:
                print(f"Failed to restart scheduler: {e}")
                # Try to recreate scheduler
                try:
                    global scheduler
                    scheduler.shutdown(wait=False)
                    scheduler = BackgroundScheduler()
                    scheduler.start()
                    print("Scheduler recreated and restarted")
                except Exception as e2:
                    print(f"Failed to recreate scheduler: {e2}")
        
        # Check for problematic jobs
        restart_needed = False
        for job in scheduler.get_jobs():
            job_func = job.func
            if hasattr(job_func, '__monitored__') and hasattr(job_func, 'fail_count'):
                if job_func.fail_count >= 3:  # If failed 3+ times
                    print(f"Job {job.id} is problematic (failed {job_func.fail_count} times)")
                    restart_needed = True
        
        # Restart scheduler if needed
        if restart_needed:
            try:
                print("Restarting scheduler due to problematic jobs")
                scheduler.shutdown(wait=False)
                scheduler = BackgroundScheduler()
                scheduler.start()
                print("Scheduler restarted due to problematic jobs")
                
                # Alert if available
                try:
                    from alerts import alert_system_health
                    alert_system_health(custom_metrics={"scheduler_restart": "due to problematic jobs"})
                except Exception:
                    pass
            except Exception as e:
                print(f"Failed to restart scheduler: {e}")

# Blueprint routes for health checks
@health_bp.route('/system-health')
def system_health():
    """System health check endpoint"""
    try:
        # Check cache if available
        cache_status = "unknown"
        try:
            from cache_utils import cache
            if cache:
                cache.set('health_check', 'ok', timeout=10)
                cache_status = "ok" if cache.get('health_check') == 'ok' else "failed"
        except Exception as e:
            cache_status = f"error: {str(e)}"
        
        # Check database if available
        db_status = "unknown"
        try:
            from models import db
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            db_status = "ok"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # Check scheduler
        scheduler_status = "ok" if scheduler and scheduler.running else "not running"
        
        # Check snapshot
        snapshot_count = len(load_snapshot())
        
        # Get system metrics if available
        metrics = {}
        try:
            import psutil
            metrics['cpu'] = psutil.cpu_percent()
            metrics['memory'] = psutil.virtual_memory().percent
            metrics['disk'] = psutil.disk_usage('/').percent
        except ImportError:
            pass
        
        # Build response
        health_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'cache': cache_status,
            'database': db_status,
            'scheduler': scheduler_status,
            'snapshot_count': snapshot_count,
            'system_metrics': metrics
        }
        
        # Overall status
        health_data['status'] = 'healthy'
        if cache_status != 'ok' or db_status != 'ok' or scheduler_status != 'ok':
            health_data['status'] = 'degraded'
        
        return jsonify(health_data)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# Blueprint routes for rescue operations
@rescue_bp.route('/restart-scheduler')
def restart_scheduler_endpoint():
    """Manually restart the scheduler"""
    try:
        scheduler.shutdown(wait=False)
        scheduler.start()
        return jsonify({
            'success': True,
            'message': 'Scheduler restarted successfully',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@rescue_bp.route('/refresh-snapshot')
def refresh_snapshot():
    """Force a refresh of the snapshot from database"""
    try:
        # Import inside function to avoid circular imports
        from dragon_core import load_from_db
        
        # Load from DB and write snapshot
        opportunities = load_from_db()
        if opportunities:
            write_snapshot(opportunities)
            return jsonify({
                'success': True,
                'message': f'Snapshot refreshed with {len(opportunities)} opportunities',
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Could not load opportunities from database',
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@rescue_bp.route('/run-scrapers')
def run_scrapers():
    """Manually trigger scrapers to run"""
    try:
        from dragon_core import run_all_scrapers
        
        opportunities = run_all_scrapers()
        if opportunities:
            write_snapshot(opportunities)
            return jsonify({
                'success': True,
                'message': f'Scrapers ran successfully, found {len(opportunities)} opportunities',
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Scrapers ran but found no opportunities',
                'timestamp': datetime.utcnow().isoformat()
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500