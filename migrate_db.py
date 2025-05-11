#!/usr/bin/env python3
"""
Database migration script to update schema
"""
import os
import sys
from main import app, db
from sqlalchemy import text

def update_database_schema():
    """Update database schema to match models.py"""
    with app.app_context():
        # Define the columns to check and add if they don't exist
        columns_to_add = {
            "avatar_url": "VARCHAR(500)",
            "bio": "TEXT",
            "location": "VARCHAR(100)",
            "referral_code": "VARCHAR(20)",
            "referred_by_id": "INTEGER",
            "referral_credits": "INTEGER",
            "portfolio_count": "INTEGER",
            "opportunity_views": "INTEGER",
            "application_count": "INTEGER",
            "ai_uses": "INTEGER",
            "_badges": "TEXT",
            "_interests": "TEXT",
            "last_suggestion_time": "TIMESTAMP",
            "subscription_start_date": "TIMESTAMP",
            "subscription_end_date": "TIMESTAMP",
            "_selected_states": "TEXT"
        }
        
        for column_name, column_type in columns_to_add.items():
            try:
                # Check if column exists
                result = db.session.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='user' AND column_name='{column_name}'"))
                exists = result.fetchone()
                
                if not exists:
                    print(f"Adding {column_name} column to user table...")
                    db.session.execute(text(f"ALTER TABLE \"user\" ADD COLUMN {column_name} {column_type}"))
                    db.session.commit()
                    print(f"{column_name} column added successfully")
                else:
                    print(f"{column_name} column already exists")
            except Exception as e:
                print(f"Error adding {column_name} column: {e}")
                db.session.rollback()
            
def create_test_user():
    """Create a test user for the platform"""
    from models import User
    from datetime import datetime, timedelta
    
    with app.app_context():
        # Check if test user already exists
        test_user = User.query.filter_by(email='test@proletto.com').first()
        
        if test_user:
            print('Test user already exists with ID:', test_user.id)
            print('Login email: test@proletto.com')
            print('Login password: password123')
            # Update password if needed
            if not test_user.password_hash:
                test_user.password_hash = "password123"
                db.session.commit()
                print('Updated test user password')
        else:
            # Create a new test user with comprehensive profile
            test_user = User(
                email='test@proletto.com',
                name='Test Artist',
                is_supporter=True,
                bio='Contemporary painter focused on urban landscapes and social commentary.',
                location='Brooklyn, NY',
                auth_type='email',
                role='user',
                password_hash='password123',  # Simple password for testing
                last_login=datetime.utcnow(),
                email_confirmed=True,
                membership_level='supporter',
                referral_code='TESTUSER2025',
                portfolio_count=3,
                opportunity_views=27,
                application_count=5,
                ai_uses=12,
                _badges='{"badges": ["early_adopter", "portfolio_creator", "application_starter"]}',
                _interests='{"media": ["painting", "digital", "mixed-media"], "subjects": ["urban", "social", "abstract"]}',
                _selected_states='["New York", "California", "Florida"]',
                subscription_start_date=datetime.utcnow() - timedelta(days=30),
                subscription_end_date=datetime.utcnow() + timedelta(days=335)
            )
            
            # Add to database
            db.session.add(test_user)
            db.session.commit()
            
            print('Created new test user with ID:', test_user.id)
            print('Login email: test@proletto.com')
            print('Login password: password123')
            print('Membership level: supporter')

if __name__ == "__main__":
    # First update the database schema
    update_database_schema()
    
    # Then create the test user
    create_test_user()