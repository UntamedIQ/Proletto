"""
Proletto Dashboard Routes
This module provides the dashboard functionality for the Proletto platform.
"""

import os
import json
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app
from flask_login import current_user, login_required
from models import db, User, Opportunity
from werkzeug.utils import secure_filename
# Import opportunity service functions
try:
    from opportunity_service import get_db_opportunities
except ImportError:
    # Fallback for when the opportunity service is not available
    def get_db_opportunities(limit=10, offset=0, filters=None, search=None, **kwargs):
        """Fallback function to get opportunities from the database"""
        try:
            query = Opportunity.query.order_by(Opportunity.scraped_at.desc())
            
            # Apply filtering if needed
            if filters:
                # Add filtering logic here based on filter parameters
                pass
                
            # Apply search if needed
            if search:
                search_term = search.lower()
                query = query.filter(
                    Opportunity.title.ilike(f'%{search_term}%') | 
                    Opportunity.description.ilike(f'%{search_term}%')
                )
                
            # Apply pagination
            opportunities = query.offset(offset).limit(limit).all()
            
            # Convert to dictionaries
            opportunity_dicts = []
            for op in opportunities:
                # Use the to_dict method if available, otherwise create a dict manually
                if hasattr(op, 'to_dict'):
                    opportunity_dicts.append(op.to_dict())
                else:
                    # Create a simplified dict with basic attributes
                    opportunity_dicts.append({
                        'id': op.id,
                        'title': op.title,
                        'description': op.description,
                        'source': getattr(op, 'source', 'Unknown'),
                        'deadline': str(op.deadline) if hasattr(op, 'deadline') and op.deadline else None,
                        'category': getattr(op, 'category', None),
                        'tags': getattr(op, 'tags', None),
                        'location': getattr(op, 'location', None),
                        'membership_level': getattr(op, 'membership_level', 'free'),
                        'engine': getattr(op, 'engine', None),
                        'apply_url': getattr(op, 'apply_url', None),
                        'image_url': getattr(op, 'image_url', None),
                    })
            
            return {'opportunities': opportunity_dicts}
        except Exception as e:
            logging.error(f"Error getting opportunities: {str(e)}")
            return None

# Set up logging
logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def dashboard():
    """Dashboard home page"""
    return redirect(url_for('index'))  # Redirects to main dashboard for now

@dashboard_bp.route('/opportunities')
@login_required
def dashboard_opportunities():
    """User opportunities dashboard page"""
    # Get tab parameter (if any)
    tab = request.args.get('tab', 'all')
    
    # Fetch general opportunities
    opportunities_result = get_db_opportunities(limit=10)
    opportunities = opportunities_result.get('opportunities', []) if opportunities_result else []
    
    # Get user's saved opportunities
    saved_opportunities = []
    if hasattr(current_user, 'saved_opportunities'):
        saved_opportunities = current_user.saved_opportunities
    
    # Get recommended opportunities (for now, just use regular opportunities)
    # In the future, we can implement a more sophisticated recommendation algorithm
    recommended_result = get_db_opportunities(limit=5)
    recommended_opportunities = recommended_result.get('opportunities', []) if recommended_result else []
    
    return render_template(
        'dashboard/opportunities.html',
        active_page='opportunities',
        tab=tab,
        opportunities=opportunities,
        saved_opportunities=saved_opportunities,
        recommended_opportunities=recommended_opportunities
    )

@dashboard_bp.route('/opportunities/save', methods=['POST'])
@login_required
def save_opportunity():
    """Save an opportunity to user's saved list"""
    data = request.json or {}
    opportunity_id = data.get('opportunity_id')
    
    if not opportunity_id:
        return jsonify({"success": False, "error": "Missing opportunity ID"}), 400
    
    # Find opportunity by ID in the database
    opportunity = Opportunity.query.get(opportunity_id)
    if not opportunity:
        return jsonify({"success": False, "error": "Opportunity not found"}), 404
    
    # Check if user model has saved_opportunities relationship
    if not hasattr(current_user, 'saved_opportunities'):
        return jsonify({"success": False, "error": "Saved opportunities not supported"}), 501
    
    # Add opportunity to user's saved list if not already saved
    if opportunity not in current_user.saved_opportunities:
        current_user.saved_opportunities.append(opportunity)
        db.session.commit()
        return jsonify({"success": True, "message": "Opportunity saved successfully"})
    
    return jsonify({"success": True, "message": "Opportunity already saved"})

@dashboard_bp.route('/opportunities/unsave', methods=['POST'])
@login_required
def unsave_opportunity():
    """Remove an opportunity from user's saved list"""
    data = request.json or {}
    opportunity_id = data.get('opportunity_id')
    
    if not opportunity_id:
        return jsonify({"success": False, "error": "Missing opportunity ID"}), 400
    
    # Find opportunity by ID in the database
    opportunity = Opportunity.query.get(opportunity_id)
    if not opportunity:
        return jsonify({"success": False, "error": "Opportunity not found"}), 404
    
    # Check if user model has saved_opportunities relationship
    if not hasattr(current_user, 'saved_opportunities'):
        return jsonify({"success": False, "error": "Saved opportunities not supported"}), 501
    
    # Remove opportunity from user's saved list
    if opportunity in current_user.saved_opportunities:
        current_user.saved_opportunities.remove(opportunity)
        db.session.commit()
        return jsonify({"success": True, "message": "Opportunity removed from saved list"})
    
    return jsonify({"success": True, "message": "Opportunity not in saved list"})

@dashboard_bp.route('/opportunities/view/<int:opportunity_id>')
@login_required
def view_opportunity(opportunity_id):
    """View a specific opportunity"""
    # Find opportunity by ID in the database
    opportunity = Opportunity.query.get(opportunity_id)
    if not opportunity:
        return render_template('errors/404.html'), 404
    
    # Check if opportunity is saved by user
    is_saved = False
    if hasattr(current_user, 'saved_opportunities'):
        is_saved = opportunity in current_user.saved_opportunities
    
    return render_template(
        'dashboard/opportunity_detail.html',
        active_page='opportunities',
        opportunity=opportunity,
        is_saved=is_saved
    )

def init_app(app):
    """Initialize the dashboard blueprint"""
    app.register_blueprint(dashboard_bp)
    logger.info("Dashboard blueprint registered successfully")