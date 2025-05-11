#!/usr/bin/env python3
"""
Zarf Test Digest Email

This script sends a test digest email to Zarf's account.
"""

import os
import sys
import logging
from datetime import datetime, timedelta

# Adjust path to import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import application modules
from main import app, db
from models import User, DigestEmail, Opportunity
from email_digest import send_weekly_digest
from email_service import get_email_service
from jinja2 import Environment, FileSystemLoader

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("zarf_digest_test")

def create_test_opportunities():
    """Create some test opportunities if needed"""
    opps_count = Opportunity.query.count()
    if opps_count < 10:
        logger.info(f"Found only {opps_count} opportunities. Creating test opportunities...")
        
        # Create some test opportunities
        test_opps = [
            {
                "title": "Digital Art Exhibition 2025",
                "source": "Modern Digital Gallery",
                "description": "Submit your digital artwork for our annual exhibition.",
                "tags": "digital art,exhibition,contemporary",
                "location": "New York, NY",
                "category": "Exhibition",
                "deadline": datetime.utcnow() + timedelta(days=30),
                "url": "https://example.com/digital-art-exhibition"
            },
            {
                "title": "Sculpture Residency Program",
                "source": "Art Foundation",
                "description": "3-month residency for sculptors to work on new pieces.",
                "tags": "sculpture,residency,3d art",
                "location": "Los Angeles, CA",
                "category": "Residency",
                "deadline": datetime.utcnow() + timedelta(days=45),
                "url": "https://example.com/sculpture-residency"
            },
            {
                "title": "Photography Grant 2025",
                "source": "Visual Arts Council",
                "description": "$5,000 grant for emerging photographers.",
                "tags": "photography,grant,emerging artists",
                "location": "Chicago, IL",
                "category": "Grant",
                "deadline": datetime.utcnow() + timedelta(days=60),
                "url": "https://example.com/photography-grant"
            },
            {
                "title": "Art in Public Spaces Commission",
                "source": "City Arts Department",
                "description": "Commission for a public art installation in the downtown area.",
                "tags": "public art,commission,installation",
                "location": "Boston, MA",
                "category": "Commission",
                "deadline": datetime.utcnow() + timedelta(days=90),
                "url": "https://example.com/public-art-commission"
            },
            {
                "title": "Painting Workshop Series",
                "source": "Community Art Center",
                "description": "Lead a series of painting workshops for the community.",
                "tags": "painting,education,workshop",
                "location": "Seattle, WA",
                "category": "Teaching",
                "deadline": datetime.utcnow() + timedelta(days=30),
                "url": "https://example.com/painting-workshop"
            }
        ]
        
        for opp_data in test_opps:
            opp = Opportunity(**opp_data)
            db.session.add(opp)
        
        db.session.commit()
        logger.info(f"Created {len(test_opps)} test opportunities for the digest email")
    
    return Opportunity.query.limit(5).all()

def send_digest_direct():
    """Send digest email using direct template rendering"""
    email = "myproletto@gmail.com"
    
    with app.app_context():
        # Get user or create new one
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, name="Zarf", membership_level="premium")
            user.profile_tags = "painting,digital art,sculpture,photography"
            db.session.add(user)
            db.session.commit()
            logger.info(f"Created test user: {email}")
            
        # Get opportunities
        opportunities = create_test_opportunities()
        
        # Load email template
        env = Environment(loader=FileSystemLoader('templates/emails'))
        template = env.get_template('digest_email.html')
        
        # Render email
        html_content = template.render(
            user=user,
            opportunities=opportunities,
            current_date=datetime.utcnow().strftime('%B %d, %Y'),
            unsubscribe_url=f"https://www.myproletto.com/unsubscribe?email={user.email}"
        )
        
        # Send email
        email_service = get_email_service()
        success = email_service.send_email(
            to_email=user.email,
            subject="Your Weekly Art Opportunities Digest",
            html_content=html_content
        )
        
        if success:
            # Record the digest email
            digest_email = DigestEmail(user_id=user.id, sent_at=datetime.utcnow())
            db.session.add(digest_email)
            db.session.commit()
            logger.info(f"✅ Sent digest to {user.email}")
            return True
        else:
            logger.error(f"❌ Failed to send digest to {user.email}")
            return False

if __name__ == "__main__":
    print("=" * 80)
    print("=" * 25 + " ZARF DIGEST EMAIL TEST " + "=" * 25)
    print("=" * 80)
    print("\nSending test digest email to Zarf's account...")
    
    # Set server name for URL generation
    app.config['SERVER_NAME'] = os.environ.get('REPLIT_DEV_DOMAIN', 'www.myproletto.com')
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    app.config['APPLICATION_ROOT'] = '/'
    
    success = send_digest_direct()
    
    if success:
        print("\nTest completed successfully. Check your inbox for the digest email.")
    else:
        print("\nTest failed. Check the logs for more information.")
    
    print("\nMake sure to verify:")
    print("- HTML formatting and styling")
    print("- Images and logo display properly")
    print("- Opportunity links work correctly with UTM parameters")
    print("- Unsubscribe link is functional")
    print("- Personalization elements show correct user data")
    print("- Dates are properly formatted")