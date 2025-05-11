"""
Proletto Maintenance Bot

This module provides automated maintenance tasks and health checks for the Proletto system.
It runs periodically to ensure the system is functioning optimally.
"""

import logging
import time
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Health check thresholds
THRESHOLDS = {
    "min_opportunities": 50,  # Minimum number of opportunities that should be in the system
    "cache_hit_rate_min": 0.7,  # Minimum acceptable cache hit rate (70%)
    "db_connection_timeout": 5.0,  # Maximum seconds for a database connection
    "api_response_timeout": 3.0,  # Maximum seconds for an API health check
    "memory_usage_max": 90.0,  # Maximum acceptable memory usage (%)
    "disk_usage_max": 85.0,  # Maximum acceptable disk usage (%)
}

def check_database_health() -> Dict[str, Any]:
    """
    Check database connection health.
    
    Returns:
        Dictionary with health metrics
    """
    try:
        start_time = time.time()
        
        # In a real implementation, this would check the database
        # For now, we'll simulate a database check
        from models import db
        from sqlalchemy import text
        
        # Use an app context if available
        try:
            from main import app
            with app.app_context():
                result = db.session.execute(text("SELECT 1")).fetchone()
                is_connected = result is not None and result[0] == 1
        except ImportError:
            # Fallback method without app context
            result = db.session.execute(text("SELECT 1")).fetchone()
            is_connected = result is not None and result[0] == 1
        
        query_time = time.time() - start_time
        
        return {
            "status": "healthy" if is_connected else "error",
            "connection_time": query_time,
            "is_slow": query_time > THRESHOLDS["db_connection_timeout"],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

def check_cache_health() -> Dict[str, Any]:
    """
    Check cache health.
    
    Returns:
        Dictionary with cache health metrics
    """
    try:
        # Try to access the cache
        try:
            from cache_utils import cache
            from main import app
            
            # Test basic cache operations
            test_key = f"maint_test_{int(time.time())}"
            cache.set(test_key, "test_value", timeout=30)
            retrieved = cache.get(test_key)
            
            # Get cache stats if possible
            stats = {}
            if hasattr(app, 'cache_backend'):
                if app.cache_backend['type'] == 'redis':
                    client = app.cache_backend['client']
                    info = client.info()
                    
                    # Extract useful Redis stats
                    hits = info.get('keyspace_hits', 0)
                    misses = info.get('keyspace_misses', 0)
                    total = hits + misses
                    
                    if total > 0:
                        hit_rate = round((hits / total) * 100, 2)
                        stats['hit_rate'] = hit_rate
                        stats['is_hit_rate_low'] = hit_rate < (THRESHOLDS["cache_hit_rate_min"] * 100)
                    
                    stats['used_memory_human'] = info.get('used_memory_human')
                    stats['connected_clients'] = info.get('connected_clients')
            
            return {
                "status": "healthy" if retrieved == "test_value" else "degraded",
                "operational": retrieved == "test_value",
                "type": getattr(app, 'cache_backend', {}).get('type', 'unknown') if 'app' in locals() else "unknown",
                "stats": stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.warning(f"Could not access primary cache: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Cache health check failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

def check_opportunity_count() -> Dict[str, Any]:
    """
    Check that we have a healthy number of opportunities.
    
    Returns:
        Dictionary with opportunity metrics
    """
    try:
        # Try to count opportunities
        try:
            # First try to get from snapshot
            import json
            snapshot_count = 0
            if os.path.exists('data/snapshot.json'):
                with open('data/snapshot.json', 'r') as f:
                    snapshot = json.load(f)
                    snapshot_count = len(snapshot)
            
            # Then try to get from database
            db_count = 0
            try:
                from models import Opportunity
                from main import app
                with app.app_context():
                    db_count = Opportunity.query.count()
            except Exception as e:
                logger.warning(f"Could not count opportunities from database: {str(e)}")
                
            # Use the higher count
            count = max(snapshot_count, db_count)
            
            return {
                "status": "healthy" if count >= THRESHOLDS["min_opportunities"] else "warning",
                "count": count,
                "snapshot_count": snapshot_count,
                "db_count": db_count,
                "is_low": count < THRESHOLDS["min_opportunities"],
                "threshold": THRESHOLDS["min_opportunities"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.warning(f"Could not count opportunities: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Opportunity count check failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

def check_system_resources() -> Dict[str, Any]:
    """
    Check system resources like CPU, memory, and disk.
    
    Returns:
        Dictionary with system resource metrics
    """
    try:
        # Try psutil if available
        try:
            import psutil
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "status": "healthy",
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": memory.percent,
                "memory_available_mb": round(memory.available / 1024 / 1024, 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                "memory_warning": memory.percent > THRESHOLDS["memory_usage_max"],
                "disk_warning": disk.percent > THRESHOLDS["disk_usage_max"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except ImportError:
            # Fallback to basic checks if psutil not available
            import shutil
            
            # Get disk usage of current directory
            total, used, free = shutil.disk_usage('.')
            disk_percent = (used / total) * 100
            
            return {
                "status": "limited",
                "note": "psutil not available, limited metrics",
                "disk_percent": disk_percent,
                "disk_free_gb": round(free / 1024 / 1024 / 1024, 2),
                "disk_warning": disk_percent > THRESHOLDS["disk_usage_max"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"System resource check failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

def alert_if_needed(checks: Dict[str, Dict[str, Any]]) -> None:
    """
    Send alerts for concerning health check results.
    
    Args:
        checks: Dictionary of health check results
    """
    try:
        # Check for issues that require alerts
        issues = []
        
        # Check database health
        if checks.get('database', {}).get('status') == 'error':
            issues.append(f"Database error: {checks['database'].get('error', 'Unknown error')}")
        elif checks.get('database', {}).get('is_slow', False):
            issues.append(f"Database is slow: {checks['database']['connection_time']:.2f}s")
            
        # Check cache health
        if checks.get('cache', {}).get('status') == 'error':
            issues.append(f"Cache error: {checks['cache'].get('error', 'Unknown error')}")
        elif checks.get('cache', {}).get('stats', {}).get('is_hit_rate_low', False):
            issues.append(f"Cache hit rate is low: {checks['cache']['stats']['hit_rate']}%")
            
        # Check opportunity count
        if checks.get('opportunities', {}).get('is_low', False):
            issues.append(f"Opportunity count is low: {checks['opportunities']['count']} (threshold: {checks['opportunities']['threshold']})")
            
        # Check system resources
        if checks.get('system', {}).get('memory_warning', False):
            issues.append(f"High memory usage: {checks['system']['memory_percent']}%")
        if checks.get('system', {}).get('disk_warning', False):
            issues.append(f"High disk usage: {checks['system']['disk_percent']}%")
            
        # Send alerts if there are issues
        if issues:
            # Use the alerts module if available
            try:
                from alerts import alert_system_health
                
                # Create custom metrics
                custom_metrics = {}
                for key, check in checks.items():
                    if key == 'database':
                        custom_metrics['db_connection_time'] = check.get('connection_time')
                    elif key == 'cache':
                        custom_metrics['cache_hit_rate'] = check.get('stats', {}).get('hit_rate')
                    elif key == 'opportunities':
                        custom_metrics['opportunity_count'] = check.get('count')
                    elif key == 'system':
                        custom_metrics['memory_percent'] = check.get('memory_percent')
                        custom_metrics['disk_percent'] = check.get('disk_percent')
                
                # Send the alert
                alert_system_health(
                    cpu_usage=checks.get('system', {}).get('cpu_percent'),
                    memory_usage=checks.get('system', {}).get('memory_percent'),
                    disk_usage=checks.get('system', {}).get('disk_percent'),
                    custom_metrics=custom_metrics
                )
                
                logger.info(f"Sent system health alert with {len(issues)} issues")
                
            except ImportError:
                # Log the issues if alerts module not available
                logger.warning("Could not send alerts: alerts module not available")
                for issue in issues:
                    logger.warning(f"Health issue: {issue}")
                    
    except Exception as e:
        logger.error(f"Failed to process alerts: {str(e)}")

def run_maintenance() -> Dict[str, Any]:
    """
    Run maintenance tasks and health checks.
    
    Returns:
        Dictionary with all health check results
    """
    logger.info("Starting maintenance run")
    start_time = time.time()
    
    try:
        # Run all health checks
        checks = {
            'database': check_database_health(),
            'cache': check_cache_health(),
            'opportunities': check_opportunity_count(),
            'system': check_system_resources()
        }
        
        # Determine overall status
        status = "healthy"
        for check in checks.values():
            if check.get('status') == 'error':
                status = "error"
                break
            elif check.get('status') == 'warning' and status == 'healthy':
                status = "warning"
                
        # Check if we should alert
        alert_if_needed(checks)
        
        # Add metadata
        result = {
            'status': status,
            'duration': time.time() - start_time,
            'timestamp': datetime.utcnow().isoformat(),
            'checks': checks
        }
        
        logger.info(f"Maintenance run completed in {result['duration']:.2f}s with status: {status}")
        return result
        
    except Exception as e:
        logger.error(f"Maintenance run failed: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'duration': time.time() - start_time,
            'timestamp': datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run maintenance
    result = run_maintenance()
    
    # Print summary
    print(f"Maintenance Status: {result['status']}")
    print(f"Run Time: {result['duration']:.2f}s")
    
    for check_name, check in result.get('checks', {}).items():
        print(f"\n{check_name.upper()}: {check.get('status', 'unknown')}")
        for key, value in check.items():
            if key not in ['status', 'timestamp'] and not isinstance(value, dict):
                print(f"  {key}: {value}")