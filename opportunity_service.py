#!/usr/bin/env python3
"""
Opportunity Service - A robust service for fetching, caching, and storing opportunities
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from flask import Blueprint, jsonify, request, current_app
from flask_caching import Cache
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import desc, func, or_
from models import Opportunity, db

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache configuration
cache = Cache()

# Create blueprint for opportunity routes
opportunity_bp = Blueprint('opportunities', __name__, url_prefix='/opportunities')

# Constants
SNAPSHOT_FILE = os.environ.get('OPPORTUNITY_SNAPSHOT_FILE', 'data/opportunities_snapshot.json')
SNAPSHOT_MAX_AGE = int(os.environ.get('OPPORTUNITY_SNAPSHOT_MAX_AGE', 86400))  # 24 hours in seconds
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000

# Ensure the snapshot directory exists
os.makedirs(os.path.dirname(SNAPSHOT_FILE), exist_ok=True)

def init_app(app):
    """Initialize the opportunities module with the Flask app"""
    # Import our enhanced cache utilities
    from cache_utils import init_cache, make_key, get_cached_data, cache_circuit_breaker
    
    # Initialize the cache using our improved utilities
    global cache
    cache = init_cache(app)
    
    # Note: We no longer register the cache health endpoint here
    # as it's now handled globally by cache_utils.py
    
    # Log cache status
    try:
        if hasattr(app, '_cache_instance') and app._cache_instance:
            logger.info(f"Cache initialized for opportunities: {app._cache_instance.get('backend', 'unknown')}")
        else:
            logger.info("Cache initialized for opportunities: using default cache")
    except Exception as e:
        logger.warning(f"Unable to determine cache type: {str(e)}")
    
    # Register the blueprint
    app.register_blueprint(opportunity_bp)
    
    # Schedule periodic snapshot creation
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=lambda: create_snapshot_file(app),
            trigger=IntervalTrigger(hours=1),  # Create snapshot every hour
            id='create_opportunity_snapshot',
            name='Create opportunity snapshot file',
            replace_existing=True
        )
        scheduler.start()
        logger.info("Scheduled periodic opportunity snapshot creation")
    except ImportError:
        logger.warning("APScheduler not available - automatic snapshots disabled")

def get_db_opportunities(filters=None, limit=DEFAULT_LIMIT, offset=0, search=None):
    """Get opportunities from the database with optional filtering"""
    try:
        query = Opportunity.query
        
        # Apply filters
        if filters:
            if 'source' in filters:
                query = query.filter(Opportunity.source == filters['source'])
            if 'category' in filters:
                query = query.filter(Opportunity.category == filters['category'])
            if 'engine' in filters:
                query = query.filter(Opportunity.engine == filters['engine'])
            if 'location' in filters:
                query = query.filter(Opportunity.location == filters['location'])
            
            # Handle membership tier filtering
            if 'tier' in filters:
                tier = filters['tier']
                if tier == 'free':
                    # For free tier, only show free opportunities or social media type
                    query = query.filter(
                        or_(
                            Opportunity.membership_level == 'free',
                            Opportunity.type == 'social_media'
                        )
                    )
                elif tier == 'supporter':
                    # For supporter tier, show free opportunities, social media, and specific states
                    if 'states' in filters and filters['states']:
                        states = filters['states']
                        # Show free opportunities OR social media OR opportunities from selected states
                        query = query.filter(
                            or_(
                                Opportunity.membership_level == 'free',
                                Opportunity.type == 'social_media',
                                Opportunity.state.in_(states)
                            )
                        )
                    else:
                        # If no states selected, just show free-tier content and social media
                        query = query.filter(
                            or_(
                                Opportunity.membership_level == 'free',
                                Opportunity.type == 'social_media'
                            )
                        )
                # For premium tier, no additional filtering needed (they see everything)
        
        # Apply search if provided
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Opportunity.title.ilike(search_term),
                    Opportunity.description.ilike(search_term),
                    Opportunity.tags.ilike(search_term)
                )
            )
        
        # Get count for pagination
        total_count = query.count()
        
        # Apply sorting and pagination
        query = query.order_by(desc(Opportunity.scraped_at)).limit(min(limit, MAX_LIMIT)).offset(offset)
        
        # Execute query and convert to dictionaries
        results = [op.to_dict() for op in query.all()]
        
        return {
            'success': True,
            'count': len(results),
            'total': total_count,
            'opportunities': results
        }
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_db_opportunities: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in get_db_opportunities: {str(e)}")
        return None

def get_snapshot_opportunities(filters=None, limit=DEFAULT_LIMIT, offset=0, search=None):
    """Get opportunities from the snapshot file with optional filtering"""
    try:
        # Check if snapshot file exists
        if not os.path.exists(SNAPSHOT_FILE):
            logger.warning(f"Snapshot file not found: {SNAPSHOT_FILE}")
            return None
        
        # Check if snapshot file is too old
        file_age = time.time() - os.path.getmtime(SNAPSHOT_FILE)
        if file_age > SNAPSHOT_MAX_AGE:
            logger.warning(f"Snapshot file is too old ({file_age} seconds)")
        
        # Load opportunities from snapshot file
        with open(SNAPSHOT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, dict) or 'opportunities' not in data:
            logger.error("Invalid snapshot file format")
            return None
        
        opportunities = data['opportunities']
        
        # Apply filters
        if filters:
            filtered_opportunities = []
            
            # Handle membership tier filtering separately
            tier = filters.get('tier')
            states = filters.get('states', [])
            
            # Remove tier and states from filters to handle them specially
            special_filters = {'tier', 'states'}
            regular_filters = {k: v for k, v in filters.items() if k not in special_filters}
            
            for op in opportunities:
                include = True
                
                # Apply regular filters
                for key, value in regular_filters.items():
                    if key in op and op[key] != value:
                        include = False
                        break
                
                # Apply tier-based filtering
                if include and tier:
                    if tier == 'free':
                        # For free tier, only show free opportunities or social media type
                        include = op.get('membership_level') == 'free' or op.get('type') == 'social_media'
                    elif tier == 'supporter':
                        # For supporter tier, show free opportunities, social media, and specific states
                        if states:
                            include = (op.get('membership_level') == 'free' or 
                                      op.get('type') == 'social_media' or 
                                      op.get('state') in states)
                        else:
                            include = op.get('membership_level') == 'free' or op.get('type') == 'social_media'
                    # For premium tier, include all opportunities (no additional filtering)
                
                if include:
                    filtered_opportunities.append(op)
            
            opportunities = filtered_opportunities
        
        # Apply search if provided
        if search:
            search_term = search.lower()
            search_results = []
            for op in opportunities:
                if (search_term in op.get('title', '').lower() or
                    search_term in op.get('description', '').lower() or
                    search_term in op.get('tags', '')):
                    search_results.append(op)
            opportunities = search_results
        
        # Apply pagination
        paginated_opportunities = opportunities[offset:offset+limit]
        
        return {
            'success': True,
            'count': len(paginated_opportunities),
            'total': len(opportunities),
            'opportunities': paginated_opportunities,
            'from_snapshot': True,
            'snapshot_age': int(file_age)
        }
    except Exception as e:
        logger.error(f"Error reading snapshot file: {str(e)}")
        return None

def create_snapshot_file(app):
    """Create a snapshot file of all opportunities"""
    with app.app_context():
        try:
            # Get all opportunities from database
            opportunities = Opportunity.query.order_by(desc(Opportunity.scraped_at)).all()
            
            # Convert to dictionaries
            opportunity_dicts = [op.to_dict() for op in opportunities]
            
            # Create snapshot data
            snapshot_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'count': len(opportunity_dicts),
                'opportunities': opportunity_dicts
            }
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(SNAPSHOT_FILE), exist_ok=True)
            
            # Write to temporary file first to avoid corruption if interrupted
            temp_file = f"{SNAPSHOT_FILE}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(snapshot_data, f, indent=2)
            
            # Rename to final file (atomic operation)
            os.replace(temp_file, SNAPSHOT_FILE)
            
            logger.info(f"Created opportunity snapshot with {len(opportunity_dicts)} opportunities")
            return True
        except Exception as e:
            logger.error(f"Error creating snapshot file: {str(e)}")
            return False

@opportunity_bp.route('/', methods=['GET'])
@cache.cached(timeout=60, query_string=True)
def list_opportunities():
    """
    Get a list of opportunities with optional filtering and caching
    
    Query parameters:
    - limit: Maximum number of opportunities to return (default: 100)
    - offset: Offset for pagination (default: 0)
    - source: Filter by source
    - category: Filter by category
    - engine: Filter by engine
    - location: Filter by location
    - search: Search term for title, description, and tags
    - tier: Membership tier ('free', 'supporter', 'premium') for tier-based access control
    - state: State filter for supporter tier (can be repeated for multiple states)
    """
    try:
        # Parse query parameters
        limit = min(int(request.args.get('limit', DEFAULT_LIMIT)), MAX_LIMIT)
        offset = int(request.args.get('offset', 0))
        
        # Build filters dictionary
        filters = {}
        for param in ['source', 'category', 'engine', 'location']:
            if param in request.args:
                filters[param] = request.args.get(param)
                
        # Handle membership tier filtering
        tier = request.args.get('tier')
        if tier:
            filters['tier'] = tier
            
        # State-based filtering for supporter tier
        states = request.args.getlist('state')
        if states and len(states) > 0:
            filters['states'] = states
        
        # Get search term if provided
        search = request.args.get('search')
        
        # Primary source: Database
        result = get_db_opportunities(filters, limit, offset, search)
        
        # If database query failed, try snapshot file
        if result is None:
            logger.warning("Database query failed, falling back to snapshot file")
            result = get_snapshot_opportunities(filters, limit, offset, search)
            
            # If snapshot also failed, return error
            if result is None:
                logger.error("Both database and snapshot fallbacks failed")
                return jsonify({
                    'success': False,
                    'error': 'Unable to retrieve opportunities'
                }), 500
            
            # Add fallback indicator
            result['using_fallback'] = True
        
        # Add metadata
        result['generated_at'] = datetime.utcnow().isoformat()
        result['cache_ttl'] = 60  # seconds
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in list_opportunities: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@opportunity_bp.route('/create-snapshot', methods=['POST'])
def create_snapshot():
    """Manually create a snapshot file (admin only)"""
    try:
        # In a real app, add authentication/authorization check here
        if create_snapshot_file(current_app):
            return jsonify({
                'success': True,
                'message': 'Snapshot created successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create snapshot'
            }), 500
    except Exception as e:
        logger.error(f"Error in create_snapshot: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@opportunity_bp.route('/status', methods=['GET'])
def status():
    """Check the status of the opportunity service"""
    try:
        # Count opportunities in database
        db_count = Opportunity.query.count()
        
        # Check snapshot file
        snapshot_exists = os.path.exists(SNAPSHOT_FILE)
        snapshot_age = None
        snapshot_count = None
        
        if snapshot_exists:
            snapshot_age = time.time() - os.path.getmtime(SNAPSHOT_FILE)
            try:
                with open(SNAPSHOT_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    snapshot_count = data.get('count', len(data.get('opportunities', [])))
            except Exception as e:
                logger.error(f"Error reading snapshot file: {str(e)}")
        
        # Get cache stats if possible
        cache_stats = None
        if hasattr(cache, 'get_stats'):
            cache_stats = cache.get_stats()
        
        return jsonify({
            'success': True,
            'database': {
                'count': db_count,
                'healthy': db_count > 0
            },
            'snapshot': {
                'exists': snapshot_exists,
                'age_seconds': int(snapshot_age) if snapshot_age else None,
                'count': snapshot_count,
                'healthy': snapshot_exists and (snapshot_age or 0) < SNAPSHOT_MAX_AGE
            },
            'cache': {
                'type': current_app.config.get('CACHE_TYPE'),
                'stats': cache_stats
            }
        })
    except Exception as e:
        logger.error(f"Error in status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500