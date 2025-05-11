#!/usr/bin/env python3
"""
Test Runner Script for Proletto CI/CD Pipeline

This script runs the test suite for CI/CD integration.
It sets up the test environment, runs the tests, and generates coverage reports.
"""

import os
import sys
import subprocess
import argparse

# Colors for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'


def print_colored(message, color=GREEN):
    """Print a colored message to the console"""
    print(f"{color}{message}{RESET}")


def setup_test_environment():
    """Set up the test environment variables"""
    # Use a test database
    os.environ["FLASK_ENV"] = "testing"
    os.environ["TESTING"] = "true"
    
    # Use SQLite for testing if no test database URL is provided
    if "TEST_DATABASE_URL" not in os.environ and "DATABASE_URL" not in os.environ:
        os.environ["DATABASE_URL"] = "sqlite:///test.db"
        print_colored("Using SQLite database for testing", YELLOW)
    
    # Disable Redis for testing unless explicitly enabled
    if "TEST_REDIS_ENABLED" not in os.environ:
        os.environ["REDIS_ENABLED"] = "false"
        print_colored("Redis disabled for testing", YELLOW)


def run_unit_tests(verbose=False, coverage=True):
    """Run the unit test suite"""
    print_colored("Running unit tests...")
    
    cmd = ["pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=.", "--cov-report=term", "--cov-report=xml:coverage.xml"])
    
    # Add specific test directories/files
    cmd.append("tests/")
    
    # Run the tests
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print_colored("❌ Unit tests failed!", RED)
        return False
    
    print_colored("✅ All unit tests passed!")
    return True


def run_api_tests(base_url=None):
    """Run API integration tests"""
    print_colored("Running API integration tests...")
    
    if not base_url:
        base_url = "http://localhost:5000"
    
    # Set the base URL for API tests
    os.environ["API_TEST_BASE_URL"] = base_url
    
    cmd = ["pytest", "tests/api/"]
    
    # Run the tests
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print_colored("❌ API tests failed!", RED)
        return False
    
    print_colored("✅ All API tests passed!")
    return True


def run_e2e_tests():
    """Run end-to-end tests with playwright"""
    print_colored("Running end-to-end tests...")
    
    # Check if playwright is installed
    try:
        import playwright
    except ImportError:
        print_colored("⚠️ Playwright not installed. Skipping E2E tests.", YELLOW)
        return True
    
    cmd = ["pytest", "tests/e2e/"]
    
    # Run the tests
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print_colored("❌ End-to-end tests failed!", RED)
        return False
    
    print_colored("✅ All end-to-end tests passed!")
    return True


def main():
    """Main entry point for the test runner"""
    parser = argparse.ArgumentParser(description="Run the Proletto test suite")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--api", action="store_true", help="Run only API tests")
    parser.add_argument("--e2e", action="store_true", help="Run only end-to-end tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-coverage", action="store_true", help="Disable coverage reporting")
    parser.add_argument("--api-url", help="Base URL for API tests", default=None)
    
    args = parser.parse_args()
    
    # If no specific test type is specified, run all tests
    run_all = not (args.unit or args.api or args.e2e)
    
    # Set up test environment
    setup_test_environment()
    
    # Run tests based on arguments
    results = []
    
    if args.unit or run_all:
        results.append(run_unit_tests(args.verbose, not args.no_coverage))
    
    if args.api or run_all:
        results.append(run_api_tests(args.api_url))
    
    if args.e2e or run_all:
        results.append(run_e2e_tests())
    
    # Check if all test suites passed
    if all(results):
        print_colored("✅ All test suites passed!")
        return 0
    else:
        print_colored("❌ One or more test suites failed!", RED)
        return 1


if __name__ == "__main__":
    sys.exit(main())