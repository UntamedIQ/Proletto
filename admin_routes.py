"""
Proletto Admin Dashboard Routes
This module provides the admin dashboard functionality.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from functools import wraps
import re
import glob

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import func

# Import scrapers_improvement here to avoid circular imports
from scrapers_improvement import get_site_health_metrics, generate_health_report

# Import the alerts module for testing alerts
try:
    from alerts import alert_slack, alert_admin_email, test_alerts
    ALERTS_AVAILABLE = True
except ImportError:
    ALERTS_AVAILABLE = False
    logger.warning("Alerts module not available. Alert functionality is disabled.")

# We'll import the models later to avoid circular imports
# from models import User, db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('admin_routes')

# Create blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        if current_user.role != 'admin':
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

# Helper functions for getting system metrics
def get_user_count():
    """Get total user count"""
    from models import User  # Import here to avoid circular imports
    return User.query.count()

def get_opportunity_count():
    """Get total opportunity count from opportunities.json"""
    try:
        with open('opportunities.json', 'r') as f:
            opportunities = json.load(f)
            return len(opportunities)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0

def get_premium_count():
    """Get count of premium users"""
    from models import User  # Import here to avoid circular imports
    return User.query.filter(User.membership_level == 'premium').count()

def get_active_engines():
    """Get count of active engines"""
    return len(get_engines_list())

def get_engines_list():
    """Get list of all engines"""
    engines = []
    
    # Engine files are named proletto_engine_*.py
    engine_files = glob.glob('proletto_engine_*.py')
    
    for i, engine_file in enumerate(engine_files):
        # Extract the engine name from the file name
        engine_name = engine_file.replace('proletto_engine_', '').replace('.py', '')
        
        # Format the engine name for display
        display_name = engine_name.replace('_', ' ').title()
        if engine_name == 'v1':
            display_name = 'General Opportunities (v1)'
        
        # Determine icon and color based on engine name
        icon = 'robot'
        color = '#8e44ad'
        
        if 'social' in engine_name:
            icon = 'hashtag'
            color = '#e74c3c'
        elif any(state in engine_name for state in ['california', 'texas', 'newyork', 'florida']):
            icon = 'map-marker-alt'
            color = '#3498db'
        
        # Get metrics from the site health system
        site_metrics = get_site_health_metrics()
        success_rate = 0
        response_time = 0
        health = 0
        opportunity_count = 0
        
        # Calculate metrics by averaging across all sites for this engine
        relevant_sites = [m for domain, m in site_metrics.items() if engine_name in domain]
        if relevant_sites:
            success_count = sum(m.get('success_count', 0) for m in relevant_sites)
            failure_count = sum(m.get('failure_count', 0) for m in relevant_sites)
            total_count = success_count + failure_count
            
            if total_count > 0:
                success_rate = round((success_count / total_count) * 100)
            
            response_times = [m.get('avg_response_time', 0) for m in relevant_sites if m.get('avg_response_time')]
            if response_times:
                response_time = round(sum(response_times) / len(response_times))
            
            # Calculate health score (combination of success rate and response time)
            health = min(100, success_rate * 0.7 + max(0, 100 - min(1000, response_time) / 10) * 0.3)
        
        # Try to get opportunity count from the opportunities.json file
        try:
            with open('opportunities.json', 'r') as f:
                opportunities = json.load(f)
                # Count opportunities from this engine
                opportunity_count = sum(1 for opp in opportunities if opp.get('source', '').lower() == engine_name)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        
        engines.append({
            'id': i + 1,
            'name': display_name,
            'file': engine_file,
            'description': f'Scrapes opportunities from {display_name} sources',
            'status': 'idle',  # Default status
            'last_run': '2025-05-04 08:30:00',  # Placeholder
            'opportunity_count': opportunity_count,
            'success_rate': success_rate,
            'response_time': response_time,
            'health': health,
            'icon': icon,
            'color': color
        })
    
    return engines

def get_site_health_list():
    """Get list of all site health metrics"""
    site_health = []
    
    metrics = get_site_health_metrics()
    
    for domain, m in metrics.items():
        success_count = m.get('success_count', 0)
        failure_count = m.get('failure_count', 0)
        total_count = success_count + failure_count
        
        success_rate = 0
        if total_count > 0:
            success_rate = round((success_count / total_count) * 100)
        
        response_time = m.get('avg_response_time', 0)
        
        # Determine status based on circuit breaker and success rate
        status = 'unknown'
        if m.get('circuit_open', False):
            status = 'offline'
        elif success_rate >= 90:
            status = 'online'
        elif success_rate >= 50:
            status = 'partial'
        elif total_count > 0:
            status = 'offline'
        
        # Extract engine name from domain
        engine = 'Unknown'
        for eng in get_engines_list():
            if eng['name'].lower() in domain.lower():
                engine = eng['name']
                break
        
        site_health.append({
            'url': m.get('url', f'https://{domain}/'),
            'domain': domain,
            'engine': engine,
            'status': status,
            'success_rate': success_rate,
            'response_time': response_time or 0,
            'last_check': m.get('last_check', 'Never'),
            'circuit_open': m.get('circuit_open', False)
        })
    
    return site_health

def get_recent_users(limit=5):
    """Get recently joined users"""
    from models import User  # Import here to avoid circular imports
    users = User.query.order_by(User.created_at.desc()).limit(limit).all()
    
    result = []
    for user in users:
        # Generate a consistent color hash for the user
        color_hash = abs(hash(user.email)) % 0xFFFFFF
        color_hex = f"{color_hash:06x}"
        
        # Determine if user is active (logged in within the last 7 days)
        active = False
        if user.last_login and user.last_login > datetime.utcnow() - timedelta(days=7):
            active = True
        
        result.append({
            'name': user.name or 'Anonymous',
            'email': user.email,
            'avatar_url': user.avatar_url,
            'avatar_color': color_hex,
            'active': active,
            'membership_level': user.membership_level,
            'joined': user.created_at.strftime('%Y-%m-%d')
        })
    
    return result

def get_system_logs(limit=10):
    """Get recent system logs"""
    logs = []
    
    # Look for log files
    log_files = ['api.log', 'bot.log']
    
    for log_file in log_files:
        if not os.path.exists(log_file):
            continue
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                
                # Extract the most recent log entries
                for line in lines[-100:]:  # Look at the last 100 lines
                    # Parse log entry
                    match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (\w+) - (\w+) - (.*)', line)
                    if match:
                        timestamp, source, level, message = match.groups()
                        logs.append({
                            'timestamp': timestamp,
                            'source': source,
                            'level': level,
                            'message': message
                        })
        except Exception as e:
            logger.error(f"Error reading log file {log_file}: {e}")
    
    # Sort logs by timestamp (most recent first)
    logs.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return logs[:limit]

def get_user_growth_data():
    """Get user growth data for the chart"""
    from models import User  # Import here to avoid circular imports
    
    # Data for the last 14 days
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=13)
    
    labels = []
    data = []
    
    current_date = start_date
    while current_date <= end_date:
        # Get user count for this day
        next_date = current_date + timedelta(days=1)
        count = User.query.filter(
            User.created_at >= current_date,
            User.created_at < next_date
        ).count()
        
        labels.append(current_date.strftime('%m/%d'))
        data.append(count)
        
        current_date = next_date
    
    return {
        'labels': labels,
        'data': data
    }

def get_opportunity_source_data():
    """Get opportunity source data for the chart"""
    try:
        with open('opportunities.json', 'r') as f:
            opportunities = json.load(f)
            
            # Count opportunities by source
            sources = {}
            for opp in opportunities:
                source = opp.get('source', 'Unknown')
                if source in sources:
                    sources[source] += 1
                else:
                    sources[source] = 1
            
            # Sort by count and take top 7
            sorted_sources = sorted(sources.items(), key=lambda x: x[1], reverse=True)[:7]
            
            # If there are more than 7 sources, add an "Others" category
            if len(sources) > 7:
                other_count = sum(sources[s] for s in sources if s not in [src[0] for src in sorted_sources])
                sorted_sources.append(('Others', other_count))
            
            labels = [src[0].title() for src in sorted_sources]
            data = [src[1] for src in sorted_sources]
            
            return {
                'labels': labels,
                'data': data
            }
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            'labels': ['No Data'],
            'data': [0]
        }

def get_engine_performance_data():
    """Get engine performance data for the chart"""
    # For now, return dummy data
    # In a real implementation, this would come from engine metrics
    dates = []
    success_rates = []
    response_times = []
    
    # Generate data for the last 14 days
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=13)
    
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime('%m/%d'))
        
        # In a real implementation, these would be real metrics
        success_rates.append(95)  # 95% success rate (placeholder)
        response_times.append(250)  # 250ms response time (placeholder)
        
        current_date += timedelta(days=1)
    
    return {
        'dates': dates,
        'success_rates': success_rates,
        'response_times': response_times
    }

# Route handlers
@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """Admin dashboard home page"""
    # Get system metrics
    user_count = get_user_count()
    opportunity_count = get_opportunity_count()
    premium_count = get_premium_count()
    active_engines = get_active_engines()
    
    # Get uptime (placeholder values for now)
    app_uptime = "5d 12h 30m"
    api_uptime = "5d 12h 30m"
    bot_uptime = "2d 4h 15m"
    db_uptime = "5d 12h 30m"
    last_check_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    # Get engines list
    engines = get_engines_list()
    
    # Get recent users
    recent_users = get_recent_users()
    
    # Get system logs
    system_logs = get_system_logs()
    
    # Get chart data
    user_growth = get_user_growth_data()
    opportunity_sources = get_opportunity_source_data()
    
    return render_template(
        'admin/dashboard.html',
        user_count=user_count,
        opportunity_count=opportunity_count,
        premium_count=premium_count,
        active_engines=active_engines,
        app_uptime=app_uptime,
        api_uptime=api_uptime,
        bot_uptime=bot_uptime,
        db_uptime=db_uptime,
        last_check_time=last_check_time,
        engines=engines,
        recent_users=recent_users,
        system_logs=system_logs,
        user_growth_labels=user_growth['labels'],
        user_growth_data=user_growth['data'],
        opportunity_source_labels=opportunity_sources['labels'],
        opportunity_source_data=opportunity_sources['data']
    )

@admin_bp.route('/engines')
@login_required
@admin_required
def engines():
    """Admin engines page"""
    # Get engines list
    engines = get_engines_list()
    
    # Get site health list
    site_health = get_site_health_list()
    
    # Get chart data
    performance_data = get_engine_performance_data()
    
    # Get opportunity distribution
    opportunity_sources = get_opportunity_source_data()
    
    return render_template(
        'admin/engines.html',
        engines=engines,
        site_health=site_health,
        performance_dates=performance_data['dates'],
        performance_success_rate=performance_data['success_rates'],
        performance_response_time=performance_data['response_times'],
        opportunity_distribution_labels=opportunity_sources['labels'],
        opportunity_distribution_data=opportunity_sources['data']
    )

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """Admin users page"""
    from models import User  # Import here to avoid circular imports
    
    # Get all users
    users_query = User.query.order_by(User.created_at.desc())
    
    # Get filter parameters
    membership = request.args.get('membership')
    if membership:
        users_query = users_query.filter(User.membership_level == membership)
    
    # Get search parameters
    search = request.args.get('search')
    if search:
        users_query = users_query.filter(
            (User.email.ilike(f'%{search}%')) | 
            (User.name.ilike(f'%{search}%'))
        )
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = users_query.paginate(page=page, per_page=per_page)
    users = pagination.items
    
    # Get user stats
    total_users = User.query.count()
    free_users = User.query.filter(User.membership_level == 'free').count()
    supporter_users = User.query.filter(User.membership_level == 'supporter').count()
    premium_users = User.query.filter(User.membership_level == 'premium').count()
    
    return render_template(
        'admin/users.html',
        users=users,
        pagination=pagination,
        total_users=total_users,
        free_users=free_users,
        supporter_users=supporter_users,
        premium_users=premium_users,
        search=search,
        membership=membership
    )

@admin_bp.route('/opportunities')
@login_required
@admin_required
def opportunities():
    """Admin opportunities page"""
    # Load opportunities from JSON file
    try:
        with open('opportunities.json', 'r') as f:
            opportunities = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        opportunities = []
    
    # Get filter parameters
    source = request.args.get('source')
    if source:
        opportunities = [opp for opp in opportunities if opp.get('source') == source]
    
    # Get search parameters
    search = request.args.get('search')
    if search:
        opportunities = [opp for opp in opportunities if 
                         search.lower() in opp.get('title', '').lower() or 
                         search.lower() in opp.get('organization', '').lower() or
                         search.lower() in opp.get('description', '').lower()]
    
    # Sort by date (newest first)
    opportunities.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    paginated_opportunities = opportunities[start_idx:end_idx]
    total_pages = (len(opportunities) + per_page - 1) // per_page
    
    # Get sources for filter
    sources = sorted(set(opp.get('source', 'Unknown') for opp in opportunities))
    
    return render_template(
        'admin/opportunities.html',
        opportunities=paginated_opportunities,
        total_opportunities=len(opportunities),
        page=page,
        total_pages=total_pages,
        sources=sources,
        source=source,
        search=search
    )

@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    """Admin logs page"""
    # Get log files
    log_files = ['api.log', 'bot.log']
    selected_log = request.args.get('log', 'api.log')
    
    # Get log level filter
    log_level = request.args.get('level', 'all')
    
    # Load log contents
    log_entries = []
    
    if os.path.exists(selected_log):
        try:
            with open(selected_log, 'r') as f:
                lines = f.readlines()
                
                for line in lines:
                    # Parse log entry
                    match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (\w+) - (\w+) - (.*)', line)
                    if match:
                        timestamp, source, level, message = match.groups()
                        
                        # Apply level filter
                        if log_level != 'all' and log_level.upper() != level:
                            continue
                        
                        log_entries.append({
                            'timestamp': timestamp,
                            'source': source,
                            'level': level,
                            'message': message
                        })
        except Exception as e:
            flash(f"Error reading log file: {e}", 'danger')
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    paginated_logs = log_entries[start_idx:end_idx]
    total_pages = (len(log_entries) + per_page - 1) // per_page
    
    return render_template(
        'admin/logs.html',
        logs=paginated_logs,
        total_logs=len(log_entries),
        page=page,
        total_pages=total_pages,
        log_files=log_files,
        selected_log=selected_log,
        log_level=log_level
    )

@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    """Admin analytics page"""
    # Get user growth data
    user_growth = get_user_growth_data()
    
    # Get user stats by membership level
    from models import User  # Import here to avoid circular imports
    free_users = User.query.filter(User.membership_level == 'free').count()
    supporter_users = User.query.filter(User.membership_level == 'supporter').count()
    premium_users = User.query.filter(User.membership_level == 'premium').count()
    
    # Calculate percentages
    total_users = free_users + supporter_users + premium_users
    if total_users > 0:
        free_percentage = round((free_users / total_users) * 100)
        supporter_percentage = round((supporter_users / total_users) * 100)
        premium_percentage = round((premium_users / total_users) * 100)
    else:
        free_percentage = supporter_percentage = premium_percentage = 0
    
    # Get opportunity sources data
    opportunity_sources = get_opportunity_source_data()
    
    # Get user activity data (placeholder for now)
    import random  # Import here for random data generation
    activity_dates = user_growth['labels']
    activity_data = [random.randint(10, 50) for _ in range(len(activity_dates))]
    
    return render_template(
        'admin/analytics.html',
        user_growth_labels=user_growth['labels'],
        user_growth_data=user_growth['data'],
        free_users=free_users,
        supporter_users=supporter_users,
        premium_users=premium_users,
        free_percentage=free_percentage,
        supporter_percentage=supporter_percentage,
        premium_percentage=premium_percentage,
        opportunity_source_labels=opportunity_sources['labels'],
        opportunity_source_data=opportunity_sources['data'],
        activity_dates=activity_dates,
        activity_data=activity_data
    )

@admin_bp.route('/settings')
@login_required
@admin_required
def settings():
    """Admin settings page"""
    return render_template('admin/settings.html')

# API routes for AJAX operations
@admin_bp.route('/api/run-engine/<int:engine_id>', methods=['POST'])
@login_required
@admin_required
def run_engine(engine_id):
    """API endpoint to run a specific engine"""
    # Get engines list
    engines = get_engines_list()
    
    # Find the engine with the given ID
    engine = next((e for e in engines if e['id'] == engine_id), None)
    if not engine:
        return jsonify({'success': False, 'message': 'Engine not found'})
    
    # In a real implementation, this would actually start the engine
    # For now, just return success
    return jsonify({'success': True, 'message': f"Engine {engine['name']} started successfully"})

@admin_bp.route('/api/engine-logs/<int:engine_id>')
@login_required
@admin_required
def get_engine_logs(engine_id):
    """API endpoint to get logs for a specific engine"""
    # Get engines list
    engines = get_engines_list()
    
    # Find the engine with the given ID
    engine = next((e for e in engines if e['id'] == engine_id), None)
    if not engine:
        return jsonify({'success': False, 'message': 'Engine not found', 'logs': []})
    
    # In a real implementation, this would get logs from the engine
    # For now, return dummy logs
    logs = []
    
    # Try to find real logs from log files
    log_files = ['api.log', 'bot.log']
    
    for log_file in log_files:
        if not os.path.exists(log_file):
            continue
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                
                # Extract log entries related to this engine
                for line in lines:
                    # Only include lines related to this engine
                    if engine['file'].replace('.py', '') in line:
                        # Parse log entry
                        match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (\w+) - (\w+) - (.*)', line)
                        if match:
                            timestamp, source, level, message = match.groups()
                            logs.append({
                                'timestamp': timestamp,
                                'level': level,
                                'message': message
                            })
        except Exception as e:
            logger.error(f"Error reading log file {log_file}: {e}")
    
    # Sort logs by timestamp (most recent first)
    logs.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # If no logs were found, add a dummy log
    if not logs:
        logs.append({
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3],
            'level': 'INFO',
            'message': f"No logs found for engine {engine['name']}"
        })
    
    return jsonify({'success': True, 'logs': logs})

@admin_bp.route('/api/engine/<int:engine_id>')
@login_required
@admin_required
def get_engine(engine_id):
    """API endpoint to get engine details"""
    # Get engines list
    engines = get_engines_list()
    
    # Find the engine with the given ID
    engine = next((e for e in engines if e['id'] == engine_id), None)
    if not engine:
        return jsonify({'success': False, 'message': 'Engine not found'})
    
    # Only return what's needed for the edit form
    return jsonify({
        'id': engine['id'],
        'name': engine['name'],
        'description': engine['description'],
        'schedule': 'daily',  # Placeholder
        'retry_attempts': 3,  # Placeholder
        'timeout': 15,  # Placeholder
        'membership_level': 'free',  # Placeholder
        'enabled': True  # Placeholder
    })

@admin_bp.route('/api/update-engine', methods=['POST'])
@login_required
@admin_required
def update_engine():
    """API endpoint to update engine configuration"""
    # Get data from request
    data = request.json
    
    # Validate data
    if not data or 'engineId' not in data:
        return jsonify({'success': False, 'message': 'Invalid data'})
    
    # Get engines list
    engines = get_engines_list()
    
    # Find the engine with the given ID
    engine = next((e for e in engines if e['id'] == int(data['engineId'])), None)
    if not engine:
        return jsonify({'success': False, 'message': 'Engine not found'})
    
    # In a real implementation, this would update the engine configuration
    # For now, just return success
    return jsonify({'success': True, 'message': f"Engine {engine['name']} updated successfully"})

@admin_bp.route('/api/toggle-engine/<int:engine_id>', methods=['POST'])
@login_required
@admin_required
def toggle_engine(engine_id):
    """API endpoint to enable/disable an engine"""
    # Get data from request
    data = request.json
    
    # Validate data
    if not data or 'status' not in data:
        return jsonify({'success': False, 'message': 'Invalid data'})
    
    # Get engines list
    engines = get_engines_list()
    
    # Find the engine with the given ID
    engine = next((e for e in engines if e['id'] == engine_id), None)
    if not engine:
        return jsonify({'success': False, 'message': 'Engine not found'})
    
    # In a real implementation, this would enable/disable the engine
    # For now, just return success
    return jsonify({'success': True, 'message': f"Engine {engine['name']} {data['status']} successfully"})

@admin_bp.route('/api/run-all-engines', methods=['POST'])
@login_required
@admin_required
def run_all_engines():
    """API endpoint to run all engines"""
    # In a real implementation, this would start all engines
    # For now, just return success
    return jsonify({'success': True, 'message': "All engines started successfully"})

@admin_bp.route('/api/engine-performance/<int:engine_id>')
@login_required
@admin_required
def get_engine_performance(engine_id):
    """API endpoint to get performance data for a specific engine"""
    # Get engines list
    engines = get_engines_list()
    
    # Find the engine with the given ID
    engine = next((e for e in engines if e['id'] == engine_id), None)
    if not engine:
        return jsonify({'success': False, 'message': 'Engine not found'})
    
    # Get general performance data
    performance_data = get_engine_performance_data()
    
    # In a real implementation, this would get engine-specific performance data
    # For now, just return the general data
    return jsonify({
        'dates': performance_data['dates'],
        'success_rates': performance_data['success_rates'],
        'response_times': performance_data['response_times']
    })

@admin_bp.route('/api/site-health')
@login_required
@admin_required
def get_site_health():
    """API endpoint to get site health metrics"""
    metrics = get_site_health_metrics()
    return jsonify({'success': True, 'metrics': metrics})

@admin_bp.route('/api/site-health/report')
@login_required
@admin_required
def get_site_health_report():
    """API endpoint to get site health report CSV"""
    report = generate_health_report()
    return jsonify({'success': True, 'report': report})

@admin_bp.route('/api/test-alert', methods=['POST'])
@login_required
@admin_required
def test_alert():
    """API endpoint to test alert functionality"""
    if not ALERTS_AVAILABLE:
        return jsonify({
            'success': False, 
            'message': 'Alerts module not available'
        })
    
    try:
        alert_type = request.json.get('type', 'slack')
        level = request.json.get('level', 'info')
        message = request.json.get('message', 'Test alert from admin dashboard')
        
        if alert_type == 'slack':
            result = alert_slack(message, level)
            return jsonify({
                'success': result,
                'message': 'Slack alert sent successfully' if result else 'Failed to send Slack alert'
            })
        elif alert_type == 'email':
            email = request.json.get('email', None)
            result = alert_admin_email('Test Alert', message, email)
            return jsonify({
                'success': result,
                'message': 'Email alert sent successfully' if result else 'Failed to send email alert'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Unknown alert type: {alert_type}'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error sending alert: {str(e)}'
        })

# Register the blueprint with the main app
def init_app(app):
    app.register_blueprint(admin_bp)
    logger.info("Admin blueprint registered successfully")