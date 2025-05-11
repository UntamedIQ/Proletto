from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
import logging
import os
import json
from datetime import datetime, timedelta

admin_bp = Blueprint('simple_admin', __name__, url_prefix='/simple-admin', template_folder='templates/admin')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('admin')

# In-memory user for now; later swap for DB
_ADMIN_USER = 'admin'
_ADMIN_PW_HASH = generate_password_hash('Untamed1Q')

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == _ADMIN_USER and check_password_hash(_ADMIN_PW_HASH, password):
            session['is_admin'] = True
            return redirect(url_for('simple_admin.dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('admin/login.html')

@admin_bp.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('simple_admin.login'))

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('simple_admin.login'))
        return f(*args, **kwargs)
    return decorated

@admin_bp.route('/')
@admin_required
def dashboard():
    # Fetch metrics from your health-tracking system and user DB
    from scrapers_improvement import get_site_health_metrics
    from flask import current_app
    
    metrics = get_site_health_metrics() 
    formatted_metrics = {}
    
    for site, data in metrics.items():
        success_count = data.get('success_count', 0)
        failure_count = data.get('failure_count', 0)
        total_count = success_count + failure_count
        
        success_rate = 0
        if total_count > 0:
            success_rate = round((success_count / total_count) * 100)
        
        # Format last check time if available
        last_check = data.get('last_check', 'Never')
        if isinstance(last_check, str) and last_check != 'Never':
            try:
                last_check = datetime.fromisoformat(last_check).strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
        
        formatted_metrics[site] = {
            'last_success': data.get('last_success', 'Never'),
            'failure_count': failure_count,
            'avg_latency': f"{data.get('avg_response_time', 0)}ms",
            'success_rate': f"{success_rate}%",
            'circuit_status': 'Open' if data.get('circuit_open', False) else 'Closed'
        }
    
    # Get user stats - safer approach to prevent SQLAlchemy context issues
    user_count = 0
    premium_count = 0
    try:
        with current_app.app_context():
            from models import User
            user_count = User.query.count()
            premium_count = User.query.filter(User.membership_level == 'premium').count()
    except Exception as e:
        logger.error(f"Error querying User data: {e}")
        # Continue with default values
        
    # Get opportunity count
    try:
        with open('opportunities.json', 'r') as f:
            opportunities = json.load(f)
            opportunity_count = len(opportunities)
    except (FileNotFoundError, json.JSONDecodeError):
        opportunity_count = 0
        
    return render_template('admin/dashboard.html',
                           metrics=formatted_metrics,
                           user_count=user_count,
                           premium_count=premium_count,
                           opportunity_count=opportunity_count)

@admin_bp.route('/engines')
@admin_required
def engines():
    from scrapers_improvement import get_site_health_metrics
    from flask import current_app
    import glob
    
    # Get all proletto engine files
    engine_files = glob.glob('proletto_engine_*.py')
    engines = []
    
    for i, engine_file in enumerate(engine_files):
        # Extract the engine name from the file name
        engine_name = engine_file.replace('proletto_engine_', '').replace('.py', '')
        
        # Format the engine name for display
        display_name = engine_name.replace('_', ' ').title()
        if engine_name == 'v1':
            display_name = 'General Opportunities (v1)'
        
        engines.append({
            'id': i + 1,
            'name': display_name,
            'file': engine_file,
            'status': 'Active'
        })
    
    # Get site health metrics
    site_metrics = get_site_health_metrics()
    formatted_metrics = []
    
    for domain, data in site_metrics.items():
        success_count = data.get('success_count', 0)
        failure_count = data.get('failure_count', 0)
        total_count = success_count + failure_count
        
        success_rate = 0
        if total_count > 0:
            success_rate = round((success_count / total_count) * 100)
            
        formatted_metrics.append({
            'domain': domain,
            'success_rate': f"{success_rate}%",
            'avg_latency': f"{data.get('avg_response_time', 0)}ms",
            'last_check': data.get('last_check', 'Never'),
            'circuit_status': 'Open' if data.get('circuit_open', False) else 'Closed'
        })
    
    return render_template('admin/engines.html',
                           engines=engines,
                           site_metrics=formatted_metrics)

@admin_bp.route('/users')
@admin_required
def users():
    """Admin users page"""
    from flask import current_app
    
    # Get user stats with safer error handling
    users_list = []
    try:
        with current_app.app_context():
            from models import User
            users = User.query.order_by(User.created_at.desc()).limit(10).all()
            for user in users:
                users_list.append({
                    'id': user.id,
                    'name': user.name or 'N/A',
                    'email': user.email,
                    'membership': user.membership_level,
                    'created_at': user.created_at.strftime('%Y-%m-%d') if user.created_at else 'N/A',
                    'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never'
                })
    except Exception as e:
        logger.error(f"Error querying User data: {e}")
        # Provide sample data if database query fails
        users_list = []
    
    return render_template('admin/users.html', users=users_list)

@admin_bp.route('/opportunities')
@admin_required
def opportunities():
    """Admin opportunities page"""
    opportunities_list = []
    
    try:
        with open('opportunities.json', 'r') as f:
            all_opportunities = json.load(f)
            
            # Take the most recent 10 opportunities
            recent_opportunities = all_opportunities[-10:] if len(all_opportunities) > 0 else []
            
            for opportunity in recent_opportunities:
                opportunities_list.append({
                    'title': opportunity.get('title', 'No Title'),
                    'source': opportunity.get('source', 'Unknown'),
                    'location': opportunity.get('location', 'Not specified'),
                    'deadline': opportunity.get('deadline', 'Not specified'),
                    'type': opportunity.get('type', 'Unknown'),
                    'url': opportunity.get('url', '#')
                })
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading opportunities data: {e}")
        opportunities_list = []
    
    # Get opportunity count
    opportunity_count = len(opportunities_list)
    
    # Count opportunities by type
    opportunity_types = {}
    for opp in opportunities_list:
        opp_type = opp.get('type', 'Unknown')
        opportunity_types[opp_type] = opportunity_types.get(opp_type, 0) + 1
    
    return render_template('admin/opportunities.html', 
                          opportunities=opportunities_list,
                          opportunity_count=opportunity_count,
                          opportunity_types=opportunity_types)

@admin_bp.route('/settings')
@admin_required
def settings():
    """Admin settings page"""
    # Get system information
    import platform
    import sys
    import os
    
    system_info = {
        'os': platform.system(),
        'python_version': platform.python_version(),
        'hostname': platform.node(),
        'cpu_count': os.cpu_count(),
        'environment': os.environ.get('FLASK_ENV', 'development')
    }
    
    # Get database connection info (sanitized)
    db_info = {
        'type': 'PostgreSQL',
        'host': 'Secured',
        'database': os.environ.get('PGDATABASE', 'Not set')
    }
    
    # Get API configuration
    api_configs = {
        'openai_available': 'OPENAI_API_KEY' in os.environ,
        'google_oauth_available': 'GOOGLE_OAUTH_CLIENT_ID' in os.environ,
        'sendgrid_available': 'SENDGRID_API_KEY' in os.environ,
        'stripe_available': 'STRIPE_SECRET_KEY' in os.environ
    }
    
    return render_template('admin/settings.html',
                          system_info=system_info,
                          db_info=db_info,
                          api_configs=api_configs)

@admin_bp.route('/api/metrics')
@admin_required
def api_metrics():
    """API endpoint to return metrics data for dashboard charts"""
    import random
    from datetime import datetime, timedelta
    
    # Generate sample data for the past 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)
    
    # Engine health metrics (success rate percentage)
    engine_health = []
    success_rate = 85  # Start with a reasonable success rate
    for date in dates:
        # Random fluctuation between -5 and +5
        fluctuation = random.uniform(-5, 5)
        # Ensure success rate stays between 75 and 100
        new_rate = max(75, min(100, success_rate + fluctuation))
        engine_health.append({
            'date': date,
            'success_rate': round(new_rate, 1)
        })
        success_rate = new_rate
    
    # User signups (random count per day)
    user_signups = []
    for date in dates:
        user_signups.append({
            'date': date,
            'count': random.randint(0, 5)  # 0-5 new users per day
        })
    
    # Opportunity counts (random additions per day)
    opp_counts = []
    for date in dates:
        opp_counts.append({
            'date': date,
            'count': random.randint(5, 20)  # 5-20 new opportunities per day
        })
    
    return {
        'engine_health': engine_health,
        'user_signups': user_signups,
        'opp_counts': opp_counts
    }

@admin_bp.route('/api/users')
@admin_required
def api_users():
    """API endpoint to return user data"""
    from flask import current_app, jsonify
    
    users_list = []
    try:
        with current_app.app_context():
            from models import User
            users = User.query.order_by(User.created_at.desc()).all()
            for user in users:
                users_list.append({
                    'id': user.id,
                    'email': user.email,
                    'name': user.name or 'N/A',
                    'membership': user.membership_level,
                    'created_at': user.created_at.strftime('%Y-%m-%d') if user.created_at else 'N/A',
                    'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never'
                })
    except Exception as e:
        logger.error(f"Error querying User data: {e}")
    
    return {'users': users_list}

@admin_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def api_delete_user(user_id):
    """API endpoint to delete a user"""
    from flask import current_app, jsonify
    
    try:
        with current_app.app_context():
            from models import db, User
            user = User.query.get(user_id)
            if user:
                db.session.delete(user)
                db.session.commit()
                return {'status': 'ok'}
            else:
                return {'status': 'error', 'message': 'User not found'}, 404
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return {'status': 'error', 'message': str(e)}, 500

@admin_bp.route('/api/metrics-v2')
@admin_required
def metrics_v2():
    """API endpoint to provide comprehensive metrics for the dashboard"""
    from flask import jsonify
    try:
        from metrics import get_scheduler_metrics, get_scraper_metrics, get_business_metrics
        
        # Get all metrics
        scheduler_metrics = get_scheduler_metrics()
        scraper_metrics = get_scraper_metrics()
        business_metrics = get_business_metrics()
        
        # Return combined metrics
        return jsonify({
            'scheduler': scheduler_metrics,
            'scrapers': scraper_metrics,
            'business': business_metrics
        })
    except Exception as e:
        logger.error(f"Error getting metrics-v2: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/metrics-dashboard')
@admin_required
def metrics_dashboard():
    """Admin metrics dashboard page"""
    return render_template('admin/metrics_dashboard.html')

@admin_bp.route('/email-digest-dashboard')
@admin_required
def email_digest_dashboard():
    """Admin email digest dashboard page"""
    from models import User, DigestEmail
    
    # Get active users for the test email form
    users = User.query.filter(
        User.email.isnot(None),
        User.membership_level.in_(['pro', 'premium', 'supporter'])
    ).order_by(User.email).all()
    
    # Get recent digest emails
    digests = DigestEmail.query.order_by(DigestEmail.sent_at.desc()).limit(50).all()
    
    return render_template(
        'admin/email_digest_dashboard.html',
        users=users,
        digests=digests
    )

@admin_bp.route('/api/email-digest/status')
@admin_required
def digest_status():
    """API endpoint to get email digest status info"""
    from flask import jsonify
    from models import DigestEmail
    
    try:
        # Try to import the scheduler info
        from email_digest_scheduler import get_digest_scheduler_info
        scheduler_info = get_digest_scheduler_info()
    except ImportError:
        logger.warning("Could not import email_digest_scheduler module")
        scheduler_info = {
            'active': False,
            'error': 'Email digest scheduler not available'
        }
    except Exception as e:
        logger.error(f"Error getting email digest scheduler info: {e}")
        scheduler_info = {
            'active': False,
            'error': str(e)
        }
    
    # Get the latest digest email
    last_digest = DigestEmail.query.order_by(DigestEmail.sent_at.desc()).first()
    
    # Get total count of digest emails
    total_count = DigestEmail.query.count()
    
    # Get count of successful digest emails
    success_count = DigestEmail.query.filter_by(status='sent').count()
    
    # Get count of failed digest emails
    failed_count = DigestEmail.query.filter_by(status='failed').count()
    
    # Get count of test digest emails
    test_count = DigestEmail.query.filter_by(status='test').count()
    
    # Combine database info with scheduler info
    status_info = {
        'last_run': last_digest.sent_at.isoformat() if last_digest else None,
        'total_emails_sent': total_count,
        'successful_emails': success_count,
        'failed_emails': failed_count,
        'test_emails': test_count
    }
    
    # Add scheduler info
    status_info.update(scheduler_info)
    
    return jsonify(status_info)

@admin_bp.route('/api/email-digest/test', methods=['POST'])
@admin_required
def test_digest_email():
    """API endpoint to send a test digest email to a specific user"""
    from flask import jsonify, request
    import email_digest
    
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    try:
        # Send test digest email
        success = email_digest.test_digest_email(user_id)
        
        if success:
            return jsonify({'status': 'success', 'message': f'Test digest email sent to user {user_id}'})
        else:
            return jsonify({'status': 'error', 'message': f'Failed to send test digest email to user {user_id}'}), 500
    except Exception as e:
        logger.error(f"Error sending test digest email: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@admin_bp.route('/api/email-digest/run-now', methods=['POST'])
@admin_required
def run_digest_now():
    """API endpoint to manually run the digest email job"""
    from flask import jsonify, current_app
    
    # Try to use the scheduler first if available
    try:
        from email_digest_scheduler import trigger_digest_job_now
        success = trigger_digest_job_now(current_app._get_current_object())
        
        if success:
            return jsonify({'success': True, 'message': 'Digest job scheduled to run in a few seconds'})
        else:
            logger.warning("Scheduler could not trigger the job, falling back to direct execution")
            # Fall through to direct execution
    except ImportError:
        logger.warning("Email digest scheduler not available, running directly")
        # Fall through to direct execution
    except Exception as scheduler_error:
        logger.error(f"Error triggering scheduled digest job: {scheduler_error}")
        # Fall through to direct execution
    
    # Direct execution as fallback
    try:
        import email_digest
        success = email_digest.run_weekly_digest()
        
        if success:
            return jsonify({'success': True, 'message': 'Digest email job executed successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to run digest email job directly'}), 500
    except Exception as e:
        logger.error(f"Error running digest email job directly: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def init_app(app):
    """Initialize the admin blueprint"""
    app.register_blueprint(admin_bp)
    logger.info("Admin blueprint registered successfully")