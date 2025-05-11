"""
Proletto Cache Utilities

This module provides cache-related utility functions for the Proletto platform.
It includes functions for managing cache and retrieving cache statistics.
"""

import logging
import json
import time
from functools import wraps
from flask import Blueprint, jsonify, current_app, g

# Initialize logger
logger = logging.getLogger(__name__)

# Create a blueprint for cache health endpoints
cache_health_bp = Blueprint('cache_health', __name__, url_prefix='/api/cache')

# Cache statistics
cache_stats = {
    'hits': 0,
    'misses': 0,
    'sets': 0,
    'get_calls': 0,
    'hit_rate': 0,
    'last_reset': time.time()
}

# Initialize global cache object that can be imported
cache = None


def init_cache(app, backend='redis'):
    """
    Initialize the cache for the application.
    
    Args:
        app: Flask application instance
        backend: Cache backend to use ('redis', 'memory', or 'none')
    
    Returns:
        Cache object
    """
    global cache
    
    try:
        if backend == 'redis':
            from redis import Redis
            import os
            
            # Get Redis URL from environment variable
            redis_url = os.environ.get('REDIS_URL')
            
            if not redis_url:
                logger.warning("REDIS_URL not found in environment variables, falling back to localhost")
                redis_url = "redis://localhost:6379/0"
            
            # Make sure the Redis URL has the correct scheme (redis://)
            if redis_url and not redis_url.startswith(('redis://', 'rediss://', 'unix://')):
                # Check if password is in environment variables
                redis_password = os.environ.get('REDIS_PASSWORD')
                
                # If we have host:port format without scheme
                if ':' in redis_url and '@' not in redis_url and redis_password:
                    # Host:port format, add password
                    redis_url = f"redis://:{redis_password}@{redis_url}"
                else:
                    # Just add the scheme
                    redis_url = f"redis://{redis_url}"
            
            logger.info(f"Attempting to connect to Redis with URL: {redis_url.replace(':', ':[REDACTED]@') if '@' in redis_url else redis_url}")
            
            # Create Redis client
            redis_client = Redis.from_url(redis_url, decode_responses=True)
            
            # Test connection
            redis_client.ping()
            
            logger.info("✅ Successfully connected to Redis cache")
            
            # Create cache object
            cache = {
                'backend': 'redis',
                'client': redis_client,
                'get': lambda key, default=None: json.loads(redis_client.get(key)) if redis_client.get(key) else default,
                'set': lambda key, value, timeout=None: redis_client.set(key, json.dumps(value), ex=timeout),
                'delete': lambda key: redis_client.delete(key),
                'clear': lambda: redis_client.flushdb(),
                'has': lambda key: redis_client.exists(key)
            }
            
        elif backend == 'memory':
            # In-memory cache implementation
            memory_store = {}
            
            cache = {
                'backend': 'memory',
                'store': memory_store,
                'get': lambda key, default=None: memory_store.get(key, default),
                'set': lambda key, value, timeout=None: memory_store.update({key: value}),
                'delete': lambda key: memory_store.pop(key, None),
                'clear': lambda: memory_store.clear(),
                'has': lambda key: key in memory_store
            }
            
            logger.info("✅ Using in-memory cache")
            
        else:
            # No-op cache for when caching is disabled
            cache = {
                'backend': 'none',
                'get': lambda key, default=None: default,
                'set': lambda key, value, timeout=None: None,
                'delete': lambda key: None,
                'clear': lambda: None,
                'has': lambda key: False
            }
            
            logger.info("ℹ️ Cache disabled")
        
        # Set app.cache_backend reference
        app.cache_backend = cache
        
        # Reset cache stats
        reset_cache_stats()
        
        return cache
    
    except Exception as e:
        logger.error(f"Failed to initialize cache: {str(e)}", exc_info=True)
        
        # Create a fallback in-memory cache when primary cache fails
        memory_store = {}
        
        cache = {
            'backend': 'memory_fallback',
            'store': memory_store,
            'get': lambda key, default=None: memory_store.get(key, default),
            'set': lambda key, value, timeout=None: memory_store.update({key: value}),
            'delete': lambda key: memory_store.pop(key, None),
            'clear': lambda: memory_store.clear(),
            'has': lambda key: key in memory_store
        }
        
        # Set app.cache_backend reference
        app.cache_backend = cache
        
        logger.warning("⚠️ Using fallback in-memory cache due to primary cache initialization failure")
        
        return cache


def cached(timeout=300):
    """
    Decorator to cache function results.
    
    Args:
        timeout: Cache timeout in seconds (default: 300)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not cache or cache['backend'] == 'none':
                return f(*args, **kwargs)
            
            # Create a unique cache key based on function name and arguments
            key_parts = [f.__module__, f.__name__]
            for arg in args:
                key_parts.append(str(arg))
            
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}:{v}")
            
            cache_key = "cached:" + ":".join(key_parts)
            
            # Update stats
            cache_stats['get_calls'] += 1
            
            # Try to get from cache
            cached_result = cache['get'](cache_key)
            
            if cached_result is not None:
                # Cache hit
                cache_stats['hits'] += 1
                cache_stats['hit_rate'] = cache_stats['hits'] / cache_stats['get_calls']
                return cached_result
            
            # Cache miss
            cache_stats['misses'] += 1
            cache_stats['hit_rate'] = cache_stats['hits'] / cache_stats['get_calls']
            
            # Call the function and cache the result
            result = f(*args, **kwargs)
            cache['set'](cache_key, result, timeout)
            cache_stats['sets'] += 1
            
            return result
        
        return decorated_function
    
    return decorator


def reset_cache_stats():
    """Reset cache statistics"""
    cache_stats['hits'] = 0
    cache_stats['misses'] = 0
    cache_stats['sets'] = 0
    cache_stats['get_calls'] = 0
    cache_stats['hit_rate'] = 0
    cache_stats['last_reset'] = time.time()


def get_cache_stats():
    """Get cache statistics"""
    return cache_stats


def get_cached_data(key, default=None):
    """Get data from cache
    
    Args:
        key: Cache key
        default: Default value if key not found
    
    Returns:
        Cached data or default value
    """
    if not cache:
        return default
    
    return cache['get'](key, default)


def flush_cache():
    """Flush the entire cache"""
    if cache:
        cache['clear']()
        reset_cache_stats()
        return True
    return False


def delete_cache_key(key):
    """Delete a specific key from the cache"""
    if cache:
        return cache['delete'](key)
    return False


def make_key(key_parts):
    """Create a cache key from key parts
    
    Args:
        key_parts: List of key parts to join
        
    Returns:
        String cache key
    """
    return "cache:" + ":".join(str(p) for p in key_parts if p is not None)


# Add cache health endpoints
@cache_health_bp.route('/stats', methods=['GET'])
def get_cache_stats_endpoint():
    """API endpoint to get cache statistics"""
    stats = get_cache_stats()
    backend_info = "unknown"
    
    if cache:
        backend_info = cache.get('backend', 'unknown')
    
    return jsonify({
        'success': True,
        'stats': stats,
        'backend': backend_info,
        'timestamp': time.time()
    })


@cache_health_bp.route('/flush', methods=['POST'])
def flush_cache_endpoint():
    """API endpoint to flush the cache"""
    success = flush_cache()
    return jsonify({
        'success': success,
        'message': 'Cache flushed successfully' if success else 'Failed to flush cache'
    })


def register_cache_extensions(app):
    """Register cache extensions with the Flask app
    
    Args:
        app: Flask application instance
    """
    try:
        # Register the cache health blueprint if not already registered
        try:
            app.register_blueprint(cache_health_bp)
            logger.info("Cache health endpoints registered successfully")
        except Exception as blueprint_error:
            logger.warning(f"Cache blueprint already registered: {str(blueprint_error)}")
        
        # Add cache instance to app
        app._cache_instance = cache
        
        return True
    except Exception as e:
        logger.error(f"Failed to register cache extensions: {str(e)}")
        return False


def cache_circuit_breaker(func):
    """Decorator that acts as a circuit breaker for cache functions
    
    If the cache operation fails, it logs the error and returns the default value.
    
    Args:
        func: Function to wrap with circuit breaker
    
    Returns:
        Wrapped function that catches exceptions
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Cache circuit breaker triggered: {str(e)}")
            # Return default value or fallback behavior
            if 'default' in kwargs:
                return kwargs['default']
            return None
    
    return wrapper