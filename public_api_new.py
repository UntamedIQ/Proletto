#!/usr/bin/env python3
"""
Proletto Public API v2

This module provides a public, versioned API for external access to Proletto data.
All endpoints are protected with API key authentication.
"""

import os
import json
import time
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, abort, current_app, make_response, g
from self_learning_bot import get_recommendations as get_bot_recommendations
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded
from alerts import alert_slack
from sqlalchemy import text
from flask_caching import Cache

# The cache object will be initialized when the Flask app is created
# This avoids circular imports
cache = None

# Simple metrics tracking - in a production environment, you would use a proper metrics system like Prometheus
class APIMetrics:
    def __init__(self):
        self.rate_limit_exceeded = {}  # Counter for rate limit events
        
    def increment_rate_limit(self, endpoint, plan):
        """Increment the counter for rate limit exceeded events"""
        key = f"{endpoint}:{plan}"
        self.rate_limit_exceeded[key] = self.rate_limit_exceeded.get(key, 0) + 1
        
        # Alert if threshold exceeded (5 within a short time)
        count = self.rate_limit_exceeded.get(key, 0)
        if count % 5 == 0:  # Alert every 5th occurrence
            alert_slack(
                f"Rate limit threshold exceeded for API endpoint '{endpoint}' with plan '{plan}'",
                level="warning",
                context={"count": count, "plan": plan}
            )
        
    def get_rate_limit_metrics(self):
        """Get all rate limit metrics"""
        return self.rate_limit_exceeded

# Initialize metrics
api_metrics = APIMetrics()

# Create the blueprint
public_api = Blueprint('public_api', __name__, url_prefix='/api/v2')

# Import the database-backed API key verification service
from api_key_db_service import verify_key, record_rate_limit_hit, engine

# Plan Rate Limits
PLAN_LIMITS = {
    "free": "30 per minute",
    "pro": "60 per minute", 
    "partner": "120 per minute",
    "admin": "240 per minute"  # Admin tier has much higher limits
}

# Custom key function for rate limiting
def get_api_key_or_ip():
    key = request.args.get('key') or request.headers.get('X-API-KEY')
    if key:
        return key
    return get_remote_address()

# Create a limiter with memory storage initially
# It will be properly initialized with the app later in api.py
limiter = Limiter(
    key_func=get_api_key_or_ip,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",  # Use memory storage by default
    strategy="fixed-window",  # Standard fixed-window strategy
    headers_enabled=True  # Include rate-limit info in response headers
)

# Dynamic rate limiting based on API key's plan
def limit_by_plan(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get plan from g object, which was set in require_api_key
        plan = getattr(g, 'api_plan', 'free')
        
        # Special case: admin plan has higher limits
        if plan == 'admin':
            limit = "240 per minute"  # Admin tier has much higher limits
        else:
            limit = PLAN_LIMITS.get(plan, PLAN_LIMITS['free'])
        
        # Apply the appropriate limit for this plan
        key = request.args.get('key') or request.headers.get('X-API-KEY')
        return limiter.shared_limit(limit, scope=key)(f)(*args, **kwargs)
    return decorated

# Standardized error response
def error_response(status_code, message):
    """Create a standardized error response format"""
    response = make_response(
        jsonify({
            "error": {
                "code": status_code,
                "message": message
            },
            "api_version": "v2",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }),
        status_code
    )
    return response

# Format ISO timestamp with UTC timezone
def iso_timestamp():
    """Return current timestamp in ISO 8601 format with UTC timezone"""
    return datetime.now(timezone.utc).isoformat()

# API key authentication decorator
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.args.get('key') or request.headers.get('X-API-KEY')
        if not key:
            return error_response(401, "API key is required. Provide it as a 'key' query parameter or 'X-API-KEY' header.")
        
        # Check if key is valid using our verification service
        valid, key_info = verify_key(key)
        
        if not valid:
            return error_response(401, "Invalid API key.")
        
        # Store the plan and other key info in the Flask g object for access in the view function
        g.api_plan = key_info.get('plan', 'free')
        g.api_key_info = key_info  # Store full key info for potential use in other decorators
        
        # Log API request (could be expanded later for analytics)
        if current_app.debug:
            current_app.logger.debug(f"API request with key plan: {g.api_plan}")
            
        return f(*args, **kwargs)
    return decorated

@public_api.route('/recommendations', methods=['GET'])
@require_api_key
@limit_by_plan
def recommendations():
    """
    Get personalized art opportunity recommendations for a user
    
    Authentication:
    - Requires API key via 'key' query parameter or 'X-API-KEY' header
    
    Query Parameters:
    - user_id: ID of the user to get recommendations for
    - limit: (optional) Maximum number of recommendations to return (default: 10, max: 50)
    - offset: (optional) Number of recommendations to skip for pagination (default: 0)
    
    Returns:
    JSON object with the following structure:
    {
        "api_version": "v2",
        "timestamp": "2025-05-06T21:49:25.123456Z", (ISO 8601 format with UTC timezone)
        "recommendations": [
            {
                "id": "123",
                "title": "Artist Residency Program",
                "url": "https://example.com/opportunity/123",
                "confidence": 0.92,
                "category": "residency",
                "deadline": "2025-06-15"
            },
            ...
        ],
        "user_id": 1,
        "count": 10,
        "pagination": {
            "limit": 10,
            "offset": 0,
            "next_offset": 10, (null if no more results)
            "has_more": true
        }
    }
    """
    user_id = request.args.get('user_id')
    if not user_id:
        return error_response(400, "Missing user_id parameter")
    
    try:
        user_id = int(user_id)
    except ValueError:
        return error_response(400, "user_id must be an integer")
    
    # Get limit parameter, default to 10
    try:
        limit = int(request.args.get('limit', 10))
        if limit < 1 or limit > 50:
            return error_response(400, "limit must be between 1 and 50")
    except ValueError:
        return error_response(400, "limit must be an integer")
        
    # Get offset parameter for pagination, default to 0
    try:
        offset = int(request.args.get('offset', 0))
        if offset < 0:
            return error_response(400, "offset must be a non-negative integer")
    except ValueError:
        return error_response(400, "offset must be an integer")
    
    # Get recommendations using global function to avoid circular imports
    recs = get_bot_recommendations(user_id, limit=limit)
    
    # Apply offset for pagination (slice the results after retrieving them)
    if offset > 0 and offset < len(recs):
        recs = recs[offset:]
    
    # Process recommendations to simplify for API output
    simplified_recs = []
    for rec in recs:
        simplified_recs.append({
            'id': rec.get('id'),
            'title': rec.get('title'),
            'url': rec.get('url'),
            'confidence': rec.get('confidence', 0.5),
            'category': rec.get('category', 'Unknown'),
            'deadline': rec.get('deadline')
        })
    
    # Pagination metadata
    total_count = len(simplified_recs)
    has_more = (total_count == limit)
    next_offset = offset + limit if has_more else None
    
    # Build the response with consistent format
    response = {
        'recommendations': simplified_recs,
        'user_id': user_id,
        'count': total_count,
        'api_version': 'v2',
        'timestamp': iso_timestamp(),
        'pagination': {
            'limit': limit,
            'offset': offset,
            'next_offset': next_offset,
            'has_more': has_more
        }
    }
    
    return jsonify(response)

@public_api.route('/health', methods=['GET'])
@require_api_key
@limit_by_plan
def health():
    """
    Get API health status
    
    Authentication:
    - Requires API key via 'key' query parameter or 'X-API-KEY' header
    
    Returns:
    JSON object with the following structure:
    {
        "status": "ok",
        "api_version": "v2",
        "timestamp": "2025-05-06T21:49:25.123456Z", (ISO 8601 format with UTC timezone)
        "server_time": "2025-05-06 21:49:25 UTC"
    }
    
    Possible Status Values:
    - "ok": API is functioning normally
    - "degraded": API is operational but some features may be slow or unavailable
    - "maintenance": API is undergoing scheduled maintenance
    """
    return jsonify({
        'status': 'ok',
        'api_version': 'v2',
        'timestamp': iso_timestamp(),
        'server_time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    })

@public_api.route('/stats', methods=['GET'])
@require_api_key
@limit_by_plan
def stats():
    """
    Get high-level API usage statistics
    
    Authentication:
    - Requires API key via 'key' query parameter or 'X-API-KEY' header
    
    Returns:
    JSON object with the following structure:
    {
        "api_version": "v2",
        "timestamp": "2025-05-06T21:49:25.123456Z", (ISO 8601 format with UTC timezone)
        "stats": {
            "user_count": 3,
            "premium_users": 2,
            "opportunity_count": 2254,
            "scheduler_status": "running",
            "environments": {
                "web": true,
                "api": true,
                "scheduler": true,
                "database": true
            }
        }
    }
    
    Scheduler Status Values:
    - "running": Scheduler is actively running and processing jobs
    - "paused": Scheduler is running but jobs are paused
    - "stopped": Scheduler is not running
    - "not_initialized": Scheduler has not been initialized yet
    - "unknown": Scheduler status cannot be determined
    """
    # Get basic stats using db session from current app context
    # Import within function to avoid circular imports
    from flask import current_app
    with current_app.app_context():
        from models import User, db
        user_count = db.session.query(User).count()
        premium_count = db.session.query(User).filter(User.membership_level == 'premium').count()
    
    from ap_scheduler import get_scheduler_info
    scheduler_status = get_scheduler_info().get('status', 'unknown')
    
    # Get opportunity count
    try:
        import json
        with open('opportunities.json', 'r') as f:
            opportunities = json.load(f)
            opportunity_count = len(opportunities)
    except Exception:
        opportunity_count = 0
    
    return jsonify({
        'api_version': 'v2',
        'timestamp': iso_timestamp(),
        'stats': {
            'user_count': user_count,
            'premium_users': premium_count,
            'opportunity_count': opportunity_count,
            'scheduler_status': scheduler_status,
            'environments': {
                'web': True,
                'api': True,
                'scheduler': scheduler_status != 'not_initialized',
                'database': True
            }
        }
    })

# Custom error handler for rate limit exceeded
@public_api.errorhandler(429)
def ratelimit_handler(e):
    # Get the plan from the g object if available (set in require_api_key)
    # This is more reliable than looking up the plan again
    plan = getattr(g, 'api_plan', None)
    
    key = request.args.get('key') or request.headers.get('X-API-KEY')
    
    # If plan not in g, fall back to verification lookup
    if plan is None and key:
        valid, key_info = verify_key(key)
        if valid:
            plan = key_info.get('plan', 'free')
        else:
            plan = 'free'  # Default to free if verification fails
    elif plan is None:
        plan = 'free'  # Default to free if no key
    
    # Calculate retry_after time
    retry_after = getattr(e, 'retry_after', None)
    
    # If we don't have a retry_after value but have a reset_at timestamp
    if retry_after is None and hasattr(e, 'reset_at'):
        retry_after = int(e.reset_at.timestamp() - time.time())
    
    # Log the rate limit exceeded event
    current_app.logger.warning(f"Rate limit exceeded for API key with plan '{plan}' on endpoint '{request.endpoint}'")
    
    # Track the rate limit event in our metrics
    api_metrics.increment_rate_limit(request.endpoint, plan)
    
    # Record this rate limit hit in the database for the key
    if key:
        record_rate_limit_hit(key)
    
    # Provide a more helpful response
    response = jsonify({
        "error": {
            "code": 429,
            "message": "Rate limit exceeded. Please wait and retry.",
            "retry_after": retry_after,
            "current_plan": plan,
            "docs": "https://myproletto.replit.app/api/docs/",
            "upgrade_info": "https://www.myproletto.com/api-plans" if plan == 'free' else None
        },
        "api_version": "v2",
        "timestamp": iso_timestamp()
    })
    
    # Set standard Retry-After header
    if retry_after is not None:
        response.headers['Retry-After'] = str(retry_after)
    
    return response, 429

# Test endpoint for rate limiting
@public_api.route('/test-rate-limit', methods=['GET'])
@require_api_key
@limit_by_plan
def test_rate_limit():
    """
    Simple test endpoint for rate limiting
    
    Authentication:
    - Requires API key via 'key' query parameter or 'X-API-KEY' header
    
    Returns:
    JSON object with the following structure:
    {
        "api_version": "v2",
        "timestamp": "2025-05-06T21:49:25.123456Z", (ISO 8601 format with UTC timezone)
        "message": "Rate limit test successful",
        "plan": "free|pro|partner|admin", (current plan based on API key)
        "limit": "30 per minute|60 per minute|120 per minute|240 per minute" (current limit based on plan)
    }
    """
    plan = getattr(g, 'api_plan', 'free')
    
    if plan == 'admin':
        limit = "240 per minute"
    else:
        limit = PLAN_LIMITS.get(plan, PLAN_LIMITS['free'])
    
    return jsonify({
        'api_version': 'v2',
        'timestamp': iso_timestamp(),
        'message': 'Rate limit test successful',
        'plan': plan,
        'limit': limit
    })

# New endpoint to expose rate limit metrics (admin only)
@public_api.route('/admin/rate-limit-metrics', methods=['GET'])
@require_api_key
def rate_limit_metrics():
    """
    Get rate limit metrics for monitoring
    
    Authentication:
    - Requires API key via 'key' query parameter or 'X-API-KEY' header
    - Only available to admin users
    
    Returns:
    JSON object with the following structure:
    {
        "api_version": "v2",
        "timestamp": "2025-05-06T21:49:25.123456Z", (ISO 8601 format with UTC timezone)
        "metrics": {
            "rate_limit_exceeded": {
                "endpoint:plan": count,
                ...
            }
        }
    }
    """
    # Check if user has admin plan from the g object (set in require_api_key)
    plan = getattr(g, 'api_plan', None)
    
    if plan != 'admin':
        return error_response(403, "Admin access required")
    
    # Get database metrics too
    db_metrics = {}
    try:
        with engine.connect() as conn:
            # Get top rate limited keys
            top_rate_limited = conn.execute(text("""
                SELECT key_prefix, plan, rate_limit_hits, name 
                FROM "api_key" 
                WHERE rate_limit_hits > 0 
                ORDER BY rate_limit_hits DESC 
                LIMIT 10
            """)).fetchall()
            
            if top_rate_limited:
                db_metrics['top_rate_limited_keys'] = [
                    {
                        'key_prefix': row['key_prefix'],
                        'plan': row['plan'],
                        'rate_limit_hits': row['rate_limit_hits'],
                        'name': row['name']
                    } for row in top_rate_limited
                ]
                
            # Get hits by plan
            hits_by_plan = conn.execute(text("""
                SELECT plan, SUM(rate_limit_hits) as total_hits 
                FROM "api_key" 
                GROUP BY plan
                ORDER BY total_hits DESC
            """)).fetchall()
            
            if hits_by_plan:
                db_metrics['rate_limit_hits_by_plan'] = {
                    row['plan']: row['total_hits'] for row in hits_by_plan
                }
                
    except Exception as e:
        current_app.logger.error(f"Error getting database metrics: {e}")
        db_metrics = {'error': str(e)}
    
    return jsonify({
        'api_version': 'v2',
        'timestamp': iso_timestamp(),
        'metrics': {
            'rate_limit_exceeded': api_metrics.get_rate_limit_metrics(),
            'database': db_metrics
        }
    })