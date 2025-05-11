#!/usr/bin/env python3
"""
Proletto Redis Authentication Fixer

This script fixes the Redis authentication by setting the correct password
and testing the connection before updating environment variables.

Usage:
    python fix_redis_auth.py
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
logger = logging.getLogger('redis-auth-fixer')

def test_redis_auth():
    """Test Redis connection with the known password and update configuration."""
    # Current Redis settings
    redis_url = os.environ.get('REDIS_URL', '')
    redis_password = "Pvaa4zVI1rFkrOmTSqH5bLUklovyXHfH"  # Use the known working password
    
    if not redis_url:
        logger.error("❌ REDIS_URL environment variable is not set")
        return False
    
    # Extract host and port from REDIS_URL
    host = None
    port = None
    
    # Parse URL to extract host and port
    if '@' in redis_url:
        # URL already has auth part, extract host:port
        host_part = redis_url.split('@', 1)[1]
        if ':' in host_part:
            host, port_str = host_part.rsplit(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                logger.error(f"❌ Invalid port number in REDIS_URL: {port_str}")
                port = 6379
        else:
            host = host_part
            port = 6379
    elif ':' in redis_url and '://' in redis_url:
        # URL without auth part
        url_parts = redis_url.split('://', 1)[1]
        if ':' in url_parts:
            host, port_str = url_parts.rsplit(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                logger.error(f"❌ Invalid port number in REDIS_URL: {port_str}")
                port = 6379
        else:
            host = url_parts
            port = 6379
    elif ':' in redis_url:
        # Simple host:port format
        host, port_str = redis_url.rsplit(':', 1)
        try:
            port = int(port_str)
        except ValueError:
            logger.error(f"❌ Invalid port number in REDIS_URL: {port_str}")
            port = 6379
    else:
        # Just host
        host = redis_url
        port = 6379
        
    if not host:
        logger.error("❌ Could not extract host from REDIS_URL")
        return False
        
    logger.info(f"Extracted Redis host: {host}, port: {port}")
    
    # Format password for URL (special characters need encoding)
    encoded_password = urllib.parse.quote_plus(redis_password)
    
    # Try both encoded and raw password formats
    test_urls = [
        f"redis://:{encoded_password}@{host}:{port}",
        f"redis://:{redis_password}@{host}:{port}",
        f"redis://default:{encoded_password}@{host}:{port}",
        f"redis://default:{redis_password}@{host}:{port}",
    ]
    
    success = False
    working_url = None
    
    for i, test_url in enumerate(test_urls, 1):
        masked_url = test_url.replace(redis_password, '***').replace(encoded_password, '***')
        logger.info(f"Testing format {i}: {masked_url}")
        
        try:
            redis_client = Redis.from_url(test_url, socket_connect_timeout=5)
            if redis_client.ping():
                logger.info(f"✅ Connection successful with format {i}")
                success = True
                working_url = test_url
                break
        except RedisError as e:
            logger.error(f"❌ Format {i} failed: {str(e)}")
    
    if success and working_url:
        logger.info("✅ Successfully authenticated to Redis!")
        
        # Update environment variables
        os.environ['REDIS_URL'] = working_url
        os.environ['REDIS_PASSWORD'] = redis_password
        
        # Update .env file if it exists
        env_file = '.env'
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                lines = f.readlines()
            
            redis_url_found = False
            redis_pwd_found = False
            
            with open(env_file, 'w') as f:
                for line in lines:
                    if line.startswith('REDIS_URL='):
                        masked_url = working_url.replace(redis_password, '***').replace(encoded_password, '***')
                        logger.info(f"Updating REDIS_URL in {env_file}: {masked_url}")
                        f.write(f'REDIS_URL={working_url}\n')
                        redis_url_found = True
                    elif line.startswith('REDIS_PASSWORD='):
                        logger.info(f"Updating REDIS_PASSWORD in {env_file}")
                        f.write(f'REDIS_PASSWORD={redis_password}\n')
                        redis_pwd_found = True
                    else:
                        f.write(line)
                
                if not redis_url_found:
                    masked_url = working_url.replace(redis_password, '***').replace(encoded_password, '***')
                    logger.info(f"Adding REDIS_URL to {env_file}: {masked_url}")
                    f.write(f'REDIS_URL={working_url}\n')
                
                if not redis_pwd_found:
                    logger.info(f"Adding REDIS_PASSWORD to {env_file}")
                    f.write(f'REDIS_PASSWORD={redis_password}\n')
        
        # Also update environment file for Replit
        replit_env = '.replit.env'
        if os.path.exists(replit_env):
            logger.info(f"Updating {replit_env} file")
            with open(replit_env, 'r') as f:
                lines = f.readlines()
            
            redis_url_found = False
            redis_pwd_found = False
            
            with open(replit_env, 'w') as f:
                for line in lines:
                    if line.startswith('REDIS_URL='):
                        masked_url = working_url.replace(redis_password, '***').replace(encoded_password, '***')
                        logger.info(f"Updating REDIS_URL in {replit_env}: {masked_url}")
                        f.write(f'REDIS_URL={working_url}\n')
                        redis_url_found = True
                    elif line.startswith('REDIS_PASSWORD='):
                        logger.info(f"Updating REDIS_PASSWORD in {replit_env}")
                        f.write(f'REDIS_PASSWORD={redis_password}\n')
                        redis_pwd_found = True
                    else:
                        f.write(line)
                
                if not redis_url_found:
                    masked_url = working_url.replace(redis_password, '***').replace(encoded_password, '***')
                    logger.info(f"Adding REDIS_URL to {replit_env}: {masked_url}")
                    f.write(f'REDIS_URL={working_url}\n')
                
                if not redis_pwd_found:
                    logger.info(f"Adding REDIS_PASSWORD to {replit_env}")
                    f.write(f'REDIS_PASSWORD={redis_password}\n')
        
        # Disable Redis fallback if it was enabled
        if os.environ.get('REDIS_DISABLED') == '1':
            logger.info("Clearing REDIS_DISABLED flag to enable Redis again")
            os.environ['REDIS_DISABLED'] = '0'
            
            # Update .env file if it exists
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    lines = f.readlines()
                
                with open(env_file, 'w') as f:
                    for line in lines:
                        if line.startswith('REDIS_DISABLED='):
                            f.write('REDIS_DISABLED=0\n')
                        else:
                            f.write(line)
        
        logger.info("✅ Redis authentication configuration completed successfully")
        return True
    else:
        logger.error("❌ All Redis connection attempts failed")
        logger.error("❌ Application will continue to use SimpleCache fallback")
        return False

if __name__ == "__main__":
    logger.info("=== PROLETTO REDIS AUTHENTICATION FIXER ===")
    success = test_redis_auth()
    sys.exit(0 if success else 1)