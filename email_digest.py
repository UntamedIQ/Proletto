"""
Proletto Email Digest Helper

This module provides functions to send weekly digest emails to users with personalized
art opportunity recommendations. It uses Jinja2 templates and SendGrid for email delivery.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

import flask
from flask import current_app, render_template
from jinja2 import Template
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent

from models import User, DigestEmail, Opportunity, Feedback

# Set up logging
logger = logging.getLogger(__name__)

# Get SendGrid API key and from email from environment variables
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
FROM_EMAIL = os.environ.get('SENDGRID_FROM_EMAIL')

# Import the recommendation engine if available
try:
    from self_learning_bot import ArtRecommendationBot
    recommendation_bot = ArtRecommendationBot()
    logger.info("Initialized recommendation bot for digest emails")
except ImportError:
    logger.warning("Could not import ArtRecommendationBot for digest emails")
    recommendation_bot = None


def get_recommendations_for_user(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get personalized art opportunity recommendations for a user.
    
    Args:
        user_id: The ID of the user to get recommendations for
        limit: Maximum number of recommendations to return
        
    Returns:
        List of recommendation dictionaries with opportunity details
    """
    from models import db, User, Opportunity
    
    user = User.query.get(user_id)
    if not user:
        logger.error(f"User {user_id} not found for digest recommendations")
        return []
    
    # Try to use the recommendation bot if available
    if recommendation_bot:
        try:
            # Get recommendations from the AI engine
            recs = recommendation_bot.get_recommendations_for_user(user_id, limit)
            if recs and len(recs) > 0:
                return recs
        except Exception as e:
            logger.error(f"Error getting recommendations from bot: {e}")
    
    # Fallback to basic recommendations if the bot fails or doesn't exist
    logger.info(f"Using fallback recommendation method for user {user_id}")
    
    # Get opportunities that match the user's profile tags/interests
    # This is a simple implementation - the real recommendation engine would be more sophisticated
    profile_tags = user.profile_tags.split(',') if user.profile_tags else []
    
    # Base query for active opportunities
    query = Opportunity.query.filter(
        Opportunity.is_active == True,
        Opportunity.deadline > datetime.utcnow()
    ).order_by(Opportunity.deadline.asc())
    
    # If the user has profile tags, prioritize matching opportunities
    matched_opportunities = []
    if profile_tags:
        for tag in profile_tags:
            tag = tag.strip().lower()
            if not tag:
                continue
                
            # Find opportunities that match this tag
            tag_matches = query.filter(
                Opportunity.tags.like(f'%{tag}%')
            ).limit(10).all()
            
            for opp in tag_matches:
                if opp not in matched_opportunities:
                    matched_opportunities.append(opp)
                
                if len(matched_opportunities) >= limit:
                    break
                    
            if len(matched_opportunities) >= limit:
                break
    
    # If we still need more recommendations, add some recent opportunities
    if len(matched_opportunities) < limit:
        recent_opportunities = query.limit(limit - len(matched_opportunities)).all()
        for opp in recent_opportunities:
            if opp not in matched_opportunities:
                matched_opportunities.append(opp)
    
    # Convert opportunities to dictionary format
    recommendations = []
    for opp in matched_opportunities[:limit]:
        opp_tags = opp.tags.split(',') if opp.tags else []
        opp_tags = [tag.strip() for tag in opp_tags if tag.strip()]
        
        recommendations.append({
            'id': opp.id,
            'title': opp.title,
            'organization': opp.organization or 'Unknown Organization',
            'description': opp.description or '',
            'deadline': opp.deadline.strftime('%B %d, %Y') if opp.deadline else 'No deadline',
            'tags': opp_tags,
            'location': opp.location or 'Remote/Various',
            'opportunity_type': opp.opportunity_type or 'Grant/Opportunity',
            'learn_more_url': f"https://www.myproletto.com/opportunity/{opp.id}"
        })
    
    return recommendations


def send_weekly_digest(user_id: int, opportunities: List[Dict[str, Any]]) -> bool:
    """
    Send a weekly digest email to a user with personalized recommendations.
    
    Args:
        user_id: The ID of the user to send the digest to
        opportunities: List of opportunity dictionaries with details
        
    Returns:
        Boolean indicating if the email was sent successfully
    """
    if not SENDGRID_API_KEY or not FROM_EMAIL:
        logger.error("SendGrid API key or FROM_EMAIL not set")
        return False
    
    from models import db, User, DigestEmail
    
    # Get the user
    user = User.query.get(user_id)
    if not user:
        logger.error(f"User {user_id} not found for sending digest")
        return False
    
    if not user.email:
        logger.error(f"User {user_id} has no email address")
        return False
    
    # Load the email template
    try:
        html_content = render_template(
            'emails/digest_email.html',
            user=user,
            opportunities=opportunities
        )
    except Exception as e:
        logger.error(f"Error rendering digest email template: {e}")
        return False
    
    # Create the email message
    message = Mail(
        from_email=Email(FROM_EMAIL),
        to_emails=To(user.email),
        subject=f"Your Weekly Art Opportunities from Proletto",
        html_content=HtmlContent(html_content)
    )
    
    # Send the email
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        # Log the status code
        status_code = response.status_code
        logger.info(f"Sent digest email to {user.email} (status: {status_code})")
        
        # Record the email in the database
        digest_email = DigestEmail(
            user_id=user.id,
            sent_at=datetime.utcnow(),
            opportunity_count=len(opportunities),
            status='sent' if status_code == 202 else 'failed'
        )
        db.session.add(digest_email)
        db.session.commit()
        
        return status_code == 202
    except Exception as e:
        logger.error(f"Error sending digest email to {user.email}: {e}")
        
        # Record the failed email attempt
        try:
            digest_email = DigestEmail(
                user_id=user.id,
                sent_at=datetime.utcnow(),
                opportunity_count=len(opportunities),
                status='failed'
            )
            db.session.add(digest_email)
            db.session.commit()
        except Exception as db_error:
            logger.error(f"Error recording failed digest email: {db_error}")
        
        return False


def run_weekly_digest() -> bool:
    """
    Run the weekly digest email job for all Pro subscribers.
    
    Returns:
        Boolean indicating if the job completed successfully
    """
    from models import db, User
    
    logger.info("Starting weekly digest email job")
    
    # Get all Pro subscribers
    pro_users = User.query.filter(
        User.membership_level.in_(['pro', 'premium']),
        User.email.isnot(None),
        User.is_active == True
    ).all()
    
    logger.info(f"Found {len(pro_users)} active Pro/Premium subscribers for digest emails")
    
    success_count = 0
    error_count = 0
    
    for user in pro_users:
        try:
            # Get recommendations for this user
            recommendations = get_recommendations_for_user(user.id, limit=5)
            
            # Skip if no recommendations
            if not recommendations:
                logger.warning(f"No recommendations available for user {user.id}")
                continue
            
            # Send the digest email
            if send_weekly_digest(user.id, recommendations):
                success_count += 1
            else:
                error_count += 1
                
        except Exception as e:
            logger.error(f"Error processing digest for user {user.id}: {e}")
            error_count += 1
    
    logger.info(f"Weekly digest completed - {success_count} successes, {error_count} errors")
    
    return error_count == 0


def test_digest_email(user_id: int) -> bool:
    """
    Send a test digest email to a specific user.
    
    Args:
        user_id: The ID of the user to send the test email to
        
    Returns:
        Boolean indicating if the test email was sent successfully
    """
    from models import db, User, DigestEmail
    
    logger.info(f"Sending test digest email to user {user_id}")
    
    # Get the user
    user = User.query.get(user_id)
    if not user:
        logger.error(f"User {user_id} not found for test digest")
        return False
    
    # Get recommendations for this user
    recommendations = get_recommendations_for_user(user.id, limit=5)
    
    # Send the digest email
    try:
        success = send_weekly_digest(user.id, recommendations)
        
        # Update the status to 'test' in the database
        if success:
            digest_email = DigestEmail.query.filter_by(
                user_id=user.id
            ).order_by(DigestEmail.sent_at.desc()).first()
            
            if digest_email:
                digest_email.status = 'test'
                db.session.commit()
                logger.info(f"Updated digest email status to 'test' for user {user.id}")
        
        return success
    except Exception as e:
        logger.error(f"Error sending test digest email to user {user_id}: {e}")
        return False


if __name__ == "__main__":
    # This allows testing the digest email functions directly
    app = flask.Flask(__name__)
    with app.app_context():
        # Set up the database
        from models import db
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        
        # Run the digest job
        run_weekly_digest()