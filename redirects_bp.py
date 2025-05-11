"""
Proletto Redirects Blueprint

This module handles redirects from legacy routes to the new route structure,
ensuring backward compatibility while transitioning to the new organization.
"""

from flask import Blueprint, redirect, url_for, current_app
from flask_login import current_user, login_required

redirects_bp = Blueprint('redirects', __name__)

# Legacy URLs → New Dashboard Routes
@redirects_bp.route('/opportunities')
@login_required
def old_opportunities():
    """Redirect from old /opportunities to new dashboard feed page"""
    return redirect(url_for('dashboard.feed'), code=302)

@redirects_bp.route('/opportunities/')
@login_required
def old_opportunities_slash():
    """Redirect from old /opportunities/ to new dashboard feed page"""
    return redirect(url_for('dashboard.feed'), code=302)

@redirects_bp.route('/portfolio')
@login_required
def old_portfolio():
    """Redirect from old /portfolio to new dashboard portfolio page"""
    return redirect(url_for('dashboard.portfolio'), code=302)

@redirects_bp.route('/portfolio-optimizer')
@redirects_bp.route('/portfolio_optimizer')
@login_required
def old_portfolio_optimizer():
    """Redirect from old portfolio optimizer routes to new dashboard portfolio optimizer page"""
    return redirect(url_for('dashboard.portfolio_optimizer'), code=302)

@redirects_bp.route('/profile')
@login_required
def old_profile():
    """Redirect from old /profile to new dashboard settings page"""
    return redirect(url_for('dashboard.settings'), code=302)

@redirects_bp.route('/dashboard')
@login_required
def old_dashboard():
    """Redirect from old /dashboard to new dashboard home"""
    return redirect(url_for('dashboard.member_dashboard'), code=302)

@redirects_bp.route('/workspace')
@login_required
def old_workspace():
    """Redirect from old /workspace to new dashboard workspace page"""
    return redirect(url_for('dashboard.workspace'), code=302)

@redirects_bp.route('/workspace/<int:workspace_id>')
@login_required
def old_workspace_detail(workspace_id):
    """Redirect from old workspace detail to new dashboard workspace detail page"""
    return redirect(url_for('dashboard.workspace_detail', workspace_id=workspace_id), code=302)

@redirects_bp.route('/workspace/<int:workspace_id>/project/<int:project_id>')
@login_required
def old_project_detail(workspace_id, project_id):
    """Redirect from old project detail to new dashboard project detail page"""
    return redirect(url_for('dashboard.project_detail', 
                           workspace_id=workspace_id, 
                           project_id=project_id), code=302)

@redirects_bp.route('/workspace/<int:workspace_id>/project/<int:project_id>/files')
@login_required
def old_project_files(workspace_id, project_id):
    """Redirect from old project files to new dashboard project files page"""
    return redirect(url_for('dashboard.project_files', 
                           workspace_id=workspace_id, 
                           project_id=project_id), code=302)

# Legacy Public/Auth URLs
@redirects_bp.route('/sign-in')
def old_sign_in():
    """Redirect from old /sign-in to auth login"""
    return redirect(url_for('auth_fix.login'), code=302)

@redirects_bp.route('/sign-up')
def old_sign_up():
    """Redirect from old /sign-up to auth register"""
    return redirect(url_for('auth_fix.register'), code=302)

@redirects_bp.route('/signup.html')
def old_signup_html():
    """Redirect from old /signup.html to auth register"""
    return redirect(url_for('auth_fix.register'), code=302)

@redirects_bp.route('/how-it-works')
def old_how_it_works():
    """Redirect from old /how-it-works to new public how-it-works page"""
    return redirect(url_for('public.how_it_works'), code=302)

# Helper function to initialize redirects
def init_app(app):
    """Register the redirects blueprint with the Flask app"""
    app.register_blueprint(redirects_bp)
    app.logger.info("Redirects blueprint registered successfully")
    return True