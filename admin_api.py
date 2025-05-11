"""
Proletto Admin API

This module provides API endpoints for the admin dashboard metrics and analytics.
These endpoints return JSON data that is consumed by the admin dashboard charts and widgets.
"""

import os
import json
import psutil
import logging
from datetime import datetime, timedelta
from sqlalchemy import func
from flask import Blueprint, jsonify, request, current_app, g
from flask_login import login_required

from admin_utils import admin_required
from models import User, Portfolio, Opportunity, Application, Engine
from cache_utils import get_cache_stats

# Initialize logger
logger = logging.getLogger(__name__)

# Create blueprint
admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/admin/api')


@admin_api_bp.route('/metrics-v2', methods=['GET'])
@login_required
@admin_required
def metrics_v2():
    """
    Comprehensive API endpoint to provide all metrics for the admin dashboard.
    Returns all data needed for the dashboard in a single request to minimize
    client-side API calls.
    
    Query parameters:
        range: int - Number of days to include in the data (default: 30)
        chart: str - Specific chart to return data for (default: all)
        period: str - Period for time-series data (daily, weekly, monthly)
    """
    try:
        # Get query parameters
        days_range = request.args.get('range', '30', type=int)
        chart_type = request.args.get('chart', 'all')
        period = request.args.get('period', 'daily')
        
        # Initialize response data
        response_data = {
            'success': True,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Get stats for all dashboard components
        if chart_type == 'all' or chart_type == 'stats':
            response_data['stats'] = get_dashboard_stats(days_range)
        
        # Get user growth data
        if chart_type == 'all' or chart_type == 'userGrowth':
            response_data['userGrowth'] = get_user_growth_data(days_range, period)
        
        # Get user distribution data
        if chart_type == 'all' or chart_type == 'userDistribution':
            response_data['userDistribution'] = get_user_distribution_data()
        
        # Get opportunity sources data
        if chart_type == 'all' or chart_type == 'opportunitySources':
            response_data['opportunitySources'] = get_opportunity_sources_data()
        
        # Get engine performance data
        if chart_type == 'all' or chart_type == 'enginePerformance':
            response_data['enginePerformance'] = get_engine_performance_data()
        
        # Get user retention data
        if chart_type == 'all' or chart_type == 'retention':
            response_data['retention'] = get_user_retention_data(days_range)
        
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"Error in metrics API: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f"Error retrieving metrics data: {str(e)}"
        })


@admin_api_bp.route('/users/growth', methods=['GET'])
@login_required
@admin_required
def users_growth_api():
    """API endpoint to get user growth data for the chart"""
    try:
        days_range = request.args.get('range', '30', type=int)
        period = request.args.get('period', 'daily')
        
        data = get_user_growth_data(days_range, period)
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error in users growth API: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f"Error retrieving user growth data: {str(e)}"
        })


@admin_api_bp.route('/users/distribution', methods=['GET'])
@login_required
@admin_required
def users_distribution_api():
    """API endpoint to get user distribution data for the chart"""
    try:
        data = get_user_distribution_data()
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error in users distribution API: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f"Error retrieving user distribution data: {str(e)}"
        })


@admin_api_bp.route('/opportunities/sources', methods=['GET'])
@login_required
@admin_required
def opportunity_sources_api():
    """API endpoint to get opportunity sources data for the chart"""
    try:
        data = get_opportunity_sources_data()
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error in opportunity sources API: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f"Error retrieving opportunity sources data: {str(e)}"
        })


@admin_api_bp.route('/engine/performance', methods=['GET'])
@login_required
@admin_required
def engine_performance_api():
    """API endpoint to get engine performance data for the chart"""
    try:
        data = get_engine_performance_data()
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error in engine performance API: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f"Error retrieving engine performance data: {str(e)}"
        })


@admin_api_bp.route('/system/health', methods=['GET'])
@login_required
@admin_required
def system_health_api():
    """API endpoint to get system health metrics"""
    try:
        data = get_system_health_data()
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error in system health API: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f"Error retrieving system health data: {str(e)}"
        })


@admin_api_bp.route('/retention', methods=['GET'])
@login_required
@admin_required
def user_retention_api():
    """API endpoint to get user retention data"""
    try:
        days_range = request.args.get('range', '180', type=int)
        data = get_user_retention_data(days_range)
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error in user retention API: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f"Error retrieving user retention data: {str(e)}"
        })


# Helper functions for gathering data

def get_dashboard_stats(days_range=30):
    """Get overall stats for the dashboard"""
    try:
        # Get date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_range)
        previous_start_date = start_date - timedelta(days=days_range)
        
        # Get total users count
        total_users = User.query.count()
        
        # Get premium users count (any paid tier)
        premium_users = User.query.filter(User.membership_tier != 'free').count()
        
        # Get total opportunities count
        try:
            total_opportunities = Opportunity.query.count()
        except:
            # Fallback to the opportunities.json file if database table doesn't exist
            opportunities_path = os.path.join(current_app.root_path, 'data', 'opportunities.json')
            if os.path.exists(opportunities_path):
                with open(opportunities_path, 'r') as f:
                    opportunities_data = json.load(f)
                    total_opportunities = len(opportunities_data)
            else:
                total_opportunities = 0
        
        # Get active engines count
        try:
            active_engines = Engine.query.filter_by(active=True).count()
        except:
            # If Engine model doesn't exist, try to get from cache or config
            try:
                if hasattr(current_app, 'cache_backend') and current_app.cache_backend:
                    active_engines = current_app.cache_backend.get('active_engines_count', 0)
                else:
                    # Fallback to a reasonable default
                    active_engines = 5
            except:
                active_engines = 5
        
        # Get user growth rate (compared to previous period)
        users_current_period = User.query.filter(
            User.created_at >= start_date,
            User.created_at <= end_date
        ).count()
        
        users_previous_period = User.query.filter(
            User.created_at >= previous_start_date,
            User.created_at <= start_date
        ).count()
        
        if users_previous_period > 0:
            user_growth_rate = ((users_current_period - users_previous_period) / users_previous_period) * 100
        else:
            user_growth_rate = 0
        
        # Get premium user growth rate
        premium_current_period = User.query.filter(
            User.membership_tier != 'free',
            User.created_at >= start_date,
            User.created_at <= end_date
        ).count()
        
        premium_previous_period = User.query.filter(
            User.membership_tier != 'free',
            User.created_at >= previous_start_date,
            User.created_at <= start_date
        ).count()
        
        if premium_previous_period > 0:
            premium_growth_rate = ((premium_current_period - premium_previous_period) / premium_previous_period) * 100
        else:
            premium_growth_rate = 0
        
        # Get opportunity growth rate
        try:
            opps_current_period = Opportunity.query.filter(
                Opportunity.created_at >= start_date,
                Opportunity.created_at <= end_date
            ).count()
            
            opps_previous_period = Opportunity.query.filter(
                Opportunity.created_at >= previous_start_date,
                Opportunity.created_at <= start_date
            ).count()
            
            if opps_previous_period > 0:
                opportunity_growth_rate = ((opps_current_period - opps_previous_period) / opps_previous_period) * 100
            else:
                opportunity_growth_rate = 0
        except:
            # Fallback if Opportunity model doesn't have created_at field or doesn't exist
            opportunity_growth_rate = 0
        
        # Get engine change rate
        # This would typically track changes in the number of active engines
        # For now, we'll return 0 as engines are usually a fixed number
        engine_change_rate = 0
        
        return {
            'totalUsers': total_users,
            'premiumUsers': premium_users,
            'totalOpportunities': total_opportunities,
            'activeEngines': active_engines,
            'userGrowthRate': user_growth_rate,
            'premiumGrowthRate': premium_growth_rate,
            'opportunityGrowthRate': opportunity_growth_rate,
            'engineChangeRate': engine_change_rate
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}", exc_info=True)
        raise


def get_user_growth_data(days_range=30, period='daily'):
    """Get user growth data for the chart"""
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_range)
        
        labels = []
        total_users_data = []
        premium_users_data = []
        
        if period == 'daily':
            # Daily data points
            current_date = start_date
            while current_date <= end_date:
                next_date = current_date + timedelta(days=1)
                
                # Format date for label
                labels.append(current_date.strftime('%b %d'))
                
                # Get total users count up to this date
                total_count = User.query.filter(User.created_at <= next_date).count()
                total_users_data.append(total_count)
                
                # Get premium users count up to this date
                premium_count = User.query.filter(
                    User.membership_tier != 'free', 
                    User.created_at <= next_date
                ).count()
                premium_users_data.append(premium_count)
                
                current_date = next_date
        
        elif period == 'weekly':
            # Weekly data points
            weeks = days_range // 7
            for i in range(weeks + 1):
                week_end = end_date - timedelta(days=i*7)
                week_start = week_end - timedelta(days=7)
                
                # Format date range for label
                labels.append(f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}")
                
                # Get total users count up to this week
                total_count = User.query.filter(User.created_at <= week_end).count()
                total_users_data.append(total_count)
                
                # Get premium users count up to this week
                premium_count = User.query.filter(
                    User.membership_tier != 'free', 
                    User.created_at <= week_end
                ).count()
                premium_users_data.append(premium_count)
        
        elif period == 'monthly':
            # Monthly data points
            months = days_range // 30
            for i in range(months + 1):
                month_end = end_date - timedelta(days=i*30)
                month_start = month_end - timedelta(days=30)
                
                # Format date range for label
                labels.append(month_end.strftime('%b %Y'))
                
                # Get total users count up to this month
                total_count = User.query.filter(User.created_at <= month_end).count()
                total_users_data.append(total_count)
                
                # Get premium users count up to this month
                premium_count = User.query.filter(
                    User.membership_tier != 'free', 
                    User.created_at <= month_end
                ).count()
                premium_users_data.append(premium_count)
        
        # Reverse lists so they're in chronological order
        labels.reverse()
        total_users_data.reverse()
        premium_users_data.reverse()
        
        return {
            'labels': labels,
            'totalUsers': total_users_data,
            'premiumUsers': premium_users_data
        }
    except Exception as e:
        logger.error(f"Error getting user growth data: {str(e)}", exc_info=True)
        raise


def get_user_distribution_data():
    """Get user distribution data for the chart"""
    try:
        # Get counts by membership tier
        tiers = ['free', 'essentials', 'insider', 'gallery']
        labels = ['Free', 'Essentials', 'Proletto Insider', 'Gallery/Event']
        values = []
        
        for tier in tiers:
            count = User.query.filter_by(membership_tier=tier).count()
            values.append(count)
        
        return {
            'labels': labels,
            'values': values
        }
    except Exception as e:
        logger.error(f"Error getting user distribution data: {str(e)}", exc_info=True)
        raise


def get_opportunity_sources_data():
    """Get opportunity sources data for the chart"""
    try:
        # Try to get from database
        try:
            result = current_app.db.session.query(
                Opportunity.type,
                func.count(Opportunity.id)
            ).group_by(Opportunity.type).all()
            
            labels = [r[0] for r in result]
            values = [r[1] for r in result]
            
            # If no types are found, create fallback
            if not labels:
                raise Exception("No opportunity types found")
                
        except Exception as db_error:
            logger.warning(f"Could not get opportunity sources from database: {str(db_error)}")
            
            # Fallback to opportunities.json
            opportunities_path = os.path.join(current_app.root_path, 'data', 'opportunities.json')
            if os.path.exists(opportunities_path):
                with open(opportunities_path, 'r') as f:
                    opportunities_data = json.load(f)
                
                # Count by opportunity type
                type_counts = {}
                for opp in opportunities_data:
                    opp_type = opp.get('type', 'Other')
                    if opp_type in type_counts:
                        type_counts[opp_type] += 1
                    else:
                        type_counts[opp_type] = 1
                
                labels = list(type_counts.keys())
                values = list(type_counts.values())
            else:
                # If no opportunities.json either, create placeholder labels
                labels = ['Grants', 'Residencies', 'Exhibitions', 'Commissions', 'Competitions', 'Others']
                values = [0, 0, 0, 0, 0, 0]
        
        return {
            'labels': labels,
            'values': values
        }
    except Exception as e:
        logger.error(f"Error getting opportunity sources data: {str(e)}", exc_info=True)
        raise


def get_engine_performance_data():
    """Get engine performance data for the chart"""
    try:
        # Try to get engines from database
        try:
            engines = Engine.query.all()
            labels = [engine.name for engine in engines]
            found = [engine.opportunities_found for engine in engines]
            matched = [engine.opportunities_matched for engine in engines]
        except Exception as db_error:
            logger.warning(f"Could not get engines from database: {str(db_error)}")
            
            # Fallback to engines from cache or config
            try:
                if hasattr(current_app, 'cache_backend') and current_app.cache_backend:
                    engines_data = current_app.cache_backend.get('engines_performance', None)
                    if engines_data:
                        labels = engines_data.get('labels', [])
                        found = engines_data.get('found', [])
                        matched = engines_data.get('matched', [])
                    else:
                        raise Exception("No engines data in cache")
                else:
                    raise Exception("No cache backend available")
            except:
                # Final fallback to placeholder data
                labels = ['NY Engine', 'CA Engine', 'Global Engine', 'Exhibition Engine', 'Grant Engine', 'Residency Engine']
                found = [0, 0, 0, 0, 0, 0]
                matched = [0, 0, 0, 0, 0, 0]
        
        return {
            'labels': labels,
            'found': found,
            'matched': matched
        }
    except Exception as e:
        logger.error(f"Error getting engine performance data: {str(e)}", exc_info=True)
        raise


def get_system_health_data():
    """Get system health metrics"""
    try:
        # Get CPU usage
        cpu_usage = psutil.cpu_percent(interval=1)
        
        # Get memory usage
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        
        # Get disk usage
        disk = psutil.disk_usage('/')
        disk_usage = disk.percent
        
        # Get API response time (simulated)
        api_response_time = 128  # ms
        
        # Get cache hit rate
        try:
            if hasattr(current_app, 'cache_backend') and current_app.cache_backend:
                cache_stats = get_cache_stats()
                if cache_stats and 'hit_rate' in cache_stats:
                    cache_hit_rate = cache_stats['hit_rate']
                else:
                    cache_hit_rate = 0
            else:
                cache_hit_rate = 0
        except:
            cache_hit_rate = 0
        
        return {
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'disk_usage': disk_usage,
            'api_response_time': api_response_time,
            'cache_hit_rate': cache_hit_rate
        }
    except Exception as e:
        logger.error(f"Error getting system health data: {str(e)}", exc_info=True)
        raise


def get_user_retention_data(days_range=180):
    """Get user retention data for cohort analysis"""
    try:
        # Define cohort periods (typically months)
        end_date = datetime.utcnow()
        months = days_range // 30
        cohort_periods = []
        
        for i in range(months):
            period_end = end_date - timedelta(days=i*30)
            period_start = period_end - timedelta(days=30)
            cohort_periods.append((period_start, period_end))
        
        # Reverse to get chronological order
        cohort_periods.reverse()
        
        # Get retention data for each cohort
        datasets = []
        labels = ['Month 1', 'Month 2', 'Month 3', 'Month 4', 'Month 5', 'Month 6']
        colors = [
            'rgba(108, 92, 231, 1)',
            'rgba(0, 184, 148, 1)',
            'rgba(9, 132, 227, 1)',
            'rgba(253, 203, 110, 1)',
            'rgba(214, 48, 49, 1)',
            'rgba(253, 121, 168, 1)'
        ]
        
        for i, (start_date, end_date) in enumerate(cohort_periods):
            if i >= 6:  # Limit to 6 cohorts for readability
                break
                
            # Get users who signed up in this cohort
            cohort_users = User.query.filter(
                User.created_at >= start_date,
                User.created_at <= end_date
            ).all()
            
            if not cohort_users:
                continue
                
            cohort_size = len(cohort_users)
            cohort_user_ids = [user.id for user in cohort_users]
            
            # Calculate retention for each month after signup
            retention_data = [100]  # Start with 100% for Month 1
            
            for month in range(1, min(months, 6)):
                month_start = end_date + timedelta(days=month*30)
                month_end = month_start + timedelta(days=30)
                
                # Count active users in this month who were in the original cohort
                try:
                    # Using login_activity or similar table if available
                    active_cohort_users = User.query.filter(
                        User.id.in_(cohort_user_ids),
                        User.last_login >= month_start,
                        User.last_login <= month_end
                    ).count()
                except:
                    # Fallback - assume decreasing retention
                    retention_factor = 0.85 ** month
                    active_cohort_users = int(cohort_size * retention_factor)
                
                retention_percentage = (active_cohort_users / cohort_size) * 100
                retention_data.append(retention_percentage)
            
            # Format dataset for Chart.js
            dataset = {
                'label': f"{start_date.strftime('%b')} Cohort",
                'data': retention_data,
                'borderColor': colors[i % len(colors)],
                'backgroundColor': 'transparent',
                'tension': 0.1
            }
            
            datasets.append(dataset)
        
        return {
            'labels': labels[:len(datasets[0]['data']) if datasets else 0],
            'datasets': datasets
        }
    except Exception as e:
        logger.error(f"Error getting user retention data: {str(e)}", exc_info=True)
        raise


def init_app(app):
    """Initialize the admin API blueprint with the app"""
    app.register_blueprint(admin_api_bp)
    logger.info("Admin API blueprint registered successfully")