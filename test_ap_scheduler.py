"""
Test APScheduler Implementation
This script tests the APScheduler implementation for Proletto's scraper automation.

Usage:
    python test_ap_scheduler.py [--simulate-production]
"""
import argparse
import os
import sys
import time
from datetime import datetime

# Import the ap_scheduler module for testing
try:
    from ap_scheduler import (
        init_scheduler,
        shutdown_scheduler,
        get_scheduler_info,
        run_scraper_job,
    )
except ImportError:
    print("Error: ap_scheduler.py module not found. Make sure it exists in the current directory.")
    sys.exit(1)


def main():
    """Test the APScheduler implementation"""
    parser = argparse.ArgumentParser(description="Test the APScheduler implementation")
    parser.add_argument(
        "--simulate-production",
        action="store_true",
        help="Simulate production environment (will actually run jobs)",
    )
    args = parser.parse_args()

    # Save original environment value
    original_env = os.environ.get("REPLIT_DEPLOYMENT")

    try:
        # Set environment variable based on command line arguments
        if args.simulate_production:
            os.environ["REPLIT_DEPLOYMENT"] = "true"
            print("\033[93mRunning in SIMULATED PRODUCTION MODE - Jobs will execute!\033[0m")
        else:
            if os.environ.get("REPLIT_DEPLOYMENT"):
                del os.environ["REPLIT_DEPLOYMENT"]
            print("\033[92mRunning in DEVELOPMENT MODE - Jobs will be scheduled but not executed\033[0m")

        # Initialize the scheduler
        print(f"\nInitializing scheduler at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        scheduler = init_scheduler()

        # Print scheduler info
        print("\nScheduler Information:")
        info = get_scheduler_info()
        for key, value in info.items():
            print(f"  - {key}: {value}")

        print("\nScheduled Jobs:")
        for job in scheduler.get_jobs():
            print(f"  - {job.id}: Next run at {job.next_run_time}")

        # If in simulated production mode, run a test job
        if args.simulate_production:
            print("\nRunning test job (social engine)")
            run_scraper_job("social")
            print("Test job completed")

        # Wait for user input before shutting down
        input("\nPress Enter to shut down the scheduler...")

    finally:
        # Restore original environment variable
        if original_env:
            os.environ["REPLIT_DEPLOYMENT"] = original_env
        else:
            if "REPLIT_DEPLOYMENT" in os.environ:
                del os.environ["REPLIT_DEPLOYMENT"]

        # Shut down the scheduler
        print("Shutting down scheduler...")
        shutdown_scheduler()
        print("Scheduler shut down successfully")


if __name__ == "__main__":
    main()