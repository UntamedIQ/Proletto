"""
Proletto System Monitoring Module

This module provides system monitoring capabilities including:
- System health metrics (CPU, memory, disk usage)
- Application metrics (requests, response times, error rates)
- Database connection health
- Redis connection health
- API endpoint performance tracking
- System alerts based on thresholds

Usage:
    from utils.monitoring import monitor

    # Get system health metrics
    health_metrics = monitor.get_system_health()

    # Record an API request
    with monitor.track_request("/api/v1/opportunities", method="GET"):
        # Process the request
        pass

    # Check if a system is within normal operating parameters
    if not monitor.is_healthy("database"):
        # Take remedial action
        pass
"""

import os
import time
import json
import socket
import threading
import platform
import datetime
import functools
import traceback
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable, Union
from contextlib import contextmanager

# Import error logging
from utils.error_logging import logger

# Import optional dependencies
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available, system metrics collection limited")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis client not available, Redis monitoring disabled")

# Metric storage (in-memory for development)
_metrics = {
    "requests": {
        # Endpoint -> metrics
    },
    "system": {
        "samples": [],
        "last_updated": None
    },
    "databases": {
        # Connection name -> health status
    },
    "caches": {
        # Cache name -> health status
    },
    "api_latency": [],
    "error_counts": {
        "total": 0,
        "by_endpoint": {},
        "by_type": {}
    }
}

# Settings
MAX_SAMPLES = int(os.environ.get("MONITOR_MAX_SAMPLES", "100"))
SAMPLE_INTERVAL = int(os.environ.get("MONITOR_SAMPLE_INTERVAL", "60"))  # seconds
ENABLE_REQUEST_LOGGING = os.environ.get("MONITOR_REQUEST_LOGGING", "1") == "1"
ENABLE_SYSTEM_METRICS = os.environ.get("MONITOR_SYSTEM_METRICS", "1") == "1"
ENABLE_SCHEDULED_CHECKS = os.environ.get("MONITOR_SCHEDULED_CHECKS", "1") == "1"
UNHEALTHY_THRESHOLD = int(os.environ.get("MONITOR_UNHEALTHY_THRESHOLD", "3"))
HEALTH_CHECK_INTERVAL = int(os.environ.get("MONITOR_HEALTH_CHECK_INTERVAL", "60"))  # seconds

# Dataclasses for metrics
@dataclass
class RequestMetrics:
    endpoint: str
    method: str
    count: int = 0
    error_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    status_counts: Dict[int, int] = field(default_factory=dict)
    last_status: Optional[int] = None
    last_error: Optional[str] = None
    last_request_time: Optional[float] = None

    def add_request(self, duration: float, status_code: int, error: Optional[str] = None) -> None:
        self.count += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        self.status_counts[status_code] = self.status_counts.get(status_code, 0) + 1
        self.last_status = status_code
        self.last_request_time = time.time()
        
        if error:
            self.error_count += 1
            self.last_error = error
            
    @property
    def avg_time(self) -> float:
        return self.total_time / self.count if self.count > 0 else 0
        
    @property
    def error_rate(self) -> float:
        return (self.error_count / self.count) if self.count > 0 else 0
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "endpoint": self.endpoint,
            "method": self.method,
            "count": self.count,
            "error_count": self.error_count,
            "avg_time": self.avg_time,
            "min_time": self.min_time if self.min_time != float('inf') else 0,
            "max_time": self.max_time,
            "status_counts": self.status_counts,
            "last_status": self.last_status,
            "last_error": self.last_error,
            "last_request_time": self.last_request_time,
            "error_rate": self.error_rate
        }

@dataclass
class SystemMetrics:
    timestamp: float
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    open_files: Optional[int] = None
    network_connections: Optional[int] = None
    system_load: Optional[list] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "disk_percent": self.disk_percent,
            "open_files": self.open_files,
            "network_connections": self.network_connections,
            "system_load": self.system_load
        }

@dataclass
class HealthStatus:
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    last_check: float
    message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    failure_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "name": self.name,
            "status": self.status,
            "last_check": self.last_check,
            "message": self.message,
            "metrics": self.metrics,
            "failure_count": self.failure_count
        }

@dataclass
class AlertThreshold:
    metric: str
    warning_threshold: float
    critical_threshold: float
    duration: int = 0  # seconds
    handler: Optional[Callable] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "metric": self.metric,
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold,
            "duration": self.duration
        }

class Monitor:
    """Main monitoring class"""
    
    def __init__(self):
        self.metrics = _metrics
        self.thresholds = []
        self.background_thread = None
        self.stop_event = threading.Event()
        self._lock = threading.RLock()
        self._last_system_check = 0
        
        # Register default alert thresholds
        self.register_threshold("cpu_percent", 80, 95, 300)
        self.register_threshold("memory_percent", 85, 95, 300)
        self.register_threshold("disk_percent", 85, 95, 0)
        
        # Start background thread if enabled
        if ENABLE_SCHEDULED_CHECKS:
            self.start_background_monitoring()
            
    def start_background_monitoring(self):
        """Start the background monitoring thread"""
        if self.background_thread is not None and self.background_thread.is_alive():
            return
            
        self.stop_event.clear()
        self.background_thread = threading.Thread(
            target=self._background_monitoring_task,
            daemon=True,
            name="MonitoringThread"
        )
        self.background_thread.start()
        logger.info("Background monitoring thread started")
    
    def stop_background_monitoring(self):
        """Stop the background monitoring thread"""
        if self.background_thread is not None:
            self.stop_event.set()
            self.background_thread.join(timeout=5)
            self.background_thread = None
            logger.info("Background monitoring thread stopped")
    
    def _background_monitoring_task(self):
        """Background task that periodically collects metrics"""
        while not self.stop_event.is_set():
            try:
                current_time = time.time()
                
                # Check if we need to collect system metrics
                if ENABLE_SYSTEM_METRICS and (current_time - self._last_system_check) >= SAMPLE_INTERVAL:
                    self.collect_system_metrics()
                    self._last_system_check = current_time
                    
                # Check system health
                self.check_health()
                
                # Check thresholds and send alerts
                self.check_thresholds()
                
                # Sleep until next interval
                self.stop_event.wait(HEALTH_CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Error in monitoring background task: {str(e)}", exc_info=e)
                # Sleep a bit to prevent tight error loops
                time.sleep(5)
    
    def register_threshold(self, metric: str, warning: float, critical: float, 
                          duration: int = 0, handler: Optional[Callable] = None) -> None:
        """Register a new alert threshold"""
        self.thresholds.append(AlertThreshold(
            metric=metric,
            warning_threshold=warning,
            critical_threshold=critical,
            duration=duration,
            handler=handler
        ))
        logger.info(f"Registered alert threshold for {metric}: warning={warning}, critical={critical}")
    
    @contextmanager
    def track_request(self, endpoint: str, method: str = "GET") -> None:
        """Context manager to track API request metrics"""
        if not ENABLE_REQUEST_LOGGING:
            yield
            return
            
        start_time = time.time()
        error = None
        status_code = 200
        
        try:
            yield
        except Exception as e:
            error = str(e)
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time
            endpoint_key = f"{method}:{endpoint}"
            
            with self._lock:
                if endpoint_key not in self.metrics["requests"]:
                    self.metrics["requests"][endpoint_key] = RequestMetrics(endpoint, method)
                
                self.metrics["requests"][endpoint_key].add_request(
                    duration=duration,
                    status_code=status_code,
                    error=error
                )
                
                # Record in the latency tracker
                self.metrics["api_latency"].append({
                    "endpoint": endpoint,
                    "method": method,
                    "duration": duration,
                    "timestamp": time.time(),
                    "status": status_code,
                    "error": error
                })
                
                # Trim latency list if too long
                if len(self.metrics["api_latency"]) > MAX_SAMPLES:
                    self.metrics["api_latency"] = self.metrics["api_latency"][-MAX_SAMPLES:]
                    
                # Update error counts if there was an error
                if error:
                    self.metrics["error_counts"]["total"] += 1
                    
                    # By endpoint
                    if endpoint not in self.metrics["error_counts"]["by_endpoint"]:
                        self.metrics["error_counts"]["by_endpoint"][endpoint] = 0
                    self.metrics["error_counts"]["by_endpoint"][endpoint] += 1
                    
                    # By error type
                    error_type = error.split(":")[0] if ":" in error else error
                    if error_type not in self.metrics["error_counts"]["by_type"]:
                        self.metrics["error_counts"]["by_type"][error_type] = 0
                    self.metrics["error_counts"]["by_type"][error_type] += 1
    
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect system metrics"""
        metrics = {}
        metrics["timestamp"] = time.time()
        
        # Get basic system metrics
        if PSUTIL_AVAILABLE:
            metrics["cpu_percent"] = psutil.cpu_percent(interval=0.5)
            metrics["memory_percent"] = psutil.virtual_memory().percent
            metrics["disk_percent"] = psutil.disk_usage("/").percent
            metrics["open_files"] = len(psutil.Process().open_files())
            metrics["network_connections"] = len(psutil.net_connections())
            metrics["system_load"] = [x / psutil.cpu_count() for x in psutil.getloadavg()]
        else:
            # Fallback metrics when psutil is not available
            metrics["cpu_percent"] = -1
            metrics["memory_percent"] = -1
            metrics["disk_percent"] = -1
        
        system_metrics = SystemMetrics(**metrics)
        
        # Store the metrics
        with self._lock:
            self.metrics["system"]["samples"].append(system_metrics.to_dict())
            self.metrics["system"]["last_updated"] = metrics["timestamp"]
            
            # Trim samples if too many
            if len(self.metrics["system"]["samples"]) > MAX_SAMPLES:
                self.metrics["system"]["samples"] = self.metrics["system"]["samples"][-MAX_SAMPLES:]
        
        return system_metrics
    
    def check_redis(self, redis_url: str = None, redis_client: Any = None, name: str = "redis") -> HealthStatus:
        """Check Redis connection health"""
        if not REDIS_AVAILABLE and not redis_client:
            return HealthStatus(
                name=name,
                status="unknown",
                last_check=time.time(),
                message="Redis client not available"
            )
        
        start_time = time.time()
        try:
            if redis_client:
                client = redis_client
            else:
                client = redis.from_url(redis_url)
                
            # Try ping
            response = client.ping()
            
            # Get info
            info = client.info()
            
            # Get metrics
            metrics = {
                "used_memory_human": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "uptime_in_days": info.get("uptime_in_days", 0),
                "response_time_ms": (time.time() - start_time) * 1000
            }
            
            status = HealthStatus(
                name=name,
                status="healthy",
                last_check=time.time(),
                message="Redis is available",
                metrics=metrics
            )
            
            # Reset failure count
            if name in self.metrics["caches"]:
                old_status = self.metrics["caches"][name]
                if old_status.status != "healthy":
                    logger.info(f"Redis ({name}) recovered from {old_status.status} state")
                status.failure_count = 0
            
            # Store the status
            with self._lock:
                self.metrics["caches"][name] = status
                
            return status
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            
            # If we already have a status, increment failure count
            failure_count = 0
            if name in self.metrics["caches"]:
                old_status = self.metrics["caches"][name]
                failure_count = old_status.failure_count + 1
            
            # Determine status based on failure count
            status_level = "degraded"
            if failure_count >= UNHEALTHY_THRESHOLD:
                status_level = "unhealthy"
                logger.error(f"Redis ({name}) is unhealthy: {str(e)}")
            else:
                logger.warning(f"Redis ({name}) is degraded: {str(e)}")
            
            status = HealthStatus(
                name=name,
                status=status_level,
                last_check=time.time(),
                message=f"Redis error: {str(e)}",
                metrics={"response_time_ms": duration},
                failure_count=failure_count
            )
            
            # Store the status
            with self._lock:
                self.metrics["caches"][name] = status
                
            return status
            
    def check_database(self, db: Any = None, name: str = "database") -> HealthStatus:
        """Check database connection health"""
        if db is None:
            return HealthStatus(
                name=name,
                status="unknown",
                last_check=time.time(),
                message="No database connection provided"
            )
            
        start_time = time.time()
        try:
            # Try a simple query
            with db.app.app_context():
                result = db.session.execute("SELECT 1").scalar()
                
            duration = (time.time() - start_time) * 1000
            
            status = HealthStatus(
                name=name,
                status="healthy",
                last_check=time.time(),
                message="Database is available",
                metrics={
                    "response_time_ms": duration
                }
            )
            
            # Reset failure count
            if name in self.metrics["databases"]:
                old_status = self.metrics["databases"][name]
                if old_status.status != "healthy":
                    logger.info(f"Database ({name}) recovered from {old_status.status} state")
                status.failure_count = 0
            
            # Store the status
            with self._lock:
                self.metrics["databases"][name] = status
                
            return status
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            
            # If we already have a status, increment failure count
            failure_count = 0
            if name in self.metrics["databases"]:
                old_status = self.metrics["databases"][name]
                failure_count = old_status.failure_count + 1
            
            # Determine status based on failure count
            status_level = "degraded"
            if failure_count >= UNHEALTHY_THRESHOLD:
                status_level = "unhealthy"
                logger.error(f"Database ({name}) is unhealthy: {str(e)}")
            else:
                logger.warning(f"Database ({name}) is degraded: {str(e)}")
            
            status = HealthStatus(
                name=name,
                status=status_level,
                last_check=time.time(),
                message=f"Database error: {str(e)}",
                metrics={"response_time_ms": duration},
                failure_count=failure_count
            )
            
            # Store the status
            with self._lock:
                self.metrics["databases"][name] = status
                
            return status
            
    def check_external_service(self, url: str, name: str = None, 
                              timeout: int = 5, expected_status: int = 200,
                              method: str = "GET", headers: Dict[str, str] = None,
                              verify_ssl: bool = True) -> HealthStatus:
        """Check external service health by making an HTTP request"""
        try:
            import requests
        except ImportError:
            logger.warning("requests module not available, external service check disabled")
            return HealthStatus(
                name=name or url,
                status="unknown",
                last_check=time.time(),
                message="requests module not available"
            )
            
        start_time = time.time()
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers or {},
                timeout=timeout,
                verify=verify_ssl
            )
            
            duration = (time.time() - start_time) * 1000
            
            # Check if status code matches expected
            if response.status_code == expected_status:
                status = "healthy"
                message = f"Service returned status {response.status_code}"
            else:
                status = "degraded"
                message = f"Service returned unexpected status {response.status_code}, expected {expected_status}"
                
            health_status = HealthStatus(
                name=name or url,
                status=status,
                last_check=time.time(),
                message=message,
                metrics={
                    "response_time_ms": duration,
                    "status_code": response.status_code
                }
            )
            
            return health_status
            
        except requests.exceptions.RequestException as e:
            duration = (time.time() - start_time) * 1000
            
            return HealthStatus(
                name=name or url,
                status="unhealthy",
                last_check=time.time(),
                message=f"Service error: {str(e)}",
                metrics={"response_time_ms": duration}
            )
            
    def check_health(self) -> Dict[str, Any]:
        """Check the health of all monitored systems"""
        health = {
            "timestamp": time.time(),
            "system": {},
            "services": {}
        }
        
        # System health
        if ENABLE_SYSTEM_METRICS and PSUTIL_AVAILABLE:
            system_metrics = self.collect_system_metrics()
            
            # Determine system health
            system_health = "healthy"
            if system_metrics.cpu_percent > 90 or system_metrics.memory_percent > 90 or system_metrics.disk_percent > 90:
                system_health = "critical"
            elif system_metrics.cpu_percent > 75 or system_metrics.memory_percent > 80 or system_metrics.disk_percent > 80:
                system_health = "warning"
                
            health["system"] = {
                "status": system_health,
                "metrics": system_metrics.to_dict()
            }
            
        # Database health
        for name, status in self.metrics["databases"].items():
            health["services"][name] = status.to_dict()
            
        # Cache health
        for name, status in self.metrics["caches"].items():
            health["services"][name] = status.to_dict()
            
        # Overall health
        statuses = [health["system"].get("status", "healthy")]
        for service in health["services"].values():
            statuses.append(service["status"])
            
        if "unhealthy" in statuses:
            health["status"] = "unhealthy"
        elif "degraded" in statuses or "warning" in statuses:
            health["status"] = "degraded"
        else:
            health["status"] = "healthy"
            
        health["hostname"] = socket.gethostname()
        health["environment"] = os.environ.get("FLASK_ENV", "development")
            
        return health
    
    def check_thresholds(self) -> List[Dict[str, Any]]:
        """Check all registered thresholds and trigger alerts if needed"""
        alerts = []
        
        # Get the latest system metrics
        if not self.metrics["system"]["samples"]:
            return alerts
            
        latest_metrics = self.metrics["system"]["samples"][-1]
        
        # Check each threshold
        for threshold in self.thresholds:
            metric_value = latest_metrics.get(threshold.metric)
            
            if metric_value is None:
                continue
                
            # Check if threshold is exceeded
            if metric_value >= threshold.critical_threshold:
                level = "critical"
            elif metric_value >= threshold.warning_threshold:
                level = "warning"
            else:
                continue
                
            # Check if duration threshold is met (if specified)
            if threshold.duration > 0:
                # Get historical samples within the duration window
                duration_ago = time.time() - threshold.duration
                historical_samples = [
                    s for s in self.metrics["system"]["samples"]
                    if s["timestamp"] >= duration_ago
                ]
                
                # Check if threshold is consistently exceeded
                if not all(s.get(threshold.metric, 0) >= (
                    threshold.critical_threshold if level == "critical" else threshold.warning_threshold
                ) for s in historical_samples):
                    continue
                    
            # Threshold is exceeded, create alert
            alert = {
                "metric": threshold.metric,
                "value": metric_value,
                "threshold": threshold.critical_threshold if level == "critical" else threshold.warning_threshold,
                "level": level,
                "timestamp": time.time(),
                "message": f"{threshold.metric} is {level} ({metric_value} >= {threshold.critical_threshold if level == 'critical' else threshold.warning_threshold})"
            }
            
            # Add to alerts list
            alerts.append(alert)
            
            # Log the alert
            if level == "critical":
                logger.critical(f"🚨 ALERT: {alert['message']}")
            else:
                logger.warning(f"⚠️ Alert: {alert['message']}")
                
            # Call handler if provided
            if threshold.handler:
                try:
                    threshold.handler(alert)
                except Exception as e:
                    logger.error(f"Error in alert handler: {str(e)}", exc_info=e)
                    
        return alerts
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health metrics"""
        if not ENABLE_SYSTEM_METRICS:
            return {"status": "disabled"}
            
        return self.check_health()
    
    def get_request_metrics(self) -> Dict[str, Any]:
        """Get API request metrics"""
        if not ENABLE_REQUEST_LOGGING:
            return {"status": "disabled"}
            
        with self._lock:
            return {
                "endpoints": {k: v.to_dict() for k, v in self.metrics["requests"].items()},
                "total_requests": sum(v.count for v in self.metrics["requests"].values()),
                "total_errors": sum(v.error_count for v in self.metrics["requests"].values()),
                "error_rate": sum(v.error_count for v in self.metrics["requests"].values()) / 
                             max(1, sum(v.count for v in self.metrics["requests"].values())),
                "recent_latency": self.metrics["api_latency"][-20:] if self.metrics["api_latency"] else []
            }
    
    def get_error_report(self) -> Dict[str, Any]:
        """Get error report metrics"""
        with self._lock:
            return {
                "total": self.metrics["error_counts"]["total"],
                "by_endpoint": self.metrics["error_counts"]["by_endpoint"],
                "by_type": self.metrics["error_counts"]["by_type"],
                "error_rate": sum(v.error_count for v in self.metrics["requests"].values()) / 
                             max(1, sum(v.count for v in self.metrics["requests"].values())) 
                             if self.metrics["requests"] else 0
            }
            
    def get_metrics_report(self) -> Dict[str, Any]:
        """Get comprehensive metrics report"""
        return {
            "timestamp": time.time(),
            "system_health": self.get_system_health(),
            "request_metrics": self.get_request_metrics(),
            "error_report": self.get_error_report(),
            "database_health": {name: status.to_dict() for name, status in self.metrics["databases"].items()},
            "cache_health": {name: status.to_dict() for name, status in self.metrics["caches"].items()}
        }
        
    def is_healthy(self, component: str = None) -> bool:
        """Check if a specific component is healthy"""
        health = self.get_system_health()
        
        if component is None:
            # Check overall health
            return health.get("status") == "healthy"
        elif component == "system":
            # Check system health
            return health.get("system", {}).get("status") == "healthy"
        elif component in health.get("services", {}):
            # Check specific service health
            return health["services"][component]["status"] == "healthy"
            
        return False
    
    def export_metrics(self, format="json"):
        """Export metrics in various formats"""
        metrics = self.get_metrics_report()
        
        if format == "json":
            return json.dumps(metrics, indent=2)
        elif format == "prometheus":
            lines = []
            
            # System metrics
            system = metrics["system_health"].get("system", {}).get("metrics", {})
            for key, value in system.items():
                if isinstance(value, (int, float)) and key != "timestamp":
                    lines.append(f"proletto_system_{key} {value}")
                    
            # Request metrics
            req_metrics = metrics["request_metrics"]
            lines.append(f"proletto_total_requests {req_metrics.get('total_requests', 0)}")
            lines.append(f"proletto_total_errors {req_metrics.get('total_errors', 0)}")
            lines.append(f"proletto_error_rate {req_metrics.get('error_rate', 0)}")
            
            # Endpoint metrics
            for endpoint_key, endpoint_data in req_metrics.get("endpoints", {}).items():
                safe_name = endpoint_key.replace(":", "_").replace("/", "_").replace("-", "_")
                lines.append(f"proletto_endpoint_{safe_name}_requests {endpoint_data.get('count', 0)}")
                lines.append(f"proletto_endpoint_{safe_name}_errors {endpoint_data.get('error_count', 0)}")
                lines.append(f"proletto_endpoint_{safe_name}_avg_time {endpoint_data.get('avg_time', 0)}")
                
            return "\n".join(lines)
        else:
            raise ValueError(f"Unknown format: {format}")

# Create singleton instance
monitor = Monitor()

# Decorator for tracking function execution time
def track_execution_time(name=None):
    """Decorator to track function execution time"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            endpoint = name or f"{func.__module__}.{func.__name__}"
            with monitor.track_request(endpoint, method="FUNC"):
                return func(*args, **kwargs)
        return wrapper
    return decorator

# Flask integration
def init_app(app, db=None, redis_client=None):
    """Initialize monitoring with a Flask app"""
    
    # Check database health if provided
    if db is not None:
        monitor.check_database(db)
        
    # Check Redis health if provided
    if redis_client is not None:
        monitor.check_redis(redis_client=redis_client)
        
    # Add request tracking middleware
    @app.before_request
    def before_request():
        """Store request start time"""
        from flask import request, g
        g.request_start_time = time.time()
        g.request_endpoint = request.path
        
    @app.after_request
    def after_request(response):
        """Record request metrics"""
        if not ENABLE_REQUEST_LOGGING:
            return response
            
        from flask import g
        start_time = getattr(g, 'request_start_time', None)
        endpoint = getattr(g, 'request_endpoint', None)
        
        if start_time and endpoint:
            from flask import request
            method = request.method
            duration = time.time() - start_time
            error = None
            
            if response.status_code >= 400:
                error = f"HTTP {response.status_code}"
                
            with monitor.track_request(endpoint, method=method):
                pass
                
        return response
        
    # Add monitoring endpoints
    @app.route("/api/monitor/health")
    def monitor_health():
        """Health check endpoint"""
        return app.response_class(
            response=json.dumps(monitor.get_system_health()),
            status=200,
            mimetype="application/json"
        )
        
    @app.route("/api/monitor/metrics")
    def monitor_metrics():
        """Metrics endpoint"""
        return app.response_class(
            response=json.dumps(monitor.get_metrics_report()),
            status=200,
            mimetype="application/json"
        )
        
    @app.route("/api/monitor/prometheus")
    def monitor_prometheus():
        """Prometheus metrics endpoint"""
        return app.response_class(
            response=monitor.export_metrics(format="prometheus"),
            status=200,
            mimetype="text/plain"
        )
        
    logger.info("Monitoring initialized with Flask app")
    return monitor