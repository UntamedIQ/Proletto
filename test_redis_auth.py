#!/usr/bin/env python3
"""
Redis Authentication Test Script
This script tests Redis authentication with different formats and strategies
and provides detailed error information to help diagnose connection issues.
"""

import os
import logging
import redis
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("redis-auth-test")

def test_redis_connection(url, name="Redis URL"):
    """Test a Redis connection URL and return details about the connection."""
    logger.info(f"Testing {name}: {url.replace(':password@', ':***@') if '@' in url else url}")
    try:
        # Create Redis client
        r = redis.from_url(url)
        
        # Test connection with PING
        start = time.time()
        ping_result = r.ping()
        latency = (time.time() - start) * 1000  # Convert to ms
        
        # Get server info
        info = r.info()
        
        logger.info(f"✅ Connection successful for {name}")
        logger.info(f"  Ping response: {ping_result}")
        logger.info(f"  Latency: {latency:.2f}ms")
        logger.info(f"  Redis version: {info.get('redis_version', 'unknown')}")
        logger.info(f"  Used memory: {info.get('used_memory_human', 'unknown')}")
        logger.info(f"  Connected clients: {info.get('connected_clients', 'unknown')}")
        
        # More useful stats for diagnostics
        if "redis_mode" in info:
            logger.info(f"  Redis mode: {info['redis_mode']}")
        if "maxmemory_human" in info:
            logger.info(f"  Max memory: {info['maxmemory_human']}")
        if "maxmemory_policy" in info:
            logger.info(f"  Memory policy: {info['maxmemory_policy']}")
            
        return True, None
    except redis.exceptions.AuthenticationError as e:
        logger.error(f"❌ Authentication error for {name}: {e}")
        logger.error(f"  The password in the URL is incorrect or the format is wrong")
        return False, f"Authentication error: {e}"
    except redis.exceptions.ConnectionError as e:
        logger.error(f"❌ Connection error for {name}: {e}")
        logger.error(f"  Cannot reach Redis server, check host and port")
        return False, f"Connection error: {e}"
    except Exception as e:
        logger.error(f"❌ Unexpected error for {name}: {e}")
        return False, f"Error: {e}"

def main():
    """Main function to test different Redis connection formats."""
    print("\n======= REDIS CONNECTION TESTER =======\n")
    
    # Get REDIS_URL and REDIS_PASSWORD from environment
    redis_url = os.environ.get("REDIS_URL", "")
    redis_password = os.environ.get("REDIS_PASSWORD", "")
    
    if not redis_url:
        logger.error("❌ REDIS_URL environment variable is not set")
        return
    
    # Test connection with original REDIS_URL
    print("\n--- Testing with original REDIS_URL ---")
    success, error = test_redis_connection(redis_url, "original REDIS_URL")
    
    # Try without password if it has one
    if not success and '@' in redis_url:
        print("\n--- Testing without password ---")
        try:
            scheme, rest = redis_url.split("://", 1)
            if '@' in rest:
                host_part = rest.split('@', 1)[1]
                no_auth_url = f"{scheme}://{host_part}"
                success, error = test_redis_connection(no_auth_url, "URL without auth")
        except Exception as e:
            logger.error(f"Error parsing URL for no-auth test: {e}")
    
    # If we have a password, try with just the password
    if not success and redis_password:
        print("\n--- Testing with just REDIS_PASSWORD ---")
        try:
            scheme, rest = redis_url.split("://", 1) if "://" in redis_url else ("redis", redis_url)
            if '@' in rest:
                host_part = rest.split('@', 1)[1]
            else:
                host_part = rest
            
            password_url = f"{scheme}://:{redis_password}@{host_part}"
            success, error = test_redis_connection(password_url, "URL with REDIS_PASSWORD")
        except Exception as e:
            logger.error(f"Error creating URL with password: {e}")
    
    # Try some standard formats
    if not success and "redis-14544.c253.us-central1-1.gce.redns.redis-cloud.com" in redis_url:
        print("\n--- Testing with known Redis Cloud format ---")
        # Redis Cloud default format
        test_formats = [
            f"redis://:{redis_password}@redis-14544.c253.us-central1-1.gce.redns.redis-cloud.com:14544",
            f"redis://default:{redis_password}@redis-14544.c253.us-central1-1.gce.redns.redis-cloud.com:14544",
            # Redis Cloud API sometimes tells you the username is "default" but it's actually blank
            f"redis://:{redis_password}@redis-14544.c253.us-central1-1.gce.redns.redis-cloud.com:14544/0",
        ]
        
        for i, test_url in enumerate(test_formats):
            print(f"\nTest format {i+1}:")
            success, error = test_redis_connection(test_url, f"Test format {i+1}")
            if success:
                break
    
    print("\n======= RESULTS =======")
    if success:
        print("✅ Successfully connected to Redis")
        print(f"Last working URL format: {test_url.replace(':'+redis_password+'@', ':***@') if '@' in test_url and redis_password else test_url}")
    else:
        print("❌ All Redis connection attempts failed")
        print(f"Last error: {error}")
        print("\nRecommendations:")
        print("1. Verify the REDIS_PASSWORD is correct")
        print("2. Make sure the Redis server allows connections from your IP")
        print("3. Check the Redis server is running and accessible")
        print("4. Ensure the correct port is being used (default is 6379)")
        print("5. Your application will fall back to SimpleCache")
    
    print("\n=======================")
    
if __name__ == "__main__":
    main()