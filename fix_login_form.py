#!/usr/bin/env python3
"""
Fix Login Form

This script fixes the login form submission issue where the API endpoint 
expects JSON but the form is submitting as form data.
"""
import os
import logging
from flask import Blueprint, request, redirect, url_for, flash, render_template, jsonify
from flask_login import login_user, current_user
from werkzeug.middleware.proxy_fix import ProxyFix

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create a blueprint for the form-based login route
form_login = Blueprint('form_login', __name__)

@form_login.route('/auth/form-login', methods=['GET', 'POST'])
def login():
    """Handle form-based login"""
    if current_user.is_authenticated:
        return redirect(url_for('opportunities'))
    
    # Import here to avoid circular imports
    from models import User, db
    from email_auth import LoginForm
    
    form = LoginForm()
    
    # Debug logging for request method and data
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request form data: {request.form}")
    
    # Handle POST submission - simplified flow per canonical pattern
    if request.method == 'POST':
        logger.info("Processing POST request")
        
        # Check validate_on_submit status and log 
        is_valid = form.validate_on_submit()
        logger.info(f"form.validate_on_submit(): {is_valid}")
        
        # Log any form errors
        if form.errors:
            logger.error(f"Form validation errors: {form.errors}")
        
        # Continue only if validation succeeds
        if is_valid:
            logger.info("Form validated successfully")
            
            # Look up the user
            user = User.query.filter_by(email=form.email.data).first()
            logger.info(f"User lookup result: {user is not None}")
            
            # Check password - outside try/except for better error visibility
            if user and user.verify_password(form.password.data):
                logger.info(f"Password verified for user: {user.email}")
                
                # Update login time
                from datetime import datetime
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                # Log the user in
                login_user(user, remember=form.remember.data)
                
                # Set success message and redirect
                next_page = request.args.get('next')
                flash('Login successful!', 'success')
                target = next_page or url_for('opportunities')
                logger.info(f"Redirecting to: {target}")
                return redirect(target)
            else:
                logger.warning("Invalid email or password")
                flash('Invalid email or password. Please try again.', 'danger')
    
    # For GET requests or failed validation, render the form
    return render_template('login.html', form=form, title='Login to Proletto')

def register_form_login_bp(app):
    """Register the form login blueprint with the app"""
    # Apply proxy fix to handle forwarded headers properly
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    
    # Register the blueprint
    app.register_blueprint(form_login)
    
    # Also update template form action to use the new endpoint
    @app.context_processor
    def inject_form_action():
        return {'login_form_action': url_for('form_login.login')}
    
    logger.info("Form-based login route registered successfully")
    return app