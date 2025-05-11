#!/usr/bin/env python3
"""
Proletto API Backend
Serves the scraped opportunities data and provides API endpoints
"""
import os
import json
import logging
import time
import uuid
import sys
import re
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, Blueprint, g
from flask_cors import CORS
from flask_login import current_user, login_required
from sqlalchemy import or_
from werkzeug.utils import secure_filename
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from flask_caching import Cache
import token_blocklist  # We'll initialize this later after db setup
from ai_helper import generate_personalized_suggestions, track_user_activity
from portfolio_optimizer import PortfolioOptimizer
from portfolio_routes import portfolio_bp
from art_routes import art_bp

# =========================================
# Environment Validation - START
# =========================================

# Set the known working Redis password for Proletto
redis_password = "Pvaa4zVI1rFkrOmTSqH5bLUklovyXHfH"
os.environ['REDIS_PASSWORD'] = redis_password

# Set the full Redis URL directly - using the correct format with just the password (no username)
redis_url = f"redis://:{redis_password}@redis-14544.c253.us-central1-1.gce.redns.redis-cloud.com:14544"
os.environ['REDIS_URL'] = redis_url
print(f"Using Redis URL (masked): redis://:{redis_password[:3]}***@redis-14544.c253.us-central1-1.gce.redns.redis-cloud.com:14544")

# List all required env vars and their expected patterns
REQUIRED_ENVS = {
    'DATABASE_URL': r'.+',
    'API_KEY': r'.+'
}

# For production, add these critical services
if os.environ.get('FLASK_ENV') == 'production':
    REQUIRED_ENVS.update({
        'REDIS_URL': r'^(redis|rediss)://.+',
        'JWT_SECRET_KEY': r'.+',
        'OPENAI_API_KEY': r'^sk-'
    })

# Validate all required environment variables
errors = []
for name, pattern in REQUIRED_ENVS.items():
    val = os.environ.get(name)
    if not val:
        errors.append(f"Missing required env var: {name}")
    elif not re.match(pattern, val):
        errors.append(f"Env var {name} doesn't match expected pattern")

if errors:
    for err in errors:
        print(f"ERROR: {err}", file=sys.stderr)
    if os.environ.get('FLASK_ENV') == 'production':
        # In production, fail fast
        sys.exit(1)
    else:
        # In development, just warn
        print("⚠️ Environment validation warnings (continuing in dev mode)...")
# Import recommendation routes
try:
    from recommendation_routes import recommendation_bp
    recommendation_routes_available = True
except ImportError as e:
    recommendation_routes_available = False
    logger.warning(f"Recommendation routes not available: {e}")
from application_autofill import ApplicationFormDetector, ApplicationAutoFiller, ApplicationSubmitter, ApplicationTracker
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from models import User
# The following models are not available yet
# Workspace, WorkspaceMember, Project, Task, TaskComment, ProjectFile, Message, MessageReadReceipt

# Import Google Drive integration
try:
    from drive_integration import get_drive_service
    
    # Check if credentials file exists and has content
    if os.path.exists('credentials.json') and os.path.getsize('credentials.json') > 10:
        DRIVE_ENABLED = True
    else:
        DRIVE_ENABLED = False
        logging.warning("Google Drive credentials file missing or invalid. Using local storage only.")
except (ImportError, Exception) as e:
    DRIVE_ENABLED = False
    logging.error(f"Google Drive integration not available: {e}")

# File path for local storage
OPPORTUNITIES_FILE = 'opportunities.json'
PORTFOLIOS_DIR = 'portfolios'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='api.log'
)
logger = logging.getLogger('proletto_api')

# Create Blueprints for the API
api_bp = Blueprint('api', __name__, url_prefix='/api')
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Import from main.py 
from main import db, app as main_app

# Setup a function to test database connection
@api_bp.route('/test-db', methods=['GET'])
def test_db():
    """Test database connection"""
    try:
        # Use main app context for database operations
        with main_app.app_context():
            from models import User
            users = User.query.limit(5).all()
            return jsonify({
                'success': True,
                'message': f'Database connection works! Found {len(users)} users.'
            })
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Paths
OPPORTUNITIES_FILE = "opportunities.json"

# Authentication routes
@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate a user and return JWT tokens
    """
    try:
        data = request.json
        if not data or not isinstance(data, dict):
            return jsonify({
                'success': False,
                'error': 'Invalid login data'
            }), 400
            
        # Get username/email and password
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Email and password are required'
            }), 400
            
        # Store user ID outside of context managers
        user_id = None
        user_email = None
        user_name = None
        user_membership = None
            
        # Authenticate the user against the database
        with main_app.app_context():
            # Import here to ensure User is properly loaded in the app context
            from models import User
            user = User.query.filter_by(email=email).first()
            
            # Special case for bot user: Auto-create if it doesn't exist
            if email == 'bot@proletto.com' and not user:
                logger.info("Creating bot user account for API access")
                from models import User
                bot_user = User(
                    name='Proletto Bot',
                    email='bot@proletto.com',
                    membership_level='premium',
                    role='bot'
                )
                bot_user.set_password(password)
                db.session.add(bot_user)
                db.session.commit()
                user = bot_user
                logger.info(f"Bot user created with ID: {user.id}")
            
            # Check credentials
            if not user:
                logger.warning(f"Failed login attempt for non-existent user: {email}")
                return jsonify({
                    'success': False,
                    'error': 'Invalid email or password'
                }), 401
                
            if not user.verify_password(password):
                logger.warning(f"Failed login attempt (password mismatch) for {email}")
                return jsonify({
                    'success': False,
                    'error': 'Invalid email or password'
                }), 401
                
            # Save user data
            user_id = user.id
            user_email = user.email
            user_name = user.name
            user_membership = user.membership_level
            
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"User authenticated: ID {user_id}, email {user_email}")
            
        # Create tokens in the app with JWT initialized
        access_token = None
        refresh_token = None
        
        with app.app_context():
            # Create access and refresh tokens
            access_token = create_access_token(identity=user_id)
            refresh_token = create_refresh_token(identity=user_id)
            
        if not access_token or not refresh_token:
            logger.error(f"Failed to create JWT tokens for user {user_id}")
            return jsonify({
                'success': False,
                'error': 'Token creation failed'
            }), 500
        
        # Log successful login
        logger.info(f"Successful login for user {user_id} ({user_email})")
        
        # Return the tokens
        return jsonify({
            'success': True,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user_id,
                'email': user_email,
                'name': user_name,
                'membership_level': user_membership
            }
        })
            
    except Exception as e:
        logger.error(f"Error in login: {e}")
        return jsonify({
            'success': False,
            'error': 'Authentication failed'
        }), 500
        
@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh the access token using a valid refresh token
    
    This endpoint creates a new access token when provided with a valid refresh token.
    The current refresh token will remain valid as it has a longer lifespan.
    
    If token rotation is enabled, the old refresh token will be revoked and a new 
    refresh token will be issued. This provides better security but requires clients
    to update both tokens.
    """
    try:
        # Get the user identity from the refresh token
        user_id = get_jwt_identity()
        
        # Get the JWT payload for potential blocklisting
        jwt_payload = get_jwt()
        
        # Track token usage and detect potential token reuse attacks
        jti = jwt_payload.get('jti')
        
        # Convert to int if the identity is a string (our user IDs are integers)
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid user ID format in JWT refresh token: {user_id}")
            return jsonify({
                'success': False,
                'error': 'Invalid user ID format in token'
            }), 400
        
        # Get user details from the database
        user_data = None
        with main_app.app_context():
            from models import User
            user = User.query.get(user_id)
            
            if not user:
                logger.error(f"User not found for ID during refresh: {user_id}")
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
                
            user_data = {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'membership_level': user.membership_level,
                'role': user.role
            }
        
        # Create a new access token
        access_token = create_access_token(identity=user_id)
        
        # Enable token rotation for enhanced security
        # This adds enhanced security by invalidating old tokens and implementing token reuse detection
        
        # Revoke the current refresh token
        token_blocklist.add_token_to_blocklist(jwt_payload, user_id=user_id, token_type='refresh')
        
        # Create a new refresh token
        refresh_token = create_refresh_token(identity=user_id)
        
        # Log successful token refresh with rotation
        logger.info(f"Successfully refreshed tokens with rotation for user ID: {user_id}")
        
        # Return both new tokens
        return jsonify({
            'success': True,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user_data
        })
        
    except Exception as e:
        logger.error(f"Error in refresh: {e}")
        return jsonify({
            'success': False,
            'error': f'Token refresh failed: {str(e)}'
        }), 500
        
@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """
    Verify that the JWT token is valid
    """
    try:
        # Get the user identity from the token (will be a string due to our identity loader)
        user_id = get_jwt_identity()
        
        # Convert to int if the identity is a string (our user IDs are integers)
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid user ID format in JWT token: {user_id}")
            return jsonify({
                'success': False,
                'error': 'Invalid user ID format in token'
            }), 400
        
        # Get user details from the database
        with main_app.app_context():
            # Import here to ensure User is properly loaded in the app context
            from models import User
            user = User.query.get(user_id)
            
            if not user:
                logger.error(f"User not found for ID: {user_id}")
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
                
            logger.info(f"Successfully verified token for user ID: {user_id}")
            
            # Return basic user info
            return jsonify({
                'success': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': user.name,
                    'membership_level': user.membership_level,
                    'role': user.role
                }
            })
            
    except Exception as e:
        logger.error(f"Error in verify_token: {e}")
        return jsonify({
            'success': False,
            'error': f'Token verification failed: {str(e)}'
        }), 500
        
@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Log out a user by revoking their tokens
    
    This endpoint blacklists the current access token and optionally
    the refresh token if provided.
    """
    try:
        # Get JWT payload for the current token
        jwt_payload = get_jwt()
        user_id = get_jwt_identity()
        
        # Convert to int if the identity is a string
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid user ID format in JWT token during logout: {user_id}")
            return jsonify({
                'success': False,
                'error': 'Invalid user ID format in token'
            }), 400
            
        # Add the current access token to the blocklist
        token_blocklist.add_token_to_blocklist(jwt_payload, user_id=user_id, token_type='access')
        logger.info(f"Access token blacklisted for user ID: {user_id}")
        
        # Check if a refresh token is provided to revoke as well
        data = request.json or {}
        refresh_token = data.get('refresh_token')
        
        if refresh_token:
            try:
                # Import jwt decoder to get the payload without verification
                from flask_jwt_extended import decode_token
                refresh_token_payload = decode_token(refresh_token)
                token_blocklist.add_token_to_blocklist(refresh_token_payload, user_id=user_id, token_type='refresh')
                logger.info(f"Refresh token blacklisted for user ID: {user_id}")
            except Exception as e:
                logger.warning(f"Failed to blacklist refresh token for user ID: {user_id}, error: {e}")
                # Continue with the logout even if refresh token revocation fails
        
        # Clean up expired tokens from blocklist to keep the database size manageable
        try:
            removed_count = token_blocklist.prune_blocklist()
            logger.info(f"Pruned {removed_count} expired tokens from blocklist")
        except Exception as e:
            logger.error(f"Failed to prune token blocklist: {e}")
            # Continue with the logout even if pruning fails
        
        return jsonify({
            'success': True,
            'message': 'Successfully logged out'
        })
        
    except Exception as e:
        logger.error(f"Error in logout: {e}")
        return jsonify({
            'success': False,
            'error': f'Logout failed: {str(e)}'
        }), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Returns the current user's profile information
    Used for dashboard personalization and user settings
    """
    try:
        # Get the user identity from the token
        user_id = get_jwt_identity()
        
        # Convert to int if the identity is a string (our user IDs are integers)
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid user ID format in JWT token: {user_id}")
            return jsonify({
                'error': 'Invalid user ID format in token'
            }), 400
        
        # Get user details from the database
        with main_app.app_context():
            from models import User
            user = User.query.get(user_id)
            
            if not user:
                logger.error(f"User not found for ID: {user_id}")
                return jsonify({
                    'error': 'User not found'
                }), 404
            
            # Format the joined date if available
            joined_date = user.created_at.strftime("%Y-%m-%d") if hasattr(user, "created_at") and user.created_at else None
            
            # Return user profile data
            logger.info(f"Profile data requested for user ID: {user_id}")
            return jsonify({
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'bio': user.bio,
                'location': user.location,
                'avatar_url': user.avatar_url,
                'role': user.role,
                'membership_level': user.membership_level,
                'joined': joined_date
            }), 200
    
    except Exception as e:
        logger.error(f"Error in get_current_user: {e}")
        return jsonify({
            'error': f'Failed to retrieve user profile: {str(e)}'
        }), 500

@auth_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_user_profile():
    """
    Update the current user's profile information
    """
    try:
        # Get the user identity from the token
        user_id = get_jwt_identity()
        
        # Convert to int if the identity is a string (our user IDs are integers)
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid user ID format in JWT token: {user_id}")
            return jsonify({
                'error': 'Invalid user ID format in token'
            }), 400
        
        # Get request data
        data = request.get_json()
        if not data:
            logger.error(f"No data provided in request")
            return jsonify({
                'error': 'No data provided'
            }), 400
        
        # Get user details from the database
        with main_app.app_context():
            from models import User, db
            user = User.query.get(user_id)
            
            if not user:
                logger.error(f"User not found for ID: {user_id}")
                return jsonify({
                    'error': 'User not found'
                }), 404
            
            # Update user fields if provided in the request
            if 'name' in data:
                user.name = data['name']
            if 'bio' in data:
                user.bio = data['bio']
            if 'location' in data:
                user.location = data['location']
            if 'avatar_url' in data:
                user.avatar_url = data['avatar_url']
            
            # Save changes to the database
            db.session.commit()
            
            # Format the joined date if available for response
            joined_date = user.created_at.strftime("%Y-%m-%d") if hasattr(user, "created_at") and user.created_at else None
            
            # Return updated user profile data
            logger.info(f"Profile updated for user ID: {user_id}")
            return jsonify({
                'message': 'Profile updated successfully',
                'user': {
                    'id': user.id,
                    'name': user.name,
                    'email': user.email,
                    'bio': user.bio,
                    'location': user.location,
                    'avatar_url': user.avatar_url,
                    'role': user.role,
                    'membership_level': user.membership_level,
                    'joined': joined_date
                }
            }), 200
    
    except Exception as e:
        logger.error(f"Error in update_user_profile: {e}")
        return jsonify({
            'error': f'Failed to update user profile: {str(e)}'
        }), 500

@auth_bp.route('/test', methods=['GET'])
@jwt_required()
def test_auth():
    """
    Simple test endpoint for JWT authentication
    Doesn't depend on any external services
    Just returns success and basic identity information from the token
    """
    try:
        # Get the user identity from the token (will be a string due to our identity loader)
        user_id = get_jwt_identity()
        
        # Convert to int if the identity is a string (our user IDs are integers)
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid user ID format in JWT token: {user_id}")
            return jsonify({
                'success': False,
                'error': 'Invalid user ID format in token',
                'user_id_from_token': user_id
            }), 400
        
        # Get user details from the database
        with main_app.app_context():
            from models import User
            user = User.query.get(user_id)
            
            if not user:
                logger.error(f"User not found for ID: {user_id}")
                return jsonify({
                    'success': False,
                    'error': 'User not found',
                    'user_id_from_token': user_id
                }), 404
            
            # Return basic auth test success with user details
            logger.info(f"Authentication test successful for user ID: {user_id}, role: {user.role}")
            return jsonify({
                'success': True,
                'message': 'Authentication test successful',
                'token_contains': {
                    'user_id': user_id
                },
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': user.name,
                    'role': user.role,
                    'membership_level': user.membership_level
                }
            })
    
    except Exception as e:
        logger.error(f"Error in test_auth: {e}")
        return jsonify({
            'success': False,
            'error': f'Authentication test failed: {str(e)}'
        }), 500

@api_bp.route('/opportunities/add/test', methods=['POST'])
@jwt_required()
def test_add_opportunity():
    """
    Test endpoint for adding opportunities without external dependencies
    Only saves to the local file, skips Google Drive
    Only for testing bot authentication and permission checks
    """
    try:
        # Get user identity from token
        user_id = get_jwt_identity()
        
        # Convert to int if the identity is a string
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid user ID format in JWT token: {user_id}")
            return jsonify({
                'success': False,
                'error': 'Invalid user ID format in token',
                'user_id_from_token': user_id
            }), 400
        
        # Check if user has permission (bot or admin)
        with main_app.app_context():
            # Import here to ensure User is properly loaded in the app context
            from models import User
            user = User.query.get(user_id)
            
            if not user:
                logger.warning(f"User not found for ID {user_id} when attempting to add opportunity")
                return jsonify({
                    'success': False,
                    'error': 'User not found.'
                }), 404
                
            # Authenticated but checking specific role permissions
            if user.role != 'bot' and user.role != 'admin':
                logger.warning(f"Unauthorized attempt to add opportunity by user ID {user_id}, role: {user.role}")
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized. Only bot or admin users can add opportunities via API.'
                }), 403
                
            # Success - user has proper role
            logger.info(f"Authorized access for test opportunity addition by {user.role} user (ID: {user.id}, email: {user.email})")
        
        # Get opportunity data from request
        data = request.json
        
        if not data or not isinstance(data, dict):
            return jsonify({
                'success': False,
                'error': 'Invalid opportunity data'
            }), 400
        
        # Validate required fields
        required_fields = ['title', 'url']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Add scraped_date if not provided
        if 'scraped_date' not in data:
            data['scraped_date'] = datetime.utcnow().isoformat()
        
        # Load existing opportunities from local file only
        try:
            with open(OPPORTUNITIES_FILE, 'r', encoding='utf-8') as f:
                opportunities = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            opportunities = []
            logger.warning(f"Creating new opportunities file at {OPPORTUNITIES_FILE}")
        
        # Add a marker to identify test opportunities
        data['source'] = f"Test: {data.get('source', 'API Test')}"
        data['test_flag'] = True
        
        # Check for duplicates (by URL)
        for opp in opportunities:
            if opp.get('url') == data.get('url'):
                # Update existing opportunity
                opp.update(data)
                break
        else:
            # Add new opportunity
            opportunities.append(data)
        
        # Save updated opportunities to local file only
        with open(OPPORTUNITIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(opportunities, f, indent=2)
        
        logger.info(f"Test opportunity saved successfully: {data['title']} - local storage only")
        return jsonify({
            'success': True,
            'message': 'Test opportunity added successfully to local storage',
            'data': data
        })
    
    except Exception as e:
        logger.error(f"Error in test_add_opportunity: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to add test opportunity: {str(e)}'
        }), 500

@api_bp.route('/opportunities', methods=['GET'])
def get_opportunities():
    """
    Get all opportunities, with optional filtering
    """
    try:
        # Just load directly from the local file for now
        app.logger.info(f"Loading opportunities from local file: {OPPORTUNITIES_FILE}")
        
        # Check if the file exists and is readable
        if not os.path.exists(OPPORTUNITIES_FILE):
            app.logger.error(f"Opportunities file does not exist: {OPPORTUNITIES_FILE}")
            return jsonify({
                'success': False,
                'error': 'Opportunities file not found',
                'file_path': OPPORTUNITIES_FILE
            }), 404
        
        try:
            with open(OPPORTUNITIES_FILE, 'r', encoding='utf-8') as f:
                opportunities = json.load(f)
            
            # Extra logging to debug the structure
            app.logger.info(f"Successfully loaded {len(opportunities)} opportunities")
            
        except json.JSONDecodeError as e:
            app.logger.error(f"JSON decode error when reading {OPPORTUNITIES_FILE}: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Invalid JSON in opportunities file: {str(e)}'
            }), 500
        except Exception as e:
            app.logger.error(f"Error reading {OPPORTUNITIES_FILE}: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Error reading opportunities file: {str(e)}'
            }), 500
            
        # Handle file not found or empty
        if not opportunities:
            app.logger.warning(f"Opportunities file found but empty: {OPPORTUNITIES_FILE}")
            opportunities = []
        
        # Get request parameters for filtering
        keyword = request.args.get('keyword', '').lower()
        limit = request.args.get('limit')
        if limit:
            try:
                limit = int(limit)
            except ValueError:
                limit = None
        
        # Filter by keyword if provided
        if keyword:
            filtered_opportunities = [
                opp for opp in opportunities 
                if (keyword in opp.get('title', '').lower() or
                    keyword in opp.get('description', '').lower() or
                    keyword in opp.get('location', '').lower() or
                    keyword in opp.get('source', '').lower())
            ]
        else:
            filtered_opportunities = opportunities
        
        # Sort by scraped date (newest first)
        sorted_opportunities = sorted(
            filtered_opportunities,
            key=lambda x: x.get('scraped_date', ''),
            reverse=True
        )
        
        # Apply limit if provided
        if limit and limit > 0:
            result = sorted_opportunities[:limit]
        else:
            result = sorted_opportunities
        
        # Return the opportunities as JSON
        return jsonify({
            'success': True,
            'count': len(result),
            'opportunities': result
        })
    
    except Exception as e:
        app.logger.error(f"Error in get_opportunities: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/opportunities/add', methods=['POST'])
@jwt_required()
def add_opportunity():
    """
    Add a new opportunity to the database
    Requires JWT authentication
    Only bot and admin users can add opportunities directly via API
    """
    try:
        # Get user identity from token
        user_id = get_jwt_identity()
        
        # Check if user has permission (bot or admin)
        with main_app.app_context():
            # Import here to ensure User is properly loaded in the app context
            from models import User
            user = User.query.get(user_id)
            
            if not user:
                logger.warning(f"User not found for ID {user_id} when attempting to add opportunity")
                return jsonify({
                    'success': False,
                    'error': 'User not found.'
                }), 404
                
            # Authenticated but checking specific role permissions
            if user.role != 'bot' and user.role != 'admin':
                logger.warning(f"Unauthorized attempt to add opportunity by user ID {user_id}, role: {user.role}")
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized. Only bot or admin users can add opportunities via API.'
                }), 403
                
            # Success - user has proper role
            logger.info(f"Authorized access for opportunity addition by {user.role} user (ID: {user.id}, email: {user.email})")
        
        # Get opportunity data from request
        data = request.json
        
        if not data or not isinstance(data, dict):
            return jsonify({
                'success': False,
                'error': 'Invalid opportunity data'
            }), 400
        
        # Validate required fields
        required_fields = ['title', 'url']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Add scraped_date if not provided
        if 'scraped_date' not in data:
            data['scraped_date'] = datetime.utcnow().isoformat()
        
        # Load existing opportunities from Google Drive or local file
        opportunities = []
        if DRIVE_ENABLED:
            try:
                drive_service = get_drive_service()
                opportunities = drive_service.load_opportunities()
                if not opportunities:
                    # Fall back to local file if no opportunities found
                    with open(OPPORTUNITIES_FILE, 'r', encoding='utf-8') as f:
                        opportunities = json.load(f)
            except Exception as e:
                logger.error(f"Error loading from Google Drive: {e}, falling back to local file")
                with open(OPPORTUNITIES_FILE, 'r', encoding='utf-8') as f:
                    opportunities = json.load(f)
        else:
            # Load from local file
            try:
                with open(OPPORTUNITIES_FILE, 'r', encoding='utf-8') as f:
                    opportunities = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                opportunities = []
        
        # Check for duplicates (by URL)
        for opp in opportunities:
            if opp.get('url') == data.get('url'):
                # Update existing opportunity
                opp.update(data)
                break
        else:
            # Add new opportunity
            opportunities.append(data)
        
        # Save updated opportunities to both local file and Google Drive
        with open(OPPORTUNITIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(opportunities, f, indent=2)
        
        # Save to Google Drive if enabled
        if DRIVE_ENABLED:
            try:
                drive_service = get_drive_service()
                file_id = drive_service.save_opportunities(opportunities)
                logger.info(f"Successfully saved opportunities to Google Drive with ID: {file_id}")
            except Exception as e:
                logger.error(f"Failed to save to Google Drive: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Opportunity added successfully'
        })
    
    except Exception as e:
        logger.error(f"Error in add_opportunity: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    Get statistics about the opportunities
    """
    try:
        # Just load directly from the local file for now
        opportunities = []
        app.logger.info(f"Loading opportunities from local file for stats: {OPPORTUNITIES_FILE}")
        try:
            with open(OPPORTUNITIES_FILE, 'r', encoding='utf-8') as f:
                opportunities = json.load(f)
            app.logger.info(f"Successfully loaded {len(opportunities)} opportunities for stats")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            app.logger.warning(f"Opportunities file not found or invalid: {OPPORTUNITIES_FILE}, Error: {str(e)}")
            opportunities = []
        
        # Calculate stats
        total_count = len(opportunities)
        
        # Count opportunities by scraped date (last 7 days)
        today = datetime.utcnow().date()
        daily_counts = {}
        
        for opp in opportunities:
            try:
                scraped_date = datetime.fromisoformat(opp.get('scraped_date', '')).date()
                days_ago = (today - scraped_date).days
                
                if days_ago <= 7:
                    date_str = scraped_date.isoformat()
                    daily_counts[date_str] = daily_counts.get(date_str, 0) + 1
            except (ValueError, TypeError):
                continue
        
        # Return the stats as JSON
        return jsonify({
            'success': True,
            'total_count': total_count,
            'daily_counts': daily_counts
        })
    
    except Exception as e:
        app.logger.error(f"Error in get_stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/portfolio/save', methods=['POST'])
@jwt_required()
def save_portfolio():
    """
    Save a user's portfolio to Google Drive or local storage
    Requires JWT authentication
    """
    try:
        # Get portfolio data from request
        data = request.json
        
        if not data or not isinstance(data, dict):
            return jsonify({
                'success': False,
                'error': 'Invalid portfolio data'
            }), 400
        
        # Validate required fields
        required_fields = ['user_id', 'portfolio_data']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Setup file paths
        user_id = data['user_id']
        portfolio_data = data['portfolio_data']
        file_name = f"portfolio_{user_id}.json"
        
        # Create portfolios directory if it doesn't exist
        if not os.path.exists(PORTFOLIOS_DIR):
            os.makedirs(PORTFOLIOS_DIR)
            
        local_path = os.path.join(PORTFOLIOS_DIR, file_name)
        
        # Save locally
        with open(local_path, 'w', encoding='utf-8') as f:
            json.dump(portfolio_data, f, indent=2)
            
        logger.info(f"Portfolio saved locally to {local_path}")
        
        file_id = None
        drive_success = False
        
        # Upload to Google Drive if available
        if DRIVE_ENABLED:
            try:
                drive_service = get_drive_service()
                if drive_service:
                    file_id = drive_service.upload_file(local_path, 'portfolios')
                    logger.info(f"Portfolio saved to Google Drive with ID: {file_id}")
                    drive_success = True
                else:
                    logger.warning("Google Drive service unavailable, using local storage only")
            except Exception as e:
                # Log but continue with local storage
                logger.error(f"Failed to save portfolio to Google Drive: {e}")
        
        # Update user's portfolio count in the database
        try:
            # Use main app context for database operations
            with main_app.app_context():
                from models import User
                
                # Try to convert user_id to integer if it's a string
                user_db_id = user_id
                try:
                    if isinstance(user_id, str) and user_id.isdigit():
                        user_db_id = int(user_id)
                except (ValueError, TypeError):
                    pass
                
                user = User.query.get(user_db_id)
                if user:
                    # Always increment portfolio count when we save a portfolio
                    # We can add more logic later to only increment for new portfolios
                    user.portfolio_count += 1
                    db.session.commit()
                    logger.info(f"Updated portfolio count for user {user_id}: {user.portfolio_count}")
                else:
                    logger.warning(f"User with ID {user_id} not found, portfolio count not updated")
        except Exception as e:
            # Log but continue - this shouldn't stop the save operation from succeeding
            logger.error(f"Failed to update user portfolio count: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Portfolio saved successfully' + 
                       ('' if drive_success else ' (using local storage only)'),
            'file_id': file_id,
            'local_path': local_path
        })
    
    except Exception as e:
        logger.error(f"Error in save_portfolio: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/portfolio/list', methods=['GET'])
def list_portfolios():
    """
    List all portfolios stored in Google Drive or local storage
    """
    try:
        portfolios = []
        source = "local storage"
        
        # Try Google Drive first if enabled
        if DRIVE_ENABLED:
            try:
                drive_service = get_drive_service()
                if drive_service:
                    portfolios = drive_service.list_files('portfolios')
                    source = "Google Drive"
                    logger.info(f"Listed {len(portfolios)} portfolios from Google Drive")
            except Exception as e:
                logger.error(f"Error listing portfolios from Google Drive: {e}")
                # Continue to try local storage
        
        # If Google Drive is not available or failed, list from local storage
        if not portfolios and os.path.exists(PORTFOLIOS_DIR):
            try:
                # Get all JSON files in the portfolios directory
                local_portfolios = []
                for filename in os.listdir(PORTFOLIOS_DIR):
                    if filename.endswith('.json') and filename.startswith('portfolio_'):
                        # Extract user_id from filename (portfolio_<user_id>.json)
                        try:
                            user_id = filename.replace('portfolio_', '').replace('.json', '')
                            file_path = os.path.join(PORTFOLIOS_DIR, filename)
                            modified_time = os.path.getmtime(file_path)
                            modified_date = datetime.fromtimestamp(modified_time).isoformat()
                            
                            local_portfolios.append({
                                'id': f"local_{user_id}",
                                'name': filename,
                                'user_id': user_id,
                                'modified_date': modified_date,
                                'local_path': file_path
                            })
                        except Exception as e:
                            logger.error(f"Error processing local portfolio file {filename}: {e}")
                            continue
                
                portfolios = local_portfolios
                source = "local storage"
                logger.info(f"Listed {len(portfolios)} portfolios from local storage")
            except Exception as e:
                logger.error(f"Error listing portfolios from local storage: {e}")
        
        return jsonify({
            'success': True,
            'count': len(portfolios),
            'portfolios': portfolios,
            'source': source
        })
    
    except Exception as e:
        logger.error(f"Error in list_portfolios: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/portfolio/<file_id>', methods=['GET'])
def get_portfolio(file_id):
    """
    Get a specific portfolio from Google Drive or local storage
    """
    try:
        # Check if this is a local ID (format: "local_<user_id>")
        is_local = file_id.startswith('local_')
        
        # Handle local file case
        if is_local:
            user_id = file_id.replace('local_', '')
            file_path = os.path.join(PORTFOLIOS_DIR, f"portfolio_{user_id}.json")
            
            if not os.path.exists(file_path):
                return jsonify({
                    'success': False,
                    'error': f'Local portfolio file not found for user ID: {user_id}'
                }), 404
                
            # Read the portfolio data
            with open(file_path, 'r', encoding='utf-8') as f:
                portfolio_data = json.load(f)
                
            return jsonify({
                'success': True,
                'portfolio': portfolio_data,
                'source': 'local storage'
            })
        
        # Handle Google Drive case
        if DRIVE_ENABLED:
            try:
                drive_service = get_drive_service()
                if drive_service:
                    temp_file = f"temp_portfolio_{file_id}.json"
                    
                    # Download the file
                    success = drive_service.download_file(file_id, temp_file)
                    
                    if success:
                        # Read the portfolio data
                        with open(temp_file, 'r', encoding='utf-8') as f:
                            portfolio_data = json.load(f)
                        
                        # Delete the temporary file
                        os.remove(temp_file)
                        
                        return jsonify({
                            'success': True,
                            'portfolio': portfolio_data,
                            'source': 'Google Drive'
                        })
                    else:
                        logger.error(f"Failed to download portfolio from Google Drive: {file_id}")
            except Exception as e:
                logger.error(f"Error getting portfolio from Google Drive: {e}")
        
        # If we get here, either Google Drive is not available or the file wasn't found
        return jsonify({
            'success': False,
            'error': 'Portfolio not found. Google Drive may be unavailable or the file does not exist.'
        }), 404
    
    except Exception as e:
        logger.error(f"Error in get_portfolio: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/suggestions', methods=['POST'])
def get_personalized_suggestions():
    """
    Get personalized opportunity suggestions based on user profile
    """
    try:
        # Get user profile data from request
        data = request.json
        
        if not data or not isinstance(data, dict):
            return jsonify({
                'success': False,
                'error': 'Invalid user profile data'
            }), 400
        
        # Generate personalized suggestions using AI
        suggestions = generate_personalized_suggestions(data)
        
        # Track AI usage for badges
        if 'user_id' in data and data['user_id']:
            # We use our own db instance
            from models import User
            
            user = User.query.get(data['user_id'])
            if user:
                # Update the user's AI usage count and check for badges
                new_badges = track_user_activity(user, "use_ai")
                db.session.commit()
                
                # Include badge information in the response if any were earned
                if new_badges:
                    suggestions['new_badges'] = new_badges
        
        # Return the suggestions
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
    
    except Exception as e:
        logger.error(f"Error in get_personalized_suggestions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/user/profile', methods=['GET'])
@jwt_required()
def get_user_profile():
    """
    Get user profile information including badges, referrals, and activity stats
    Requires JWT authentication
    """
    try:
        # Get user ID from query parameters
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Missing user_id parameter'
            }), 400
        
        # Use main app context for database operations
        with main_app.app_context():
            # Get user from database
            from models import User
            
            user = User.query.get(user_id)
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
            
            # Build profile response
            profile = {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'membership_level': user.membership_level,
                'digest_enabled': user.digest_enabled if hasattr(user, 'digest_enabled') else True,
                'digest_day_of_week': user.digest_day_of_week if hasattr(user, 'digest_day_of_week') else 0,
                'badges': user.badges,
                'interests': user.interests,
                'referrals': {
                    'code': user.referral_code or user.generate_referral_code(),
                    'count': user.get_referral_count()
                },
                'activity': {
                    'portfolio_count': user.portfolio_count,
                    'opportunity_views': user.opportunity_views,
                    'application_count': user.application_count,
                    'ai_uses': user.ai_uses
                },
                'selected_states': user.selected_states
            }
            
            if user.subscription_end_date:
                profile['subscription'] = {
                    'active': user.subscription_end_date > datetime.utcnow(),
                    'end_date': user.subscription_end_date.isoformat()
                }
        
        return jsonify({
            'success': True,
            'profile': profile
        })
    
    except Exception as e:
        logger.error(f"Error in get_user_profile: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/user/profile', methods=['POST'])
@jwt_required()
def update_user_profile():
    """
    Update user profile information
    Requires JWT authentication
    """
    try:
        # Get profile data from request
        data = request.json
        
        if not data or not isinstance(data, dict):
            return jsonify({
                'success': False,
                'error': 'Invalid profile data'
            }), 400
        
        # Validate required fields
        if 'user_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: user_id'
            }), 400
        
        # Use main app context for database operations
        with main_app.app_context():
            # Get user from database
            from models import User
            
            user = User.query.get(data['user_id'])
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
            
            # Update user profile fields
            updatable_fields = ['name', 'interests', 'selected_states', 'digest_enabled', 'digest_day_of_week']
            
            for field in updatable_fields:
                if field in data:
                    if field == 'interests':
                        user.interests = data[field]
                    elif field == 'selected_states':
                        # Check if user is allowed to select states (Supporter tier)
                        if user.membership_level != 'supporter' and user.membership_level != 'premium':
                            return jsonify({
                                'success': False,
                                'error': 'Only Supporter and Premium members can select states'
                            }), 403
                        # Limit to 3 states for Supporter tier
                        if user.membership_level == 'supporter' and len(data[field]) > 3:
                            return jsonify({
                                'success': False,
                                'error': 'Supporter tier is limited to 3 selected states'
                            }), 400
                        user.selected_states = data[field]
                    elif field == 'digest_enabled':
                        # Update digest enabled status
                        user.digest_enabled = bool(data[field])
                        
                        # If disabling digest, reset failure count
                        if not user.digest_enabled:
                            user.digest_failure_count = 0
                    elif field == 'digest_day_of_week':
                        # Check if user is allowed to set custom day (Premium tier)
                        day_value = int(data[field])
                        
                        # Validate day value (0-6 representing Monday-Sunday)
                        if day_value < 0 or day_value > 6:
                            return jsonify({
                                'success': False,
                                'error': 'Invalid day of week value. Must be 0-6 (Monday-Sunday).'
                            }), 400
                            
                        # Only premium users can set custom day
                        if user.membership_level == 'premium':
                            user.digest_day_of_week = day_value
                        else:
                            # For non-premium, we still store the preference but will only apply it
                            # if they upgrade to premium
                            user.digest_day_of_week = day_value
                    else:
                        setattr(user, field, data[field])
            
            # Save changes
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully'
        })
    
    except Exception as e:
        logger.error(f"Error in update_user_profile: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/user/track-activity', methods=['POST'])
@jwt_required()
def track_activity():
    """
    Track user activity for badge awards
    Requires JWT authentication
    """
    try:
        # Get activity data from request
        data = request.json
        
        if not data or not isinstance(data, dict):
            return jsonify({
                'success': False,
                'error': 'Invalid activity data'
            }), 400
        
        # Validate required fields
        required_fields = ['user_id', 'activity_type']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Use main app context for database operations
        with main_app.app_context():
            # Get user from database
            from models import User
            
            user = User.query.get(data['user_id'])
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
            
            # Track activity and get new badges
            new_badges = track_user_activity(user, data['activity_type'], data.get('details'))
            db.session.commit()
        
        # Return success response with new badges if any
        response = {
            'success': True,
            'message': 'Activity tracked successfully'
        }
        
        if new_badges:
            response['new_badges'] = new_badges
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error in track_activity: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/feedback', methods=['POST'])
@jwt_required()
def submit_feedback():
    """
    Submit user feedback for an opportunity
    Requires JWT authentication
    """
    try:
        # Get data from request
        data = request.json
        
        if not data or not isinstance(data, dict):
            return jsonify({
                'success': False,
                'error': 'Invalid feedback data'
            }), 400
        
        # Validate required fields
        required_fields = ['opp_id', 'rating']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Get values from request
        opp_id = data.get('opp_id')
        rating = data.get('rating')
        comment = data.get('comment', None)
        
        # Validate data types
        if not isinstance(opp_id, str) or not isinstance(rating, bool):
            return jsonify({
                'success': False,
                'error': 'Invalid data format: opp_id must be a string and rating must be a boolean'
            }), 400
        
        # Get user from JWT token
        user_id = get_jwt_identity()
        
        # Save feedback to database
        try:
            with main_app.app_context():
                from models import User, Feedback
                
                user = User.query.get(user_id)
                if not user:
                    return jsonify({
                        'success': False,
                        'error': 'User not found'
                    }), 404
                
                # Create new feedback record
                feedback = Feedback(
                    user_id=user_id,
                    opp_id=opp_id,
                    rating=rating,
                    comment=comment
                )
                
                # Add to database
                db.session.add(feedback)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Feedback submitted successfully',
                    'feedback_id': feedback.id
                }), 200
                
        except Exception as e:
            logger.error(f"Database error in submit_feedback: {str(e)}")
            return jsonify({
                'success': False,
                'error': f"Database error: {str(e)}"
            }), 500
            
    except Exception as e:
        logger.error(f"Error in submit_feedback: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Server error: {str(e)}"
        }), 500

@api_bp.route('/application/detect', methods=['POST'])
def detect_application_form():
    """
    Detect an application form from a URL
    """
    try:
        # Get URL from request
        data = request.json
        
        if not data or not isinstance(data, dict) or 'url' not in data:
            return jsonify({
                'success': False,
                'error': 'URL is required'
            }), 400
        
        url = data['url']
        
        # Import the check_openai_availability function and verify OpenAI status
        from application_autofill import check_openai_availability
        ai_available = check_openai_availability()
        
        # Create form detector
        detector = ApplicationFormDetector()
        
        # Add AI availability info to log
        logger.info(f"Detecting application form at {url} (AI available: {ai_available})")
        
        # Detect form
        result = detector.detect_form(url)
        
        # Add AI availability to the response
        result['ai_available'] = ai_available
        
        # Track activity for the user if provided
        if 'user_id' in data:
            try:
                # Use main app context for database operations
                with main_app.app_context():
                    # Get user from database
                    from models import User
                    
                    user = User.query.get(data['user_id'])
                    if user:
                        # Track activity
                        track_user_activity(user, 'application_form_detected', {
                            'url': url,
                            'success': result.get('success', False)
                        })
                        db.session.commit()
            except Exception as e:
                logger.error(f"Error tracking application detection activity: {e}")
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error in detect_application_form: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/application/autofill', methods=['POST'])
@jwt_required()
def autofill_application():
    """
    Generate content for an application form
    Requires JWT authentication
    """
    try:
        # Get data from request
        data = request.json
        
        if not data or not isinstance(data, dict):
            return jsonify({
                'success': False,
                'error': 'Invalid request data'
            }), 400
        
        # Validate required fields
        required_fields = ['artist_data', 'opportunity_data', 'form_fields']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Import the check_openai_availability function and verify OpenAI status
        from application_autofill import check_openai_availability
        ai_available = check_openai_availability()
        
        # Create auto-filler
        auto_filler = ApplicationAutoFiller()
        
        # Add AI availability info to log
        logger.info(f"Generating application content for {data['opportunity_data'].get('title', 'Unknown')} (AI available: {ai_available})")
        
        # Generate content
        result = auto_filler.generate_application_content(
            data['artist_data'],
            data['opportunity_data'],
            data['form_fields']
        )
        
        # Add AI availability to the response
        result['ai_available'] = ai_available
        
        # Track activity for the user if provided
        if 'user_id' in data['artist_data']:
            try:
                # Use main app context for database operations
                with main_app.app_context():
                    # Get user from database
                    from models import User
                    
                    user = User.query.get(data['artist_data']['user_id'])
                    if user:
                        # Update AI uses count
                        user.ai_uses += 1
                        
                        # Track activity
                        track_user_activity(user, 'application_autofill', {
                            'opportunity_title': data['opportunity_data'].get('title', 'Unknown'),
                            'field_count': len(data['form_fields']),
                            'success': result.get('success', False)
                        })
                        db.session.commit()
            except Exception as e:
                logger.error(f"Error tracking application autofill activity: {e}")
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error in autofill_application: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/application/submit', methods=['POST'])
@jwt_required()
def submit_application():
    """
    Submit an application form
    Requires JWT authentication
    """
    try:
        # Get data from request
        data = request.json
        
        if not data or not isinstance(data, dict):
            return jsonify({
                'success': False,
                'error': 'Invalid request data'
            }), 400
        
        # Validate required fields
        required_fields = ['url', 'form_data', 'artist_data']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Create submitter
        submitter = ApplicationSubmitter()
        
        # Submit application
        result = submitter.submit_application(
            data['url'],
            data['form_data'],
            data['artist_data']
        )
        
        # Track activity for the user if provided
        if 'id' in data['artist_data'] or 'user_id' in data['artist_data']:
            try:
                # Use main app context for database operations
                with main_app.app_context():
                    # Get user from database
                    from models import User
                    
                    user_id = data['artist_data'].get('id') or data['artist_data'].get('user_id')
                    user = User.query.get(user_id)
                    if user:
                        # Update application count
                        user.application_count += 1
                        
                        # Track activity
                        track_user_activity(user, 'application_submitted', {
                            'opportunity_title': data['form_data'].get('opportunity_title', 'Unknown'),
                            'submission_id': result.get('submission_id'),
                            'success': result.get('success', False)
                        })
                        db.session.commit()
            except Exception as e:
                logger.error(f"Error tracking application submission activity: {e}")
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error in submit_application: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/application/track', methods=['POST'])
@jwt_required()
def track_application_status():
    """
    Track the status of a submitted application
    Requires JWT authentication
    """
    try:
        # Get data from request
        data = request.json
        
        if not data or not isinstance(data, dict):
            return jsonify({
                'success': False,
                'error': 'Invalid request data'
            }), 400
        
        # Validate required fields
        if 'application_data' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: application_data'
            }), 400
        
        # Create tracker
        tracker = ApplicationTracker()
        
        # Track application status
        result = tracker.track_application(
            data['application_data'],
            data.get('check_url')
        )
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error in track_application_status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/services/status', methods=['GET'])
def services_status():
    """
    Get the current status of various services
    Used by the frontend to adapt its behavior when certain services are unavailable
    """
    try:
        # Check Google Drive status
        drive_status = {
            'available': False,
            'message': 'Google Drive integration is disabled.'
        }
        
        if DRIVE_ENABLED:
            try:
                drive_service = get_drive_service()
                if drive_service:
                    drive_status = {
                        'available': True,
                        'message': 'Google Drive integration is available.'
                    }
                else:
                    drive_status = {
                        'available': False,
                        'message': 'Google Drive service unavailable (credentials may be invalid).'
                    }
            except Exception as e:
                drive_status = {
                    'available': False,
                    'message': f'Google Drive error: {str(e)}'
                }
        
        # Check database status
        db_status = {
            'available': False,
            'message': 'Database connection not verified.'
        }
        
        try:
            # Use main app context for database operations
            with main_app.app_context():
                # Simple query to test database
                from models import User
                User.query.count()
                db_status = {
                    'available': True,
                    'message': 'Database connection successful.'
                }
        except Exception as e:
            db_status = {
                'available': False,
                'message': f'Database error: {str(e)}'
            }
        
        # Check local storage for portfolios
        portfolio_storage_status = {
            'available': os.path.exists(PORTFOLIOS_DIR),
            'message': f"Portfolio storage {'available' if os.path.exists(PORTFOLIOS_DIR) else 'not initialized'}"
        }
        
        # Check opportunities file
        opportunities_status = {
            'available': os.path.exists(OPPORTUNITIES_FILE),
            'message': f"Opportunities data {'available' if os.path.exists(OPPORTUNITIES_FILE) else 'not found'}"
        }
        
        # Check OpenAI API status using our dedicated function
        openai_status = {
            'available': False,
            'message': 'OpenAI API not configured.'
        }
        
        try:
            # Import the check_openai_availability function
            from application_autofill import check_openai_availability, OPENAI_AVAILABLE
            
            # Check if API is available
            is_available = check_openai_availability()
            
            if is_available:
                openai_status = {
                    'available': True,
                    'message': 'OpenAI API connection successful.'
                }
            else:
                if not os.environ.get("OPENAI_API_KEY"):
                    openai_status = {
                        'available': False,
                        'message': 'OpenAI API key not provided.'
                    }
                else:
                    openai_status = {
                        'available': False,
                        'message': 'OpenAI API not available. Check quota or connectivity.'
                    }
        except Exception as e:
            openai_status = {
                'available': False,
                'message': f'OpenAI API check error: {str(e)}'
            }
        
        return jsonify({
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'services': {
                'google_drive': drive_status,
                'database': db_status,
                'portfolio_storage': portfolio_storage_status,
                'opportunities': opportunities_status,
                'openai': openai_status
            }
        })
    
    except Exception as e:
        logger.error(f"Error in services_status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Workspace API Endpoints
@api_bp.route('/workspaces', methods=['GET'])
@login_required
def get_workspaces():
    """Get all workspaces for the current user"""
    try:
        # Get workspaces where user is a member or creator
        user_memberships = WorkspaceMember.query.filter_by(user_id=current_user.id).all()
        member_workspace_ids = [membership.workspace_id for membership in user_memberships]
        
        # Also include workspaces created by the user
        user_workspaces = Workspace.query.filter(
            or_(
                Workspace.id.in_(member_workspace_ids),
                Workspace.creator_id == current_user.id
            )
        ).all()
        
        # Format workspace data
        workspaces_data = []
        for workspace in user_workspaces:
            # Get membership for this user
            membership = WorkspaceMember.query.filter_by(
                workspace_id=workspace.id, 
                user_id=current_user.id
            ).first()
            
            role = membership.role if membership else 'owner'
            
            # Get project count
            project_count = Project.query.filter_by(workspace_id=workspace.id).count()
            
            # Get member count
            member_count = WorkspaceMember.query.filter_by(workspace_id=workspace.id).count() + 1  # +1 for owner
            
            workspaces_data.append({
                'id': workspace.id,
                'name': workspace.name,
                'description': workspace.description,
                'status': workspace.status,
                'created_at': workspace.created_at.isoformat(),
                'role': role,
                'project_count': project_count,
                'member_count': member_count,
                'is_owner': workspace.creator_id == current_user.id
            })
        
        return jsonify({
            'success': True,
            'workspaces': workspaces_data
        })
        
    except Exception as e:
        logger.error(f"Error in get_workspaces: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/workspaces', methods=['POST'])
@login_required
def create_workspace():
    """Create a new workspace"""
    try:
        data = request.json
        
        if not data or 'name' not in data:
            return jsonify({
                'success': False,
                'error': 'Workspace name is required'
            }), 400
        
        # Create new workspace
        workspace = Workspace(
            name=data['name'],
            description=data.get('description', ''),
            creator_id=current_user.id
        )
        
        db.session.add(workspace)
        db.session.commit()
        
        # Return the created workspace
        return jsonify({
            'success': True,
            'workspace': {
                'id': workspace.id,
                'name': workspace.name,
                'description': workspace.description,
                'status': workspace.status,
                'created_at': workspace.created_at.isoformat(),
                'is_owner': True
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in create_workspace: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/workspaces/<int:workspace_id>', methods=['GET'])
@login_required
def get_workspace(workspace_id):
    """Get details of a specific workspace"""
    try:
        # Check if user has access to the workspace
        workspace = Workspace.query.get(workspace_id)
        if not workspace:
            return jsonify({
                'success': False,
                'error': 'Workspace not found'
            }), 404
        
        # Check if user is a member or creator
        is_member = WorkspaceMember.query.filter_by(
            workspace_id=workspace_id, 
            user_id=current_user.id
        ).first() is not None
        
        is_creator = workspace.creator_id == current_user.id
        
        if not (is_member or is_creator):
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        # Get projects for this workspace
        projects = Project.query.filter_by(workspace_id=workspace_id).all()
        projects_data = []
        
        for project in projects:
            # Get task counts by status
            task_count = Task.query.filter_by(project_id=project.id).count()
            completed_tasks = Task.query.filter_by(project_id=project.id, status='completed').count()
            
            projects_data.append({
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'status': project.status,
                'created_at': project.created_at.isoformat(),
                'deadline': project.deadline.isoformat() if project.deadline else None,
                'task_count': task_count,
                'completed_tasks': completed_tasks
            })
        
        # Get members of this workspace
        members = WorkspaceMember.query.filter_by(workspace_id=workspace_id).all()
        members_data = []
        
        for member in members:
            user = User.query.get(member.user_id)
            if user:
                members_data.append({
                    'id': user.id,
                    'name': user.name,
                    'email': user.email,
                    'role': member.role,
                    'joined_at': member.joined_at.isoformat()
                })
        
        # Add the creator as a member
        creator = User.query.get(workspace.creator_id)
        members_data.append({
            'id': creator.id,
            'name': creator.name,
            'email': creator.email,
            'role': 'owner',
            'joined_at': workspace.created_at.isoformat()
        })
        
        # Get recent messages
        messages = Message.query.filter_by(workspace_id=workspace_id).order_by(Message.created_at.desc()).limit(10).all()
        messages_data = []
        
        for message in messages:
            sender = User.query.get(message.sender_id)
            messages_data.append({
                'id': message.id,
                'content': message.content,
                'created_at': message.created_at.isoformat(),
                'sender': {
                    'id': sender.id,
                    'name': sender.name
                }
            })
        
        # Return workspace details
        return jsonify({
            'success': True,
            'workspace': {
                'id': workspace.id,
                'name': workspace.name,
                'description': workspace.description,
                'status': workspace.status,
                'created_at': workspace.created_at.isoformat(),
                'is_owner': is_creator,
                'projects': projects_data,
                'members': members_data,
                'recent_messages': messages_data
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get_workspace: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/workspaces/<int:workspace_id>/projects', methods=['POST'])
@login_required
def create_project(workspace_id):
    """Create a new project in a workspace"""
    try:
        # Check if user has access to the workspace
        workspace = Workspace.query.get(workspace_id)
        if not workspace:
            return jsonify({
                'success': False,
                'error': 'Workspace not found'
            }), 404
        
        # Check if user is a member or creator with edit rights
        member = WorkspaceMember.query.filter_by(
            workspace_id=workspace_id, 
            user_id=current_user.id
        ).first()
        
        is_creator = workspace.creator_id == current_user.id
        has_edit_rights = is_creator or (member and member.role in ['admin', 'editor'])
        
        if not has_edit_rights:
            return jsonify({
                'success': False,
                'error': 'You do not have permission to create projects in this workspace'
            }), 403
        
        # Get project data
        data = request.json
        if not data or 'name' not in data:
            return jsonify({
                'success': False,
                'error': 'Project name is required'
            }), 400
        
        # Parse deadline if provided
        deadline = None
        if 'deadline' in data and data['deadline']:
            try:
                deadline = datetime.fromisoformat(data['deadline'])
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid deadline format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'
                }), 400
        
        # Create the project
        project = Project(
            workspace_id=workspace_id,
            name=data['name'],
            description=data.get('description', ''),
            status=data.get('status', 'in_progress'),
            deadline=deadline
        )
        
        db.session.add(project)
        db.session.commit()
        
        # Return the created project
        return jsonify({
            'success': True,
            'project': {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'status': project.status,
                'created_at': project.created_at.isoformat(),
                'deadline': project.deadline.isoformat() if project.deadline else None
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in create_project: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/projects/<int:project_id>/tasks', methods=['POST'])
@login_required
def create_task(project_id):
    """Create a new task in a project"""
    try:
        # Check if project exists
        project = Project.query.get(project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': 'Project not found'
            }), 404
        
        # Check if user has access to the workspace
        workspace = Workspace.query.get(project.workspace_id)
        if not workspace:
            return jsonify({
                'success': False,
                'error': 'Workspace not found'
            }), 404
        
        # Check if user is a member or creator with edit rights
        member = WorkspaceMember.query.filter_by(
            workspace_id=workspace.id, 
            user_id=current_user.id
        ).first()
        
        is_creator = workspace.creator_id == current_user.id
        has_edit_rights = is_creator or (member and member.role in ['admin', 'editor'])
        
        if not has_edit_rights:
            return jsonify({
                'success': False,
                'error': 'You do not have permission to create tasks in this project'
            }), 403
        
        # Get task data
        data = request.json
        if not data or 'title' not in data:
            return jsonify({
                'success': False,
                'error': 'Task title is required'
            }), 400
        
        # Parse due date if provided
        due_date = None
        if 'due_date' in data and data['due_date']:
            try:
                due_date = datetime.fromisoformat(data['due_date'])
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid due date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'
                }), 400
        
        # Create the task
        task = Task(
            project_id=project_id,
            title=data['title'],
            description=data.get('description', ''),
            status=data.get('status', 'to_do'),
            priority=data.get('priority', 'medium'),
            assigned_to_id=data.get('assigned_to'),
            assigned_by_id=current_user.id,
            due_date=due_date
        )
        
        db.session.add(task)
        db.session.commit()
        
        # Get assigned user info if applicable
        assigned_to = None
        if task.assigned_to_id:
            user = User.query.get(task.assigned_to_id)
            if user:
                assigned_to = {
                    'id': user.id,
                    'name': user.name,
                    'email': user.email
                }
        
        # Return the created task
        return jsonify({
            'success': True,
            'task': {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'created_at': task.created_at.isoformat(),
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'assigned_to': assigned_to
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in create_task: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/workspaces/<int:workspace_id>/members', methods=['POST'])
@login_required
def add_workspace_member(workspace_id):
    """Add a new member to a workspace"""
    try:
        # Check if workspace exists
        workspace = Workspace.query.get(workspace_id)
        if not workspace:
            return jsonify({
                'success': False,
                'error': 'Workspace not found'
            }), 404
        
        # Check if user is the workspace creator or an admin
        is_creator = workspace.creator_id == current_user.id
        member = WorkspaceMember.query.filter_by(
            workspace_id=workspace_id, 
            user_id=current_user.id,
            role='admin'
        ).first()
        
        if not (is_creator or member):
            return jsonify({
                'success': False,
                'error': 'Only workspace creator or admins can add members'
            }), 403
        
        # Get member data
        data = request.json
        if not data or 'email' not in data:
            return jsonify({
                'success': False,
                'error': 'Member email is required'
            }), 400
        
        # Find user by email
        user = User.query.filter_by(email=data['email']).first()
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Check if user is already a member
        existing_member = WorkspaceMember.query.filter_by(
            workspace_id=workspace_id,
            user_id=user.id
        ).first()
        
        if existing_member:
            return jsonify({
                'success': False,
                'error': 'User is already a member of this workspace'
            }), 400
        
        # Add member to workspace
        role = data.get('role', 'viewer')
        if role not in ['admin', 'editor', 'viewer']:
            role = 'viewer'  # Default to viewer if invalid role
            
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user.id,
            role=role
        )
        
        db.session.add(member)
        db.session.commit()
        
        # Return the added member
        return jsonify({
            'success': True,
            'member': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'role': member.role,
                'joined_at': member.joined_at.isoformat()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in add_workspace_member: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/workspaces/<int:workspace_id>/messages', methods=['POST'])
@login_required
def send_message(workspace_id):
    """Send a message in a workspace"""
    try:
        # Check if workspace exists
        workspace = Workspace.query.get(workspace_id)
        if not workspace:
            return jsonify({
                'success': False,
                'error': 'Workspace not found'
            }), 404
        
        # Check if user is a member or creator
        member = WorkspaceMember.query.filter_by(
            workspace_id=workspace_id, 
            user_id=current_user.id
        ).first()
        
        is_creator = workspace.creator_id == current_user.id
        
        if not (member or is_creator):
            return jsonify({
                'success': False,
                'error': 'You are not a member of this workspace'
            }), 403
        
        # Get message data
        data = request.json
        if not data or 'content' not in data or not data['content'].strip():
            return jsonify({
                'success': False,
                'error': 'Message content is required'
            }), 400
        
        # Create the message
        message = Message(
            workspace_id=workspace_id,
            sender_id=current_user.id,
            content=data['content'].strip()
        )
        
        db.session.add(message)
        db.session.commit()
        
        # Return the created message
        return jsonify({
            'success': True,
            'message': {
                'id': message.id,
                'content': message.content,
                'created_at': message.created_at.isoformat(),
                'sender': {
                    'id': current_user.id,
                    'name': current_user.name
                }
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in send_message: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Project and Task API Endpoints
@api_bp.route('/projects/<int:project_id>', methods=['GET'])
@login_required
def get_project(project_id):
    """Get details of a specific project"""
    try:
        # Check if project exists
        project = Project.query.get(project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': 'Project not found'
            }), 404
        
        # Check if user has access to the workspace
        workspace = Workspace.query.get(project.workspace_id)
        if not workspace:
            return jsonify({
                'success': False,
                'error': 'Workspace not found'
            }), 404
        
        # Check if user is a member or creator
        is_member = WorkspaceMember.query.filter_by(
            workspace_id=workspace.id, 
            user_id=current_user.id
        ).first() is not None
        
        is_creator = workspace.creator_id == current_user.id
        
        if not (is_member or is_creator):
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        # Return project details
        return jsonify({
            'success': True,
            'project': {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'status': project.status,
                'created_at': project.created_at.isoformat(),
                'deadline': project.deadline.isoformat() if project.deadline else None
            },
            'workspace_name': workspace.name
        })
        
    except Exception as e:
        logger.error(f"Error in get_project: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/projects/<int:project_id>/tasks', methods=['GET'])
@login_required
def get_tasks(project_id):
    """Get all tasks for a project"""
    try:
        # Check if project exists
        project = Project.query.get(project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': 'Project not found'
            }), 404
        
        # Check if user has access to the workspace
        workspace = Workspace.query.get(project.workspace_id)
        if not workspace:
            return jsonify({
                'success': False,
                'error': 'Workspace not found'
            }), 404
        
        # Check if user is a member or creator
        is_member = WorkspaceMember.query.filter_by(
            workspace_id=workspace.id, 
            user_id=current_user.id
        ).first() is not None
        
        is_creator = workspace.creator_id == current_user.id
        
        if not (is_member or is_creator):
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        # Get all tasks for this project
        tasks = Task.query.filter_by(project_id=project_id).all()
        tasks_data = []
        
        for task in tasks:
            # Get assigned user info if applicable
            assigned_to = None
            if task.assigned_to_id:
                user = User.query.get(task.assigned_to_id)
                if user:
                    assigned_to = {
                        'id': user.id,
                        'name': user.name,
                        'email': user.email
                    }
            
            # Get assigned by user info
            assigned_by = None
            if task.assigned_by_id:
                user = User.query.get(task.assigned_by_id)
                if user:
                    assigned_by = {
                        'id': user.id,
                        'name': user.name
                    }
            
            tasks_data.append({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat(),
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'assigned_to': assigned_to,
                'assigned_by': assigned_by
            })
        
        # Return tasks
        return jsonify({
            'success': True,
            'tasks': tasks_data
        })
        
    except Exception as e:
        logger.error(f"Error in get_tasks: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/tasks/<int:task_id>/status', methods=['PUT'])
@login_required
def update_task_status(task_id):
    """Update the status of a task"""
    try:
        # Check if task exists
        task = Task.query.get(task_id)
        if not task:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
        
        # Check if user has access to the project
        project = Project.query.get(task.project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': 'Project not found'
            }), 404
        
        # Check if user has access to the workspace
        workspace = Workspace.query.get(project.workspace_id)
        if not workspace:
            return jsonify({
                'success': False,
                'error': 'Workspace not found'
            }), 404
        
        # Check if user is a member or creator with edit rights
        member = WorkspaceMember.query.filter_by(
            workspace_id=workspace.id, 
            user_id=current_user.id
        ).first()
        
        is_creator = workspace.creator_id == current_user.id
        has_edit_rights = is_creator or (member and member.role in ['admin', 'editor'])
        is_assigned = task.assigned_to_id == current_user.id
        
        if not (has_edit_rights or is_assigned):
            return jsonify({
                'success': False,
                'error': 'You do not have permission to update this task'
            }), 403
        
        # Get status data
        data = request.json
        if not data or 'status' not in data:
            return jsonify({
                'success': False,
                'error': 'Status is required'
            }), 400
        
        # Validate status
        valid_statuses = ['to_do', 'in_progress', 'review', 'completed']
        if data['status'] not in valid_statuses:
            return jsonify({
                'success': False,
                'error': f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }), 400
        
        # Update the task status
        old_status = task.status
        task.status = data['status']
        
        # If status is completed, set completed_at
        if data['status'] == 'completed' and old_status != 'completed':
            task.completed_at = datetime.utcnow()
        # If status is changed from completed, clear completed_at
        elif data['status'] != 'completed' and old_status == 'completed':
            task.completed_at = None
        
        db.session.commit()
        
        # Return success
        return jsonify({
            'success': True,
            'task': {
                'id': task.id,
                'status': task.status
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in update_task_status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/tasks/<int:task_id>/comments', methods=['GET'])
@login_required
def get_task_comments(task_id):
    """Get comments for a task"""
    try:
        # Check if task exists
        task = Task.query.get(task_id)
        if not task:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
        
        # Check if user has access to the project
        project = Project.query.get(task.project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': 'Project not found'
            }), 404
        
        # Check if user has access to the workspace
        workspace = Workspace.query.get(project.workspace_id)
        if not workspace:
            return jsonify({
                'success': False,
                'error': 'Workspace not found'
            }), 404
        
        # Check if user is a member or creator
        is_member = WorkspaceMember.query.filter_by(
            workspace_id=workspace.id, 
            user_id=current_user.id
        ).first() is not None
        
        is_creator = workspace.creator_id == current_user.id
        
        if not (is_member or is_creator):
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        # Get comments for this task
        comments = TaskComment.query.filter_by(task_id=task_id).all()
        comments_data = []
        
        for comment in comments:
            user = User.query.get(comment.user_id)
            if user:
                comments_data.append({
                    'id': comment.id,
                    'content': comment.content,
                    'created_at': comment.created_at.isoformat(),
                    'user': {
                        'id': user.id,
                        'name': user.name
                    }
                })
        
        # Return comments
        return jsonify({
            'success': True,
            'comments': comments_data
        })
        
    except Exception as e:
        logger.error(f"Error in get_task_comments: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/tasks/<int:task_id>/comments', methods=['POST'])
@login_required
def add_task_comment(task_id):
    """Add a comment to a task"""
    try:
        # Check if task exists
        task = Task.query.get(task_id)
        if not task:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
        
        # Check if user has access to the project
        project = Project.query.get(task.project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': 'Project not found'
            }), 404
        
        # Check if user has access to the workspace
        workspace = Workspace.query.get(project.workspace_id)
        if not workspace:
            return jsonify({
                'success': False,
                'error': 'Workspace not found'
            }), 404
        
        # Check if user is a member or creator
        is_member = WorkspaceMember.query.filter_by(
            workspace_id=workspace.id, 
            user_id=current_user.id
        ).first() is not None
        
        is_creator = workspace.creator_id == current_user.id
        
        if not (is_member or is_creator):
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        # Get comment data
        data = request.json
        if not data or 'content' not in data or not data['content'].strip():
            return jsonify({
                'success': False,
                'error': 'Comment content is required'
            }), 400
        
        # Create the comment
        comment = TaskComment(
            task_id=task_id,
            user_id=current_user.id,
            content=data['content'].strip()
        )
        
        db.session.add(comment)
        db.session.commit()
        
        # Return the created comment
        return jsonify({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'created_at': comment.created_at.isoformat(),
                'user': {
                    'id': current_user.id,
                    'name': current_user.name
                }
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in add_task_comment: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# File Sharing API Endpoints
@api_bp.route('/projects/<int:project_id>/files', methods=['GET'])
@login_required
def get_project_files(project_id):
    """Get all files for a project"""
    try:
        # Check if project exists
        project = Project.query.get(project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': 'Project not found'
            }), 404
        
        # Check if user has access to the workspace
        workspace = Workspace.query.get(project.workspace_id)
        if not workspace:
            return jsonify({
                'success': False,
                'error': 'Workspace not found'
            }), 404
        
        # Check if user is a member or creator
        is_member = WorkspaceMember.query.filter_by(
            workspace_id=workspace.id, 
            user_id=current_user.id
        ).first() is not None
        
        is_creator = workspace.creator_id == current_user.id
        
        if not (is_member or is_creator):
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        # Get all files for this project
        files = ProjectFile.query.filter_by(project_id=project_id).all()
        files_data = []
        
        for file in files:
            uploader = User.query.get(file.user_id)
            
            files_data.append({
                'id': file.id,
                'filename': file.filename,
                'file_path': file.file_path,
                'file_type': file.file_type,
                'file_size': file.file_size,
                'description': file.description,
                'uploaded_at': file.uploaded_at.isoformat(),
                'folder_id': file.folder_id,
                'uploader': {
                    'id': uploader.id,
                    'name': uploader.name
                } if uploader else None
            })
        
        # Get custom folders for this project (implementation would vary)
        folders = []  # This would typically come from a Folder model
        
        return jsonify({
            'success': True,
            'files': files_data,
            'folders': folders
        })
        
    except Exception as e:
        logger.error(f"Error in get_project_files: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/files/upload', methods=['POST'])
@login_required
def upload_files():
    """Upload files to a project"""
    try:
        # Check if project ID was provided
        project_id = request.form.get('project_id')
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'Project ID is required'
            }), 400
        
        # Check if project exists
        project = Project.query.get(project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': 'Project not found'
            }), 404
        
        # Check if user has access to the workspace
        workspace = Workspace.query.get(project.workspace_id)
        if not workspace:
            return jsonify({
                'success': False,
                'error': 'Workspace not found'
            }), 404
        
        # Check if user is a member or creator with edit rights
        member = WorkspaceMember.query.filter_by(
            workspace_id=workspace.id, 
            user_id=current_user.id
        ).first()
        
        is_creator = workspace.creator_id == current_user.id
        has_edit_rights = is_creator or (member and member.role in ['admin', 'editor'])
        
        if not has_edit_rights:
            return jsonify({
                'success': False,
                'error': 'You do not have permission to upload files to this project'
            }), 403
        
        # Get folder ID and description
        folder_id = request.form.get('folder_id', 'all')
        description = request.form.get('description', '')
        
        # Check if files were uploaded
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No files were uploaded'
            }), 400
        
        files = request.files.getlist('files')
        if len(files) == 0:
            return jsonify({
                'success': False,
                'error': 'No files were uploaded'
            }), 400
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join('static', 'uploads', 'projects', str(project_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        # Upload files
        uploaded_files = []
        
        for file in files:
            if file.filename == '':
                continue
            
            # Generate a secure filename to avoid path traversal
            filename = secure_filename(file.filename)
            
            # Generate a unique filename to avoid collisions
            unique_filename = f"{int(time.time())}_{filename}"
            
            # Save the file
            file_path = os.path.join(upload_dir, unique_filename)
            file.save(file_path)
            
            # Determine file type
            file_type = file.content_type
            
            # Determine file size
            file_size = os.path.getsize(file_path)
            
            # Create database record
            project_file = ProjectFile(
                project_id=project_id,
                user_id=current_user.id,
                filename=filename,
                file_path=os.path.join('/static', 'uploads', 'projects', str(project_id), unique_filename),
                file_type=file_type,
                file_size=file_size,
                description=description,
                folder_id=folder_id
            )
            
            db.session.add(project_file)
            db.session.commit()
            
            # Add to uploaded files list
            uploaded_files.append({
                'id': project_file.id,
                'filename': project_file.filename,
                'file_path': project_file.file_path,
                'file_type': project_file.file_type,
                'file_size': project_file.file_size,
                'description': project_file.description,
                'uploaded_at': project_file.uploaded_at.isoformat(),
                'folder_id': project_file.folder_id,
                'uploader': {
                    'id': current_user.id,
                    'name': current_user.name
                }
            })
        
        return jsonify({
            'success': True,
            'files': uploaded_files
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in upload_files: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/files/<int:file_id>', methods=['DELETE'])
@login_required
def delete_file(file_id):
    """Delete a file"""
    try:
        # Check if file exists
        file = ProjectFile.query.get(file_id)
        if not file:
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
        
        # Check if user has access to the project
        project = Project.query.get(file.project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': 'Project not found'
            }), 404
        
        # Check if user has access to the workspace
        workspace = Workspace.query.get(project.workspace_id)
        if not workspace:
            return jsonify({
                'success': False,
                'error': 'Workspace not found'
            }), 404
        
        # Check if user is a member or creator with edit rights or file uploader
        member = WorkspaceMember.query.filter_by(
            workspace_id=workspace.id, 
            user_id=current_user.id
        ).first()
        
        is_creator = workspace.creator_id == current_user.id
        is_uploader = file.user_id == current_user.id
        has_edit_rights = is_creator or (member and member.role in ['admin', 'editor']) or is_uploader
        
        if not has_edit_rights:
            return jsonify({
                'success': False,
                'error': 'You do not have permission to delete this file'
            }), 403
        
        # Delete file from filesystem
        if file.file_path and os.path.exists(os.path.join('.', file.file_path.lstrip('/'))):
            os.remove(os.path.join('.', file.file_path.lstrip('/')))
        
        # Delete database record
        db.session.delete(file)
        db.session.commit()
        
        return jsonify({
            'success': True
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in delete_file: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/folders', methods=['POST'])
@login_required
def create_folder():
    """Create a new folder for project files"""
    try:
        # Get folder data
        data = request.json
        if not data or 'name' not in data or not data['name'].strip():
            return jsonify({
                'success': False,
                'error': 'Folder name is required'
            }), 400
        
        if 'project_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Project ID is required'
            }), 400
        
        # Check if project exists
        project = Project.query.get(data['project_id'])
        if not project:
            return jsonify({
                'success': False,
                'error': 'Project not found'
            }), 404
        
        # Check if user has access to the workspace
        workspace = Workspace.query.get(project.workspace_id)
        if not workspace:
            return jsonify({
                'success': False,
                'error': 'Workspace not found'
            }), 404
        
        # Check if user is a member or creator with edit rights
        member = WorkspaceMember.query.filter_by(
            workspace_id=workspace.id, 
            user_id=current_user.id
        ).first()
        
        is_creator = workspace.creator_id == current_user.id
        has_edit_rights = is_creator or (member and member.role in ['admin', 'editor'])
        
        if not has_edit_rights:
            return jsonify({
                'success': False,
                'error': 'You do not have permission to create folders in this project'
            }), 403
        
        # Create folder (implementation would vary)
        # For simplicity, we'll return a mock folder object
        # In a real app, you would have a Folder model
        folder = {
            'id': str(int(time.time())),  # Generate a timestamp-based ID
            'name': data['name'].strip(),
            'project_id': data['project_id'],
            'created_at': datetime.utcnow().isoformat(),
            'created_by': current_user.id
        }
        
        return jsonify({
            'success': True,
            'folder': folder
        })
        
    except Exception as e:
        logger.error(f"Error in create_folder: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def create_app():
    """
    Create and configure the Flask application
    """
    app = Flask(__name__)
    
    # Configure the SQLAlchemy database (using the same instance from main.py)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Configure JWT with proper token expiration
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", str(uuid.uuid4()))
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=15)  # Shorter-lived access tokens for security
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)    # Long-lived refresh tokens for convenience
    app.config["JWT_BLACKLIST_ENABLED"] = True  # Enable token blacklisting
    app.config["JWT_BLACKLIST_TOKEN_CHECKS"] = ["access", "refresh"]  # Check both token types
    # JWT will be initialized after app creation
    
    # Configure Redis caching
    if os.environ.get('REDIS_URL'):
        redis_url = os.environ.get('REDIS_URL')
        # Check if the URL has the required scheme prefix
        if not redis_url.startswith(('redis://', 'rediss://', 'unix://')):
            # Add the redis:// prefix if missing
            redis_url = f"redis://{redis_url}"
            
        app.config['CACHE_TYPE'] = 'RedisCache'
        app.config['CACHE_REDIS_URL'] = redis_url
        app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # Default timeout in seconds (5 minutes)
        app.logger.info(f"Using Redis caching with URL: {redis_url}")
    else:
        app.config['CACHE_TYPE'] = 'SimpleCache'
        app.config['CACHE_DEFAULT_TIMEOUT'] = 300
        app.logger.info("Redis URL not found, using in-memory SimpleCache instead")
    
    # Configure rate limiting
    # Rate limits can be adjusted based on API usage patterns and requirements
    
    # Rate limiting configuration - use memory storage for simplicity and reliability
    # This avoids Redis authentication issues in development
    app.logger.info("Using memory storage for rate limiting for reliability")
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",
        strategy="fixed-window"
    )
    
    # Register rate limiting for specific endpoints
    @app.before_request
    def before_request():
        # Store the limiter in g for access in route functions
        g.limiter = limiter
        
    # Log all requests for monitoring and debugging
    @app.after_request
    def log_request(response):
        # Skip logging for assets
        if not request.path.startswith('/static/'):
            logger.info(f"{request.remote_addr} - {request.method} {request.path} - {response.status_code}")
        return response
    
    # Configure CORS to allow requests from Proletto domains
    # First, check if CORS_ALLOWED_ORIGINS is set in environment variables
    if os.environ.get('CORS_ALLOWED_ORIGINS'):
        # Parse comma-separated list of origins
        cors_origins = os.environ.get('CORS_ALLOWED_ORIGINS').split(',')
        app.logger.info(f"Using CORS origins from environment: {cors_origins}")
    else:
        # Default origins if not set in environment
        cors_origins = [
            'https://www.myproletto.com',
            'https://app.myproletto.com',
            'https://dashboard.myproletto.com',
            'https://digest.myproletto.com',
        ]
        app.logger.info(f"Using default CORS origins: {cors_origins}")
    
    # Add development domains when in development environment
    if os.environ.get('FLASK_ENV') == 'development' or os.environ.get('REPLIT_DEV_DOMAIN'):
        dev_origins = [
            'http://localhost:3000',
            'http://localhost:5000',
        ]
        
        # Add the Replit dev domain if available
        if os.environ.get('REPLIT_DEV_DOMAIN'):
            dev_origins.append(f"https://{os.environ.get('REPLIT_DEV_DOMAIN')}")
        
        cors_origins.extend(dev_origins)
        app.logger.info(f"Added development CORS origins: {dev_origins}")
    
    CORS(app, 
         resources={r"/*": {
             "origins": cors_origins,
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"],
             "supports_credentials": True
         }})
    
    # Register the API and auth blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(art_bp, url_prefix="/api")
    
    # Create API cache health endpoint
    from flask import Blueprint, jsonify
    api_cache_bp = Blueprint('api_cache_health', __name__, url_prefix='/api/cache-utils')
    
    @api_cache_bp.route('/health')
    def api_cache_health():
        """Report cache health status for the API layer"""
        if not hasattr(app, 'cache_backend'):
            return jsonify({
                'backend': 'unknown',
                'status': 'not_initialized',
                'message': 'Cache system not properly initialized'
            }), 500
            
        backend = app.cache_backend
        data = {'backend': backend['type']}
        
        if backend['type'] == 'redis':
            try:
                info = backend['client'].info()
                # Extract useful Redis stats
                data.update({
                    'status': 'connected',
                    'uptime_in_seconds': info.get('uptime_in_seconds'),
                    'used_memory_human': info.get('used_memory_human'),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0),
                    'connected_clients': info.get('connected_clients')
                })
                
                # Calculate hit rate if available
                hits = info.get('keyspace_hits', 0)
                misses = info.get('keyspace_misses', 0)
                total = hits + misses
                if total > 0:
                    data['hit_rate'] = round((hits / total) * 100, 2)
                    
            except Exception as e:
                data.update({
                    'status': 'error',
                    'error': str(e)
                })
        else:
            # SimpleCache info
            data.update({
                'status': 'fallback',
                'message': 'Using in-memory SimpleCache as fallback',
                'error': backend.get('error')
            })
            
        return jsonify(data)
    
    # Register the API cache health blueprint
    app.register_blueprint(api_cache_bp)
    logger.info("API Cache Health blueprint registered successfully")
    
    # Register recommendation blueprint if available
    if recommendation_routes_available:
        app.register_blueprint(recommendation_bp)
        logger.info("Recommendation routes registered successfully")
    
    # Initialize cache with enhanced utilities
    try:
        # Import the enhanced cache utilities
        from cache_utils import init_cache, cache_health_bp, register_cache_extensions, get_cached_data
        
        # Initialize cache with app using our improved utilities
        cache_instance = register_cache_extensions(app)
        
        # Register public API v2 blueprint
        from public_api_new import public_api, limiter
        
        # Set the cache object for public_api_new
        import sys
        # Create a module-level variable to store the cache instance
        sys.modules['public_api_new'].cache = cache_instance
        
        # Log success
        logger.info(f"Cache initialized for API: {app.cache_backend['type']}")
    except Exception as e:
        # Fallback to basic cache if there's an issue with the enhanced utilities
        from flask_caching import Cache
        logger.warning(f"Enhanced cache utilities failed: {str(e)}. Using basic Cache.")
        
        # Make sure the Redis URL has the proper scheme
        redis_url = app.config.get('CACHE_REDIS_URL')
        if redis_url and not redis_url.startswith(('redis://', 'rediss://', 'unix://')):
            app.config['CACHE_REDIS_URL'] = f"redis://{redis_url}"
            logger.info(f"Updated Redis URL with redis:// scheme: {app.config['CACHE_REDIS_URL']}")
        
        # Initialize basic cache with app
        cache_instance = Cache(app)
        
        # Register public API v2 blueprint
        from public_api_new import public_api, limiter
        
        # Set the cache object for public_api_new
        import sys
        # Create a module-level variable to store the cache instance
        sys.modules['public_api_new'].cache = cache_instance
        
        app.register_blueprint(public_api)
        # Initialize the limiter with the app
        limiter.init_app(app)
        logger.info("Public API v2 blueprint registered successfully")
        logger.info("API rate limiter initialized successfully")
    except Exception as e:
        logger.error(f"Failed to register Public API v2 blueprint: {e}")
    
    # Register Swagger documentation
    try:
        from swagger import init_app as init_swagger
        init_swagger(app)
        logger.info("Swagger documentation registered successfully")
    except Exception as e:
        logger.error(f"Failed to register Swagger documentation: {e}")
    
    # Register alternative routes for portfolio endpoints (both /api/portfolio/... and /portfolio/...)
    try:
        from portfolio_routes import register_portfolio_alt_routes
        register_portfolio_alt_routes(app)
        logger.info("Registered alternative portfolio routes")
    except Exception as e:
        logger.error(f"Failed to register alternative portfolio routes: {e}")
    
    # Root route for health check
    @app.route('/')
    def index():
        return jsonify({
            'service': 'Proletto API',
            'status': 'healthy',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    # Test endpoint for rate limiting
    @app.route('/api/rate-limit-test')
    @limiter.limit("5 per minute")
    def rate_limit_test():
        """Test endpoint for rate limiting"""
        # Check if we're using Redis or memory storage
        storage_type = "Redis" if "redis" in os.environ.get('REDIS_URL', "memory://").lower() else "Memory"
        
        return jsonify({
            'message': 'Rate limit test endpoint',
            'rate_limit': '5 per minute',
            'storage_backend': storage_type,
            'client_ip': get_remote_address(),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    # Custom error handler for rate limit exceeded
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            "error": {
                "code": 429,
                "message": "Rate limit exceeded. Please try again later.",
                "retry_after": getattr(e, 'retry_after', None)
            },
            "api_version": "v2",
            "timestamp": datetime.utcnow().isoformat()
        }), 429
    
    return app

# Create the application for both direct execution and imports
app = create_app()

# Initialize the app with the same db instance from main app
with app.app_context():
    db.init_app(app)

# Initialize cache with enhanced utilities if not already initialized
if not hasattr(app, 'cache_backend'):
    try:
        # Import the enhanced cache utilities
        from cache_utils import init_cache, cache_health_bp, register_cache_extensions
        cache = register_cache_extensions(app)
        app.logger.info(f"Cache initialized for API (global): {app.cache_backend['type']}")
    except Exception as e:
        # Fallback to basic cache if there's an issue with the enhanced utilities
        from flask_caching import Cache
        app.logger.warning(f"Enhanced cache utilities failed: {str(e)}. Using basic Cache.")
        
        # Make sure the Redis URL has the proper scheme
        redis_url = app.config.get('CACHE_REDIS_URL')
        if redis_url and not redis_url.startswith(('redis://', 'rediss://', 'unix://')):
            app.config['CACHE_REDIS_URL'] = f"redis://{redis_url}"
            app.logger.info(f"Updated Redis URL with redis:// scheme: {app.config['CACHE_REDIS_URL']}")
        
        # Initialize basic cache with app
        cache = Cache(app)
else:
    cache = app._cache_instance if hasattr(app, '_cache_instance') else Cache(app)

# Initialize JWT for the app and set up error handlers
jwt = JWTManager(app)

# Initialize token_blocklist with the database
with app.app_context():
    token_blocklist.init_db(db)
    token_blocklist.define_token_blocklist()
    logger.info("Token blocklist system initialized")

# Configure JWT to check for token revocation
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    return token_blocklist.is_token_revoked(jwt_payload)

# JWT error handlers for better debugging
@jwt.invalid_token_loader
def invalid_token_callback(error_string):
    logger.error(f"Invalid JWT token: {error_string}")
    return jsonify({"success": False, "error": f"Invalid token: {error_string}"}), 401

@jwt.unauthorized_loader
def unauthorized_callback(error_string):
    logger.error(f"Unauthorized access: {error_string}")
    return jsonify({"success": False, "error": f"Missing token: {error_string}"}), 401

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    logger.error(f"Expired token with payload: {jwt_payload}")
    return jsonify({"success": False, "error": "Token has expired"}), 401

@jwt.user_identity_loader
def user_identity_lookup(user_id):
    # Convert user IDs to strings for JWT
    return str(user_id)

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    logger.info(f"Authenticated user ID: {identity}")
    with main_app.app_context():
        from models import User
        return User.query.get(identity)
    
# Create an application context that can be used by route handlers
app_context = app.app_context()
app_context.push()

# Initialize APScheduler for automated scraper jobs (only in production/Always-On environment)
def init_scheduler_if_production():
    """Initialize APScheduler if running in production environment"""
    # Check for Always-On flag (Replit-specific)
    is_production = os.environ.get('REPLIT_DEPLOYMENT') == 'true'
    
    if is_production:
        try:
            logger.info("Initializing APScheduler for Proletto scrapers in production environment")
            from ap_scheduler import init_scheduler
            
            # Initialize the scheduler
            result = init_scheduler()
            if result:
                logger.info("APScheduler successfully initialized and started")
            else:
                logger.warning("APScheduler initialization returned False (may already be running)")
                
            return result
        except Exception as e:
            logger.error(f"Error initializing APScheduler: {e}")
            return False
    else:
        logger.info("Skipping APScheduler initialization in development environment")
        return False

# Initialize Email Digest Scheduler for weekly digest emails (only in production/Always-On environment)
def init_digest_scheduler_if_production(app):
    """Initialize Email Digest Scheduler if running in production environment"""
    # Check for Always-On flag (Replit-specific)
    is_production = os.environ.get('REPLIT_DEPLOYMENT') == 'true'
    
    if is_production:
        try:
            logger.info("Initializing Email Digest Scheduler for weekly emails in production environment")
            from email_digest_scheduler import init_digest_scheduler
            
            # Initialize the digest scheduler with the app context
            result = init_digest_scheduler(app)
            if result:
                logger.info("Email Digest Scheduler successfully initialized and started")
            else:
                logger.warning("Email Digest Scheduler initialization returned False (may already be running)")
                
            return result
        except Exception as e:
            logger.error(f"Error initializing Email Digest Scheduler: {e}")
            return False
    else:
        logger.info("Skipping Email Digest Scheduler initialization in development environment")
        return False

# Scheduler API endpoints for managing jobs
@app.route('/admin/api/scheduler-status')
@jwt_required()
def scheduler_status():
    """
    Get the status of all scheduled jobs
    Only accessible to admin users
    """
    # Check if user is admin
    current_user = get_jwt_identity()
    with main_app.app_context():
        from models import User
        user = User.query.get(current_user)
        if not user or not user.is_admin:
            return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # Import on demand to avoid issues when scheduler is not available
        from ap_scheduler import get_scheduler_info
        status = get_scheduler_info()
        return jsonify(status)
    except ImportError:
        return jsonify({"error": "Scheduler module not available"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/api/scheduler/jobs/<job_id>/pause', methods=['POST'])
@jwt_required()
def pause_job(job_id):
    """
    Pause a scheduled job
    Only accessible to admin users
    """
    # Check if user is admin
    current_user = get_jwt_identity()
    with main_app.app_context():
        from models import User
        user = User.query.get(current_user)
        if not user or not user.is_admin:
            return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # Import on demand to avoid issues when scheduler is not available
        from ap_scheduler import scheduler
        if not scheduler:
            return jsonify({"error": "Scheduler not initialized"}), 500
        
        # Get the job
        job = scheduler.get_job(job_id)
        if not job:
            return jsonify({"error": f"Job {job_id} not found"}), 404
        
        # Pause the job
        scheduler.pause_job(job_id)
        return jsonify({"status": "success", "message": f"Job {job_id} paused"}), 200
    except ImportError:
        return jsonify({"error": "Scheduler module not available"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/api/scheduler/jobs/<job_id>/resume', methods=['POST'])
@jwt_required()
def resume_job(job_id):
    """
    Resume a paused job
    Only accessible to admin users
    """
    # Check if user is admin
    current_user = get_jwt_identity()
    with main_app.app_context():
        from models import User
        user = User.query.get(current_user)
        if not user or not user.is_admin:
            return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # Import on demand to avoid issues when scheduler is not available
        from ap_scheduler import scheduler
        if not scheduler:
            return jsonify({"error": "Scheduler not initialized"}), 500
        
        # Get the job
        job = scheduler.get_job(job_id)
        if not job:
            return jsonify({"error": f"Job {job_id} not found"}), 404
        
        # Resume the job
        scheduler.resume_job(job_id)
        return jsonify({"status": "success", "message": f"Job {job_id} resumed"}), 200
    except ImportError:
        return jsonify({"error": "Scheduler module not available"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/api/scheduler/jobs/<job_id>/run-now', methods=['POST'])
@jwt_required()
def run_job_now(job_id):
    """
    Run a job immediately
    Only accessible to admin users
    """
    # Check if user is admin
    current_user = get_jwt_identity()
    with main_app.app_context():
        from models import User
        user = User.query.get(current_user)
        if not user or not user.is_admin:
            return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # Import on demand to avoid issues when scheduler is not available
        from ap_scheduler import scheduler, run_scraper_job
        if not scheduler:
            return jsonify({"error": "Scheduler not initialized"}), 500
        
        # Get the job
        job = scheduler.get_job(job_id)
        if not job:
            return jsonify({"error": f"Job {job_id} not found"}), 404
        
        # Extract the engine name from the job_id (assuming format like premium_california)
        if '_' in job_id:
            engine_name = job_id.split('_', 1)[1]
            
            # Run the job immediately in a separate thread to not block API response
            import threading
            thread = threading.Thread(target=run_scraper_job, args=(engine_name,))
            thread.daemon = True
            thread.start()
            
            return jsonify({
                "status": "success", 
                "message": f"Job {job_id} scheduled for immediate execution",
                "engine": engine_name
            }), 200
        else:
            return jsonify({"error": f"Cannot determine engine name from job_id: {job_id}"}), 400
            
    except ImportError:
        return jsonify({"error": "Scheduler module not available"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/api/scheduler/run-all', methods=['POST'])
@jwt_required()
def run_all_jobs():
    """
    Run all scraper jobs immediately
    Only accessible to admin users
    """
    # Check if user is admin
    current_user = get_jwt_identity()
    with main_app.app_context():
        from models import User
        user = User.query.get(current_user)
        if not user or not user.is_admin:
            return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # Import on demand to avoid issues when scheduler is not available
        from ap_scheduler import run_all_scrapers
        
        # Run all scrapers immediately in a separate thread to not block API response
        import threading
        thread = threading.Thread(target=run_all_scrapers)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "success", 
            "message": "All jobs scheduled for immediate execution"
        }), 200
            
    except ImportError:
        return jsonify({"error": "Scheduler module not available"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Admin endpoints for Email Digest Scheduler
@app.route('/admin/api/digest-scheduler-status')
@jwt_required()
def digest_scheduler_status():
    """
    Get the status of the Email Digest Scheduler
    Only accessible to admin users
    """
    # Check if user is admin
    current_user = get_jwt_identity()
    with main_app.app_context():
        from models import User
        user = User.query.get(current_user)
        if not user or not user.is_admin:
            return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # Import on demand to avoid issues when scheduler is not available
        from email_digest_scheduler import get_digest_scheduler_info
        status = get_digest_scheduler_info()
        return jsonify(status)
    except ImportError:
        return jsonify({"error": "Email Digest Scheduler module not available"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/api/run-digest-now')
@jwt_required()
def run_digest_now_endpoint():
    """
    Manually run the weekly digest email job
    Only accessible to admin users
    """
    # Check if user is admin
    current_user = get_jwt_identity()
    with main_app.app_context():
        from models import User
        user = User.query.get(current_user)
        if not user or not user.is_admin:
            return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # Import on demand to avoid issues when scheduler is not available
        from email_digest_scheduler import run_digest_now
        success = run_digest_now()
        
        if success:
            return jsonify({"status": "success", "message": "Digest job scheduled for immediate execution"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to schedule digest job"}), 500
    except ImportError:
        return jsonify({"error": "Email Digest Scheduler module not available"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/api/test-digest-email/<int:user_id>')
@jwt_required()
def test_digest_email_endpoint(user_id):
    """
    Send a test digest email to a specific user
    Only accessible to admin users
    """
    # Check if user is admin
    current_user = get_jwt_identity()
    with main_app.app_context():
        from models import User
        user = User.query.get(current_user)
        if not user or not user.is_admin:
            return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # Import on demand to avoid issues when scheduler is not available
        from email_digest_scheduler import test_digest_email
        
        # Create session for the test
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import create_engine
        
        engine = create_engine(os.environ.get("DATABASE_URL"))
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Run the test
        success = test_digest_email(user_id, session)
        
        if success:
            return jsonify({
                "status": "success", 
                "message": f"Test digest email sent to user {user_id}"
            }), 200
        else:
            return jsonify({
                "status": "error", 
                "message": f"Failed to send test digest email to user {user_id}"
            }), 500
    except ImportError:
        return jsonify({"error": "Email Digest Scheduler module not available"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Initialize APScheduler after app context is created (only in production)
init_scheduler_if_production()

# Initialize Email Digest Scheduler after app context is created (only in production)
init_digest_scheduler_if_production(app)

def run_api():
    """Function to run the API application with proper environment configuration"""
    # Use deployment configuration to determine the correct port
    try:
        from deployment_config import get_port
        # For API backend, we use port 80 in deployment but a different port in development
        if os.environ.get("REPLIT_DEPLOYMENT") == "1":
            port = 80
        else:
            port = int(os.environ.get('API_PORT', 5001))
    except ImportError:
        # Fallback if the deployment_config module is not available
        if os.environ.get("REPLIT_DEPLOYMENT") == "1":
            port = 80
        else:
            port = int(os.environ.get('API_PORT', 5001))
    
    # Set debug mode only in development
    debug_mode = os.environ.get("FLASK_ENV") == "development" or os.environ.get("FLASK_DEBUG") == "1"
    
    # Always bind to all interfaces (0.0.0.0)
    print(f"\n🔍 API Flask app starting on port {port} with host 0.0.0.0")
    
    # Run the application
    app.run(host='0.0.0.0', port=port, debug=debug_mode)

# Run the application when executed directly
if __name__ == '__main__':
    # Initialize scheduler in dev mode if manually specified
    if os.environ.get('ENABLE_SCHEDULER') == 'true':
        logger.info("Manually enabling APScheduler in development environment")
        init_scheduler_if_production()
        
        # Also enable Email Digest Scheduler if specified
        logger.info("Manually enabling Email Digest Scheduler in development environment")
        init_digest_scheduler_if_production(app)
    
    # Run the API application
    run_api()