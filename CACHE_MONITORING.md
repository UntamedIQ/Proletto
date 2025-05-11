# Cache Monitoring in Proletto

This document explains the cache monitoring features implemented in Proletto to help track and diagnose cache performance.

## Cache Health Endpoints

Proletto provides three consistent cache health endpoints across different layers of the application:

1. **Main Web Application**: `/cache-utils/health`
2. **Admin Dashboard**: `/admin/cache-utils/health`
3. **API Backend**: `/api/cache-utils/health`

All endpoints return the same data structure with cache status information for their respective application components.

## Response Format

The cache health endpoints return a JSON object with the following structure:

### Redis Connected Response

```json
{
  "backend": "redis",
  "status": "connected",
  "uptime_in_seconds": 86400,
  "used_memory_human": "1.2M",
  "keyspace_hits": 10000,
  "keyspace_misses": 500,
  "connected_clients": 3,
  "hit_rate": 95.24,
  "circuit_breaker": {
    "status": "closed",
    "failures": 0,
    "max_failures": 3,
    "reset_timeout": 120
  }
}
```

### Redis Error Response

```json
{
  "backend": "redis",
  "status": "error",
  "error": "Connection refused"
}
```

### SimpleCache Fallback Response

```json
{
  "backend": "simple",
  "status": "fallback",
  "message": "Using in-memory SimpleCache as fallback",
  "error": "Redis authentication failed"
}
```

### Redis Disabled Response

```json
{
  "backend": "simple",
  "status": "fallback",
  "message": "Using in-memory SimpleCache as fallback",
  "error": "Redis explicitly disabled"
}
```

## Monitoring Redis Performance

The cache health endpoints provide key metrics for monitoring Redis performance:

- **Hit Rate**: The percentage of cache requests that resulted in a hit. Higher is better, typically above 80% indicates good cache efficiency.
- **Memory Usage**: Shows how much memory Redis is using. Monitor this to ensure Redis isn't approaching its memory limit.
- **Connected Clients**: The number of active connections to Redis. Too many connections can degrade performance.
- **Circuit Breaker Status**: Shows if the circuit breaker is open or closed and the current failure count.

## Interpreting Results

- **High Hit Rate (>90%)**: Cache is working efficiently; most requests are being served from cache.
- **Low Hit Rate (<50%)**: Cache may be underutilized; consider adjusting cache TTLs or caching additional data.
- **Frequent Circuit Breaker Trips**: Redis may be experiencing intermittent issues; check Redis server health.
- **High Memory Usage**: Redis may need more memory or cache pruning strategies.

## Cross-Layer Monitoring

The consistent URL structure allows for easy integration with monitoring tools:

1. **Monitoring Endpoints**:
   - Main App: `https://app.myproletto.com/cache-utils/health`
   - Admin: `https://app.myproletto.com/admin/cache-utils/health`
   - API: `https://api.myproletto.com/api/cache-utils/health`

2. **Dashboard Integration**:
   Monitor all three endpoints together to detect discrepancies between application layers.

3. **Alert Configuration**:
   - Critical: Any endpoint reports "status": "error"
   - Warning: Hit rate drops below 70%
   - Warning: Circuit breaker status changes to "open"

## Accessing the Endpoints

### Via Web Browser

Simply visit the endpoint URLs in your browser:

- Main App: `/cache-utils/health`
- Admin: `/admin/cache-utils/health`
- API: `/api/cache-utils/health`

### Via Command Line

```bash
# Main app endpoint
curl https://app.myproletto.com/cache-utils/health

# Admin endpoint
curl https://app.myproletto.com/admin/cache-utils/health

# API endpoint
curl https://api.myproletto.com/api/cache-utils/health
```

### Via Admin Dashboard

The admin dashboard integrates these endpoints and presents the information in a more user-friendly format.

## Troubleshooting

If any of the cache health endpoints show errors or indicate SimpleCache fallback:

1. **Check Redis Connection**:
   - Verify Redis is running
   - Check authentication credentials
   - Ensure network connectivity

2. **Verify Cache Configuration**:
   - Check that environment variables are set correctly
   - Ensure Redis URL format is correct

3. **Monitor Circuit Breaker**:
   - If the circuit breaker is frequently tripping, investigate Redis stability
   - Consider increasing the `max_failures` threshold if occurrences are minor

4. **Compare Layer Results**:
   - If one layer shows errors while others don't, check layer-specific Redis configuration

## Conclusion

The cache health monitoring system provides transparency into cache performance across all layers of Proletto. By regularly checking these endpoints, developers and operations teams can:

1. Detect cache issues early
2. Monitor cache efficiency
3. Troubleshoot Redis connection problems
4. Verify that Redis authentication is working properly
5. Understand when the system falls back to SimpleCache