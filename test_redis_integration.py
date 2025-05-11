#!/usr/bin/env python3
"""
Redis Integration Test Script for Proletto API

This script tests the Redis integration for both caching and rate limiting
in the Proletto API. It runs a series of tests against the API to verify
that Redis is properly configured and functioning.

Usage:
  python test_redis_integration.py

Requirements:
  - requests
  - colorama (optional, for colored output)
  - An API key with appropriate permissions

Environment variables:
  - TEST_API_KEY: API key to use for testing (required)
  - API_BASE_URL: Base URL for the API (default: http://localhost:5001)
"""

import os
import time
import json
import requests
from datetime import datetime
import sys

# Try to use colorama for colored output
try:
    from colorama import init, Fore, Style
    init()
    
    def print_success(message):
        print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")
        
    def print_error(message):
        print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")
        
    def print_info(message):
        print(f"{Fore.BLUE}ℹ {message}{Style.RESET_ALL}")
        
    def print_warning(message):
        print(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")
        
    def print_section(message):
        print(f"\n{Fore.CYAN}== {message} =={Style.RESET_ALL}")
        
except ImportError:
    # Fallback if colorama is not installed
    def print_success(message):
        print(f"✓ {message}")
        
    def print_error(message):
        print(f"✗ {message}")
        
    def print_info(message):
        print(f"ℹ {message}")
        
    def print_warning(message):
        print(f"⚠ {message}")
        
    def print_section(message):
        print(f"\n== {message} ==")

# Configuration
API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:5001')
API_KEY = os.environ.get('TEST_API_KEY', '')

# Check for API key
if not API_KEY:
    print_error("No API key provided. Please set the TEST_API_KEY environment variable.")
    print_info("Example: TEST_API_KEY=your_api_key python test_redis_integration.py")
    sys.exit(1)

# Endpoints to test
ENDPOINTS = {
    'health': '/health',
    'stats': '/stats',
    'recommendations': '/recommendations?user_id=1',
    'rate_limit_test': '/test-rate-limit'
}

# Test session
session = requests.Session()
session.headers.update({
    'X-API-KEY': API_KEY,
    'Accept': 'application/json'
})

def call_endpoint(endpoint_name, expected_status=200):
    """Call an API endpoint and return the response"""
    url = f"{API_BASE_URL}{ENDPOINTS[endpoint_name]}"
    try:
        start_time = time.time()
        response = session.get(url, timeout=10)
        elapsed = time.time() - start_time
        
        if response.status_code == expected_status:
            print_success(f"{endpoint_name.capitalize()}: {response.status_code} ({elapsed:.3f}s)")
        else:
            print_error(f"{endpoint_name.capitalize()}: Expected {expected_status}, got {response.status_code} ({elapsed:.3f}s)")
            
        try:
            return response.json()
        except ValueError:
            print_error(f"Could not parse JSON response from {endpoint_name}")
            return None
    except requests.exceptions.RequestException as e:
        print_error(f"{endpoint_name.capitalize()}: {str(e)}")
        return None

def test_caching(endpoint_name, iterations=3, delay=0.1):
    """Test if an endpoint is being cached"""
    print_section(f"Testing caching for {endpoint_name}")
    
    response_times = []
    responses = []
    
    for i in range(iterations):
        print_info(f"Request {i+1}/{iterations}...")
        start_time = time.time()
        response = call_endpoint(endpoint_name)
        elapsed = time.time() - start_time
        response_times.append(elapsed)
        responses.append(response)
        
        if i < iterations - 1:
            time.sleep(delay)
    
    # Check if responses are identical (indicating caching)
    all_identical = all(json.dumps(resp, sort_keys=True) == json.dumps(responses[0], sort_keys=True) 
                       for resp in responses[1:])
                       
    # Check if subsequent responses were faster (indicating caching)
    first_time = response_times[0]
    avg_subsequent_time = sum(response_times[1:]) / len(response_times[1:])
    
    if all_identical and avg_subsequent_time < first_time:
        print_success(f"Caching check: Responses were identical and subsequent calls were faster ({avg_subsequent_time:.3f}s vs {first_time:.3f}s)")
        return True
    elif all_identical:
        print_warning(f"Partial caching check: Responses were identical but not faster ({avg_subsequent_time:.3f}s vs {first_time:.3f}s)")
        return True
    else:
        print_error("Caching check: Responses were different, caching may not be working")
        return False

def test_rate_limiting(requests_per_second=10, duration=3):
    """Test if rate limiting is being enforced"""
    print_section("Testing rate limiting")
    
    total_requests = requests_per_second * duration
    successful_requests = 0
    rate_limited_requests = 0
    start_time = time.time()
    
    print_info(f"Sending {total_requests} requests over {duration} seconds...")
    
    for i in range(total_requests):
        try:
            response = session.get(f"{API_BASE_URL}{ENDPOINTS['rate_limit_test']}", timeout=5)
            if response.status_code == 200:
                successful_requests += 1
            elif response.status_code == 429:
                rate_limited_requests += 1
                
                # Check for Retry-After header
                retry_after = response.headers.get('Retry-After')
                if retry_after:
                    print_info(f"Rate limit hit with Retry-After: {retry_after}s")
                
                # Try to get the error message
                try:
                    error_data = response.json()
                    if 'error' in error_data and 'retry_after' in error_data['error']:
                        print_info(f"Rate limit error with retry_after: {error_data['error']['retry_after']}")
                except:
                    pass
            else:
                print_warning(f"Unexpected response: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print_error(f"Request failed: {str(e)}")
        
        # Sleep for a bit to spread out the requests
        if i < total_requests - 1:
            time.sleep(duration / total_requests)
    
    elapsed = time.time() - start_time
    
    print_info(f"Completed {total_requests} requests in {elapsed:.2f} seconds")
    print_info(f"Successful: {successful_requests}, Rate Limited: {rate_limited_requests}")
    
    if rate_limited_requests > 0:
        print_success("Rate limiting is active (some requests were rate limited)")
        return True
    else:
        # If no rate limiting occurred, it might be because our limits are high enough
        plan = None
        response = call_endpoint('rate_limit_test')
        if response and 'plan' in response:
            plan = response.get('plan')
            limit = response.get('limit')
            print_warning(f"No rate limiting occurred. Your plan '{plan}' may have a high limit ({limit})")
        else:
            print_warning("No rate limiting occurred. Your API key may have a high limit or rate limiting is disabled")
        return False

def main():
    """Main test function"""
    print_section("Redis Integration Tests")
    print_info(f"Testing against API URL: {API_BASE_URL}")
    print_info(f"Using API key: {API_KEY[:5]}...{API_KEY[-3:]}")
    print_info(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test basic endpoint access
    print_section("Testing basic endpoint access")
    call_endpoint('health')
    call_endpoint('stats')
    stats_response = call_endpoint('recommendations')
    
    if not stats_response:
        print_error("Could not access basic endpoints. Aborting tests.")
        return
    
    # Test caching on various endpoints
    test_caching('health')
    test_caching('stats')
    test_caching('recommendations')
    
    # Test rate limiting
    test_rate_limiting()
    
    print_section("Test Summary")
    print_info(f"Tests completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info("Check the logs above for detailed results")

if __name__ == "__main__":
    main()