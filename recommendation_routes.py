#!/usr/bin/env python3
"""
Recommendation Routes for Proletto

This module provides the API endpoints for the recommendation system, including:
1. Getting personalized recommendations for a user
2. Submitting feedback on recommended opportunities 
3. Retraining the recommendation model

These endpoints work with the Self-Learning Bot to provide continuously improving
art opportunity recommendations to users.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("recommendation_routes")

# Create a recommendation blueprint
recommendation_bp = Blueprint('recommendation', __name__, url_prefix='/api/recommendations')

# Import recommendation functions
try:
    from self_learning_bot import get_recommendations, retrain_recommender
except ImportError as e:
    logger.error(f"Error importing recommendation functions: {e}")
    # Define fallback functions in case import fails
    def get_recommendations(user_id, limit=10):
        logger.error("Recommendation module not available, using fallback")
        return []
    
    def retrain_recommender():
        logger.error("Recommendation module not available, using fallback")
        return False


@recommendation_bp.route('/user/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_recommendations(user_id: int):
    """
    Get personalized recommendations for a user
    
    Args:
        user_id: ID of the user to get recommendations for
    
    Returns:
        JSON response with recommendations or error
    """
    try:
        # Verify JWT identity matches the requested user ID
        # or the user is an admin
        current_user_id = get_jwt_identity()
        
        with current_app.app_context():
            from models import User
            current_user = User.query.get(current_user_id)
            
            # Only allow access to the user's own recommendations or admin access
            if int(current_user_id) != user_id and current_user.role != 'admin':
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized access'
                }), 403
        
        # Get recommendations from the bot
        limit = request.args.get('limit', default=10, type=int)
        recommendations = get_recommendations(user_id=user_id, limit=limit)
        
        # Return recommendations
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'count': len(recommendations),
            'limit': limit,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get recommendations: {str(e)}'
        }), 500


@recommendation_bp.route('/feedback', methods=['POST'])
@jwt_required()
def submit_feedback():
    """
    Submit feedback on a recommendation
    
    Request body:
    {
        "opportunity_id": 123,
        "rating": 4,
        "comment": "This opportunity was great!"
    }
    
    Returns:
        JSON response with success or error
    """
    try:
        # Get current user from JWT
        current_user_id = get_jwt_identity()
        
        # Get request data
        request_data = request.json
        if not request_data:
            return jsonify({
                'success': False,
                'error': 'No feedback data provided'
            }), 400
        
        # Extract feedback data
        opportunity_id = request_data.get('opportunity_id')
        rating = request_data.get('rating')
        comment = request_data.get('comment', '')
        
        # Validate data
        if opportunity_id is None:
            return jsonify({
                'success': False,
                'error': 'opportunity_id is required'
            }), 400
            
        if rating is None or not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({
                'success': False,
                'error': 'rating must be an integer between 1 and 5'
            }), 400
        
        # Create feedback record
        with current_app.app_context():
            from models import db, Opportunity, Feedback
            
            # Check if opportunity exists
            opportunity = Opportunity.query.get(opportunity_id)
            if not opportunity:
                return jsonify({
                    'success': False,
                    'error': f'Opportunity with ID {opportunity_id} not found'
                }), 404
            
            # Check if user has already provided feedback for this opportunity
            existing_feedback = Feedback.query.filter_by(
                user_id=current_user_id,
                opportunity_id=opportunity_id
            ).first()
            
            if existing_feedback:
                # Update existing feedback
                existing_feedback.rating = rating
                existing_feedback.comment = comment
                db.session.commit()
                
                feedback_id = existing_feedback.id
                logger.info(f"Updated feedback {feedback_id} for opportunity {opportunity_id} by user {current_user_id}")
            else:
                # Create new feedback
                feedback = Feedback(
                    user_id=current_user_id,
                    opportunity_id=opportunity_id,
                    rating=rating,
                    comment=comment
                )
                
                db.session.add(feedback)
                db.session.commit()
                
                feedback_id = feedback.id
                logger.info(f"Created feedback {feedback_id} for opportunity {opportunity_id} by user {current_user_id}")
        
        # Return success response
        return jsonify({
            'success': True,
            'feedback_id': feedback_id,
            'message': 'Feedback submitted successfully'
        })
    
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to submit feedback: {str(e)}'
        }), 500


@recommendation_bp.route('/retrain', methods=['POST'])
@jwt_required()
def retrain_model():
    """
    Retrain the recommendation model with latest data
    Only accessible to admin users
    
    Returns:
        JSON response with success or error
    """
    try:
        # Get current user from JWT
        current_user_id = get_jwt_identity()
        
        # Check if user is admin
        with current_app.app_context():
            from models import User
            current_user = User.query.get(current_user_id)
            
            if not current_user or current_user.role != 'admin':
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized access'
                }), 403
        
        # Retrain the model
        success = retrain_recommender()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Recommendation model retrained successfully',
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to retrain recommendation model'
            }), 500
    
    except Exception as e:
        logger.error(f"Error retraining model: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to retrain model: {str(e)}'
        }), 500


@recommendation_bp.route('/opportunities', methods=['GET'])
@jwt_required()
def get_opportunities():
    """
    Get all opportunities
    
    Returns:
        JSON response with opportunities or error
    """
    try:
        # Get query parameters
        limit = request.args.get('limit', default=100, type=int)
        offset = request.args.get('offset', default=0, type=int)
        source = request.args.get('source')
        location = request.args.get('location')
        category = request.args.get('category')
        
        # Query opportunities
        with current_app.app_context():
            from models import Opportunity
            
            # Build query
            query = Opportunity.query
            
            # Apply filters
            if source:
                query = query.filter(Opportunity.source == source)
            if location:
                query = query.filter(Opportunity.location == location)
            if category:
                query = query.filter(Opportunity.category == category)
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination
            opportunities = query.order_by(Opportunity.created_at.desc()).offset(offset).limit(limit).all()
            
            # Convert to dictionaries
            opportunities_dict = [opp.to_dict() for opp in opportunities]
            
            # Return opportunities
            return jsonify({
                'success': True,
                'opportunities': opportunities_dict,
                'count': len(opportunities_dict),
                'total': total_count,
                'offset': offset,
                'limit': limit
            })
    
    except Exception as e:
        logger.error(f"Error getting opportunities: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get opportunities: {str(e)}'
        }), 500


@recommendation_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_recommendation_stats():
    """
    Get recommendation system statistics
    Only accessible to admin users
    
    Returns:
        JSON response with statistics or error
    """
    try:
        # Get current user from JWT
        current_user_id = get_jwt_identity()
        
        # Check if user is admin
        with current_app.app_context():
            from models import User, Opportunity, Feedback
            current_user = User.query.get(current_user_id)
            
            if not current_user or current_user.role != 'admin':
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized access'
                }), 403
            
            # Get stats
            opportunity_count = Opportunity.query.count()
            feedback_count = Feedback.query.count()
            user_with_feedback_count = Feedback.query.with_entities(Feedback.user_id).distinct().count()
            
            # Calculate average rating
            avg_rating = db.session.query(db.func.avg(Feedback.rating)).scalar() or 0
            
            # Get most recent feedback
            recent_feedback = Feedback.query.order_by(Feedback.created_at.desc()).limit(5).all()
            recent_feedback_dict = []
            
            for fb in recent_feedback:
                user = User.query.get(fb.user_id)
                opportunity = Opportunity.query.get(fb.opportunity_id)
                
                recent_feedback_dict.append({
                    'id': fb.id,
                    'user': user.email if user else 'Unknown',
                    'opportunity': opportunity.title if opportunity else 'Unknown',
                    'rating': fb.rating,
                    'comment': fb.comment,
                    'created_at': fb.created_at.isoformat()
                })
            
            # Return stats
            return jsonify({
                'success': True,
                'stats': {
                    'opportunity_count': opportunity_count,
                    'feedback_count': feedback_count,
                    'user_with_feedback_count': user_with_feedback_count,
                    'avg_rating': round(float(avg_rating), 2),
                    'recent_feedback': recent_feedback_dict
                },
                'timestamp': datetime.utcnow().isoformat()
            })
    
    except Exception as e:
        logger.error(f"Error getting recommendation stats: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get recommendation stats: {str(e)}'
        }), 500