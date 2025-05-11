"""
Auth Router Fix
This module adds additional routes to fix the missing auth endpoints
"""
from flask import Blueprint, redirect, url_for, flash
from flask_login import current_user, logout_user

# Create a blueprint for the missing auth routes
auth_router_fix = Blueprint('auth_router_fix', __name__, url_prefix='/auth')

@auth_router_fix.route("/logout")
def logout():
    """Log out the current user"""
    if current_user.is_authenticated:
        logout_user()
        flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@auth_router_fix.route("/reset-password-request", methods=["GET"])
def reset_password_request_get():
    """GET handler for password reset request"""
    if current_user.is_authenticated:
        return redirect(url_for('opportunities'))
    return redirect(url_for('email_auth.reset_password_request'))

@auth_router_fix.route("/confirm-email", methods=["GET"])
def confirm_email_get():
    """GET handler for email confirmation"""
    if current_user.is_authenticated:
        return redirect(url_for('opportunities'))
    flash('Please check your email for a confirmation link.', 'info')
    return redirect(url_for('index'))