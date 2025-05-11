"""
Proletto Error Logging and Monitoring System

This module provides a centralized error logging and monitoring system for Proletto.
It supports multiple output destinations:
- Console logging
- File logging with rotation
- Slack notifications for critical errors
- Database logging for error analytics

Usage:
    from utils.error_logging import logger

    # Regular logging
    logger.debug("Debug message")
    logger.info("Information message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical error message")

    # Exception logging with context
    try:
        # Some operation
        result = 1 / 0
    except Exception as e:
        logger.exception("An error occurred during operation", 
                         exc_info=e,
                         extra={
                             "user_id": "12345",
                             "action": "division",
                             "component": "calculator"
                         })
"""

import os
import sys
import time
import json
import logging
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from functools import wraps

# Import optional dependencies
try:
    import slack_sdk
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False

try:
    from flask_sqlalchemy import SQLAlchemy
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# Get environment configuration
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.environ.get("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
LOG_DIR = os.environ.get("LOG_DIR", "logs")
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID")
ENV = os.environ.get("FLASK_ENV", "development")
APP_NAME = os.environ.get("APP_NAME", "proletto")

# Ensure log directory exists
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Create a custom logger
logger = logging.getLogger(APP_NAME)
logger.setLevel(getattr(logging, LOG_LEVEL))

# Remove existing handlers if any
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Create handlers
# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(getattr(logging, LOG_LEVEL))
console_formatter = logging.Formatter(LOG_FORMAT)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# File handler (rotating by size - 10MB max, keep 10 backup files)
file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, f"{APP_NAME}.log"),
    maxBytes=10*1024*1024,
    backupCount=10
)
file_handler.setLevel(getattr(logging, LOG_LEVEL))
file_formatter = logging.Formatter(LOG_FORMAT)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Error file handler (rotating daily, keep 30 days of error logs)
error_file_handler = TimedRotatingFileHandler(
    os.path.join(LOG_DIR, f"{APP_NAME}_error.log"),
    when="midnight",
    interval=1,
    backupCount=30
)
error_file_handler.setLevel(logging.ERROR)
error_formatter = logging.Formatter(LOG_FORMAT)
error_file_handler.setFormatter(error_formatter)
logger.addHandler(error_file_handler)

# JSON handler for structured logging (rotating by size - 20MB max, keep 20 backup files)
json_file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, f"{APP_NAME}_structured.json"),
    maxBytes=20*1024*1024, 
    backupCount=20
)
json_file_handler.setLevel(getattr(logging, LOG_LEVEL))

class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": record.process,
            "thread_id": record.thread,
            "environment": ENV
        }
        
        # Add exception info if available
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
            
        # Add extra fields if available
        if hasattr(record, "extra"):
            log_record.update(record.extra)
        
        return json.dumps(log_record)

json_formatter = JsonFormatter()
json_file_handler.setFormatter(json_formatter)
logger.addHandler(json_file_handler)

# Slack handler for critical errors
class SlackHandler(logging.Handler):
    """Custom handler for sending critical log messages to Slack"""
    def __init__(self, webhook_url=None, bot_token=None, channel_id=None, level=logging.CRITICAL):
        super().__init__(level)
        self.webhook_url = webhook_url
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.client = None
        
        if SLACK_AVAILABLE:
            if bot_token:
                self.client = slack_sdk.WebClient(token=bot_token)
            elif webhook_url:
                self.client = slack_sdk.WebhookClient(webhook_url)
        
    def emit(self, record):
        if not SLACK_AVAILABLE or not (self.webhook_url or self.bot_token):
            return
        
        try:
            log_entry = self.format(record)
            
            # Create a formatted Slack message
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"⚠️ {record.levelname} Alert - {APP_NAME.capitalize()}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Message:* {record.getMessage()}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Environment:* {ENV}"},
                        {"type": "mrkdwn", "text": f"*Timestamp:* {datetime.fromtimestamp(record.created).isoformat()}"},
                        {"type": "mrkdwn", "text": f"*Module:* {record.module}"},
                        {"type": "mrkdwn", "text": f"*Function:* {record.funcName}:{record.lineno}"}
                    ]
                }
            ]
            
            # Add exception information if available
            if record.exc_info:
                exc_type = record.exc_info[0].__name__
                exc_message = str(record.exc_info[1])
                exc_traceback = "".join(traceback.format_exception(*record.exc_info))
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Exception:* {exc_type}: {exc_message}"
                    }
                })
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Traceback:*\n```{exc_traceback[:2000]}```" # Truncate long tracebacks
                    }
                })
            
            # Add extra fields if available
            if hasattr(record, "extra") and record.extra:
                fields = []
                for key, value in record.extra.items():
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    fields.append({"type": "mrkdwn", "text": f"*{key}:* {value}"})
                
                if fields:
                    blocks.append({
                        "type": "section",
                        "fields": fields[:10]  # Limit to 10 fields
                    })
            
            # Send to Slack
            if self.client and self.channel_id:
                self.client.chat_postMessage(
                    channel=self.channel_id,
                    text=f"{record.levelname} Alert - {record.getMessage()}",
                    blocks=blocks
                )
            elif self.client:  # WebhookClient
                self.client.send(
                    text=f"{record.levelname} Alert - {record.getMessage()}",
                    blocks=blocks
                )
                
        except Exception as e:
            # Don't use the logger here to avoid infinite recursion
            print(f"Error sending to Slack: {str(e)}", file=sys.stderr)

# Add Slack handler for CRITICAL messages if configured
if (SLACK_WEBHOOK or SLACK_BOT_TOKEN) and SLACK_AVAILABLE:
    slack_handler = SlackHandler(
        webhook_url=SLACK_WEBHOOK,
        bot_token=SLACK_BOT_TOKEN,
        channel_id=SLACK_CHANNEL_ID,
        level=logging.CRITICAL
    )
    slack_formatter = logging.Formatter("%(levelname)s - %(message)s")
    slack_handler.setFormatter(slack_formatter)
    logger.addHandler(slack_handler)
    logger.info("Slack notifications enabled for critical errors")

# Database logging if available
db_instance = None
ErrorLog = None

def initialize_db_logging(db):
    """Initialize database logging with the provided SQLAlchemy db instance"""
    global db_instance, ErrorLog
    
    if not DB_AVAILABLE:
        logger.warning("SQLAlchemy not available. Database logging disabled.")
        return False
        
    db_instance = db
    
    # Create ErrorLog model if it doesn't exist
    if 'error_logs' not in [t.name for t in db.metadata.tables.values()]:
        class _ErrorLogRecord(db.Model):
            __tablename__ = 'error_logs'
            
            id = db.Column(db.Integer, primary_key=True)
            timestamp = db.Column(db.DateTime, default=datetime.utcnow)
            level = db.Column(db.String(20), index=True)
            message = db.Column(db.Text)
            location = db.Column(db.String(200))
            exception_type = db.Column(db.String(100), nullable=True)
            exception_message = db.Column(db.Text, nullable=True)
            traceback = db.Column(db.Text, nullable=True)
            user_id = db.Column(db.String(100), nullable=True, index=True)
            component = db.Column(db.String(100), nullable=True, index=True)
            environment = db.Column(db.String(50))
            extra_data = db.Column(db.Text, nullable=True)  # JSON string for additional data (renamed from metadata)
            
            def __repr__(self):
                return f"<ErrorLog {self.id} - {self.level}: {self.message[:50]}>"
        
        ErrorLog = _ErrorLogRecord
        with db.app.app_context():
            db.create_all()
        
        logger.info("Database logging initialized with ErrorLog model")
        return True
    else:
        # Model already exists, get reference to it
        ErrorLog = db.metadata.tables['error_logs']
        logger.info("Connected to existing ErrorLog model for database logging")
        return True

class DatabaseHandler(logging.Handler):
    """Handler for logging errors to the database"""
    def __init__(self, level=logging.ERROR):
        super().__init__(level)
    
    def emit(self, record):
        if not db_instance or not ErrorLog:
            return
            
        try:
            # Only log ERROR and above
            if record.levelno < logging.ERROR:
                return
                
            # Create a new error log entry
            entry = ErrorLog(
                timestamp=datetime.fromtimestamp(record.created),
                level=record.levelname,
                message=record.getMessage(),
                location=f"{record.module}.{record.funcName}:{record.lineno}",
                environment=ENV
            )
            
            # Add exception info if available
            if record.exc_info:
                entry.exception_type = record.exc_info[0].__name__
                entry.exception_message = str(record.exc_info[1])
                entry.traceback = "".join(traceback.format_exception(*record.exc_info))
            
            # Add extra fields if available
            if hasattr(record, "extra"):
                extra = record.extra
                if "user_id" in extra:
                    entry.user_id = str(extra.pop("user_id"))
                if "component" in extra:
                    entry.component = str(extra.pop("component"))
                    
                # Store remaining extra data as JSON
                if extra:
                    entry.extra_data = json.dumps(extra)
            
            # Save to database
            with db_instance.app.app_context():
                db_instance.session.add(entry)
                db_instance.session.commit()
                
        except Exception as e:
            # Don't use the logger here to avoid infinite recursion
            print(f"Error logging to database: {str(e)}", file=sys.stderr)

# Function decorators for logging and error handling
def log_function_call(level=logging.DEBUG):
    """Decorator to log function calls with parameters and return values"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            module_name = func.__module__
            
            # Log function call with arguments
            arg_str = ", ".join([repr(a) for a in args])
            kwarg_str = ", ".join([f"{k}={repr(v)}" for k, v in kwargs.items()])
            params = ", ".join(filter(None, [arg_str, kwarg_str]))
            
            logger.log(level, f"Calling {module_name}.{func_name}({params})")
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                # Log return value (truncate if too large)
                result_repr = repr(result)
                if len(result_repr) > 1000:
                    result_repr = result_repr[:1000] + "... [truncated]"
                    
                logger.log(level, f"{module_name}.{func_name} returned {result_repr} (took {elapsed:.3f}s)")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.exception(
                    f"Exception in {module_name}.{func_name} (took {elapsed:.3f}s): {str(e)}",
                    extra={"component": module_name}
                )
                raise
        return wrapper
    return decorator

def handle_errors(reraise=True, fallback_value=None, fallback_function=None, 
                  log_level=logging.ERROR, notify_critical=True):
    """
    Decorator to handle and log exceptions in functions
    
    Args:
        reraise (bool): Whether to re-raise the exception after logging
        fallback_value: Value to return if an exception occurs
        fallback_function: Function to call to get a fallback value
        log_level (int): Level to log the error at
        notify_critical (bool): Whether to treat errors as critical for notification
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Determine function info
                func_name = func.__name__
                module_name = func.__module__
                
                # Log the error
                error_level = logging.CRITICAL if notify_critical else log_level
                logger.log(
                    error_level,
                    f"Error in {module_name}.{func_name}: {str(e)}",
                    exc_info=e,
                    extra={"component": module_name}
                )
                
                # Handle fallback value or function
                if fallback_function is not None:
                    return fallback_function(*args, **kwargs)
                
                # Re-raise or return fallback
                if reraise:
                    raise
                return fallback_value
        return wrapper
    return decorator

# Add function to add a database handler when DB is available
def add_db_handler(db):
    """Add a database handler to the logger"""
    if initialize_db_logging(db):
        db_handler = DatabaseHandler(level=logging.ERROR)
        logger.addHandler(db_handler)
        logger.info("Database handler added to logger")
        return True
    return False

# Allow capturing exceptions in a context manager
class ErrorCapture:
    """Context manager for capturing and logging errors"""
    def __init__(self, component=None, user_id=None, extra=None, reraise=True, 
                log_level=logging.ERROR):
        self.component = component
        self.user_id = user_id
        self.extra = extra or {}
        self.reraise = reraise
        self.log_level = log_level
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Build extra context
            extra = self.extra.copy()
            if self.component:
                extra["component"] = self.component
            if self.user_id:
                extra["user_id"] = self.user_id
                
            # Log the error
            logger.log(
                self.log_level,
                f"Caught exception: {exc_val}",
                exc_info=(exc_type, exc_val, exc_tb),
                extra=extra
            )
            
            # Return True to suppress exception if reraise is False
            return not self.reraise
        return True

# Alert on startup
logger.info(f"Proletto error logging initialized - Level: {LOG_LEVEL}, Environment: {ENV}")

# Sample usage of context manager
# with ErrorCapture(component="auth", user_id="12345"):
#     # Code that might throw an exception
#     result = 1 / 0