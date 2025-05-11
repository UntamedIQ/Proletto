# File: feed_routes.py
from flask import Blueprint, jsonify, render_template, request, current_app
from flask_login import login_required, current_user
import random
import json
import os
from datetime import datetime

feed_bp = Blueprint('feed', __name__, url_prefix='/dashboard')

@feed_bp.before_request
@login_required
def require_login():
    # ensures everything in /dashboard/* needs auth
    pass

@feed_bp.route('/feed')
def feed_page():
    """Render the member-only feed page."""
    return render_template('member/feed.html')

def get_all_opportunities():
    """
    Retrieve all opportunities from the data files.
    This is a placeholder that will be replaced with proper database calls.
    """
    opportunities = []
    
    # Look for opportunity data files
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    if not os.path.exists(data_dir):
        data_dir = 'data'  # Try relative path as fallback
    
    try:
        # Try to load from opportunities.json if it exists
        opps_file = os.path.join(data_dir, 'opportunities.json')
        if os.path.exists(opps_file):
            with open(opps_file, 'r') as f:
                opportunities = json.load(f)
                
                # Make sure each opportunity has a scraped_at timestamp
                for opp in opportunities:
                    if 'scraped_at' not in opp:
                        opp['scraped_at'] = datetime.now().isoformat()
        
        # If no opportunities found, create some sample ones for testing
        if not opportunities:
            current_app.logger.warning("No opportunities found, using sample data")
            opportunities = get_sample_opportunities()
            
    except Exception as e:
        current_app.logger.error(f"Error loading opportunities: {str(e)}")
        opportunities = get_sample_opportunities()
    
    return opportunities

def get_sample_opportunities():
    """
    Generate sample opportunities for testing purposes.
    This will only be used if no real opportunity data is available.
    """
    now = datetime.now().isoformat()
    return [
        {
            "id": f"sample-{i}",
            "title": f"Sample Opportunity {i}",
            "description": "This is a sample opportunity description for testing purposes.",
            "url": "https://example.com/opportunity",
            "deadline": (datetime.now().replace(day=15 + i % 15)).isoformat(),
            "location": "New York, NY",
            "category": ["Grant", "Exhibition"][i % 2],
            "scraped_at": now,
            "source": "Sample Data"
        }
        for i in range(1, 31)
    ]

def get_personalized_opps(user_id, limit=5):
    """
    Get personalized opportunity recommendations for a user.
    This is a placeholder that will be replaced with actual recommendation logic.
    """
    all_opps = get_all_opportunities()
    
    # For now, just randomly select opportunities
    # In a real system, this would use the user's preferences and behavior
    if len(all_opps) <= limit:
        return all_opps
    
    # Use random.sample to get unique opportunities
    selected = random.sample(all_opps, limit)
    
    # Add a recommendation score for each opportunity
    for opp in selected:
        opp['recommendation_score'] = float(round(random.uniform(0.7, 0.99) * 100)) / 100
    
    return selected

@feed_bp.route('/api/feed')
def api_feed():
    """
    Return a paginated, algorithmically shuffled feed of opportunities.
    Query params: page (int), per_page (int)
    """
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    # 1) Fetch all live opportunities
    all_ops = get_all_opportunities()

    # 2) Score by recency + slight randomness
    scored = []
    for opp in all_ops:
        # Parse the timestamp or use current time if not available
        try:
            if isinstance(opp.get('scraped_at'), str):
                ts = datetime.fromisoformat(opp['scraped_at'].replace('Z', '+00:00')).timestamp()
            else:
                ts = float(opp.get('scraped_at', datetime.now().timestamp()))
        except (KeyError, ValueError):
            ts = datetime.now().timestamp()
            
        # Ensure we have a float score
        score = float(ts) + random.uniform(0, 3600)
        scored.append((score, opp))

    # 3) Sort descending and paginate
    scored.sort(key=lambda x: x[0], reverse=True)
    start = (page - 1) * per_page
    sliced = [opp for _, opp in scored[start : start + per_page]]
    return jsonify(sliced)

@feed_bp.route('/api/curation')
def api_curation():
    """
    Return top-5 personalized picks based on user feedback/profile.
    """
    recs = get_personalized_opps(user_id=current_user.id, limit=5)
    return jsonify(recs)

def init_app(app):
    """Initialize the feed blueprint with the app"""
    app.register_blueprint(feed_bp)
    app.logger.info("Feed blueprint registered successfully")