"""
Proletto Dashboard Routes V2

This module provides the member dashboard functionality with a more organized structure.
All member features are now accessible under the /dashboard/* route structure.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps

# Create the blueprint
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# =========================================
# Core Dashboard Routes
# =========================================

@dashboard_bp.route('/')
@login_required
def member_dashboard():
    """Main dashboard landing page"""
    return render_template('member/dashboard.html')

@dashboard_bp.route('/feed')
@login_required
def feed():
    """Opportunity feed with infinite scroll"""
    return render_template('member/feed.html', api_path='/opportunities')

@dashboard_bp.route('/curation')
@login_required
def curation():
    """Personalized top picks"""
    return render_template('member/curation.html')

@dashboard_bp.route('/portfolio')
@login_required
def portfolio():
    """Portfolio management page"""
    return render_template('member/portfolio.html')

@dashboard_bp.route('/portfolio-optimizer')
@login_required
def portfolio_optimizer():
    """Portfolio optimization and AI analysis"""
    return render_template('member/portfolio_optimizer.html')

@dashboard_bp.route('/settings')
@login_required
def settings():
    """User settings page"""
    return render_template('member/settings.html')

@dashboard_bp.route('/submit')
@login_required
def submit():
    """Gallery/Event submission page"""
    return render_template('member/submit.html')

# =========================================
# Workspace Routes
# =========================================

@dashboard_bp.route('/workspace')
@login_required
def workspace():
    """Workspace listing page"""
    return render_template('member/workspace.html')

@dashboard_bp.route('/workspace/<int:workspace_id>')
@login_required
def workspace_detail(workspace_id):
    """Workspace detail page"""
    return render_template('member/workspace_detail.html', workspace_id=workspace_id)

@dashboard_bp.route('/workspace/<int:workspace_id>/project/<int:project_id>')
@login_required
def project_detail(workspace_id, project_id):
    """Project detail page"""
    return render_template('member/project_detail.html', workspace_id=workspace_id, project_id=project_id)

@dashboard_bp.route('/workspace/<int:workspace_id>/project/<int:project_id>/files')
@login_required
def project_files(workspace_id, project_id):
    """Project files page"""
    return render_template('member/project_files.html', workspace_id=workspace_id, project_id=project_id)

# =========================================
# Legacy Route Redirects
# =========================================

def init_legacy_redirects(app):
    """Register redirects for legacy routes to maintain backward compatibility"""
    
    @app.route('/opportunities')
    @login_required
    def opportunities_redirect():
        """Redirect legacy opportunities route to new feed"""
        return redirect(url_for('dashboard.feed'))
        
    @app.route('/portfolio')
    @login_required
    def portfolio_redirect():
        """Redirect legacy portfolio route"""
        return redirect(url_for('dashboard.portfolio'))
        
    @app.route('/portfolio-optimizer')
    @app.route('/portfolio_optimizer')
    @login_required
    def portfolio_optimizer_redirect():
        """Redirect legacy portfolio optimizer routes"""
        return redirect(url_for('dashboard.portfolio_optimizer'))
        
    @app.route('/workspace')
    @login_required
    def workspace_redirect():
        """Redirect legacy workspace route"""
        return redirect(url_for('dashboard.workspace'))
        
    @app.route('/workspace/<int:workspace_id>')
    @login_required
    def workspace_detail_redirect(workspace_id):
        """Redirect legacy workspace detail route"""
        return redirect(url_for('dashboard.workspace_detail', workspace_id=workspace_id))
        
    @app.route('/workspace/<int:workspace_id>/project/<int:project_id>')
    @login_required
    def project_detail_redirect(workspace_id, project_id):
        """Redirect legacy project detail route"""
        return redirect(url_for('dashboard.project_detail', 
                               workspace_id=workspace_id, 
                               project_id=project_id))
                               
    @app.route('/workspace/<int:workspace_id>/project/<int:project_id>/files')
    @login_required
    def project_files_redirect(workspace_id, project_id):
        """Redirect legacy project files route"""
        return redirect(url_for('dashboard.project_files', 
                               workspace_id=workspace_id, 
                               project_id=project_id))

    app.logger.info("Legacy route redirects registered successfully")

def init_app(app):
    """Register the dashboard blueprint with the Flask app"""
    app.register_blueprint(dashboard_bp)
    init_legacy_redirects(app)
    app.logger.info("Dashboard V2 blueprint registered successfully")
    return True