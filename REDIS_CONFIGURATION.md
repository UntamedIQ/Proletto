# Redis Configuration for Proletto

This document explains how Redis caching is configured and used within the Proletto application, including fallback mechanisms and troubleshooting strategies.

## Overview

Proletto uses Redis as a distributed cache to improve performance, but is designed to gracefully degrade to an in-memory SimpleCache when Redis is unavailable. This provides flexibility and resilience in different deployment environments.

## Redis Configuration

### Environment Variables

The following environment variables control Redis functionality:

- `REDIS_URL`: The connection URL for the Redis server (e.g., `redis://redis-14544.c253.us-central1-1.gce.redns.redis-cloud.com:14544`)
- `REDIS_PASSWORD`: The password for Redis authentication
- `REDIS_DISABLED`: Set to `1` to completely disable Redis and always use SimpleCache

### Connection URL Formats

Redis connection URLs should follow this format:
```
redis://:password@hostname:port
```

Note the colon before the password - this indicates an empty username, which is common for Redis Cloud and many other Redis providers.

For SSL/TLS connections, use:
```
rediss://:password@hostname:port
```

### Connection Pooling

Proletto uses Redis connection pooling with the following configuration:

- Max connections: 10
- Socket connect timeout: 5 seconds
- Socket timeout: 5 seconds
- Socket keepalive: Enabled
- Health check interval: 30 seconds

This configuration balances reliability with performance.

## Fallback Mechanism

Proletto implements a multi-level fallback strategy:

1. First, it tries connecting to Redis using the provided credentials
2. If that fails, it attempts multiple retry attempts with slight delays
3. If all retries fail, it falls back to SimpleCache

The fallback is transparent to the application and happens in these components:
- `cache_utils.py`: Main cache initialization
- `opportunity_service.py`: Opportunity-specific caching
- `api.py`: API-specific caching

## Circuit Breaker Pattern

Proletto implements a circuit breaker pattern for Redis operations to prevent cascading failures:

- After multiple consecutive Redis failures, the circuit "trips" and all cache operations temporarily use SimpleCache
- After a cooldown period, the circuit attempts to "reset" by trying Redis again
- If Redis is working again, normal operation resumes
- If Redis is still failing, the circuit stays open

This pattern improves application resilience during Redis outages or performance degradation.

## Cache Health Endpoints

Proletto provides cache health endpoints at consistent URL paths:

- Main web app: `/cache-utils/health`
- Admin dashboard: `/admin/cache-utils/health`
- API backend: `/api/cache-utils/health`

These endpoints return detailed information about:

- Current cache backend (Redis or SimpleCache)
- Redis performance metrics (when using Redis)
- Redis hit/miss ratio (when using Redis)
- Circuit breaker status
- Error information (when in fallback mode)

## Performance Considerations

- Redis provides better performance than SimpleCache under high load
- Redis enables cache sharing across multiple application instances
- SimpleCache provides adequate performance for development and low-traffic deployments
- Cache keys use namespacing to avoid collisions across different application components

## Troubleshooting

### Testing Redis Connection

Use the `fix_redis_url.py` script to test different Redis connection formats:

```bash
python fix_redis_url.py --test-only
```

Or use the more comprehensive `fix_redis_connection.py` script that handles special characters in passwords:

```bash
python fix_redis_connection.py
```

These scripts will try multiple connection formats and provide detailed error information.

### Current Redis Status

As of the latest update (May 2025), Redis connection has been fixed using the correct authentication credentials:

- **Redis URL**: `redis://BrandonZarif:Pvaa4zVI1rFkrOmTSqH5bLUklovyXHfH@redis-14544.c253.us-central1-1.gce.redns.redis-cloud.com:14544`
- **Redis Password**: `Pvaa4zVI1rFkrOmTSqH5bLUklovyXHfH`

These credentials have been hardcoded into the application for reliable operation. The fallback to SimpleCache remains available as a safety net should Redis experience any issues, ensuring uninterrupted operation.

### Common Redis Issues

1. **Authentication failures**: Verify that the REDIS_PASSWORD is correct and properly formatted in the URL
   - Special characters in passwords (like `&`) need URL encoding
   - Redis Cloud may require specific authentication formats

2. **Connection timeouts**: Check network connectivity and firewall rules
   - Replit's environment may have restricted access to certain Redis hosts
   - Ensure Redis Cloud allows connections from Replit's IP ranges

3. **Redis URL format**: Ensure the URL follows the correct format
   - Most reliable format: `redis://:password@hostname:port` 
   - For SSL: `rediss://:password@hostname:port`

4. **SSL/TLS issues**: If experiencing SSL errors
   - Some Redis providers require SSL/TLS connections
   - SSL connections may require additional configuration

5. **Redis server issues**: Check Redis server health and available memory

### Monitoring Redis Usage

Monitor Redis usage through:

1. The cache health endpoints
2. Redis CLI commands (INFO, MONITOR)
3. Application logs for Redis-related warnings or errors

## Conclusion

Redis caching in Proletto is designed to be:

1. **Optional**: The application works with or without Redis
2. **Resilient**: Automatic fallback to SimpleCache when needed
3. **Self-healing**: Circuit breaker pattern for graceful recovery
4. **Transparent**: Application code doesn't need to handle cache type differences
5. **Monitorable**: Health endpoints provide visibility into cache performance