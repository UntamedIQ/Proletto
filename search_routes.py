"""
Proletto Search Routes

This module provides search functionality for the Proletto platform,
including both the search results page and API endpoints for searching
opportunities.
"""

import logging
from flask import Blueprint, request, jsonify, render_template, current_app, g
from flask_login import login_required, current_user
from sqlalchemy import or_, and_
from models import Opportunity, db

# Initialize logger
logger = logging.getLogger(__name__)

# Create blueprint
search_bp = Blueprint('search', __name__)


@search_bp.route('/search')
def search_page():
    """
    Render the search results page with search bar.
    
    This page provides a UI for users to search for opportunities and filter
    the results based on various criteria such as medium, location, and deadline.
    """
    # Get search query and filters from URL parameters
    query = request.args.get('q', '')
    medium = request.args.get('medium', '')
    location = request.args.get('location', '')
    
    # Get available filter options for dropdowns
    filter_options = get_filter_options()
    
    return render_template(
        'public/search.html',
        query=query,
        medium=medium,
        location=location,
        filter_options=filter_options
    )


@search_bp.route('/api/search')
def api_search():
    """
    Backend endpoint to search opportunities.
    
    Query params:
        q (string): Search query
        medium (string): Art medium filter
        location (string): Location filter
        deadline_start (string): Earliest deadline (ISO format)
        deadline_end (string): Latest deadline (ISO format)
        page (int): Page number for pagination (default: 1)
        per_page (int): Items per page (default: 20)
    
    Returns:
        JSON object with results array and total count
    """
    try:
        # Get search parameters
        q = request.args.get('q', '')
        medium = request.args.get('medium')
        location = request.args.get('location')
        deadline_start = request.args.get('deadline_start')
        deadline_end = request.args.get('deadline_end')
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)  # Limit max per_page
        
        # Prepare search filters
        filters = {
            'query': q,
            'medium': medium,
            'location': location,
            'deadline_start': deadline_start,
            'deadline_end': deadline_end,
            'page': page,
            'per_page': per_page
        }
        
        # Execute search
        results, total = search_opportunities(**filters)
        
        # Return results as JSON
        return jsonify({
            'success': True,
            'results': results,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })
    
    except Exception as e:
        logger.error(f"Error in search API: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f"Error during search: {str(e)}"
        }), 500


@search_bp.route('/api/search/suggestions')
def api_search_suggestions():
    """
    API endpoint for search auto-suggestions as user types.
    
    Query params:
        q (string): Partial search query
        limit (int): Maximum number of suggestions to return
    
    Returns:
        JSON array of suggestion objects with title and type properties
    """
    try:
        # Get partial query
        q = request.args.get('q', '')
        limit = min(int(request.args.get('limit', 5)), 10)  # Limit max suggestions
        
        # Return empty array for empty queries
        if not q or len(q) < 2:
            return jsonify([])
        
        # Get suggestions
        suggestions = get_search_suggestions(q, limit)
        
        return jsonify(suggestions)
    
    except Exception as e:
        logger.error(f"Error in search suggestions API: {str(e)}", exc_info=True)
        return jsonify([])


def search_opportunities(query='', medium=None, location=None, deadline_start=None, 
                        deadline_end=None, page=1, per_page=20):
    """
    Search for opportunities based on query and filters.
    
    Args:
        query (str): Search text
        medium (str): Art medium filter
        location (str): Location filter
        deadline_start (str): Earliest deadline (ISO format)
        deadline_end (str): Latest deadline (ISO format)
        page (int): Page number
        per_page (int): Items per page
    
    Returns:
        tuple: (list of opportunity dicts, total count)
    """
    try:
        # Start with a base query for active opportunities
        search_query = Opportunity.query.filter(Opportunity.active == True)
        
        # Add text search condition if query is not empty
        if query:
            # Create a search condition for relevant text fields
            search_condition = or_(
                Opportunity.title.ilike(f'%{query}%'),
                Opportunity.description.ilike(f'%{query}%'),
                Opportunity.organization.ilike(f'%{query}%'),
                Opportunity.location.ilike(f'%{query}%'),
                Opportunity.type.ilike(f'%{query}%'),
                Opportunity.categories.ilike(f'%{query}%')
            )
            search_query = search_query.filter(search_condition)
        
        # Add medium filter if specified
        if medium:
            search_query = search_query.filter(Opportunity.categories.ilike(f'%{medium}%'))
        
        # Add location filter if specified
        if location:
            search_query = search_query.filter(Opportunity.location.ilike(f'%{location}%'))
        
        # Add deadline range filters if specified
        deadline_conditions = []
        if deadline_start:
            deadline_conditions.append(Opportunity.deadline >= deadline_start)
        if deadline_end:
            deadline_conditions.append(Opportunity.deadline <= deadline_end)
        
        if deadline_conditions:
            search_query = search_query.filter(and_(*deadline_conditions))
        
        # Get total count before pagination
        total = search_query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        search_query = search_query.order_by(Opportunity.deadline.asc())
        search_query = search_query.offset(offset).limit(per_page)
        
        # Execute query
        opportunities = search_query.all()
        
        # Convert to dictionary list for JSON response
        results = [opp.to_dict() for opp in opportunities]
        
        return results, total
        
    except Exception as e:
        logger.error(f"Error searching opportunities: {str(e)}", exc_info=True)
        # Fallback to cached opportunities if database query fails
        return search_opportunities_from_cache(query, medium, location, deadline_start, 
                                             deadline_end, page, per_page)


def search_opportunities_from_cache(query='', medium=None, location=None, deadline_start=None, 
                                  deadline_end=None, page=1, per_page=20):
    """
    Fallback search from cached opportunities when database is unavailable.
    
    Uses the same parameters as search_opportunities.
    """
    try:
        import json
        import os
        from datetime import datetime
        
        # Try to load cached opportunities
        cache_path = os.path.join(current_app.root_path, 'data', 'opportunities_snapshot.json')
        
        if not os.path.exists(cache_path):
            logger.error("Cache file not found")
            return [], 0
        
        with open(cache_path, 'r') as f:
            opportunities = json.load(f)
        
        # Filter opportunities
        filtered_opps = opportunities
        
        # Text search across multiple fields
        if query:
            query = query.lower()
            filtered_opps = [
                opp for opp in filtered_opps if
                query in opp.get('title', '').lower() or 
                query in opp.get('description', '').lower() or
                query in opp.get('organization', '').lower() or
                query in opp.get('location', '').lower() or
                query in opp.get('type', '').lower() or
                any(query in cat.lower() for cat in opp.get('categories', []))
            ]
        
        # Medium filter
        if medium:
            medium = medium.lower()
            filtered_opps = [
                opp for opp in filtered_opps if
                any(medium in cat.lower() for cat in opp.get('categories', []))
            ]
        
        # Location filter
        if location:
            location = location.lower()
            filtered_opps = [
                opp for opp in filtered_opps if
                location in opp.get('location', '').lower()
            ]
        
        # Deadline filters
        if deadline_start or deadline_end:
            deadline_filtered = []
            
            for opp in filtered_opps:
                deadline_str = opp.get('deadline')
                
                # Skip items with no deadline
                if not deadline_str:
                    continue
                
                try:
                    deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
                    
                    if deadline_start:
                        start_date = datetime.fromisoformat(deadline_start.replace('Z', '+00:00'))
                        if deadline < start_date:
                            continue
                    
                    if deadline_end:
                        end_date = datetime.fromisoformat(deadline_end.replace('Z', '+00:00'))
                        if deadline > end_date:
                            continue
                    
                    deadline_filtered.append(opp)
                except ValueError:
                    # Skip items with invalid date format
                    continue
            
            filtered_opps = deadline_filtered
        
        # Get total before pagination
        total = len(filtered_opps)
        
        # Sort by deadline
        filtered_opps.sort(key=lambda x: x.get('deadline', '9999-12-31'))
        
        # Apply pagination
        offset = (page - 1) * per_page
        paginated_opps = filtered_opps[offset:offset + per_page]
        
        return paginated_opps, total
        
    except Exception as e:
        logger.error(f"Error in cache fallback search: {str(e)}", exc_info=True)
        return [], 0


def get_search_suggestions(query, limit=5):
    """
    Get search suggestions based on a partial query.
    
    Args:
        query (str): Partial search query
        limit (int): Maximum number of suggestions
    
    Returns:
        list: List of suggestion objects with title and type properties
    """
    try:
        # Search for matching opportunities
        suggestions = []
        
        # Title suggestions
        title_results = Opportunity.query.filter(
            Opportunity.active == True,
            Opportunity.title.ilike(f'%{query}%')
        ).order_by(Opportunity.deadline.asc()).limit(limit).all()
        
        for opp in title_results:
            suggestions.append({
                'id': opp.id,
                'title': opp.title,
                'type': 'opportunity',
                'url': f'/opportunity/{opp.id}'
            })
        
        # Organization suggestions
        if len(suggestions) < limit:
            remaining = limit - len(suggestions)
            org_results = Opportunity.query.filter(
                Opportunity.active == True,
                Opportunity.organization.ilike(f'%{query}%')
            ).order_by(Opportunity.deadline.asc()).limit(remaining).all()
            
            for opp in org_results:
                # Check for duplicates
                if not any(s['id'] == opp.id for s in suggestions):
                    suggestions.append({
                        'id': opp.id,
                        'title': opp.organization,
                        'subtitle': opp.title,
                        'type': 'organization',
                        'url': f'/opportunity/{opp.id}'
                    })
        
        # Location suggestions
        if len(suggestions) < limit:
            remaining = limit - len(suggestions)
            loc_results = Opportunity.query.filter(
                Opportunity.active == True,
                Opportunity.location.ilike(f'%{query}%')
            ).order_by(Opportunity.deadline.asc()).limit(remaining).all()
            
            for opp in loc_results:
                # Check for duplicates
                if not any(s['id'] == opp.id for s in suggestions):
                    suggestions.append({
                        'id': opp.id,
                        'title': opp.location,
                        'subtitle': opp.title,
                        'type': 'location',
                        'url': f'/opportunity/{opp.id}'
                    })
        
        return suggestions
    
    except Exception as e:
        logger.error(f"Error getting search suggestions: {str(e)}", exc_info=True)
        return []


def get_filter_options():
    """
    Get available filter options for the search form dropdowns.
    
    Returns:
        dict: Dictionary with available options for each filter
    """
    try:
        # Get distinct art mediums/categories
        medium_options = set()
        opportunities = Opportunity.query.filter(Opportunity.active == True).all()
        
        for opp in opportunities:
            if opp.categories:
                categories = opp.categories.split(',')
                for category in categories:
                    if category.strip():
                        medium_options.add(category.strip())
        
        # Get distinct locations
        location_options = Opportunity.query.filter(
            Opportunity.active == True,
            Opportunity.location.isnot(None)
        ).with_entities(Opportunity.location).distinct().all()
        
        location_options = sorted([loc[0] for loc in location_options if loc[0]])
        
        return {
            'mediums': sorted(list(medium_options)),
            'locations': location_options
        }
    
    except Exception as e:
        logger.error(f"Error getting filter options: {str(e)}", exc_info=True)
        # Fallback to basic options
        return {
            'mediums': ['Painting', 'Sculpture', 'Photography', 'Digital', 'Mixed Media', 'Installation'],
            'locations': ['New York', 'Los Angeles', 'Chicago', 'London', 'Berlin', 'Paris']
        }


def init_app(app):
    """Initialize the search blueprint with the app"""
    app.register_blueprint(search_bp)
    logger.info("Search blueprint registered successfully")