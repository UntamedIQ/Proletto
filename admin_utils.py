"""
Proletto Admin Utilities

This module provides utilities for admin-only functionality, including
the admin_required decorator to protect routes that should only be accessible to admins.
"""

from functools import wraps
from flask import redirect, url_for, flash, session, request, current_app
from flask_login import current_user, login_required

def admin_required(f):
    """
    Decorator to verify the user is an admin before allowing access to admin pages.
    Regular members will be redirected to their member dashboard.
    """
    @wraps(f)
    @login_required  # Ensure the user is logged in first
    def decorated_function(*args, **kwargs):
        # First ensure user is logged in (handled by login_required)
        
        # Check if user has admin role
        if not current_user.is_admin:
            flash('You do not have access to the admin dashboard', 'error')
            # Redirect regular members to their member dashboard
            return redirect(url_for('dashboard.member_dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function

def init_app(app):
    """Initialize the admin utils with the Flask app"""
    app.logger.info("Admin utilities initialized successfully")
    return True