#!/usr/bin/env python3
"""
Environment Variable Fixer for Proletto Deployment

This script processes and normalizes environment variables to ensure they
match the expected patterns for Gunicorn and other services.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("env-fixer")

def fix_redis_url():
    """Fix REDIS_URL format if needed and ensure authentication is included.
    This function handles both scenarios where Redis requires authentication
    and where it doesn't require authentication.
    """
    # Set the known working Redis password for Proletto
    redis_password = "Pvaa4zVI1rFkrOmTSqH5bLUklovyXHfH"
    os.environ['REDIS_PASSWORD'] = redis_password
    logger.info("✅ Set the known working Redis password for Proletto")
    
    if 'REDIS_URL' in os.environ and os.environ['REDIS_URL']:
        redis_url = os.environ['REDIS_URL']
        
        # Check if URL needs prefix
        if not (redis_url.startswith('redis://') or 
                redis_url.startswith('rediss://') or 
                redis_url.startswith('unix://')):
            redis_url = f"redis://{redis_url}"
        
        # Insert the known working password into the URL
        scheme = redis_url.split('://', 1)[0] if '://' in redis_url else 'redis'
        rest = redis_url.split('://', 1)[1] if '://' in redis_url else redis_url
        
        # Handle if URL already has auth pattern
        if '@' in rest:
            host_part = rest.split('@', 1)[1]
            auth_redis_url = f"{scheme}://:{redis_password}@{host_part}"
        else:
            auth_redis_url = f"{scheme}://:{redis_password}@{rest}"
        
        redis_url = auth_redis_url
        logger.info("✅ Added Redis password to URL")
        
        # Now test the connection
        import redis
        try:
            # Quick ping test with the current URL
            logger.info("Testing Redis connection with current URL...")
            r = redis.from_url(redis_url)
            r.ping()
            logger.info("✅ Redis connection successful with current URL")
            
            # If we get here, the URL works as-is
            os.environ['REDIS_URL'] = redis_url
            # Mask any passwords in the URL for logging
            masked_url = redis_url
            if '@' in redis_url:
                scheme, rest = redis_url.split('://', 1)
                auth, host = rest.split('@', 1)
                masked_url = f"{scheme}://***@{host}"
            logger.info(f"Using Redis URL: {masked_url}")
            print(f"export REDIS_URL='{redis_url}'")
            
        except redis.exceptions.AuthenticationError:
            # Redis requires authentication but we don't have it in the URL or it's incorrect
            logger.warning("⚠️ Redis requires authentication")
            
            # If we already tried with REDIS_PASSWORD and it failed, it's the wrong password
            if os.environ.get('REDIS_PASSWORD') and ":{os.environ['REDIS_PASSWORD']}@" in redis_url:
                logger.error(f"❌ Redis authentication failed with provided password")
                logger.warning("⚠️ Application will use SimpleCache fallback")
                # Keep the URL so the application can handle the fallback properly
                print(f"export REDIS_URL='{redis_url}'")
            # Otherwise, try asking the user for the correct password if needed
            else:
                if os.environ.get('REDIS_PASSWORD'):
                    # Try with the current REDIS_PASSWORD
                    try:
                        # We don't need to modify the URL again if we already did it above
                        if ":{os.environ['REDIS_PASSWORD']}@" not in redis_url:
                            # Parse the redis URL to insert the password
                            scheme = redis_url.split('://', 1)[0] if '://' in redis_url else 'redis'
                            rest = redis_url.split('://', 1)[1] if '://' in redis_url else redis_url
                            
                            # Handle if URL already has auth pattern
                            if '@' in rest:
                                host_part = rest.split('@', 1)[1]
                                auth_redis_url = f"{scheme}://:{os.environ['REDIS_PASSWORD']}@{host_part}"
                            else:
                                auth_redis_url = f"{scheme}://:{os.environ['REDIS_PASSWORD']}@{rest}"
                            
                            redis_url = auth_redis_url
                        
                        # Test if this works
                        r = redis.from_url(redis_url)
                        r.ping()
                        
                        # Success with authentication
                        os.environ['REDIS_URL'] = redis_url
                        logger.info("✅ Redis connection successful with added authentication")
                        
                        # Mask the password in logs
                        masked_url = redis_url.replace(os.environ['REDIS_PASSWORD'], '***')
                        logger.info(f"Using authenticated Redis URL: {masked_url}")
                        print(f"export REDIS_URL='{redis_url}'")
                    except Exception as auth_err:
                        logger.error(f"❌ Redis authentication failed: {auth_err}")
                        logger.warning("⚠️ Application will use SimpleCache fallback")
                        print(f"export REDIS_URL='{redis_url}'")
                else:
                    logger.error("❌ Redis requires password but REDIS_PASSWORD is not set")
                    logger.warning("⚠️ Application will use SimpleCache fallback")
                    print(f"export REDIS_URL='{redis_url}'")
                
        except redis.exceptions.ConnectionError as conn_err:
            # Connection issue - this is common in dev environments
            logger.warning(f"⚠️ Redis connection error: {conn_err}")
            logger.warning("⚠️ Application will use SimpleCache fallback")
            os.environ['REDIS_URL'] = redis_url
            print(f"export REDIS_URL='{redis_url}'")
            
        except Exception as e:
            # Any other Redis error
            logger.warning(f"⚠️ Redis error: {e}")
            logger.warning("⚠️ Application will use SimpleCache fallback")
            os.environ['REDIS_URL'] = redis_url
            print(f"export REDIS_URL='{redis_url}'")
    else:
        logger.warning("⚠️ REDIS_URL not set")
        logger.warning("⚠️ Application will use SimpleCache fallback")
        
    # If we still don't have REDIS_PASSWORD but we have a URL, try to extract it
    if not os.environ.get('REDIS_PASSWORD') and os.environ.get('REDIS_URL') and '@' in os.environ['REDIS_URL']:
        try:
            # Try to extract password from redis URL if it has auth info
            url = os.environ['REDIS_URL']
            if '://:' in url and '@' in url:
                password = url.split('://:')[1].split('@')[0]
                if password:  # Only set if we actually got something
                    os.environ['REDIS_PASSWORD'] = password
                    logger.info("✅ Extracted REDIS_PASSWORD from REDIS_URL")
                    print(f"export REDIS_PASSWORD='{password}'")
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract REDIS_PASSWORD: {e}")

def fix_stripe_keys():
    """Fix Stripe API key formats."""
    for key in ['STRIPE_SECRET_KEY', 'STRIPE_PUBLIC_KEY', 'STRIPE_WEBHOOK_SECRET']:
        if key in os.environ and os.environ[key]:
            # Strip any whitespace
            os.environ[key] = os.environ[key].strip()
            logger.info(f"Normalized {key}")
            # Export it for shell environment
            print(f"export {key}='{os.environ[key]}'")
        else:
            logger.warning(f"{key} not set")

def set_prod_env():
    """Set production environment variables."""
    os.environ['FLASK_ENV'] = 'production'
    logger.info("Set FLASK_ENV=production")
    print("export FLASK_ENV='production'")
    
    os.environ['REPLIT_DEPLOYMENT'] = '1'
    logger.info("Set REPLIT_DEPLOYMENT=1")
    print("export REPLIT_DEPLOYMENT='1'")
    
    # Critical for Replit deployment: set PORT=5000 for correct port forwarding
    os.environ['PORT'] = '5000'
    logger.info("Set PORT=5000 (critical for Replit deployment forwarding to port 80)")
    print("export PORT='5000'")

def main():
    """Main function."""
    logger.info("Fixing environment variables for Proletto deployment...")
    
    # Print the shell script header
    print("#!/bin/bash")
    print("# Generated environment variables - source this file before starting the server")
    print("")
    
    fix_redis_url()
    fix_stripe_keys()
    set_prod_env()
    
    logger.info("Environment variable fixing complete")
    print("")
    print("echo 'Environment variables updated successfully'")

if __name__ == "__main__":
    main()