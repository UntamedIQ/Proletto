#!/usr/bin/env python3
"""
Test script for demonstrating API rate limiting with different plans.
"""

import time
import requests
import concurrent.futures
import json
from datetime import datetime

# Base API URL
BASE_URL = "http://127.0.0.1:5001/api/v2/test-rate-limit"

# Available API keys with different plans
API_KEYS = {
    "free": "freekey123",      # 30 per minute
    "pro": "prokey456",        # 60 per minute
    "partner": "partner789",   # 120 per minute
}

# Get the environment master API key (will be treated as admin)
# In a real app, you'd get this from the environment
import os
ADMIN_KEY = os.environ.get("API_KEY", "master_key_abc")

def make_request(api_key, request_id):
    """Make a single request to the API with the given API key."""
    start_time = time.time()
    try:
        response = requests.get(
            BASE_URL,
            params={"key": api_key},
            headers={"X-Request-ID": str(request_id)}
        )
        
        elapsed = time.time() - start_time
        
        # Get the rate limit headers
        limit = response.headers.get("X-RateLimit-Limit", "N/A")
        remaining = response.headers.get("X-RateLimit-Remaining", "N/A")
        reset = response.headers.get("X-RateLimit-Reset", "N/A")
        
        if response.status_code == 200:
            data = response.json()
            plan = data.get("plan", "unknown")
            return {
                "id": request_id,
                "status": response.status_code,
                "elapsed": elapsed,
                "plan": plan,
                "limit": limit,
                "remaining": remaining,
                "reset": reset,
                "success": True
            }
        else:
            return {
                "id": request_id,
                "status": response.status_code,
                "elapsed": elapsed,
                "limit": limit,
                "remaining": remaining,
                "reset": reset,
                "error": response.text,
                "success": False
            }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "id": request_id,
            "status": "Error",
            "elapsed": elapsed,
            "error": str(e),
            "success": False
        }

def test_api_key(key_name, api_key, requests_count, concurrency=10):
    """Test an API key by making multiple requests."""
    print(f"\n=== Testing {key_name.upper()} API key ({api_key}) ===")
    print(f"Making {requests_count} requests with concurrency={concurrency}\n")
    
    results = []
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(make_request, api_key, i) 
            for i in range(requests_count)
        ]
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            
            if len(results) % 10 == 0 or not result["success"]:
                if result["success"]:
                    status = f"{result['status']} (Plan: {result.get('plan', 'N/A')})"
                else:
                    status = f"{result['status']}: {result.get('error', 'Unknown error')}"
                
                print(f"Request {result['id']}: {status} | " +
                      f"Limit: {result.get('limit', 'N/A')}, " +
                      f"Remaining: {result.get('remaining', 'N/A')}")
    
    total_time = time.time() - start_time
    success_count = sum(1 for r in results if r["success"])
    failure_count = len(results) - success_count
    
    print(f"\nResults for {key_name.upper()}:")
    print(f"Total requests: {len(results)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {failure_count}")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Requests per second: {len(results) / total_time:.2f}")
    print("=" * 50)
    
    return results

def main():
    """Run tests for all API keys."""
    print("API Rate Limit Test")
    print("Testing all API keys with different plans...")
    
    # Test free tier (30 requests per minute)
    free_results = test_api_key("free", API_KEYS["free"], 40)
    
    # Wait a few seconds between tests
    print("\nWaiting 5 seconds before next test...\n")
    time.sleep(5)
    
    # Test pro tier (60 requests per minute)
    pro_results = test_api_key("pro", API_KEYS["pro"], 70)
    
    # Wait a few seconds between tests
    print("\nWaiting 5 seconds before next test...\n")
    time.sleep(5)
    
    # Test partner tier (120 requests per minute)
    partner_results = test_api_key("partner", API_KEYS["partner"], 130)
    
    # Wait a few seconds between tests
    print("\nWaiting 5 seconds before next test...\n")
    time.sleep(5)
    
    # Test admin tier (240 requests per minute)
    admin_results = test_api_key("admin", ADMIN_KEY, 250)
    
    # Create a report
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "free": {
                "total": len(free_results),
                "success": sum(1 for r in free_results if r["success"]),
                "failed": sum(1 for r in free_results if not r["success"])
            },
            "pro": {
                "total": len(pro_results),
                "success": sum(1 for r in pro_results if r["success"]),
                "failed": sum(1 for r in pro_results if not r["success"])
            },
            "partner": {
                "total": len(partner_results),
                "success": sum(1 for r in partner_results if r["success"]),
                "failed": sum(1 for r in partner_results if not r["success"])
            },
            "admin": {
                "total": len(admin_results),
                "success": sum(1 for r in admin_results if r["success"]),
                "failed": sum(1 for r in admin_results if not r["success"])
            }
        }
    }
    
    # Save the report
    with open("rate_limit_test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("\nTest complete! Report saved to rate_limit_test_report.json")
    
    # Check metrics endpoint
    print("\nChecking rate limit metrics...")
    try:
        response = requests.get(
            "http://127.0.0.1:5001/api/v2/admin/rate-limit-metrics",
            params={"key": ADMIN_KEY}
        )
        
        if response.status_code == 200:
            metrics = response.json()
            print("\nRate Limit Metrics:")
            print(json.dumps(metrics, indent=2))
        else:
            print(f"Failed to get metrics: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error getting metrics: {e}")

if __name__ == "__main__":
    main()