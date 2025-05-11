#!/usr/bin/env python3
"""
Redis Connection Tester with Multiple Format Options
Tests the Redis connection with various authentication formats
"""
import os
import redis
import sys

# Terminal colors for better readability
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
ENDC = '\033[0m'

def print_success(message):
    print(f"{GREEN}✅ {message}{ENDC}")

def print_error(message):
    print(f"{RED}❌ {message}{ENDC}")

def print_warning(message):
    print(f"{YELLOW}⚠️ {message}{ENDC}")

def print_info(message):
    print(f"{BLUE}ℹ️ {message}{ENDC}")

def test_redis_url(url, description):
    """Test a specific Redis URL format"""
    print_info(f"Testing {description}")
    # Mask password in output for security
    masked_url = url
    if '@' in url:
        parts = url.split('@')
        auth_part = parts[0]
        host_part = parts[1]
        if ':' in auth_part:
            protocol_and_user = auth_part.rsplit(':', 1)[0]
            masked_url = f"{protocol_and_user}:***@{host_part}"
        else:
            masked_url = f"{auth_part}:***@{host_part}"
    print(f"URL: {masked_url}")
    
    try:
        r = redis.from_url(url)
        r.ping()
        print_success("Connected successfully!")
        
        # Test operations
        try:
            r.set('proletto_test_key', 'Redis connection test from Proletto')
            print_success("Set test key")
            
            value = r.get('proletto_test_key')
            print_success(f"Retrieved test key: {value.decode('utf-8')}")
            
            r.delete('proletto_test_key')
            print_success("Deleted test key")
        except Exception as e:
            print_error(f"Operations failed: {str(e)}")
        
        return True
    except redis.exceptions.AuthenticationError as e:
        print_error(f"Authentication error: {str(e)}")
        return False
    except Exception as e:
        print_error(f"Connection error: {str(e)}")
        return False

def main():
    """Test Redis connection with various configurations"""
    print("\n===== Redis Connection Test =====\n")
    
    # Get original Redis values from environment
    redis_url = os.environ.get('REDIS_URL', '')
    redis_password = os.environ.get('REDIS_PASSWORD', '')
    
    if not redis_url:
        print_error("REDIS_URL is not set in environment variables")
        return False
    
    if not redis_password:
        print_warning("REDIS_PASSWORD is not set in environment variables")
    
    # Parse host and port from URL
    host_port = redis_url
    if '://' in redis_url:
        host_port = redis_url.split('://', 1)[1]
    if '@' in host_port:
        host_port = host_port.split('@', 1)[1]
    
    # Print hostname info (safe to show)
    print_info(f"Redis host information: {host_port}")
    
    # Test cases with different formats
    formats_to_try = []
    
    # Format 1: Original URL as-is
    formats_to_try.append((redis_url, "original REDIS_URL as-is"))
    
    # Format 2: Prefix with redis:// if needed
    if not (redis_url.startswith('redis://') or redis_url.startswith('rediss://')):
        formats_to_try.append((f"redis://{redis_url}", "REDIS_URL with redis:// prefix"))
    
    # Format 3: With password, no username (empty username with colon)
    if redis_password:
        if '://' in redis_url:
            protocol = redis_url.split('://', 1)[0] + '://'
            remaining = redis_url.split('://', 1)[1]
            if '@' in remaining:
                host_port = remaining.split('@', 1)[1]
            else:
                host_port = remaining
            formats_to_try.append((f"{protocol}:{redis_password}@{host_port}", "with password, no username"))
        else:
            formats_to_try.append((f"redis://:{redis_password}@{redis_url}", "with password, no username"))
    
    # Format 4: With default username and password
    if redis_password:
        if '://' in redis_url:
            protocol = redis_url.split('://', 1)[0] + '://'
            remaining = redis_url.split('://', 1)[1]
            if '@' in remaining:
                host_port = remaining.split('@', 1)[1]
            else:
                host_port = remaining
            formats_to_try.append((f"{protocol}default:{redis_password}@{host_port}", "with default username and password"))
        else:
            formats_to_try.append((f"redis://default:{redis_password}@{redis_url}", "with default username and password"))
            
    # Format 5: Redis Cloud specific format (just password, no username part)
    if redis_password:
        if '://' in redis_url:
            protocol = redis_url.split('://', 1)[0] + '://'
            remaining = redis_url.split('://', 1)[1]
            if '@' in remaining:
                host_port = remaining.split('@', 1)[1]
            else:
                host_port = remaining
            formats_to_try.append((f"{protocol}{redis_password}@{host_port}", "Redis Cloud format (password only)"))
        else:
            formats_to_try.append((f"redis://{redis_password}@{redis_url}", "Redis Cloud format (password only)"))
            
    # Format 6: Directly from environment variables, with password properly escaped
    import urllib.parse
    if redis_password:
        escaped_password = urllib.parse.quote_plus(redis_password)
        if '://' in redis_url:
            protocol = redis_url.split('://', 1)[0] + '://'
            remaining = redis_url.split('://', 1)[1]
            if '@' in remaining:
                host_port = remaining.split('@', 1)[1]
            else:
                host_port = remaining
            formats_to_try.append((f"{protocol}:{escaped_password}@{host_port}", "with escaped password"))
        else:
            formats_to_try.append((f"redis://:{escaped_password}@{redis_url}", "with escaped password"))
    
    # Test each format
    for url, description in formats_to_try:
        print("\n" + "-" * 50)
        if test_redis_url(url, description):
            print_info(f"✨ SUCCESS with format: {description}")
            return True
        print_warning(f"Failed with format: {description}")
    
    print("\n" + "-" * 50)
    print_error("All Redis connection formats failed")
    print_warning("The application will fall back to SimpleCache")
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)