"""
Dragon Status Dashboard for Proletto

This module provides a web interface to monitor the health and status of the
Multi-Headed Dragon system.
"""

import os
import time
import sys
import importlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from functools import wraps

from flask import Blueprint, render_template, current_app, jsonify, url_for, request, redirect, session, flash

# Create blueprint
dragon_status_bp = Blueprint('dragon_status', __name__, url_prefix='/admin/dragon-status')

# Admin authorization decorator
def admin_required(f):
    """
    Decorator to verify the user is an admin before allowing access to Dragon Status Dashboard.
    Regular members will be redirected to their member dashboard.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # For Dragon API standalone service, we're simplifying auth
        # Future: Implement proper auth or API key verification
        
        # Get admin password from environment or use default for development
        admin_key = request.args.get('admin_key')
        expected_key = os.environ.get('DRAGON_ADMIN_KEY', 'dragon_development_key')
        
        if admin_key != expected_key:
            return jsonify({
                'error': 'Authentication required',
                'message': 'You must provide a valid admin_key to access this endpoint',
                'status_code': 401
            }), 401
            
        return f(*args, **kwargs)
    return decorated_function

@dragon_status_bp.route('/')
@admin_required
def status():
    """
    Display the Dragon status dashboard page.
    
    Returns:
        Rendered HTML template with status information
    """
    try:
        # Get scheduler jobs
        jobs = []
        scheduler = getattr(current_app, 'scheduler', None)
        if scheduler:
            try:
                for job in scheduler.get_jobs():
                    jobs.append({
                        'id': job.id,
                        'next_run': job.next_run_time,
                        'failures': getattr(current_app, '_job_failures', {}).get(job.id, 0)
                    })
            except Exception as e:
                current_app.logger.error(f"Error getting scheduler jobs: {e}")
                
        # Get cache info
        cache_type = "unknown"
        hits = "N/A"
        misses = "N/A"
        
        cache_backend = getattr(current_app, 'cache_backend', None)
        if cache_backend:
            try:
                cache_type = cache_backend.get('type', 'unknown')
                
                # Redis stats if available
                if cache_type == 'redis' and 'client' in cache_backend:
                    client = cache_backend['client']
                    info = client.info()
                    hits = info.get('keyspace_hits', 'N/A')
                    misses = info.get('keyspace_misses', 'N/A')
            except Exception as e:
                current_app.logger.error(f"Error getting cache info: {e}")
                
        # Check for opportunity snapshot timestamp
        snapshot = "Not found"
        try:
            snapshot_paths = [
                'data/opportunities_latest.json',
                'data/snapshot.json',
                'data/opportunities.json'
            ]
            
            for path in snapshot_paths:
                if os.path.exists(path):
                    mtime = os.path.getmtime(path)
                    snapshot = datetime.fromtimestamp(mtime).isoformat()
                    break
        except Exception as e:
            snapshot = f"Error: {str(e)}"
            
        # System metrics
        try:
            import psutil
            mem = psutil.virtual_memory().percent
            cpu = psutil.cpu_percent(interval=0.5)
        except ImportError:
            mem = "N/A (psutil not installed)"
            cpu = "N/A (psutil not installed)"

        # Get scraper information
        scrapers = get_scraper_info()
        
        # Get maintenance metrics
        maintenance = get_maintenance_info()
            
        return render_template('admin/dragon_status.html',
            jobs=jobs,
            cache_type=cache_type,
            hits=hits,
            misses=misses,
            snapshot=snapshot,
            mem=mem,
            cpu=cpu,
            scrapers=scrapers,
            maintenance=maintenance
        )
    except Exception as e:
        return f"Error rendering Dragon status: {str(e)}"

@dragon_status_bp.route('/api/health')
@admin_required
def health_api():
    """
    API endpoint for health metrics.
    
    Returns:
        JSON with system health metrics
    """
    try:
        # Gather basic system info
        import psutil
        vm = psutil.virtual_memory()
        
        # Get scheduler status
        scheduler_status = "not_running"
        scheduler_job_count = 0
        
        scheduler = getattr(current_app, 'scheduler', None)
        if scheduler:
            try:
                scheduler_status = "running" if scheduler.running else "paused"
                scheduler_job_count = len(scheduler.get_jobs())
            except Exception as e:
                current_app.logger.error(f"Error getting scheduler status: {e}")
            
        # Check Redis connection
        redis_status = "unknown"
        try:
            cache_backend = getattr(current_app, 'cache_backend', None)
            if cache_backend and cache_backend.get('type') == 'redis':
                client = cache_backend.get('client')
                if client:
                    client.ping()
                    redis_status = "connected"
        except Exception:
            redis_status = "disconnected"
            
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": vm.percent,
                "memory_available_mb": round(vm.available / 1024 / 1024, 2),
            },
            "scheduler": {
                "status": scheduler_status,
                "job_count": scheduler_job_count
            },
            "redis": {
                "status": redis_status
            }
        }
        
        return jsonify(health_data)
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })

def get_scraper_info() -> List[Dict[str, Any]]:
    """
    Get information about configured scrapers.
    
    Returns:
        List of scraper information dictionaries
    """
    scrapers_list = []
    
    # Check for imported scrapers
    try:
        # Try to discover available scrapers
        import importlib.util
        import os
        import sys
        
        # Check if scrapers directory exists
        scrapers_dir = "scrapers"
        if os.path.isdir(scrapers_dir):
            # Get all Python files in the scrapers directory
            for file in os.listdir(scrapers_dir):
                if file.endswith(".py") and not file.startswith("__"):
                    name = file[:-3]  # Remove .py extension
                    
                    try:
                        # Load the module directly
                        module_path = os.path.join(scrapers_dir, file)
                        spec = importlib.util.spec_from_file_location(f"scrapers.{name}", module_path)
                        if spec and spec.loader:
                            mod = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(mod)
                            
                            # Extract any available metadata
                            scraper_info = {
                                "name": name,
                                "status": "available",
                                "description": getattr(mod, "__doc__", "No description available").strip(),
                                "last_run": "Never"
                            }
                            
                            # If the module has a run function, it's a valid scraper
                            if hasattr(mod, "run_instagram_scraper"):
                                scraper_info["function"] = "run_instagram_scraper"
                            
                            scrapers_list.append(scraper_info)
                    except Exception as e:
                        scrapers_list.append({
                            "name": name,
                            "status": "error",
                            "description": f"Failed to import module: {str(e)}",
                            "last_run": "Never"
                        })
    except Exception as e:
        scrapers_list.append({
            "name": "Error",
            "status": "error",
            "description": f"Failed to discover scrapers: {str(e)}",
            "last_run": "Never"
        })
        
    # Add manual entries for expected scrapers if we didn't find them
    found_names = [s["name"] for s in scrapers_list]
    
    expected_scrapers = [
        "instagram_ads",
        "grants",
        "residencies",
        "exhibitions",
        "competitions"
    ]
    
    for name in expected_scrapers:
        if name not in found_names:
            scrapers_list.append({
                "name": name,
                "status": "not_implemented" if name != "instagram_ads" else "error",
                "description": "Scraper not yet implemented" if name != "instagram_ads" else "Failed to load scraper",
                "last_run": "Never"
            })
            
    return scrapers_list

def get_maintenance_info() -> Dict[str, Any]:
    """
    Get information about maintenance tasks.
    
    Returns:
        Dictionary with maintenance metrics
    """
    maintenance = {
        "last_run": "Never",
        "status": "unknown",
        "checks": {}
    }
    
    # Try to find maintenance logs
    try:
        # Check if we have a log file with maintenance information
        log_paths = [
            "logs/dragon.log",
            "logs/maintenance.log",
            "dragon.log",
            "maintenance.log"
        ]
        
        log_content = None
        for path in log_paths:
            if os.path.exists(path):
                with open(path, "r") as f:
                    log_content = f.read()
                    break
                    
        if log_content:
            # Very simple parsing for demonstration
            if "maintenance run completed" in log_content.lower():
                maintenance["last_run"] = "Found in logs"
                
                # Try to extract status
                if "status: healthy" in log_content.lower():
                    maintenance["status"] = "healthy"
                elif "status: warning" in log_content.lower():
                    maintenance["status"] = "warning"
                elif "status: error" in log_content.lower():
                    maintenance["status"] = "error"
    except Exception as e:
        maintenance["status"] = f"Error reading logs: {str(e)}"
        
    return maintenance

# API Endpoints for Dragon Dashboard Actions
@dragon_status_bp.route('/api/run-scraper/<scraper_name>', methods=['POST'])
@admin_required
def run_scraper_api(scraper_name):
    """Run a specific scraper immediately"""
    try:
        # Safety check - limit to known scrapers
        valid_scrapers = ["instagram_ads", "grants", "residencies", "exhibitions", "competitions"]
        if scraper_name not in valid_scrapers:
            return jsonify({"status": "error", "message": f"Unknown scraper: {scraper_name}"}), 400
        
        # Try to load the scraper module
        try:
            scraper_module = importlib.import_module(f"scrapers.{scraper_name}")
        except ImportError:
            return jsonify({
                "status": "error", 
                "message": f"Scraper module not found: {scraper_name}"
            }), 404
            
        # Check if the module has a run function
        run_func = None
        if hasattr(scraper_module, "run_scraper"):
            run_func = scraper_module.run_scraper
        elif hasattr(scraper_module, f"run_{scraper_name}_scraper"):
            run_func = getattr(scraper_module, f"run_{scraper_name}_scraper")
        elif hasattr(scraper_module, "run"):
            run_func = scraper_module.run
            
        if not run_func:
            return jsonify({
                "status": "error", 
                "message": f"No run function found in scraper: {scraper_name}"
            }), 400
            
        # Run the scraper in a background thread to not block the request
        import threading
        def run_in_background():
            try:
                result = run_func()
                current_app.logger.info(f"Scraper {scraper_name} completed with result: {result}")
            except Exception as e:
                current_app.logger.error(f"Error running scraper {scraper_name}: {e}")
                
        thread = threading.Thread(target=run_in_background)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "success", 
            "message": f"Scraper {scraper_name} started in background"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in run_scraper_api: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@dragon_status_bp.route('/api/run-job/<job_id>', methods=['POST'])
@admin_required
def run_job_api(job_id):
    """Run a specific scheduler job immediately"""
    try:
        scheduler = getattr(current_app, 'scheduler', None)
        if not scheduler:
            return jsonify({
                "status": "error", 
                "message": "Scheduler not available"
            }), 500
            
        # Find the job
        job = None
        for j in scheduler.get_jobs():
            if j.id == job_id:
                job = j
                break
                
        if not job:
            return jsonify({
                "status": "error", 
                "message": f"Job not found: {job_id}"
            }), 404
            
        # Run the job
        job.func()
        
        return jsonify({
            "status": "success", 
            "message": f"Job {job_id} executed"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in run_job_api: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@dragon_status_bp.route('/api/run-all-jobs', methods=['POST'])
@admin_required
def run_all_jobs_api():
    """Run all scheduler jobs immediately"""
    try:
        scheduler = getattr(current_app, 'scheduler', None)
        if not scheduler:
            return jsonify({
                "status": "error", 
                "message": "Scheduler not available"
            }), 500
            
        # Run all jobs
        for job in scheduler.get_jobs():
            try:
                job.func()
                current_app.logger.info(f"Job {job.id} executed manually")
            except Exception as e:
                current_app.logger.error(f"Error running job {job.id}: {e}")
        
        return jsonify({
            "status": "success", 
            "message": "All jobs executed"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in run_all_jobs_api: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@dragon_status_bp.route('/api/scheduler/<action>', methods=['POST'])
@admin_required
def scheduler_control_api(action):
    """Control scheduler (pause, resume)"""
    try:
        scheduler = getattr(current_app, 'scheduler', None)
        if not scheduler:
            return jsonify({
                "status": "error", 
                "message": "Scheduler not available"
            }), 500
            
        if action == "pause":
            scheduler.pause()
            return jsonify({
                "status": "success", 
                "message": "Scheduler paused"
            })
        elif action == "resume":
            scheduler.resume()
            return jsonify({
                "status": "success", 
                "message": "Scheduler resumed"
            })
        else:
            return jsonify({
                "status": "error", 
                "message": f"Unknown action: {action}"
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error in scheduler_control_api: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@dragon_status_bp.route('/api/run-maintenance', methods=['POST'])
@admin_required
def run_maintenance_api():
    """Run the maintenance bot manually"""
    try:
        # Check if maintenance module exists
        try:
            maintenance_module = importlib.import_module("maintenance.bot")
        except ImportError:
            return jsonify({
                "status": "error", 
                "message": "Maintenance bot module not found"
            }), 404
            
        # Check if the module has a run function
        if not hasattr(maintenance_module, "run_maintenance"):
            return jsonify({
                "status": "error", 
                "message": "No run_maintenance function found in maintenance bot"
            }), 400
            
        # Run the maintenance bot in a background thread
        import threading
        def run_in_background():
            try:
                result = maintenance_module.run_maintenance()
                current_app.logger.info(f"Maintenance bot completed with result: {result}")
            except Exception as e:
                current_app.logger.error(f"Error running maintenance bot: {e}")
                
        thread = threading.Thread(target=run_in_background)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "success", 
            "message": "Maintenance bot started in background"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in run_maintenance_api: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500