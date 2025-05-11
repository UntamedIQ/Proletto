#!/usr/bin/env python3
"""
Test script for verifying that the rate limiting system works correctly with 
different API keys and their associated plans.

This script:
1. Reads the API keys from test_api_keys.txt
2. Makes rapid requests to the test endpoint to trigger rate limiting
3. Shows the difference in rate limits between different plans
"""

import os
import sys
import time
import requests
import threading
from concurrent.futures import ThreadPoolExecutor

API_HOST = os.environ.get('API_HOST', 'http://localhost:5001')
TEST_ENDPOINT = f"{API_HOST}/api/v2/test-rate-limit"
REQUESTS_PER_KEY = 35  # Number of requests to make per key


def load_test_keys():
    """Load the test API keys from the file"""
    if not os.path.exists('test_api_keys.txt'):
        print("Error: test_api_keys.txt not found. Run test_db_api_keys.py first.")
        sys.exit(1)
        
    keys = {}
    with open('test_api_keys.txt', 'r') as f:
        for line in f:
            if line.startswith('==='):
                continue
                
            if 'KEY:' in line:
                plan, key = line.strip().split('KEY:')
                plan = plan.strip().lower()
                key = key.strip()
                keys[plan] = key
                
    return keys


def make_request(key, request_num):
    """Make a request to the test endpoint with the given API key"""
    try:
        # Use a different approach for different requests to test both methods
        if request_num % 2 == 0:
            # Use query parameter
            response = requests.get(f"{TEST_ENDPOINT}?key={key}")
        else:
            # Use header
            headers = {"X-API-KEY": key}
            response = requests.get(TEST_ENDPOINT, headers=headers)
            
        status = response.status_code
        
        # Extract rate limit information from headers
        limit = response.headers.get('X-RateLimit-Limit', 'unknown')
        remaining = response.headers.get('X-RateLimit-Remaining', 'unknown')
        reset = response.headers.get('X-RateLimit-Reset', 'unknown')
        
        # If rate limited, get the retry-after value
        retry_after = None
        if status == 429:
            retry_after = response.headers.get('Retry-After', 'unknown')
            
        return {
            'status': status,
            'limit': limit,
            'remaining': remaining,
            'reset': reset,
            'retry_after': retry_after,
            'message': response.json() if status == 200 else None
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


def test_key(plan, key):
    """Test a specific API key with multiple rapid requests"""
    print(f"\n=== Testing {plan.upper()} key rate limits ({REQUESTS_PER_KEY} requests) ===")
    
    results = []
    rate_limited = 0
    
    for i in range(REQUESTS_PER_KEY):
        result = make_request(key, i)
        results.append(result)
        
        if result['status'] == 429:
            rate_limited += 1
            
        # Print every 10th result and all rate-limited ones
        if i % 10 == 0 or result['status'] == 429:
            if result['status'] == 429:
                print(f"Request {i+1}: RATE LIMITED (Retry after: {result['retry_after']}s)")
            else:
                print(f"Request {i+1}: Status {result['status']}, Remaining: {result['remaining']}/{result['limit']}")
                
        # Small delay to avoid overwhelming the server
        time.sleep(0.02)
        
    success_rate = ((REQUESTS_PER_KEY - rate_limited) / REQUESTS_PER_KEY) * 100
    print(f"\n{plan.upper()} key summary:")
    print(f"- Total requests: {REQUESTS_PER_KEY}")
    print(f"- Rate limited: {rate_limited}")
    print(f"- Success rate: {success_rate:.1f}%")
    
    return {
        'plan': plan,
        'rate_limited': rate_limited,
        'success_rate': success_rate
    }


def main():
    """Main test function"""
    print("Starting API key rate limit test...")
    
    # Load the test keys
    keys = load_test_keys()
    print(f"Loaded {len(keys)} test keys: {', '.join(keys.keys())}")
    
    # Test each key in sequence
    results = []
    for plan, key in keys.items():
        result = test_key(plan, key)
        results.append(result)
        # Wait a few seconds between key tests to allow rate limits to recover
        time.sleep(3)
        
    # Print the summary
    print("\n=== Rate Limit Test Summary ===")
    for result in results:
        print(f"{result['plan'].upper()} plan: {result['success_rate']:.1f}% success rate ({result['rate_limited']} rate-limited)")
        
    print("\nNote: Expected success rates by plan:")
    print("- FREE: ~60% (30 req/min limit)")
    print("- PRO: ~80% (60 req/min limit)")
    print("- PARTNER: ~90% (120 req/min limit)")
    print("- ADMIN: ~95% (240 req/min limit)")
    
    print("\nAPI key rate limit testing completed!")


if __name__ == "__main__":
    main()