#!/usr/bin/env python3
"""
Redis Connection Fixer

This script specifically tests the authentication credentials for Redis
and updates the environment variables with the correct format.

Usage:
    python fix_redis_connection.py
    python fix_redis_connection.py --password "your_password"
"""

import os
import sys
import logging
import urllib.parse
from redis import Redis, RedisError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('redis-connection-fixer')

def test_and_fix_redis_connection():
    """Test Redis connection with provided credentials and fix URL format."""
    redis_url = os.environ.get('REDIS_URL', '')
    
    # The known working password for Proletto Redis
    redis_password = "Pvaa4zVI1rFkrOmTSqH5bLUklovyXHfH"
    
    logger.info(f"Original REDIS_URL (masked): {redis_url.replace(redis_password, '***') if redis_password and redis_password in redis_url else redis_url}")
    
    if not redis_url:
        logger.error("❌ REDIS_URL environment variable is not set")
        return False
    
    # Extract host and port from REDIS_URL
    if ':' in redis_url and '@' not in redis_url:
        # Looks like host:port format
        host, port_str = redis_url.rsplit(':', 1)
        try:
            port = int(port_str)
        except ValueError:
            logger.error(f"❌ Invalid port number in REDIS_URL: {port_str}")
            return False
    else:
        # Try to parse as URL
        if not (redis_url.startswith('redis://') or redis_url.startswith('rediss://')):
            host = redis_url
            port = 6379
        else:
            # Already a URL, extract parts
            if '@' in redis_url:
                # Has authentication
                auth_part, host_part = redis_url.split('@', 1)
                scheme = auth_part.split('://', 1)[0]
                if ':' in host_part:
                    host, port_str = host_part.rsplit(':', 1)
                    try:
                        port = int(port_str)
                    except ValueError:
                        logger.error(f"❌ Invalid port number in REDIS_URL: {port_str}")
                        return False
                else:
                    host = host_part
                    port = 6379
            else:
                # No authentication in URL
                scheme, rest = redis_url.split('://', 1)
                if ':' in rest:
                    host, port_str = rest.rsplit(':', 1)
                    try:
                        port = int(port_str)
                    except ValueError:
                        logger.error(f"❌ Invalid port number in REDIS_URL: {port_str}")
                        return False
                else:
                    host = rest
                    port = 6379

    logger.info(f"Extracted host: {host}, port: {port}")
    
    # Format password for URL (special characters need encoding)
    encoded_password = urllib.parse.quote_plus(redis_password)
    
    # Try different formats of Redis URLs
    formats_to_try = [
        f"redis://:{encoded_password}@{host}:{port}",                # Format 1: redis://:password@host:port
        f"redis://default:{encoded_password}@{host}:{port}",         # Format 2: redis://default:password@host:port
        f"rediss://:{encoded_password}@{host}:{port}",               # Format 3: rediss://:password@host:port (SSL)
        f"redis://:{redis_password}@{host}:{port}",                 # Format 4: redis://:password@host:port (unencoded)
        f"rediss://:{redis_password}@{host}:{port}",                # Format 5: rediss://:password@host:port (SSL, unencoded)
    ]
    
    success = False
    working_url = None
    
    for i, url in enumerate(formats_to_try, 1):
        masked_url = url.replace(redis_password, '***').replace(encoded_password, '***')
        logger.info(f"Testing format {i}: {masked_url}")
        
        try:
            redis_client = Redis.from_url(url, socket_connect_timeout=5)
            if redis_client.ping():
                logger.info(f"✅ Connection successful with format {i}")
                success = True
                working_url = url
                break
        except RedisError as e:
            logger.error(f"❌ Connection failed with format {i}: {str(e)}")
    
    if success and working_url:
        logger.info(f"✅ Found working Redis URL format")
        
        # Update the environment variable with the working format
        masked_url = working_url.replace(redis_password, '***').replace(encoded_password, '***')
        logger.info(f"Updating REDIS_URL to: {masked_url}")
        
        # Write to .env file if it exists
        env_file = '.env'
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                lines = f.readlines()
            
            redis_url_found = False
            with open(env_file, 'w') as f:
                for line in lines:
                    if line.startswith('REDIS_URL='):
                        f.write(f'REDIS_URL={working_url}\n')
                        redis_url_found = True
                    else:
                        f.write(line)
                
                if not redis_url_found:
                    f.write(f'REDIS_URL={working_url}\n')
            
            logger.info(f"Updated {env_file} with working Redis URL")
        
        # Set environment variable for current process
        os.environ['REDIS_URL'] = working_url
        logger.info("Environment variable updated for current process")
        
        return True
    else:
        logger.error("❌ All Redis connection attempts failed")
        logger.error("❌ Application will use SimpleCache fallback")
        logger.info("\nTroubleshooting tips:")
        logger.info("1. Verify the REDIS_PASSWORD is correct")
        logger.info("2. Make sure the Redis server allows connections from your IP")
        logger.info("3. Check if the Redis server requires SSL/TLS (use rediss:// instead of redis://)")
        logger.info("4. Try with a completely fresh Redis instance")
        return False

if __name__ == "__main__":
    logger.info("=== REDIS CONNECTION FIXER ===")
    success = test_and_fix_redis_connection()
    sys.exit(0 if success else 1)