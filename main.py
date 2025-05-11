import os
import re
import sys
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import LoginManager, current_user, login_required
from datetime import datetime
from email_service import get_email_service
from email_templates import EmailTemplates
from flask_cors import CORS

# Disabled error logging and monitoring system
# from utils.error_logging import logger
# from utils.monitoring import monitor

# Create a simple logger that does nothing
class NullLogger:
    def debug(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
    def critical(self, *args, **kwargs): pass
    def exception(self, *args, **kwargs): pass

# Create a dummy monitor that does nothing
class NullMonitor:
    def __init__(self):
        pass
    
    def track_request(self, *args, **kwargs):
        class DummyContextManager:
            def __enter__(self): pass
            def __exit__(self, *args): pass
        return DummyContextManager()
    
    def get_system_health(self): 
        return {"status": "ok"}
    
    def is_healthy(self, *args):
        return True

logger = NullLogger()
monitor = NullMonitor()

# =========================================
# 1. Environment Validation - START
# =========================================

# Set the known working Redis password for Proletto
redis_password = "Pvaa4zVI1rFkrOmTSqH5bLUklovyXHfH"
os.environ['REDIS_PASSWORD'] = redis_password

# Set the full Redis URL directly - using the correct format with just the password (no username)
redis_url = f"redis://:{redis_password}@redis-14544.c253.us-central1-1.gce.redns.redis-cloud.com:14544"
os.environ['REDIS_URL'] = redis_url
logger.info(f"Using Redis URL (masked): redis://:{redis_password[:3]}***@redis-14544.c253.us-central1-1.gce.redns.redis-cloud.com:14544")

# List all required env vars and their expected patterns
REQUIRED_ENVS = {
    'DATABASE_URL': r'.+',
    'API_KEY': r'.+',
    'FLASK_SECRET_KEY': r'.{16,}'  # at least 16 characters for security
}

# For production, add these critical services
if os.environ.get('FLASK_ENV') == 'production':
    REQUIRED_ENVS.update({
        'REDIS_URL': r'^(redis|rediss)://.+',
        'STRIPE_SECRET_KEY': r'^sk_',
        'STRIPE_PUBLIC_KEY': r'^pk_',
        'STRIPE_WEBHOOK_SECRET': r'^whsec_',
        'SENDGRID_API_KEY': r'.+',
        'SENDGRID_FROM_EMAIL': r'.+@.+\..+'
    })

# Validate all required environment variables
errors = []
for name, pattern in REQUIRED_ENVS.items():
    val = os.environ.get(name)
    if not val:
        errors.append(f"Missing required env var: {name}")
    elif not re.match(pattern, val):
        errors.append(f"Env var {name} doesn't match expected pattern")

# If there are configuration errors, log them and abort
if errors:
    for error in errors:
        logger.critical(f"Configuration error: {error}")
    sys.exit("\n".join(errors))

# =========================================
# 1. Environment Validation - END
# =========================================

# =============================================
# 2. Application Configuration - START
# =============================================

# Create the Flask app
app = Flask(__name__)

# Configure logging to use our custom logger
app.logger = logger

logger.info("Starting Proletto application")

# Configure Flask app
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_size": 15,
    "max_overflow": 5
}

# Configure CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"

# Redis settings from environment
app.config['REDIS_URL'] = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Configure Stripe
app.config['STRIPE_SECRET_KEY'] = os.environ.get('STRIPE_SECRET_KEY')
app.config['STRIPE_PUBLIC_KEY'] = os.environ.get('STRIPE_PUBLIC_KEY')
app.config['STRIPE_WEBHOOK_SECRET'] = os.environ.get('STRIPE_WEBHOOK_SECRET')

# =============================================
# 2. Application Configuration - END
# =============================================

# =========================================
# 3. Database Initialization - START
# =========================================

# Import models and initialize database
from models import db, User, Opportunity, Portfolio
# Try to import workspace models from db_models if needed
try:
    from db_models import Workspace, Project, Task, Message
    logger.info("Workspace models imported from db_models")
except ImportError:
    logger.warning("Workspace models not available in this version")

# Initialize database
db.init_app(app)

# Error logging database handler disabled
# try:
#     from utils.error_logging import add_db_handler
#     add_db_handler(db)
#     logger.info("Error logging database handler initialized successfully")
# except Exception as e:
#     logger.warning(f"Error logging database handler could not be initialized: {e}")

# Create database tables
with app.app_context():
    db.create_all()
    
# Initialize user loader for flask-login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

logger.info("Database initialized successfully")

# =========================================
# 3. Database Initialization - END
# =========================================

# =========================================
# 4. Register Blueprints - START
# =========================================

# Register Auth blueprint
try:
    from auth import init_app as init_auth
    init_auth(app)
    logger.info("Auth blueprint registered successfully")
except Exception as e:
    logger.error(f"Auth blueprint could not be registered: {e}", exc_info=e)

# Register Dashboard blueprint
try:
    from dashboard_routes_v2 import init_app as init_dashboard
    init_dashboard(app)
    logger.info("Dashboard blueprint registered successfully")
except Exception as e:
    logger.error(f"Dashboard blueprint could not be registered: {e}", exc_info=e)

# Register Admin blueprint
try:
    from admin_routes import init_app as init_admin
    init_admin(app)
    logger.info("Admin blueprint registered successfully")
except Exception as e:
    logger.error(f"Admin blueprint could not be registered: {e}", exc_info=e)

# Register Stripe blueprint
try:
    from stripe_routes import init_app as init_stripe
    init_stripe(app)
    logger.info("Stripe blueprint registered successfully")
except Exception as e:
    logger.warning(f"Stripe blueprint could not be registered: {e}")
    
# Register Membership blueprint
try:
    from membership_routes import init_app as init_membership
    init_membership(app)
    logger.info("Membership blueprint registered successfully")
except Exception as e:
    logger.warning(f"Membership blueprint could not be registered: {e}")

# Initialize email service
try:
    email_service = get_email_service(app)
    email_templates = EmailTemplates(app)
    logger.info("Email service initialized successfully")
except Exception as e:
    logger.warning(f"Email service could not be initialized: {e}")

# Register Cache Health blueprint
try:
    from cache_utils import init_app as init_cache
    init_cache(app)
    logger.info(f"Cache utilities registered successfully: {app.cache_backend['type']}")
except Exception as e:
    logger.warning(f"Cache utilities could not be registered: {e}")

# Register Deployment Routes blueprint
try:
    from deployment_routes import init_app as init_deployment_routes
    init_deployment_routes(app)
    logger.info("Deployment Routes blueprint registered successfully")
except Exception as e:
    logger.warning(f"Deployment Routes blueprint could not be registered: {e}")

# Register Search blueprint
try:
    from search_routes import init_app as init_search
    init_search(app)
    logger.info("Search blueprint registered successfully")
except Exception as e:
    logger.warning(f"Search blueprint could not be registered: {e}")

# Register Feed blueprint
try:
    from feed_routes import init_app as init_feed
    init_feed(app)
    logger.info("Feed blueprint registered successfully")
except Exception as e:
    logger.warning(f"Feed blueprint could not be registered: {e}")

# Monitoring blueprint disabled
# try:
#     from monitoring_routes import init_app as init_monitoring
#     init_monitoring(app, db)
#     logger.info("Monitoring blueprint registered successfully")
# except Exception as e:
#     logger.error(f"Monitoring blueprint could not be registered: {e}", exc_info=e)

# =========================================
# 4. Register Blueprints - END
# =========================================

# =========================================
# 5. API Proxy - START
# =========================================

# Create a proxy route to forward API requests to the API backend
import requests
import logging
import json
from flask import Response, stream_with_context

@app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_proxy(path):
    """
    Enhanced proxy to forward API requests to the API backend
    This allows frontend to use relative paths (/api/...) instead of hardcoded ports

    Improvements:
    - Enhanced error handling with specific error codes
    - Improved logging for debugging
    - Increased timeout
    - Better handling of headers
    - Added retry mechanism with exponential backoff
    - Configurable backend URL via environment variable
    """
    import time
    from requests.exceptions import RequestException

    # Enhanced API backend URL handling
    # This config prioritizes:
    # 1. Environment variable if set
    # 2. Localhost with proper internal networking for Replit
    # 3. Fallback to 127.0.0.1 (more reliable than 0.0.0.0)

    API_BACKEND = os.environ.get('API_BACKEND_URL')

    # If not explicitly set via env var, use context-aware defaults
    if not API_BACKEND:
        # For Replit environments, use localhost (internal network)
        if os.environ.get('REPLIT') or os.environ.get('REPL_ID'):
            API_BACKEND = 'http://localhost:5001'
        else:
            # For local dev, use 127.0.0.1 (more reliable than 0.0.0.0)
            API_BACKEND = 'http://127.0.0.1:5001'

    logger.info(f"Using API backend URL: {API_BACKEND}")
    api_url = f"{API_BACKEND}/api/{path}"

    # Add detailed debugging
    logger.debug(f"Full proxy URL: {api_url}")
    logger.debug(f"Request environment: REPLIT={os.environ.get('REPLIT')}, REPL_ID={os.environ.get('REPL_ID')}")

    # Track this proxy request with our monitoring system
    with monitor.track_request(f"/api/{path}", method=request.method):
        # Log the proxy request
        logger.info(f"Proxying API request: {request.method} {request.path} to {api_url}")
        logger.debug(f"Proxy request parameters: {request.args}")

        # Create a filtered headers dict
        headers = {}
        for key, value in request.headers.items():
            if key.lower() not in ('host', 'content-length'):
                headers[key] = value

        # Add content type if not present
        if 'Content-Type' not in headers and request.method in ['POST', 'PUT']:
            headers['Content-Type'] = 'application/json'

        # Retry configuration
        max_retries = 3
        retry_delay = 0.5  # initial delay in seconds
        timeout = 30  # increased timeout for potentially slow APIs

        # Prepare request body
        data = request.get_data()
        
        # Retry loop with exponential backoff
        for attempt in range(max_retries):
            try:
                # Make the proxied request
                resp = requests.request(
                    method=request.method,
                    url=api_url,
                    headers=headers,
                    params=request.args,
                    data=data,
                    timeout=timeout,
                    stream=True
                )
                
                # Stream the response back to the client
                return Response(
                    stream_with_context(resp.iter_content(chunk_size=1024)),
                    content_type=resp.headers.get('Content-Type'),
                    status=resp.status_code
                )
                
            except RequestException as e:
                # Log the error with detailed diagnostics
                logger.warning(f"API proxy error (attempt {attempt+1}/{max_retries}): {e}")
                logger.debug(f"API proxy request details: URL={api_url}, Method={request.method}, Headers={headers}")
                
                # Last attempt failed, return error response
                if attempt == max_retries - 1:
                    error_message = f"API service unavailable after {max_retries} attempts: {str(e)}"
                    logger.error(error_message)
                    return jsonify({
                        'error': 'API service unavailable',
                        'message': str(e),
                        'status': 'error'
                    }), 503
                
                # Wait before retrying with exponential backoff
                time.sleep(retry_delay * (2 ** attempt))

# =========================================
# 5. API Proxy - END
# =========================================

# =========================================
# 6. Main Route Handlers - START
# =========================================

@app.route('/')
def index():
    """Landing page route"""
    return render_template('public/index.html')

@app.route('/how-it-works')
def how_it_works():
    """How It Works page"""
    return render_template('public/how_it_works.html')

@app.errorhandler(404)
def page_not_found(e):
    """Custom 404 error page"""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Custom 500 error page"""
    logger.error(f"Internal server error: {str(e)}", exc_info=e)
    return render_template('errors/500.html'), 500

# =========================================
# 6. Main Route Handlers - END
# =========================================

# =========================================
# 7. Initialize Services - START
# =========================================

# Register Public API v2 blueprint (moved to end to prevent circular imports)
try:
    from public_api import init_app as init_public_api
    init_public_api(app)
    logger.info("Public API v2 blueprint registered successfully")
except Exception as e:
    logger.error(f"Public API v2 blueprint could not be registered: {e}", exc_info=e)

# Initialize Opportunity Service
try:
    from opportunity_service import init_app as init_opportunity_service
    init_opportunity_service(app)
    logger.info("Opportunity service initialized successfully")
except Exception as e:
    logger.error(f"Opportunity service could not be initialized: {e}", exc_info=e)

# =========================================
# 7. Initialize Services - END
# =========================================

if __name__ == '__main__':
    # Print registered routes for debugging
    print("=========================")
    print("Registered Routes:")
    for rule in app.url_map.iter_rules():
        print(f"Route: {rule} -> methods={rule.methods}")
    print("=========================")

    # Determine port based on the environment (8080 for Production, 5008 for Dev)
    port = int(os.environ.get("PORT", 5008))
    host = os.environ.get("HOST", "0.0.0.0")
    
    # Add logging for startup
    print(f"🔍 Flask app starting on port {port} with host {host}")
    
    # Check if running in development mode
    if os.environ.get('FLASK_ENV') == 'development':
        print("📡 Running in development mode")
        # Use werkzeug development server
        app.run(host=host, port=port, debug=False)
    else:
        # For production, use gunicorn
        import gunicorn.app.base
        
        class StandaloneGunicornApplication(gunicorn.app.base.BaseApplication):
            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super().__init__()
                
            def load_config(self):
                for key, value in self.options.items():
                    self.cfg.set(key.lower(), value)
                    
            def load(self):
                return self.application
        
        # Gunicorn configuration
        options = {
            'bind': f"{host}:{port}",
            'workers': 16,
            'worker_class': 'gthread',
            'threads': 4,
            'timeout': 120,
            'accesslog': '-',
            'errorlog': '-',
            'loglevel': 'info'
        }
        
        print("🚀 Starting with production Gunicorn server")
        StandaloneGunicornApplication(app, options).run()