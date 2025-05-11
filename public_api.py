#!/usr/bin/env python3
"""
Proletto Public API v2

This module provides a public, versioned API for external access to Proletto data.
All endpoints are protected with API key authentication.

IMPORTANT: This module defines all routes before any app.register_blueprint calls.
Flask blueprints cannot have routes added after registration.
"""

import os
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, abort, current_app, make_response
from self_learning_bot import get_recommendations as get_bot_recommendations
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

public_api = Blueprint('public_api', __name__, url_prefix='/api/v2')

# Use API key for limit tracking if available, otherwise fall back to IP
def get_api_key_or_ip():
    key = request.args.get('key') or request.headers.get('X-API-KEY')
    if key:
        return key
    return get_remote_address()

# Initialize the limiter with memory storage
# Create it at module level so rate limits can be declared before blueprint registration
limiter = Limiter(
    key_func=get_api_key_or_ip,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",  # Use memory storage for simplicity
    strategy="fixed-window",  # fixed-window strategy is more efficient with Redis
    headers_enabled=True  # Include rate-limit info in response headers
)

@public_api.record_once
def setup_limiter(state):
    """
    Initialize the rate limiter when the blueprint is registered with the app
    """
    global limiter
    
    # Configure the limiter with the Flask app
    limiter.init_app(state.app)
    
    # Register error handler for rate limit exceeded
    from flask_limiter.errors import RateLimitExceeded
    
    @state.app.errorhandler(RateLimitExceeded)
    def handle_rate_limit_error(e):
        return jsonify({
            "error": {
                "code": 429,
                "message": "Rate limit exceeded. Please try again later.",
                "retry_after": getattr(e, 'retry_after', None)
            },
            "api_version": "v2",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 429
    
    try:
        state.app.logger.info("API rate limiter initialized successfully")
    except:
        print("API rate limiter initialized successfully")

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

# Simple API key check decorator with rate limiting
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.args.get('key') or request.headers.get('X-API-KEY')
        if not key:
            return error_response(401, "API key is required. Provide it as a 'key' query parameter or 'X-API-KEY' header.")
        if key != os.getenv('API_KEY'):
            return error_response(401, "Invalid API key.")
        return f(*args, **kwargs)
    return decorated

@public_api.route('/recommendations', methods=['GET'])
@limiter.limit("30 per minute")
@require_api_key
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
@limiter.limit("60 per minute")
@require_api_key
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
@limiter.limit("30 per minute")
@require_api_key
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

# Required function for integration with main.py
def init_app(app):
    """
    Initialize the public API v2 blueprint with the Flask app
    
    Args:
        app: Flask application instance
    """
    try:
        # Register the blueprint with the app
        app.register_blueprint(public_api)
        app.logger.info("Public API v2 blueprint registered successfully")
        return True
    except Exception as e:
        app.logger.error(f"Failed to register Public API v2 blueprint: {str(e)}")
        return False