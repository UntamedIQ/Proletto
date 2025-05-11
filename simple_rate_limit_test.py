#!/usr/bin/env python3
"""
Simple test script to demonstrate API rate limiting
"""

import requests
import time
import json
import os

# Base URL for the test endpoint
BASE_URL = "http://127.0.0.1:5001/api/v2"

# Available API keys with different plans
API_KEYS = {
    "free": "freekey123",  # 30 per minute
    "pro": "prokey456",    # 60 per minute
}

# Get the environment API key (admin level)
ADMIN_KEY = os.environ.get("API_KEY", "master_key_abc")

def test_rate_limit(api_key, key_name, num_requests=40):
    """
    Test rate limiting by making multiple requests with the specified API key
    """
    print(f"\nTesting rate limit with {key_name} API key ({api_key})")
    print(f"Making {num_requests} requests...\n")
    
    successful = 0
    failed = 0
    for i in range(num_requests):
        # Make a request to the test endpoint
        response = requests.get(
            f"{BASE_URL}/test-rate-limit",
            params={"key": api_key}
        )
        
        # Get rate limit info from headers
        limit = response.headers.get("X-RateLimit-Limit", "N/A")
        remaining = response.headers.get("X-RateLimit-Remaining", "N/A")
        
        if response.status_code == 200:
            successful += 1
            data = response.json()
            print(f"Request {i+1}: OK - Plan: {data.get('plan')}, Limit: {limit}, Remaining: {remaining}")
        else:
            failed += 1
            print(f"Request {i+1}: FAILED ({response.status_code}) - Limit: {limit}, Remaining: {remaining}")
            # Print the error response
            try:
                error_data = response.json()
                print(f"  Error: {error_data.get('error', {}).get('message', 'Unknown error')}")
                print(f"  Retry After: {error_data.get('error', {}).get('retry_after', 'N/A')} seconds")
            except:
                print(f"  Error: {response.text}")
        
        # Brief pause to make the output more readable
        time.sleep(0.1)
    
    print(f"\nResults for {key_name.upper()} API key:")
    print(f"Total requests: {num_requests}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    return successful, failed

def check_metrics(api_key):
    """
    Check the rate limit metrics endpoint
    """
    print("\nChecking rate limit metrics...")
    response = requests.get(
        f"{BASE_URL}/admin/rate-limit-metrics",
        params={"key": api_key}
    )
    
    if response.status_code == 200:
        metrics = response.json()
        print("\nRate Limit Metrics:")
        print(json.dumps(metrics, indent=2))
    else:
        print(f"Failed to get metrics: {response.status_code}")
        print(response.text)

def main():
    """Main test function"""
    print("=== SIMPLE API RATE LIMIT TEST ===")
    
    # Test with free tier API key (30 requests/min)
    test_rate_limit(API_KEYS["free"], "free", 40)
    
    print("\nWaiting 5 seconds...\n")
    time.sleep(5)
    
    # Test with pro tier API key (60 requests/min)
    test_rate_limit(API_KEYS["pro"], "pro", 70)
    
    print("\nWaiting 5 seconds...\n")
    time.sleep(5)
    
    # Check the metrics endpoint using admin key
    check_metrics(ADMIN_KEY)

if __name__ == "__main__":
    main()