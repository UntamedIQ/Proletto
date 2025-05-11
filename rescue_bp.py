import threading
from flask import Blueprint, jsonify, current_app
from cache_utils import cache
from datetime import datetime

rescue_bp = Blueprint('rescue', __name__, url_prefix='/admin/rescue')

def run_in_bg(fn, *args, **kwargs):
    """Spawn a thread for background execution with app context preservation."""
    app = current_app._get_current_object()  # Get the actual app object
    
    def wrapper(*args, **kwargs):
        with app.app_context():
            return fn(*args, **kwargs)
            
    t = threading.Thread(target=wrapper, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t

@rescue_bp.route('/clear-cache', methods=['POST'])
def clear_cache():
    """Trigger a full cache clear in background."""
    def do_clear():
        try:
            cache.clear()
            current_app.logger.info("[Rescue] Cache cleared successfully")
        except Exception as e:
            current_app.logger.error(f"[Rescue] Cache clear failed: {e}")

    run_in_bg(do_clear)
    return jsonify({"status": "scheduled", "action": "clear-cache"}), 202

@rescue_bp.route('/refresh-cache', methods=['POST'])
def refresh_cache():
    """Refresh the cache in background."""
    def do_refresh():
        try:
            # Import here to avoid circular imports
            from dragon_core import refresh_cache as dragon_refresh_cache
            dragon_refresh_cache()
            current_app.logger.info("[Rescue] Cache refreshed successfully")
        except Exception as e:
            current_app.logger.error(f"[Rescue] Cache refresh failed: {e}")

    run_in_bg(do_refresh)
    return jsonify({"status": "scheduled", "action": "refresh-cache"}), 202

@rescue_bp.route('/refresh-snapshot', methods=['POST'])
def refresh_snapshot():
    """Regenerate the JSON snapshot from DB in background."""
    def do_snapshot():
        try:
            # Import here to avoid circular imports
            from dragon_core import load_from_db, write_snapshot
            data = load_from_db()
            write_snapshot(data)
            current_app.logger.info("[Rescue] Snapshot refreshed successfully")
        except Exception as e:
            current_app.logger.error(f"[Rescue] Snapshot refresh failed: {e}")

    run_in_bg(do_snapshot)
    return jsonify({"status": "scheduled", "action": "refresh-snapshot"}), 202

@rescue_bp.route('/restart-scheduler', methods=['POST'])
def restart_scheduler():
    """Restart the APScheduler instance in background."""
    def do_restart():
        try:
            # Import here to avoid circular imports
            from dragon_core import restart_scheduler as dragon_restart_scheduler
            dragon_restart_scheduler()
            current_app.logger.info("[Rescue] Scheduler restarted successfully")
        except Exception as e:
            current_app.logger.error(f"[Rescue] Scheduler restart failed: {e}")

    run_in_bg(do_restart)
    return jsonify({"status": "scheduled", "action": "restart-scheduler"}), 202

@rescue_bp.route('/run-scrapers', methods=['POST'])
def trigger_scrapers():
    """Run all scrapers in background."""
    def do_scrape():
        try:
            # Import here to avoid circular imports
            from dragon_core import trigger_scrapers as dragon_trigger_scrapers
            dragon_trigger_scrapers()
            current_app.logger.info("[Rescue] Scrapers triggered successfully")
        except Exception as e:
            current_app.logger.error(f"[Rescue] Triggering scrapers failed: {e}")

    run_in_bg(do_scrape)
    return jsonify({"status": "scheduled", "action": "run-scrapers"}), 202

@rescue_bp.route('/status', methods=['GET'])
def status():
    """Get the status of background jobs"""
    return jsonify({
        "service": "Proletto Dragon Rescue",
        "status": "running",
        "available_actions": [
            "/admin/rescue/clear-cache",
            "/admin/rescue/refresh-cache", 
            "/admin/rescue/refresh-snapshot", 
            "/admin/rescue/restart-scheduler",
            "/admin/rescue/run-scrapers"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }), 200