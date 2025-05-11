#!/usr/bin/env python3
"""
Email Digest Smoke Test

This script performs a smoke test for the Proletto Weekly Digest email system.
It generates and sends digest emails to a controlled list of test users to verify
the entire pipeline works correctly.

Usage:
    DIGEST_TEST_EMAILS=test1@example.com,test2@example.com python scripts/test_digest_send.py
"""

import os
import sys
import logging
from datetime import datetime, timedelta

# Adjust path to import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import application modules
from main import app, db
from models import User, DigestEmail, Opportunity, Feedback
from email_digest import send_weekly_digest
from self_learning_bot import get_recommendations

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("digest_smoke_test")

def main():
    # Configure app with server name for URL generation
    app.config['SERVER_NAME'] = os.environ.get('REPLIT_DEV_DOMAIN', 'www.myproletto.com')
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    app.config['APPLICATION_ROOT'] = '/'
    
    with app.app_context():
        # 1. Define your test recipient list - default to Zarf's email if not specified
        test_emails = os.getenv('DIGEST_TEST_EMAILS', 'myproletto@gmail.com').split(',')
        if not test_emails or test_emails == ['']:
            logger.error("Set DIGEST_TEST_EMAILS to a comma-separated list of emails")
            return

        # 2. Create or fetch dummy test users
        test_users = []
        for email in test_emails:
            user = User.query.filter_by(email=email).first()
            if not user:
                # Special case for Zarf's test account
                if email == "myproletto@gmail.com":
                    user = User(email=email, name="Zarf", membership_level="premium")
                else:
                    user = User(email=email, name=f"Test User ({email})", membership_level="premium")
                # Add some profile tags for recommendation matching
                user.profile_tags = "painting,digital art,sculpture,photography"
                db.session.add(user)
                db.session.commit()
                logger.info(f"Created test user: {email}")
            test_users.append(user)
            
        # 2.5. Create some test opportunities if there aren't enough
        opps_count = Opportunity.query.count()
        if opps_count < 10:
            logger.info(f"Found only {opps_count} opportunities. Creating test opportunities...")
            
            # Create some test opportunities
            test_opps = [
                {
                    "title": "Digital Art Exhibition 2025",
                    "organization": "Modern Digital Gallery",
                    "description": "Submit your digital artwork for our annual exhibition.",
                    "tags": "digital art,exhibition,contemporary",
                    "location": "New York, NY",
                    "opportunity_type": "Exhibition",
                    "deadline": datetime.utcnow() + timedelta(days=30),
                    "url": "https://example.com/digital-art-exhibition",
                    "is_active": True
                },
                {
                    "title": "Sculpture Residency Program",
                    "organization": "Art Foundation",
                    "description": "3-month residency for sculptors to work on new pieces.",
                    "tags": "sculpture,residency,3d art",
                    "location": "Los Angeles, CA",
                    "opportunity_type": "Residency",
                    "deadline": datetime.utcnow() + timedelta(days=45),
                    "url": "https://example.com/sculpture-residency",
                    "is_active": True
                },
                {
                    "title": "Photography Grant 2025",
                    "organization": "Visual Arts Council",
                    "description": "$5,000 grant for emerging photographers.",
                    "tags": "photography,grant,emerging artists",
                    "location": "Chicago, IL",
                    "opportunity_type": "Grant",
                    "deadline": datetime.utcnow() + timedelta(days=60),
                    "url": "https://example.com/photography-grant",
                    "is_active": True
                },
                {
                    "title": "Art in Public Spaces Commission",
                    "organization": "City Arts Department",
                    "description": "Commission for a public art installation in the downtown area.",
                    "tags": "public art,commission,installation",
                    "location": "Boston, MA",
                    "opportunity_type": "Commission",
                    "deadline": datetime.utcnow() + timedelta(days=90),
                    "url": "https://example.com/public-art-commission",
                    "is_active": True
                },
                {
                    "title": "Painting Workshop Series",
                    "organization": "Community Art Center",
                    "description": "Lead a series of painting workshops for the community.",
                    "tags": "painting,education,workshop",
                    "location": "Seattle, WA",
                    "opportunity_type": "Teaching",
                    "deadline": datetime.utcnow() + timedelta(days=30),
                    "url": "https://example.com/painting-workshop",
                    "is_active": True
                }
            ]
            
            for opp_data in test_opps:
                opp = Opportunity(**opp_data)
                db.session.add(opp)
            
            db.session.commit()
            logger.info(f"Created {len(test_opps)} test opportunities for the digest email")

        # 3. Send a digest to each test user
        for user in test_users:
            try:
                # Get top 5 recommendations
                recs = get_recommendations(user.id)[:5]
                send_weekly_digest(user.id, recs)
                logger.info(f"✅ Sent digest to {user.email}")
            except Exception as e:
                logger.exception(f"❌ Failed to send digest to {user.email}: {e}")

        # 4. Summarize in the DB
        sent_count = DigestEmail.query.filter(
            DigestEmail.sent_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
        ).count()
        logger.info(f"Total digests sent today: {sent_count}")

if __name__ == "__main__":
    print("=" * 80)
    print("=" * 25 + " PROLETTO DIGEST EMAIL TEST " + "=" * 25)
    print("=" * 80)
    print("\nSending test digest emails to verify the email digest system...")
    main()
    print("\nTest completed. Check your test email addresses for the digest emails.")
    print("Make sure to verify:")
    print("- HTML formatting and styling")
    print("- Images and logo display properly")
    print("- Opportunity links work correctly")
    print("- Unsubscribe link is functional")
    print("- Personalization elements show correct user data")