#!/usr/bin/env python3
"""
Proletto Metrics Collection Module

This module provides functionality to collect and format various metrics
for the Proletto system, including scheduler health, scraper success rates,
business metrics, and user activity.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import func, desc, and_

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_scheduler_metrics(days: int = 14) -> List[Dict[str, Any]]:
    """
    Get scheduler health metrics for the past X days
    
    Args:
        days: Number of days of history to include
        
    Returns:
        List of daily metrics with date and success rate
    """
    try:
        # Import locally to avoid circular imports
        from ap_scheduler import get_scheduler_info
        
        # Get current scheduler state
        scheduler_info = get_scheduler_info()
        
        # Generate metrics for the past X days
        metrics = []
        
        # In a real implementation, we would query a database table
        # that tracks scheduler job executions. For now, we'll generate
        # sample data based on the current state.
        current_date = datetime.now()
        
        for i in range(days):
            date = (current_date - timedelta(days=i)).strftime('%Y-%m-%d')
            
            # Simple logic to generate synthetic success rates
            # A real implementation would query actual success/failure data
            if scheduler_info.get('consecutive_failures', 0) > 0 and i < 2:
                # If we have current failures, show them in recent data
                success_rate = max(50, 100 - (scheduler_info.get('consecutive_failures', 0) * 10))
            else:
                # Otherwise high success rate with small variations
                import random
                success_rate = min(100, max(80, 95 + random.randint(-5, 5)))
            
            metrics.append({
                'date': date,
                'success_rate': success_rate,
                'job_count': scheduler_info.get('total_runs', 0) - i if i < scheduler_info.get('total_runs', 0) else 0
            })
        
        # Sort chronologically
        return sorted(metrics, key=lambda x: x['date'])
    
    except Exception as e:
        logger.error(f"Error getting scheduler metrics: {e}")
        return []

def get_scraper_metrics() -> List[Dict[str, Any]]:
    """
    Get success metrics for different scrapers
    
    Returns:
        List of scraper metrics with site name and success rate
    """
    try:
        # Get list of scraper engines
        scrapers = [
            "creative-capital", "artjobs", "nyfa", "artsthread", "artsy", 
            "collegeart", "museumjobs", "callforentry", "submittable", 
            "artworkarchive", "artplaceamerica", "artiststhrive", "hyperallergic",
            "artnews", "artforum", "theartnewspaper"
        ]
        
        # In a real implementation, we would track scraper success/failure 
        # in a database. For now, we'll generate sample data.
        metrics = []
        
        for site in scrapers:
            # Read bot_scheduler_state.json if it exists
            state_file = "bot_scheduler_state.json"
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    
                # Use actual success data if available
                total_runs = state.get('total_runs', 0)
                total_successes = state.get('total_successes', 0)
                
                # Calculate success rate
                success_rate = int((total_successes / total_runs * 100) if total_runs > 0 else 90)
            else:
                # Generate a reasonable success rate
                import random
                success_rate = random.randint(70, 100)
            
            metrics.append({
                'site': site,
                'success_rate': success_rate,
                'last_run': datetime.now().strftime('%Y-%m-%d')
            })
        
        return metrics
    
    except Exception as e:
        logger.error(f"Error getting scraper metrics: {e}")
        return []

def get_business_metrics(days: int = 30) -> Dict[str, Any]:
    """
    Get business metrics such as MRR, signups, etc.
    
    Args:
        days: Number of days of trend data to include
        
    Returns:
        Dictionary with current stats and trend data
    """
    try:
        # Import models within the function to avoid circular imports
        from models import User, DigestEmail
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Create database session
        engine = create_engine(os.environ.get("DATABASE_URL"))
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Current stats
        current = {}
        
        # Get user counts
        current['user_count'] = session.query(User).filter(User.is_active == True).count()
        current['premium_count'] = session.query(User).filter(
            User.is_active == True, 
            User.subscription_tier >= 2
        ).count()
        
        # Get opportunity count
        try:
            with open('opportunities.json', 'r') as f:
                opportunities = json.load(f)
                current['opportunity_count'] = len(opportunities)
        except Exception:
            current['opportunity_count'] = 0
        
        # Get digest email count
        try:
            current['digest_count'] = session.query(DigestEmail).count()
        except Exception:
            current['digest_count'] = 0
        
        # Calculate MRR
        # $5 for supporter tier (tier 2), $12 for premium tier (tier 3)
        supporter_count = session.query(User).filter(
            User.is_active == True, 
            User.subscription_tier == 2
        ).count()
        
        premium_count = session.query(User).filter(
            User.is_active == True, 
            User.subscription_tier == 3
        ).count()
        
        current['mrr'] = (supporter_count * 5) + (premium_count * 12)
        
        # Historical trend data
        trend = []
        current_date = datetime.now()
        
        for i in range(days):
            date = (current_date - timedelta(days=i)).strftime('%Y-%m-%d')
            date_obj = current_date - timedelta(days=i)
            
            # Get signup count for that day
            signups = session.query(User).filter(
                func.date(User.created_at) == date_obj.date()
            ).count()
            
            # For MRR, this would typically be a different table tracking
            # historical MRR values. For now, we'll make a crude estimate.
            # In a real implementation, this should be pre-calculated and stored.
            factor = 1 - (i / (days * 2))  # Assume some growth over time
            mrr = max(0, int(current['mrr'] * factor))
            
            trend.append({
                'date': date,
                'mrr': mrr,
                'signups': signups
            })
        
        # Get user activity metrics (logins, API calls, etc.)
        activity = []
        for i in range(days):
            date = (current_date - timedelta(days=i)).strftime('%Y-%m-%d')
            
            # In a real implementation, this would query from login and API logs
            # For now, we'll generate reasonable sample data
            import random
            activity.append({
                'date': date,
                'logins': random.randint(current['user_count'] // 10, current['user_count'] // 3),
                'api_calls': random.randint(50, 200)
            })
        
        # Clean up
        session.close()
        
        # Sort chronologically
        trend = sorted(trend, key=lambda x: x['date'])
        activity = sorted(activity, key=lambda x: x['date'])
        
        return {
            'current': current,
            'trend': trend,
            'activity': activity
        }
    
    except Exception as e:
        logger.error(f"Error getting business metrics: {e}")
        return {
            'current': {
                'user_count': 0,
                'premium_count': 0,
                'opportunity_count': 0,
                'digest_count': 0,
                'mrr': 0
            },
            'trend': [],
            'activity': []
        }