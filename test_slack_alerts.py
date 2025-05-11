"""
Test Slack Alerting System for Proletto

This script tests the Slack integration for Proletto alerts.
It sends test messages to the configured Slack channel.

Usage:
    python test_slack_alerts.py [--message "Custom message"]
"""
import argparse
import os
import sys

# Import the alerts module for testing
try:
    from alerts import alert_slack, alert_scheduler_error, alert_scraper_error, alert_scraper_success
except ImportError:
    print("Error: alerts.py module not found. Make sure it exists in the current directory.")
    sys.exit(1)


def test_alert_types():
    """Test different types of alerts"""
    print("\nSending a test info alert...", end="")
    result = alert_slack(
        message="🧪 This is a test INFO message from the Proletto alert system.",
        level="info",
        context={"source": "test_slack_alerts.py", "env": "test"}
    )
    print(" ✓ Success" if result else " ✗ Failed")

    print("Sending a test warning alert...", end="")
    result = alert_slack(
        message="⚠️ This is a test WARNING message from the Proletto alert system.",
        level="warning",
        context={"source": "test_slack_alerts.py", "env": "test", "severity": "medium"}
    )
    print(" ✓ Success" if result else " ✗ Failed")

    print("Sending a test error alert...", end="")
    result = alert_slack(
        message="🚨 This is a test ERROR message from the Proletto alert system.",
        level="error",
        context={"source": "test_slack_alerts.py", "env": "test", "severity": "high"}
    )
    print(" ✓ Success" if result else " ✗ Failed")


def test_specific_alerts():
    """Test specific alert functions"""
    print("\nSending a test scheduler error alert...", end="")
    result = alert_scheduler_error(
        scheduler_name="Test APScheduler",
        error_message="Simulated scheduler error for testing",
        job_id="test_job_123",
        next_run="2025-06-06T12:00:00"
    )
    print(" ✓ Success" if result else " ✗ Failed")

    print("Sending a test scraper error alert...", end="")
    result = alert_scraper_error(
        scraper_name="Test California Scraper",
        error_message="Simulated scraper error for testing",
        url="https://example.com/opportunities",
        attempts=3
    )
    print(" ✓ Success" if result else " ✗ Failed")

    print("Sending a test scraper success alert...", end="")
    result = alert_scraper_success(
        scraper_name="Test New York Scraper",
        opportunities_count=42,
        duration=3.5
    )
    print(" ✓ Success" if result else " ✗ Failed")


def main():
    """Main function to test Slack alerts"""
    parser = argparse.ArgumentParser(description="Test Slack alerts for Proletto")
    parser.add_argument(
        "--message",
        type=str,
        help="Custom message to send to Slack (optional)",
    )
    args = parser.parse_args()

    # Check if Slack credentials are configured
    if not os.environ.get("SLACK_BOT_TOKEN") or not os.environ.get("SLACK_CHANNEL_ID"):
        print("Error: Slack credentials not configured. Please set SLACK_BOT_TOKEN and SLACK_CHANNEL_ID environment variables.")
        return 1

    # Print header
    print("=" * 60)
    print("Proletto Slack Alert System Test")
    print(f"Using channel ID: {os.environ.get('SLACK_CHANNEL_ID')}")
    print("=" * 60)

    # Send custom message if provided
    if args.message:
        print(f"\nSending custom message: '{args.message}'...", end="")
        result = alert_slack(
            message=args.message,
            level="info",
            context={"source": "test_slack_alerts.py", "type": "custom"}
        )
        print(" ✓ Success" if result else " ✗ Failed")
    else:
        # Run standard tests
        test_alert_types()
        test_specific_alerts()

    print("\nAll tests completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())