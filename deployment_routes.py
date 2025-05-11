"""
Proletto Deployment Routes

This module provides routes for the deployment interface and functionality.
"""

import os
import logging
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, current_app
from flask_login import login_required, current_user
from admin import admin_required
from deployment_status import init_app as init_deployment_status

# Create blueprint with a unique name
deployment_bp = Blueprint('deployment_tracker', __name__, url_prefix='/deployment')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('deployment-routes')

@deployment_bp.route('/', methods=['GET'])
@login_required
@admin_required
def deployment_page():
    """Render the deployment interface page"""
    return render_template('deployment.html')

@deployment_bp.route('/run', methods=['GET'])
@login_required
@admin_required
def run_deployment():
    """Run the deployment script and redirect to the tracker page"""
    # This would typically trigger the actual deployment process
    # For the UI demo, we'll just redirect to the tracker page
    return redirect(url_for('deployment_tracker.deployment_page'))

def init_app(app):
    """Initialize the deployment routes and register with the Flask app"""
    # Register this blueprint
    app.register_blueprint(deployment_bp)
    
    # Initialize the deployment status tracker
    init_deployment_status(app)
    
    logger.info("Deployment routes initialized")