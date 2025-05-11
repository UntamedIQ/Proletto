"""
Proletto Monitoring Routes

This module provides routes for monitoring and system health checks.
It integrates with the monitoring and error logging modules to expose
monitoring data and system health information through API endpoints and
an admin dashboard.
"""

import os
import json
import logging
from flask import Blueprint, jsonify, request, render_template, Response
from flask_login import login_required, current_user

from utils.error_logging import logger
from utils.monitoring import monitor
from admin_utils import admin_required

# Create Blueprint
monitoring = Blueprint('monitoring', __name__)

@monitoring.route('/health')
def health_check():
    """Simple health check endpoint for load balancers and monitoring systems"""
    return jsonify({"status": "ok", "version": os.environ.get("APP_VERSION", "dev")})

@monitoring.route('/api/monitor/health')
def monitor_health():
    """Health check endpoint with detailed system health information"""
    return jsonify(monitor.get_system_health())

@monitoring.route('/api/monitor/metrics')
def monitor_metrics():
    """Metrics endpoint for detailed monitoring data"""
    return jsonify(monitor.get_metrics_report())

@monitoring.route('/api/monitor/prometheus')
def monitor_prometheus():
    """Prometheus metrics endpoint for integration with Prometheus monitoring"""
    return Response(
        monitor.export_metrics(format="prometheus"),
        mimetype="text/plain"
    )

@monitoring.route('/admin/monitoring')
@login_required
@admin_required
def admin_monitoring():
    """Admin monitoring dashboard"""
    return render_template('admin/monitoring.html')

@monitoring.route('/api/logs', methods=['GET'])
@login_required
@admin_required
def get_logs():
    """API endpoint to retrieve application logs"""
    # Parameters
    level = request.args.get('level', 'INFO').upper()
    limit = min(int(request.args.get('limit', 100)), 1000)  # Limit max to 1000 lines
    
    # Convert string level to logging level
    numeric_level = getattr(logging, level, logging.INFO)
    
    try:
        # Read log file with specified level filter
        logs = []
        log_file = os.path.join("logs", "proletto.log")
        
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                lines = f.readlines()
                
                # Process lines in reverse (newest first)
                for line in reversed(lines):
                    # Simple parsing to determine log level
                    parts = line.split(" - ")
                    if len(parts) >= 3:
                        entry_level = parts[2].strip()
                        log_level = getattr(logging, entry_level, 0)
                        
                        # Only include if level matches filter
                        if log_level >= numeric_level:
                            logs.append({
                                "timestamp": parts[0].strip(),
                                "module": parts[1].strip(),
                                "level": entry_level,
                                "message": " - ".join(parts[3:]).strip()
                            })
                            
                            # Stop if we've reached the limit
                            if len(logs) >= limit:
                                break
        
        return jsonify({"logs": logs})
    except Exception as e:
        logger.error(f"Error retrieving logs: {str(e)}", exc_info=e)
        return jsonify({"error": str(e)}), 500

@monitoring.route('/api/errors', methods=['GET'])
@login_required
@admin_required
def get_errors():
    """API endpoint to retrieve error logs"""
    # Parameters
    limit = min(int(request.args.get('limit', 50)), 500)  # Limit max to 500 errors
    
    try:
        # Read error log file
        errors = []
        error_log_file = os.path.join("logs", "proletto_error.log")
        
        if os.path.exists(error_log_file):
            with open(error_log_file, 'r') as f:
                lines = f.readlines()
                
                # Process lines in reverse (newest first)
                for line in reversed(lines):
                    errors.append(line.strip())
                    
                    # Stop if we've reached the limit
                    if len(errors) >= limit:
                        break
        
        return jsonify({"errors": errors})
    except Exception as e:
        logger.error(f"Error retrieving error logs: {str(e)}", exc_info=e)
        return jsonify({"error": str(e)}), 500

@monitoring.route('/api/structured-logs', methods=['GET'])
@login_required
@admin_required
def get_structured_logs():
    """API endpoint to retrieve structured logs in JSON format"""
    # Parameters
    limit = min(int(request.args.get('limit', 50)), 500)  # Limit max to 500 entries
    
    try:
        # Read structured log file
        logs = []
        structured_log_file = os.path.join("logs", "proletto_structured.json")
        
        if os.path.exists(structured_log_file):
            with open(structured_log_file, 'r') as f:
                lines = f.readlines()
                
                # Process lines in reverse (newest first)
                for line in reversed(lines):
                    try:
                        log_entry = json.loads(line.strip())
                        logs.append(log_entry)
                        
                        # Stop if we've reached the limit
                        if len(logs) >= limit:
                            break
                    except json.JSONDecodeError:
                        # Skip invalid JSON lines
                        continue
        
        return jsonify({"logs": logs})
    except Exception as e:
        logger.error(f"Error retrieving structured logs: {str(e)}", exc_info=e)
        return jsonify({"error": str(e)}), 500

def init_app(app, db=None, redis_client=None):
    """Initialize the monitoring module with the Flask app"""
    # Initialize monitoring with Flask app
    from utils.monitoring import init_app as init_monitoring
    init_monitoring(app, db, redis_client)
    
    # Register blueprint
    app.register_blueprint(monitoring, url_prefix='/monitoring')
    
    # Also register key monitoring endpoints at the root
    app.add_url_rule('/health', 'health_check', health_check)
    app.add_url_rule('/api/health', 'api_health_check', health_check)
    
    # Register admin routes
    app.add_url_rule('/admin/monitoring', 'admin_monitoring', admin_monitoring)
    
    # Log initialization
    logger.info("Monitoring routes initialized")
    
    return monitoring