"""
Proletto Public Routes

This module provides the public-facing routes for the Proletto application.
These routes are accessible without authentication.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, current_app

# Create the blueprint
public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def index():
    """Public homepage"""
    return render_template('public/index.html')

@public_bp.route('/how-it-works')
def how_it_works():
    """How It Works page"""
    return render_template('public/how_it_works.html')

@public_bp.route('/membership')
def membership():
    """Membership/pricing page"""
    return render_template('public/membership.html')

@public_bp.route('/get-started')
def get_started():
    """Redirect to registration page"""
    return redirect(url_for('auth_fix.register'))

@public_bp.route('/upgrade')
def upgrade():
    """Redirect to membership page"""
    return redirect(url_for('public.membership'))

@public_bp.route('/start-trial')
def start_trial():
    """Redirect to registration with trial plan selected"""
    return redirect(url_for('auth_fix.register', plan='supporter'))

# Health check endpoint
@public_bp.route('/healthz')
def healthz():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'ok',
        'timestamp': current_app.config.get('START_TIME', 'unknown')
    })

def init_app(app):
    """Register the public routes blueprint with the Flask app"""
    app.register_blueprint(public_bp)
    app.logger.info("Public routes blueprint registered successfully")
    return True