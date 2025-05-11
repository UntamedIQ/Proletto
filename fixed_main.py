import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_required
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
from email_service import get_email_service
from email_templates import EmailTemplates
from flask_cors import CORS

# =========================================
# 1. App and Database Setup - START
# =========================================

# Initialize SQLAlchemy with a Base class
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

# Create and configure the Flask app
app = Flask(__name__, 
           static_folder='.',  # Serve static files from the root directory 
           static_url_path='',
           template_folder='templates')
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "proletto_secret_key"

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the extensions with the app
db.init_app(app)
login_manager.init_app(app)

# Configure login manager
login_manager.login_view = 'auth_fix.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Initialize database tables
def init_db():
    with app.app_context():
        # Import models here to ensure they're registered with SQLAlchemy
        import models
        # Define the token blocklist model
        try:
            import token_blocklist
            token_blocklist.init_db(db)
            token_blocklist.define_token_blocklist()
            app.logger.info("TokenBlocklist module initialized successfully")
        except Exception as e:
            app.logger.warning(f"Failed to initialize token blocklist: {e}")
        # Create all tables
        db.create_all()
        app.logger.info("All database tables created successfully")

# Call init_db to make sure tables exist
init_db()

# =========================================
# 1. App and Database Setup - END
# =========================================

# =========================================
# 2. Register Blueprints - START
# =========================================

# Register Google Auth blueprint
try:
    from google_auth import google_auth
    app.register_blueprint(google_auth, url_prefix='/auth/google')
    app.logger.info("Google Auth blueprint registered successfully")
except Exception as e:
    app.logger.warning(f"Google Auth blueprint could not be registered: {e}")

# Register Email Auth blueprint
try:
    from email_auth import email_auth
    app.register_blueprint(email_auth, url_prefix='/auth')
    app.logger.info("Email Auth blueprint registered successfully")
except Exception as e:
    app.logger.warning(f"Email Auth blueprint could not be registered: {e}")

# Register Referral Routes blueprint
try:
    from referral_routes import referral_routes
    app.register_blueprint(referral_routes, url_prefix='/referral')
    app.logger.info("Referral Routes blueprint registered successfully")
except Exception as e:
    app.logger.warning(f"Referral Routes blueprint could not be registered: {e}")

# Register Auth Router Fix blueprint
try:
    from auth_router_fix import auth_router_fix
    app.register_blueprint(auth_router_fix, url_prefix='/auth')
    app.logger.info("Auth Router Fix blueprint registered successfully")
except Exception as e:
    app.logger.warning(f"Auth Router Fix blueprint could not be registered: {e}")

# Register the Auth Fix blueprint
try:
    from fix_auth_routes import auth_fix, register_auth_fix
    app.register_blueprint(auth_fix)
    register_auth_fix(app)
    app.logger.info("Auth Fix blueprint registered successfully")
except Exception as e:
    app.logger.warning(f"Auth Fix blueprint could not be registered: {e}")

# Initialize Stripe fixed endpoints
try:
    from fix_stripe_endpoint import fix_stripe_endpoints
    fix_stripe_endpoints(app)
    app.logger.info("Stripe endpoints fixed successfully")
except Exception as e:
    app.logger.warning(f"Failed to fix Stripe endpoints: {e}")

# =========================================
# 2. Register Blueprints - END
# =========================================

# =========================================
# 3. Primary "Clean" Routes - START
# =========================================

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# Opportunities
@app.route('/opportunities')
def opportunities():
    return render_template('opportunities.html')

# Portfolio
@app.route('/portfolio')
@login_required
def portfolio():
    return render_template('portfolio.html')

# Workspace routes
@app.route('/workspace')
@login_required
def workspace():
    return render_template('workspace.html')

@app.route('/workspace/<int:workspace_id>')
@login_required
def workspace_detail(workspace_id):
    return render_template('workspace_detail.html', workspace_id=workspace_id)

@app.route('/workspace/<int:workspace_id>/project/<int:project_id>')
@login_required
def project_detail(workspace_id, project_id):
    return render_template('project_detail.html', workspace_id=workspace_id, project_id=project_id)

@app.route('/workspace/<int:workspace_id>/project/<int:project_id>/files')
@login_required
def project_files(workspace_id, project_id):
    return render_template('project_files.html', workspace_id=workspace_id, project_id=project_id)

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# User profile
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

# Portfolio optimizer
@app.route('/portfolio-optimizer')
@app.route('/portfolio_optimizer')
def portfolio_optimizer():
    return render_template('portfolio_optimizer.html')

# =========================================
# 3. Primary "Clean" Routes - END
# =========================================

# =========================================
# 4. Redirects - START
# =========================================

# Redirect legacy URLs
@app.route('/get-started')
def get_started():
    return redirect(url_for('auth_fix.register'))

@app.route('/upgrade')
def upgrade():
    return redirect(url_for('static', filename='membership.html'))

@app.route('/start-trial')
def start_trial():
    return redirect(url_for('auth_fix.register', plan='supporter'))

@app.route('/logout')
def logout():
    return redirect(url_for('auth_router_fix.logout'))

# =========================================
# 4. Redirects - END
# =========================================

# =========================================
# 5. Error Handlers - START
# =========================================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', requested_path=request.path), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html', error=str(e)), 500

# =========================================
# 5. Error Handlers - END
# =========================================

# =========================================
# 6. Debug Routes - START
# =========================================

@app.route('/debug/auth-routes')
def debug_auth_routes():
    """Return a list of all registered auth-related routes for debugging"""
    routes = []
    for rule in app.url_map.iter_rules():
        if 'auth' in rule.endpoint or 'login' in rule.endpoint or 'register' in rule.endpoint:
            routes.append({
                'endpoint': rule.endpoint,
                'path': str(rule),
                'methods': list(rule.methods)
            })
    return jsonify(routes)

@app.route('/debug/all-routes')
def debug_all_routes():
    """Return a list of all registered routes for debugging"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'path': str(rule),
            'methods': list(rule.methods)
        })
    return jsonify(routes)

@app.route('/debug/route-check')
def debug_route_check():
    """Simple view to check if dynamic routes are working"""
    return render_template('debug_route_check.html')

# Test route to check auth middleware
@app.route('/debug/auth-check')
@login_required
def debug_auth_check():
    return jsonify({
        'user_id': current_user.id,
        'email': current_user.email,
        'name': current_user.name,
        'is_authenticated': current_user.is_authenticated
    })

# =========================================
# 6. Debug Routes - END
# =========================================

# =========================================
# 7. Catch-all Route - START
# =========================================

# Catch-all route to serve static HTML files that don't have explicit routes
@app.route('/<path:anything>')
def catch_all(anything):
    # Try to serve an HTML file with the same name
    if anything.endswith('.html'):
        try:
            return render_template(anything)
        except:
            pass
            
    # Try to find a template with the given name
    try:
        return render_template(f"{anything}.html")
    except:
        pass
    
    # Return 404 if no matching file found
    abort(404)

# =========================================
# 7. Catch-all Route - END
# =========================================

if __name__ == '__main__':
    # Print out all registered routes for debugging
    with app.app_context():
        from pprint import pprint
        print("\n=== Registered Routes ===")
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(f"Route: {rule} -> methods={rule.methods}")
        routes.sort()
        for route in routes:
            print(route)
        print("=========================\n")
        
    # Start the server
    app.run(host='0.0.0.0', port=5000, debug=True)