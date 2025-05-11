#!/usr/bin/env python3
"""
Fix Redis URL Script

This script helps fix the Redis URL format issues by testing multiple format variations
and updating the environment variable with the working format.

Usage:
    python fix_redis_url.py [--test-only]

Options:
    --test-only  Only test connections but don't modify environment variables
"""

import os
import sys
import argparse
import logging
import urllib.parse
import redis
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("redis-url-fixer")

def test_redis_connection(url, name="Redis URL"):
    """Test a Redis connection URL and return details about the connection."""
    masked_url = url
    if '@' in url:
        scheme, rest = url.split('://', 1)
        auth, server = rest.split('@', 1)
        masked_url = f"{scheme}://***@{server}"
    
    logger.info(f"Testing {name}: {masked_url}")
    try:
        # Create Redis client with more conservative timeouts
        r = redis.from_url(
            url,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30
        )
        
        # Test connection with PING
        start = time.time()
        ping_result = r.ping()
        latency = (time.time() - start) * 1000  # Convert to ms
        
        # Get server info for additional diagnostics
        info = r.info()
        
        logger.info(f"✅ Connection successful for {name}")
        logger.info(f"  Ping response: {ping_result}")
        logger.info(f"  Latency: {latency:.2f}ms")
        logger.info(f"  Redis version: {info.get('redis_version', 'unknown')}")
        logger.info(f"  Used memory: {info.get('used_memory_human', 'unknown')}")
        
        return True, url
    except redis.exceptions.AuthenticationError as e:
        logger.error(f"❌ Authentication error for {name}: {e}")
        return False, None
    except redis.exceptions.ConnectionError as e:
        logger.error(f"❌ Connection error for {name}: {e}")
        return False, None
    except Exception as e:
        logger.error(f"❌ Unexpected error for {name}: {e}")
        return False, None

def fix_redis_url():
    """Test different Redis URL formats and fix the environment variable."""
    redis_url = os.environ.get('REDIS_URL', '')
    redis_password = os.environ.get('REDIS_PASSWORD', '')
    
    if not redis_url:
        logger.error("❌ REDIS_URL environment variable is not set")
        return False
    
    logger.info(f"Current REDIS_URL (masked): {'***' if redis_url else 'None'}")
    logger.info(f"REDIS_PASSWORD available: {'Yes' if redis_password else 'No'}")
    
    # Track the working formats
    working_formats = []
    
    # Test the current format first
    success, valid_url = test_redis_connection(redis_url, "Current REDIS_URL")
    if success:
        working_formats.append(valid_url)
    
    # If we have both URL and password but no authentication in URL, try adding it
    if not success and redis_url and redis_password and '@' not in redis_url:
        # Extract parts
        if '://' in redis_url:
            scheme, rest = redis_url.split('://', 1)
        else:
            scheme = 'redis'
            rest = redis_url
            
        # Add password
        password_url = f"{scheme}://:{redis_password}@{rest}"
        success, valid_url = test_redis_connection(password_url, "URL with password")
        if success:
            working_formats.append(valid_url)
    
    # If we already have authentication, but still failing, try with different formats
    if not success and '@' in redis_url:
        # Parse the URL to extract components
        parsed = urllib.parse.urlparse(redis_url)
        host = parsed.hostname or ''
        port = parsed.port or 6379
        
        # Try without username (empty username)
        if parsed.username:
            no_username_url = f"redis://:{parsed.password or ''}@{host}:{port}"
            success, valid_url = test_redis_connection(no_username_url, "URL without username")
            if success:
                working_formats.append(valid_url)
        
        # Try with 'default' username
        default_username_url = f"redis://default:{parsed.password or ''}@{host}:{port}"
        success, valid_url = test_redis_connection(default_username_url, "URL with 'default' username")
        if success:
            working_formats.append(valid_url)
        
        # Try with URL-encoded password
        if parsed.password:
            encoded_password = urllib.parse.quote_plus(parsed.password)
            encoded_url = f"redis://:{encoded_password}@{host}:{port}"
            success, valid_url = test_redis_connection(encoded_url, "URL with encoded password")
            if success:
                working_formats.append(valid_url)
    
    # Try known Redis Cloud formats if it matches our hostname
    if not success and "redis-14544.c253.us-central1-1.gce.redns.redis-cloud.com" in redis_url:
        test_formats = [
            # Standard formats
            f"redis://:{redis_password}@redis-14544.c253.us-central1-1.gce.redns.redis-cloud.com:14544",
            f"redis://default:{redis_password}@redis-14544.c253.us-central1-1.gce.redns.redis-cloud.com:14544",
            # With database number
            f"redis://:{redis_password}@redis-14544.c253.us-central1-1.gce.redns.redis-cloud.com:14544/0",
            # With encoded password (if it contains special chars)
            f"redis://:{urllib.parse.quote_plus(redis_password)}@redis-14544.c253.us-central1-1.gce.redns.redis-cloud.com:14544",
            # Sometimes Redis Cloud needs username
            f"redis://rediscloud:{redis_password}@redis-14544.c253.us-central1-1.gce.redns.redis-cloud.com:14544",
        ]
        
        for i, test_url in enumerate(test_formats):
            success, valid_url = test_redis_connection(test_url, f"Redis Cloud format {i+1}")
            if success:
                working_formats.append(valid_url)
                break  # Found a working format, stop testing
    
    # Simply try the raw host:port without auth for public Redis instances
    if not success and ':' in redis_url:
        # Just try host:port without auth (rare, but sometimes Redis is public)
        if '@' in redis_url:
            # Extract host:port part
            host_port = redis_url.split('@', 1)[1]
        else:
            host_port = redis_url
            
        public_url = f"redis://{host_port}"
        success, valid_url = test_redis_connection(public_url, "Public Redis URL")
        if success:
            working_formats.append(valid_url)
    
    # Report results
    if working_formats:
        best_url = working_formats[0]  # Use the first working format
        logger.info("✅ Found working Redis URL format!")
        
        # Update environment variable if not in test mode
        if '--test-only' not in sys.argv:
            os.environ['REDIS_URL'] = best_url
            logger.info("✅ Updated REDIS_URL environment variable with working format")
            
            # Suggest adding to .env file or environment
            masked_url = best_url
            if '@' in best_url:
                scheme, rest = best_url.split('://', 1)
                auth, server = rest.split('@', 1)
                masked_url = f"{scheme}://***@{server}"
                
            logger.info(f"✅ Use this format for REDIS_URL: {masked_url}")
            logger.info("✅ Make sure to update your .env file or deployment environment")
            return True
        else:
            logger.info("ℹ️ Test-only mode: environment variable not updated")
            return True
    else:
        logger.error("❌ All Redis connection attempts failed")
        logger.error("❌ Application will use SimpleCache fallback")
        
        # Provide troubleshooting tips
        logger.info("\nTroubleshooting tips:")
        logger.info("1. Verify the REDIS_PASSWORD is correct")
        logger.info("2. Make sure the Redis server allows connections from your IP")
        logger.info("3. Check if the Redis server requires SSL/TLS (use rediss:// instead of redis://)")
        logger.info("4. Try with a completely fresh Redis instance")
        return False

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Fix Redis URL formatting issues.")
    parser.add_argument('--test-only', action='store_true', help="Only test connections, don't modify environment variables")
    args = parser.parse_args()
    
    if args.test_only:
        logger.info("Running in test-only mode - won't modify environment variables")
    
    print("\n=== REDIS URL FIXER ===\n")
    success = fix_redis_url()
    print("\n=====================\n")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()