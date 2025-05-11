"""
Proletto Alerting System
This module provides alerting capabilities for the Proletto system,
including Slack notifications for critical events.
"""
import os
import logging
import json
import requests
import socket
import platform
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('proletto_alerts')

# Initialize Slack client with Bot Token
slack_token = os.environ.get('SLACK_BOT_TOKEN')
slack_channel_id = os.environ.get('SLACK_CHANNEL_ID')
slack_client = None

if slack_token:
    slack_client = WebClient(token=slack_token)
    logger.info("Slack client initialized successfully")
else:
    logger.warning("SLACK_BOT_TOKEN environment variable not set. Slack alerts disabled.")

def alert_slack(message, level="info", context=None):
    """
    Send an alert to Slack using the Slack SDK
    
    Args:
        message (str): The message to send
        level (str): The alert level ('info', 'warning', or 'error')
        context (dict, optional): Additional context information to include
    
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    if not slack_client or not slack_channel_id:
        logger.warning("Slack client not initialized or SLACK_CHANNEL_ID not set. Slack alerts disabled.")
        return False
    
    # Set color based on level
    color = "#36a64f"  # green for info
    icon = ":information_source:"
    if level == "warning":
        color = "#ffcc00"  # yellow
        icon = ":warning:"
    elif level == "error":
        color = "#ff0000"  # red
        icon = ":rotating_light:"
    elif level == "success":
        color = "#2eb886"  # green
        icon = ":white_check_mark:"
    
    # Get system information for context
    hostname = socket.gethostname()
    env = os.environ.get('FLASK_ENV', 'development')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Prepare context fields
    fields = [
        {
            "type": "mrkdwn",
            "text": f"*Environment:*\n{env}"
        },
        {
            "type": "mrkdwn",
            "text": f"*Host:*\n{hostname}"
        },
        {
            "type": "mrkdwn",
            "text": f"*Time:*\n{timestamp}"
        }
    ]
    
    # Add custom context if provided
    if context and isinstance(context, dict):
        for key, value in context.items():
            fields.append({
                "type": "mrkdwn",
                "text": f"*{key}:*\n{value}"
            })
    
    # Create blocks for better formatting
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{icon} Proletto Alert: {level.capitalize()}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Message:*\n{message}"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "fields": fields
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Proletto Monitoring System"
                }
            ]
        }
    ]
    
    # Create fallback text
    fallback_text = f"Proletto Alert ({level.upper()}): {message}"
    
    try:
        # Post message to channel using blocks for rich formatting
        response = slack_client.chat_postMessage(
            channel=slack_channel_id,
            text=fallback_text,  # Fallback text for notifications
            blocks=blocks,
            unfurl_links=False
        )
        logger.info(f"Slack alert sent: {message}")
        return True
    except SlackApiError as e:
        logger.error(f"Error sending Slack message: {e.response['error']}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending Slack alert: {e}")
        return False

def alert_admin_email(subject, message, admin_email=None):
    """
    Send an alert email to system administrators
    
    Args:
        subject (str): Email subject
        message (str): Email body
        admin_email (str, optional): Admin email address. If None, uses ADMIN_EMAIL env var.
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    from email_service import get_email_service
    
    admin_email = admin_email or os.environ.get('ADMIN_EMAIL')
    if not admin_email:
        logger.warning("ADMIN_EMAIL environment variable not set. Email alerts disabled.")
        return False
    
    try:
        # Format subject with environment info
        env = os.environ.get('FLASK_ENV', 'development')
        formatted_subject = f"[Proletto {env.upper()}] {subject}"
        
        # Add timestamp to message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"{message}\n\nTimestamp: {timestamp}"
        
        # Get email service instance and send email
        email_service = get_email_service()
        result = email_service.send_email(
            to_email=admin_email,
            subject=formatted_subject,
            text_content=formatted_message
        )
        
        if result:
            logger.info(f"Admin email alert sent: {subject}")
            return True
        else:
            logger.error("Failed to send admin email alert")
            return False
    except Exception as e:
        logger.error(f"Error sending admin email alert: {e}")
        return False

# Specialized alert functions for specific scenarios

def alert_scraper_error(scraper_name, error_message, url=None, attempts=None):
    """
    Send alert about a scraper error
    
    Args:
        scraper_name (str): Name of the scraper
        error_message (str): Error message
        url (str, optional): URL that was being scraped
        attempts (int, optional): Number of attempts made
        
    Returns:
        bool: True if alert was sent successfully, False otherwise
    """
    message = f"Scraper error in {scraper_name}"
    context = {
        "Error": error_message,
        "URL": url or "N/A",
        "Attempts": str(attempts) if attempts is not None else "N/A"
    }
    return alert_slack(message, "error", context)
    
def alert_scheduler_error(scheduler_name, error_message, job_id=None, next_run=None):
    """
    Send alert about a scheduler error
    
    Args:
        scheduler_name (str): Name of the scheduler (e.g., "APScheduler")
        error_message (str): Error message
        job_id (str, optional): ID of the job that failed
        next_run (str, optional): When the job was scheduled to run next
        
    Returns:
        bool: True if alert was sent successfully, False otherwise
    """
    message = f"Scheduler error in {scheduler_name}"
    context = {
        "Error": error_message,
        "Job ID": job_id or "N/A",
        "Next Run": next_run or "N/A"
    }
    return alert_slack(message, "error", context)

def alert_scraper_success(scraper_name, opportunities_count, duration=None):
    """
    Send alert about successful scraper run
    
    Args:
        scraper_name (str): Name of the scraper
        opportunities_count (int): Number of opportunities found
        duration (float, optional): Duration of the scraper run in seconds
        
    Returns:
        bool: True if alert was sent successfully, False otherwise
    """
    message = f"Scraper {scraper_name} completed successfully"
    context = {
        "Opportunities found": str(opportunities_count),
        "Duration": f"{duration:.2f} seconds" if duration is not None else "N/A"
    }
    return alert_slack(message, "success", context)

def alert_system_health(cpu_usage=None, memory_usage=None, disk_usage=None, custom_metrics=None):
    """
    Send alert about system health
    
    Args:
        cpu_usage (float, optional): CPU usage percentage
        memory_usage (float, optional): Memory usage percentage
        disk_usage (float, optional): Disk usage percentage
        custom_metrics (dict, optional): Custom metrics to include
        
    Returns:
        bool: True if alert was sent successfully, False otherwise
    """
    message = "System health report"
    context = {}
    
    if cpu_usage is not None:
        context["CPU Usage"] = f"{cpu_usage:.1f}%"
    
    if memory_usage is not None:
        context["Memory Usage"] = f"{memory_usage:.1f}%"
    
    if disk_usage is not None:
        context["Disk Usage"] = f"{disk_usage:.1f}%"
    
    if custom_metrics and isinstance(custom_metrics, dict):
        context.update(custom_metrics)
    
    level = "info"
    # Set level based on thresholds
    if (cpu_usage and cpu_usage > 90) or (memory_usage and memory_usage > 90) or (disk_usage and disk_usage > 90):
        level = "error"
    elif (cpu_usage and cpu_usage > 70) or (memory_usage and memory_usage > 70) or (disk_usage and disk_usage > 70):
        level = "warning"
    
    return alert_slack(message, level, context)

def alert_api_error(endpoint, error_message, status_code=None, user_id=None):
    """
    Send alert about API error
    
    Args:
        endpoint (str): API endpoint
        error_message (str): Error message
        status_code (int, optional): HTTP status code
        user_id (str, optional): User ID
        
    Returns:
        bool: True if alert was sent successfully, False otherwise
    """
    message = f"API Error on endpoint: {endpoint}"
    context = {
        "Error": error_message,
        "Status Code": str(status_code) if status_code is not None else "N/A",
        "User": user_id or "N/A"
    }
    return alert_slack(message, "error", context)

def alert_database_issue(operation, error_message, table=None):
    """
    Send alert about database issue
    
    Args:
        operation (str): Database operation (e.g., "query", "insert", "update")
        error_message (str): Error message
        table (str, optional): Database table
        
    Returns:
        bool: True if alert was sent successfully, False otherwise
    """
    message = f"Database issue during {operation}"
    context = {
        "Error": error_message,
        "Table": table or "N/A"
    }
    return alert_slack(message, "error", context)

# Test function
def test_alerts():
    """Test the alerting functionality"""
    # Basic alerts
    alert_slack("This is a test info message", "info")
    alert_slack("This is a test warning message", "warning")
    alert_slack("This is a test error message", "error")
    alert_slack("This is a test success message", "success")
    
    # Specialized alerts
    alert_scraper_error("CaliforniaEngine", "Connection timeout", "https://arts.ca.gov/grants", 3)
    alert_scraper_success("SocialMediaEngine", 57, 42.5)
    alert_system_health(45.2, 62.7, 38.5, {"API Requests": "1,234/min"})
    alert_api_error("/api/opportunities", "Rate limit exceeded", 429, "user123")
    alert_database_issue("query", "Connection refused", "opportunities")
    
    # Email alert
    alert_admin_email("Test Alert", "This is a test admin email alert")

if __name__ == "__main__":
    test_alerts()