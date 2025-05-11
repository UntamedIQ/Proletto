#!/usr/bin/env python3
"""
Redis Connection Tester
Tests the REDIS_URL from environment variables with proper formatting
"""
import os
import redis
import sys

def test_redis_connection():
    """Test the Redis connection with various configurations"""
    print("\n=== Redis Connection Test ===")
    
    # Get original REDIS_URL
    original_redis_url = os.environ.get('REDIS_URL')
    print(f"Original REDIS_URL: {'<set but masked>' if original_redis_url else 'not set'}")
    
    if not original_redis_url:
        print("❌ REDIS_URL is not set. Cannot test connection.")
        return False
    
    # Add prefix if needed
    redis_url = original_redis_url
    if not (redis_url.startswith('redis://') or redis_url.startswith('rediss://')):
        redis_url = 'redis://' + redis_url
        print(f"Added 'redis://' prefix to REDIS_URL")
    
    # Test connection with modified URL
    print(f"Testing connection with URL: {'<masked for security>' if '@' in redis_url else redis_url}")
    try:
        r = redis.from_url(redis_url)
        r.ping()
        print("✅ Redis connection successful!")
        
        # Store a test key
        r.set('test_key', 'This is a test value from Proletto')
        print("✅ Successfully stored a test key")
        
        # Retrieve the test key
        test_value = r.get('test_key')
        print(f"✅ Retrieved test key: {test_value.decode('utf-8')}")
        
        # Clean up the test key
        r.delete('test_key')
        print("✅ Deleted test key")
        
        return True
    except redis.exceptions.AuthenticationError:
        print("❌ Authentication error: Redis requires a password")
        
        # If URL doesn't have auth but should
        if '@' not in redis_url:
            print("ℹ️ REDIS_URL doesn't contain authentication credentials")
            redis_password = os.environ.get('REDIS_PASSWORD')
            
            if redis_password:
                # Insert auth into URL
                if redis_url.startswith('rediss://'):
                    auth_redis_url = redis_url.replace('rediss://', f"rediss://:{redis_password}@")
                else:
                    auth_redis_url = redis_url.replace('redis://', f"redis://:{redis_password}@")
                
                print("🔑 Trying again with REDIS_PASSWORD")
                try:
                    r = redis.from_url(auth_redis_url)
                    r.ping()
                    print("✅ Redis connection successful with REDIS_PASSWORD!")
                    return True
                except Exception as e:
                    print(f"❌ Still failed with authentication: {str(e)}")
            else:
                print("❌ REDIS_PASSWORD environment variable is not set")
        
        print("⚠️ The application will fall back to SimpleCache")
        return False
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")
        print("⚠️ The application will fall back to SimpleCache")
        return False

if __name__ == "__main__":
    success = test_redis_connection()
    sys.exit(0 if success else 1)