# dragon_core.py

import os
import threading
from flask import Flask, jsonify, Blueprint
from cache_utils import init_cache  # using existing cache setup
from datetime import datetime

# We'll initialize this later in create_app
cache = None

# Create blueprints that will be used by the app
health_bp = Blueprint('health_bp', __name__)  # Renamed to avoid conflicts
rescue_bp = Blueprint('rescue', __name__)

# Global variables
scheduler = None
snapshot_data = []

def load_snapshot():
    """Load opportunity data from snapshot file"""
    try:
        import json
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
        import json
        # Ensure the directory exists
        os.makedirs('data', exist_ok=True)
        with open('data/snapshot.json', 'w') as f:
            json.dump(opportunities, f)
        return True
    except Exception as e:
        print(f"Error writing snapshot: {e}")
        return False

def load_from_db():
    """Load opportunities from database"""
    try:
        # Import models here to avoid circular imports
        from models import Opportunity
        from main import app
        
        with app.app_context():
            opportunities = Opportunity.query.all()
            # Convert to JSON-serializable format
            return [opp.to_dict() for opp in opportunities]
    except Exception as e:
        print(f"Error loading from DB: {e}")
        return []

def monitored_job(max_retries=3):
    """Decorator for jobs that should be monitored for failures"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            nonlocal max_retries
            retries = 0
            while retries < max_retries:
                try:
                    result = func(*args, **kwargs)
                    # Reset retry count on success
                    func.fail_count = 0 if hasattr(func, 'fail_count') else 0
                    return result
                except Exception as e:
                    retries += 1
                    # Increment fail count
                    func.fail_count = getattr(func, 'fail_count', 0) + 1
                    print(f"Job {func.__name__} failed (attempt {retries}/{max_retries}): {e}")
                    # If we've exhausted retries, log the failure
                    if retries >= max_retries:
                        print(f"Job {func.__name__} failed after {max_retries} attempts")
                        # Try to alert via maintenance bot if available
                        try:
                            from alerts import alert_scheduler_error
                            alert_scheduler_error(
                                func.__name__, 
                                str(e), 
                                job_id=getattr(func, 'job_id', None),
                                next_run="unknown"
                            )
                        except Exception:
                            pass
            return None
        # Copy function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator

def monitor_jobs():
    """Monitor scheduled jobs and restart scheduler if too many failures"""
    global scheduler
    while True:
        import time
        # Sleep for 5 minutes
        time.sleep(300)
        
        # Check if scheduler is running
        if not scheduler or not scheduler.running:
            print("Scheduler not running, attempting to restart...")
            try:
                if scheduler:
                    scheduler.shutdown()
                import apscheduler
                from apscheduler.schedulers.background import BackgroundScheduler
                scheduler = BackgroundScheduler()
                scheduler.start()
                print("Scheduler restarted successfully")
            except Exception as e:
                print(f"Failed to restart scheduler: {e}")
                
        # Check job failure counts - future enhancement

def run_all_scrapers():
    """Run all opportunity scrapers and return aggregated results"""
    results = []
    try:
        # Import scrapers dynamically to avoid circular imports
        import importlib
        import sys
        
        # List of scraper modules to run
        scraper_modules = [
            'scrapers.instagram_ads',
            'scrapers.grants',
            'scrapers.residencies', 
            'scrapers.exhibitions'
        ]
        
        for module_name in scraper_modules:
            try:
                # Try to import the module
                if module_name in sys.modules:
                    # Reload if already imported
                    module = importlib.reload(sys.modules[module_name])
                else:
                    module = importlib.import_module(module_name)
                
                # Look for a run_scraper function
                if hasattr(module, 'run_scraper'):
                    module_results = module.run_scraper()
                    if module_results:
                        results.extend(module_results)
                        print(f"Added {len(module_results)} results from {module_name}")
            except Exception as e:
                print(f"Error running scraper {module_name}: {e}")
                # Try to alert via maintenance bot
                try:
                    from alerts import alert_scraper_error
                    alert_scraper_error(module_name, str(e))
                except Exception:
                    pass
    except Exception as e:
        print(f"Error in run_all_scrapers: {e}")
    
    return results

# Health blueprint routes
@health_bp.route('/health')
def check_health():
    """Check the health of the application - simplified for reliability"""
    global scheduler
    
    # Start with the bare minimum health data
    health_data = {
        'app': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '0.2.1',
        'name': 'Proletto Dragon'
    }
    
    # Safe cache check
    if cache:
        try:
            health_data['cache'] = 'fallback' if isinstance(cache, dict) else 'redis'
        except Exception:
            health_data['cache'] = 'error'
    else:
        health_data['cache'] = 'not initialized'
    
    # Safe scheduler check
    try:
        health_data['scheduler'] = 'running' if scheduler and scheduler.running else 'not running'
    except Exception:
        health_data['scheduler'] = 'unknown'
    
    # Safe snapshot count (no DB check to avoid timeouts)
    try:
        import time
        start = time.time()
        snapshot = load_snapshot() or []
        health_data['snapshot_count'] = len(snapshot)
        health_data['snapshot_load_time'] = f"{(time.time() - start) * 1000:.2f}ms"
    except Exception as e:
        health_data['snapshot_count'] = 0
        health_data['snapshot_error'] = str(e)
    
    # Overall status
    health_data['status'] = 'healthy' if health_data['app'] == 'ok' and health_data['scheduler'] == 'running' else 'degraded'
    
    return jsonify(health_data)

# Function used by rescue_bp.py
def restart_scheduler():
    """Manually restart the scheduler"""
    global scheduler
    try:
        if scheduler:
            scheduler.shutdown()
        
        import apscheduler
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.start()
        
        return True
    except Exception as e:
        raise e

@rescue_bp.route('/refresh-cache')
def refresh_cache():
    """Manually refresh the cache"""
    try:
        # Clear cache if available
        if cache:
            try:
                if hasattr(cache, 'clear'):
                    cache.clear()
                elif isinstance(cache, dict):
                    cache.clear()
                else:
                    # Alternative clearing method for other cache types
                    for key in ['opps_live', 'opportunity_snapshot', 'scraper_status']:
                        try:
                            cache.delete(key)
                        except:
                            pass
            except Exception as clear_error:
                return jsonify({
                    'success': False,
                    'message': f'Failed to clear cache: {str(clear_error)}',
                    'cache_type': str(type(cache)),
                    'timestamp': datetime.utcnow().isoformat()
                }), 500
        
        # Reload snapshot
        snapshot = load_snapshot() or []
        
        # Reload opportunities from DB
        opportunities = load_from_db() or []
        
        # Update cache if we can
        if opportunities and cache:
            try:
                if hasattr(cache, 'set'):
                    cache.set('opps_live', opportunities, timeout=3600)
                elif isinstance(cache, dict):
                    cache['opps_live'] = opportunities
            except Exception as set_error:
                return jsonify({
                    'success': False,
                    'message': f'Failed to update cache: {str(set_error)}',
                    'cache_type': str(type(cache)),
                    'timestamp': datetime.utcnow().isoformat()
                }), 500
            
        return jsonify({
            'success': True,
            'message': 'Cache refreshed successfully',
            'opportunities_count': len(opportunities),
            'snapshot_count': len(snapshot),
            'cache_type': str(type(cache)) if cache else 'none',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to refresh cache: {str(e)}',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@rescue_bp.route('/run-scrapers')
def trigger_scrapers():
    """Manually trigger all scrapers"""
    try:
        # Run all scrapers
        opportunities = run_all_scrapers() or []
        
        # Update snapshot
        if opportunities:
            write_snapshot(opportunities)
        
        # Update cache if we can
        if opportunities and cache:
            try:
                if hasattr(cache, 'set'):
                    cache.set('opps_live', opportunities, timeout=3600)
                elif isinstance(cache, dict):
                    cache['opps_live'] = opportunities
            except Exception as set_error:
                return jsonify({
                    'success': False,
                    'message': f'Scrapers run but failed to update cache: {str(set_error)}',
                    'cache_type': str(type(cache)),
                    'opportunities_count': len(opportunities),
                    'timestamp': datetime.utcnow().isoformat()
                }), 500
        
        return jsonify({
            'success': True,
            'message': 'Scrapers run successfully',
            'opportunities_count': len(opportunities),
            'cache_updated': True if cache else False,
            'cache_type': str(type(cache)) if cache else 'none',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to run scrapers: {str(e)}',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

def create_app():
    """Create and configure the Flask application"""
    global scheduler
    
    app = Flask(__name__)
    
    # Add a secret key for sessions (required by admin routes)
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dragon-development-key')
    
    # 1. Initialize cache
    global cache
    cache = init_cache(app)
    
    # 2. Load offline snapshot at boot
    snapshot = load_snapshot()
    app.logger.info(f"Loaded snapshot with {len(snapshot)} items")
    
    # 3. Register blueprints
    app.register_blueprint(health_bp)  # No prefix, direct access to /health
    
    # Use the external rescue_bp.py implementation for background threading
    try:
        # Import external rescue_bp that has background threading
        from rescue_bp import rescue_bp as threaded_rescue_bp
        app.register_blueprint(threaded_rescue_bp)
        app.logger.info("Using threaded rescue blueprint for admin/rescue routes")
    except ImportError as e:
        # Fallback to local rescue_bp if external one is not available
        app.register_blueprint(rescue_bp, url_prefix='/admin/rescue')
        app.logger.warning(f"Using default rescue blueprint: {e}")
    
    # Register Dragon Status dashboard
    try:
        from dragon_status import dragon_status_bp
        app.register_blueprint(dragon_status_bp)
        app.logger.info("Dragon Status dashboard registered successfully")
    except ImportError as e:
        app.logger.warning(f"Dragon Status dashboard not available: {e}")
    
    # 4. Initialize scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        
        # Schedule jobs
        # a. Core opportunity scraper every 30 minutes
        @monitored_job(max_retries=3)
        def scrape_all_sites():
            """Run all scrapers and update snapshot"""
            opportunities = run_all_scrapers()
            write_snapshot(opportunities)
            # Update cache
            cache.set('opps_live', opportunities, timeout=1800)  # 30 minutes
            return opportunities
            
        scheduler.add_job(scrape_all_sites, 'interval', minutes=30, id='core_scraper')
        
        # b. Instagram Ads scraper hourly
        try:
            from scrapers.instagram_ads import run_instagram_scraper
            instagram_job = monitored_job(max_retries=2)(run_instagram_scraper)
            scheduler.add_job(instagram_job, 'interval', hours=1, id='ig_ads')
        except ImportError:
            app.logger.warning("Instagram scraper not available")
        
        # c. Maintenance checks every 15 minutes
        try:
            from maintenance.bot import run_maintenance
            maint_job = monitored_job(max_retries=5)(run_maintenance)
            scheduler.add_job(maint_job, 'interval', minutes=15, id='maintenance')
        except ImportError:
            app.logger.warning("Maintenance bot not available")
        
        # d. Snapshot refresh daily
        scheduler.add_job(
            lambda: write_snapshot(load_from_db() or load_snapshot()), 
            'cron', 
            hour=0, 
            id='daily_snapshot'
        )
        
        # Start the scheduler
        scheduler.start()
        app.logger.info("Scheduler started successfully")
        
    except Exception as e:
        app.logger.error(f"Failed to initialize scheduler: {e}")
    
    # 5. Start watchdog thread
    try:
        t = threading.Thread(target=monitor_jobs, daemon=True)
        t.start()
        app.logger.info("Watchdog thread started")
    except Exception as e:
        app.logger.error(f"Failed to start watchdog thread: {e}")
    
    # 6. Core routes
    @app.route('/')
    def index():
        """Dragon API home page - provides service info and route discovery"""
        return jsonify({
            'service': 'Proletto Dragon',
            'status': 'running',
            'version': '0.2.1',
            'endpoints': [rule.rule for rule in app.url_map.iter_rules()],
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    @app.route('/opportunities')
    def list_opps():
        """List all opportunities with fallback mechanisms"""
        # Default to empty list to avoid NoneType errors
        data = []
        
        try:
            # Use a shorter 3-second timeout for cache operations
            import time
            start_time = time.time()
            timeout_seconds = 3
            
            # Try to get from cache first with timeout protection
            try:
                if cache and hasattr(cache, 'get'):
                    data = cache.get('opps_live')
                    if time.time() - start_time > timeout_seconds:
                        app.logger.warning("Cache get operation timed out, using fallback")
                        raise TimeoutError("Cache operation timed out")
                elif isinstance(cache, dict):
                    data = cache.get('opps_live')
            except Exception as cache_error:
                app.logger.warning(f"Cache error: {cache_error}")
                
            # If no data from cache, try DB
            if not data:
                app.logger.info("No data from cache, loading from DB")
                try:
                    # Only try DB if we have time remaining
                    if time.time() - start_time < timeout_seconds:
                        data = load_from_db() or []
                        
                        # Update cache if DB load successful and we have time
                        if data and cache and time.time() - start_time < timeout_seconds:
                            try:
                                if hasattr(cache, 'set'):
                                    cache.set('opps_live', data, timeout=1800)  # 30 minutes
                                elif isinstance(cache, dict):
                                    cache['opps_live'] = data
                            except Exception as cache_set_error:
                                app.logger.warning(f"Failed to update cache: {cache_set_error}")
                    else:
                        app.logger.warning("Skipping DB load due to timeout")
                except Exception as db_error:
                    app.logger.error(f"Database error: {db_error}")
                    
            # If still no data, try snapshot
            if not data:
                app.logger.info("No data from DB, loading from snapshot")
                data = load_snapshot() or []
                
        except Exception as e:
            app.logger.error(f"Error loading opportunities: {e}")
            # Return empty list as absolute fallback
            data = []
            
        return jsonify(data)
    
    from cache_utils import cached
    
    @app.route('/dragon-health')
    @cached(timeout=30)  # Cache for 30 seconds to reduce load
    def dragon_health():
        """Application health check - optimized for faster response"""
        # Get basic health data that's quick to compute
        health_data = {
            'app': 'ok',
            'cache': 'fallback' if isinstance(cache, dict) else 'redis',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '0.2.1',
            'name': 'Proletto Dragon'
        }
        
        # Check snapshot file without loading it fully
        try:
            snapshot_path = os.path.join('data', 'opportunities_latest.json')
            if os.path.exists(snapshot_path):
                health_data['snapshot_age'] = os.path.getmtime(snapshot_path)
                health_data['snapshot_size'] = os.path.getsize(snapshot_path)
            else:
                health_data['snapshot_age'] = None
                health_data['snapshot_size'] = 0
        except Exception as e:
            health_data['snapshot_error'] = str(e)
        
        # Safely check scheduler
        try:
            health_data['scheduler_ok'] = scheduler is not None and scheduler.running
        except Exception as e:
            health_data['scheduler_error'] = str(e)
            
        return jsonify(health_data), 200
    
    # Add debug logging for all registered routes
    app.logger.info("🐉 Dragon routes:")
    for rule in app.url_map.iter_rules():
        app.logger.info(f"🐉 Route: {rule.rule} -> {rule.endpoint}")
    
    return app

# Main entry point
if __name__ == '__main__':
    # Create the application
    app = create_app()
    
    # Run the development server
    port = int(os.environ.get('PORT', 5000))
    app.logger.info(f"🐉 Dragon HTTP server starting on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)