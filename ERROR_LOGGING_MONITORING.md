# Proletto Error Logging & Monitoring System

This document provides comprehensive information about the error logging and monitoring system implemented in Proletto.

## Table of Contents

1. [Overview](#overview)
2. [Error Logging](#error-logging)
   - [Logging Levels](#logging-levels)
   - [Log Destinations](#log-destinations)
   - [Structured Logging](#structured-logging)
   - [Error Decorators](#error-decorators)
   - [Error Context Managers](#error-context-managers)
3. [System Monitoring](#system-monitoring)
   - [System Metrics](#system-metrics)
   - [API Request Tracking](#api-request-tracking)
   - [Service Health Checks](#service-health-checks)
   - [Alert Thresholds](#alert-thresholds)
4. [Integration](#integration)
   - [Flask Integration](#flask-integration)
   - [Database Integration](#database-integration)
   - [Slack Integration](#slack-integration)
5. [Admin Dashboard](#admin-dashboard)
6. [Configuration](#configuration)
7. [Best Practices](#best-practices)

## Overview

The Proletto Error Logging & Monitoring System provides comprehensive tracking of application errors, system health, and performance metrics. It supports multiple output destinations for logs, structured logging for better analysis, and real-time monitoring of system health.

Key features:
- Multi-destination logging (console, files, database, Slack)
- Structured JSON logging
- System health monitoring (CPU, memory, disk usage)
- API request performance tracking
- Service health checks (database, Redis, external services)
- Admin monitoring dashboard
- Prometheus integration

## Error Logging

### Logging Levels

The following logging levels are used:

- **DEBUG**: Detailed information, typically useful only for diagnosing problems
- **INFO**: Confirmation that things are working as expected
- **WARNING**: Indication that something unexpected happened or may happen
- **ERROR**: Due to a more serious problem, some functionality was unable to perform
- **CRITICAL**: A serious error, indicating that the program itself may be unable to continue running

### Log Destinations

Logs are sent to multiple destinations:

1. **Console**: All logs are printed to stdout for immediate visibility
2. **Log Files**: 
   - `logs/proletto.log`: All logs with rotation by size (10MB)
   - `logs/proletto_error.log`: Error and critical logs with daily rotation
   - `logs/proletto_structured.json`: Structured JSON logs with rotation by size (20MB)
3. **Database**: Error and critical logs are stored in the database (if enabled)
4. **Slack**: Critical errors are sent to Slack (if configured)

### Structured Logging

Structured logging in JSON format provides additional context for each log entry:

```json
{
  "timestamp": "2025-05-10T06:35:12.548",
  "level": "ERROR",
  "logger": "proletto",
  "message": "Failed to connect to database",
  "module": "database_service",
  "function": "connect",
  "line": 45,
  "process_id": 1234,
  "thread_id": 5678,
  "environment": "production",
  "exception": {
    "type": "ConnectionError",
    "message": "Connection refused",
    "traceback": ["..."]
  },
  "user_id": "12345",
  "component": "database"
}
```

### Error Decorators

Two decorators are provided for easy error handling:

1. **log_function_call**: Logs function calls with parameters and return values

```python
from utils.error_logging import log_function_call, logger

@log_function_call(level=logger.DEBUG)
def important_calculation(x, y):
    return x / y
```

2. **handle_errors**: Handles and logs exceptions, with options for fallback values

```python
from utils.error_logging import handle_errors

@handle_errors(reraise=False, fallback_value=0)
def safe_division(x, y):
    return x / y
```

### Error Context Managers

A context manager for error capturing:

```python
from utils.error_logging import ErrorCapture

def user_operation(user_id):
    with ErrorCapture(component="user_service", user_id=user_id, reraise=False):
        # Code that might raise an exception
        result = risky_operation()
        return result
```

## System Monitoring

### System Metrics

The monitoring system collects the following system metrics:

- CPU usage (%)
- Memory usage (%)
- Disk usage (%)
- Open file count
- Network connection count
- System load averages

These metrics are collected at regular intervals and stored for trend analysis.

### API Request Tracking

Every API request is tracked with the following metrics:

- Endpoint path
- HTTP method
- Response time
- Status code
- Error information (if any)

These metrics are aggregated by endpoint to provide insights on:
- Total request count
- Error count and error rate
- Average, minimum, and maximum response times

### Service Health Checks

The monitoring system checks the health of:

- Database connections
- Redis connections
- External services

Each service receives a status:
- **healthy**: Service is fully operational
- **degraded**: Service is experiencing issues but still partially functional
- **unhealthy**: Service is not functioning

### Alert Thresholds

Alert thresholds can be configured for various metrics:

```python
from utils.monitoring import monitor

# Register a threshold for CPU usage
monitor.register_threshold(
    metric="cpu_percent",
    warning_threshold=80,
    critical_threshold=95,
    duration=300  # Must exceed threshold for 5 minutes
)
```

When a threshold is exceeded, alerts are triggered via:
- Log entries
- Slack notifications (for critical alerts)
- Email (if configured)

## Integration

### Flask Integration

To integrate with a Flask application:

```python
from utils.error_logging import logger
from utils.monitoring import monitor
from monitoring_routes import init_app as init_monitoring

def create_app():
    app = Flask(__name__)
    
    # Initialize database
    db.init_app(app)
    
    # Initialize monitoring
    init_monitoring(app, db=db)
    
    return app
```

This will:
- Register monitoring routes
- Add request tracking middleware
- Configure health check endpoints

### Database Integration

To enable database logging:

```python
from utils.error_logging import add_db_handler

def init_db(app, db):
    # Initialize database
    db.init_app(app)
    
    # Add database error logging
    add_db_handler(db)
```

This creates an `error_logs` table in the database and logs all errors there.

### Slack Integration

To enable Slack notifications for critical errors:

1. Set environment variables:
   - `SLACK_BOT_TOKEN` or `SLACK_WEBHOOK_URL`: Slack API credentials
   - `SLACK_CHANNEL_ID`: Channel to send notifications to

2. Slack notifications will automatically be enabled for CRITICAL level logs.

## Admin Dashboard

The monitoring system includes an admin dashboard at `/admin/monitoring` that provides:

- Real-time system health status
- System resource usage graphs
- API request metrics
- Error reports
- Service health status
- Application logs viewer

## Configuration

The following environment variables can be used to configure the system:

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Minimum log level to record | `INFO` |
| `LOG_FORMAT` | Format string for log entries | `%(asctime)s - %(name)s - %(levelname)s - %(message)s` |
| `LOG_DIR` | Directory to store log files | `logs` |
| `FLASK_ENV` | Application environment | `development` |
| `APP_NAME` | Application name used in logs | `proletto` |
| `SLACK_WEBHOOK_URL` | Slack webhook URL for notifications | |
| `SLACK_BOT_TOKEN` | Slack bot token for notifications | |
| `SLACK_CHANNEL_ID` | Slack channel ID for notifications | |
| `MONITOR_MAX_SAMPLES` | Maximum number of metric samples to store | `100` |
| `MONITOR_SAMPLE_INTERVAL` | Interval between system metric samples (seconds) | `60` |
| `MONITOR_REQUEST_LOGGING` | Enable API request logging (0/1) | `1` |
| `MONITOR_SYSTEM_METRICS` | Enable system metrics collection (0/1) | `1` |
| `MONITOR_SCHEDULED_CHECKS` | Enable scheduled health checks (0/1) | `1` |
| `MONITOR_UNHEALTHY_THRESHOLD` | Number of failures before service is marked unhealthy | `3` |
| `MONITOR_HEALTH_CHECK_INTERVAL` | Interval between health checks (seconds) | `60` |

## Best Practices

1. **Use Appropriate Log Levels**:
   - DEBUG: Detailed debug information
   - INFO: General operational information
   - WARNING: Something unexpected but not error-level
   - ERROR: Application errors that should be investigated
   - CRITICAL: Severe errors that need immediate attention

2. **Include Actionable Information in Error Logs**:
   - What operation was being performed
   - What went wrong
   - Any identifiers needed to investigate (user IDs, request IDs)
   - Do NOT include sensitive information (passwords, tokens)

3. **Use Error Decorators and Context Managers**:
   - Use the `@log_function_call` decorator for important functions
   - Use the `@handle_errors` decorator for functions that should not crash
   - Use `ErrorCapture` context manager for blocks of risky code

4. **Configure Alerts Properly**:
   - Set realistic thresholds based on normal operation
   - Ensure critical alerts are actionable
   - Avoid alert fatigue from too many non-critical alerts

5. **Monitor Dashboard Access**:
   - Restrict access to monitoring dashboard to admin users
   - Regularly review metrics to identify trends and issues

6. **Regularly Rotate and Archive Logs**:
   - Ensure log rotation is working properly
   - Archive old logs for historical analysis

7. **Use Request IDs for Tracking**:
   - Generate and include request IDs in logs
   - Pass request IDs through all service calls
   - Include request IDs in error messages to correlate logs