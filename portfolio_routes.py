"""
Proletto Portfolio Optimizer API Routes
This module provides the API endpoints for the portfolio optimizer feature
"""
import logging
import json
from flask import jsonify, request, Blueprint
from flask_jwt_extended import jwt_required, get_jwt_identity

from portfolio_optimizer import PortfolioOptimizer
from ai_helper import track_user_activity

# Configure logging
logger = logging.getLogger('portfolio_api')

# Create a Blueprint for portfolio routes
portfolio_bp = Blueprint('portfolio', __name__, url_prefix='/api/portfolio')

def get_main_app():
    """Get the main Flask app for database operations"""
    from main import app as main_app
    return main_app

# Define the register_portfolio_alt_routes function for additional routes
def register_portfolio_alt_routes(app):
    """
    Register alternative portfolio routes directly on the app.
    This allows for both /api/portfolio/... and /portfolio/... access patterns.
    
    Args:
        app: The Flask application to register routes on
    """
    @app.route('/portfolio/alt', methods=['GET'])
    def alt_portfolio_view():
        """Test endpoint for the alt portfolio routes"""
        return jsonify({"status": "Alternate portfolio endpoint works!"})
        
    # Mirror the main portfolio routes but at /portfolio/* instead of /api/portfolio/*
    @app.route('/portfolio/analyze', methods=['POST'])
    @jwt_required()
    def alt_analyze_portfolio():
        """Alternative route to analyze_portfolio"""
        return analyze_portfolio()
        
    @app.route('/portfolio/optimize', methods=['POST'])
    @jwt_required() 
    def alt_optimize_portfolio():
        """Alternative route to optimize_portfolio"""
        return optimize_portfolio()

@portfolio_bp.route('/analyze', methods=['POST'])
@jwt_required()
def analyze_portfolio():
    """
    Analyze an artist's portfolio using AI and provide feedback
    """
    try:
        # Get user identity from token
        user_id = get_jwt_identity()
        
        # Convert to int if necessary
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid user ID format in JWT token: {user_id}")
            return jsonify({
                'success': False,
                'error': 'Invalid user ID format in token'
            }), 400
        
        # Check membership level in database
        main_app = get_main_app()
        with main_app.app_context():
            from models import User
            user = User.query.get(user_id)
            
            if not user:
                logger.error(f"User not found for ID: {user_id}")
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
            
            # Check if feature is available for user's membership level
            if user.membership_level not in ['supporter', 'premium']:
                logger.warning(f"User {user_id} with {user.membership_level} membership attempted to use portfolio optimizer")
                return jsonify({
                    'success': False,
                    'error': 'This feature requires Supporter or Premium membership',
                    'upgrade_needed': True
                }), 403
            
            # Get portfolio data from request
            data = request.json
            if not data or not isinstance(data, dict):
                return jsonify({
                    'success': False,
                    'error': 'Invalid portfolio data'
                }), 400
            
            # Initialize the portfolio optimizer
            optimizer = PortfolioOptimizer()
            
            # Track activity for this user - portfolio analysis counts as engagement
            with main_app.app_context():
                try:
                    track_user_activity(user, "portfolio_analysis", {"portfolio_size": len(data.get("portfolio_items", []))})
                except Exception as activity_error:
                    logger.error(f"Error tracking user activity: {activity_error}")
            
            # Call the analyzer
            analysis_result = optimizer.analyze_portfolio(data)
            
            # Return the analysis
            return jsonify(analysis_result)
                
    except Exception as e:
        logger.error(f"Error analyzing portfolio: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@portfolio_bp.route('/optimize', methods=['POST'])
@jwt_required()
def optimize_portfolio():
    """
    Generate an optimization plan for an artist's portfolio
    """
    try:
        # Get user identity from token
        user_id = get_jwt_identity()
        
        # Convert to int if necessary
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid user ID format in JWT token: {user_id}")
            return jsonify({
                'success': False,
                'error': 'Invalid user ID format in token'
            }), 400
        
        # Check membership level in database
        main_app = get_main_app()
        with main_app.app_context():
            from models import User
            user = User.query.get(user_id)
            
            if not user:
                logger.error(f"User not found for ID: {user_id}")
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
            
            # Check if feature is available for user's membership level
            if user.membership_level not in ['supporter', 'premium']:
                logger.warning(f"User {user_id} with {user.membership_level} membership attempted to use portfolio optimizer")
                return jsonify({
                    'success': False,
                    'error': 'This feature requires Supporter or Premium membership',
                    'upgrade_needed': True
                }), 403
            
            # Get data from request
            data = request.json
            if not data or not isinstance(data, dict):
                return jsonify({
                    'success': False,
                    'error': 'Invalid optimization request data'
                }), 400
            
            portfolio_data = data.get('portfolio_data')
            analysis_result = data.get('analysis_result')
            
            if not portfolio_data:
                return jsonify({
                    'success': False,
                    'error': 'Portfolio data is required'
                }), 400
            
            # Initialize the portfolio optimizer
            optimizer = PortfolioOptimizer()
            
            # Determine optimization goals
            optimization_goals = None
            if 'optimization_goals' in portfolio_data and portfolio_data['optimization_goals']:
                optimization_goals = portfolio_data['optimization_goals']
            
            # Track activity for this user - portfolio optimization is a premium action
            with main_app.app_context():
                try:
                    track_user_activity(user, "portfolio_optimization", {"has_goals": optimization_goals is not None})
                except Exception as activity_error:
                    logger.error(f"Error tracking user activity: {activity_error}")
            
            # Call the optimizer
            optimization_result = optimizer.optimize_portfolio(portfolio_data, optimization_goals)
            
            # Process opportunity matches if available
            opportunity_matches = None
            if 'target_opportunities' in portfolio_data and portfolio_data['target_opportunities']:
                opportunity_matches = optimizer.match_opportunities(
                    portfolio_data,
                    portfolio_data['target_opportunities']
                )
            
            # Construct response
            response = {
                'success': optimization_result['success']
            }
            
            if optimization_result['success']:
                response['optimization_plan'] = optimization_result['optimization_plan']
                if opportunity_matches:
                    response['opportunity_matches'] = opportunity_matches
            else:
                response['error'] = optimization_result.get('error', 'Optimization failed')
            
            return jsonify(response)
                
    except Exception as e:
        logger.error(f"Error optimizing portfolio: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500