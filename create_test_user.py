#!/usr/bin/env python3
import os
import sys
import hashlib
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try importing from the Flask context directly
try:
    from main import app, db
    from models import User
    
    def create_test_users():
        logger.info("Creating test users in Flask context")
        with app.app_context():
            # Check if users already exist
            free_exists = User.query.filter_by(email='free@test.com').first()
            premium_exists = User.query.filter_by(email='premium@test.com').first()
            
            if not free_exists:
                free_user = User(
                    username='free_test',
                    email='free@test.com',
                    name='Free Test User',
                    membership_level='free',
                    email_confirmed=True,
                    created_at=datetime.utcnow()
                )
                free_user.set_password('password123')
                free_user.generate_referral_code()
                db.session.add(free_user)
                logger.info(f'Created free user: free@test.com / password123')
            else:
                logger.info('Free user already exists')
            
            if not premium_exists:
                premium_user = User(
                    username='premium_test',
                    email='premium@test.com',
                    name='Premium Test User',
                    membership_level='premium',
                    email_confirmed=True,
                    created_at=datetime.utcnow(),
                    subscription_start_date=datetime.utcnow(),
                    subscription_end_date=datetime.utcnow().replace(year=datetime.utcnow().year + 1)  # 1 year subscription
                )
                premium_user.set_password('password123')
                premium_user.generate_referral_code()
                db.session.add(premium_user)
                logger.info(f'Created premium user: premium@test.com / password123')
            else:
                logger.info('Premium user already exists')
            
            db.session.commit()
            logger.info("Users created and saved to database successfully")
            
    if __name__ == '__main__':
        create_test_users()
        
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.info("Trying alternative method with direct database connection")
    
    # If the Flask app import fails, try direct database connection
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Get the database URL from environment variables
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if not DATABASE_URL:
            logger.error("DATABASE_URL environment variable not set")
            sys.exit(1)
            
        logger.info(f"Connecting directly to database with SQLAlchemy")
        
        # Import models module directly
        import models
        
        # Create database connection
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create test users
        def create_test_users_direct():
            # Check if users already exist
            free_exists = session.query(models.User).filter_by(email='free@test.com').first()
            premium_exists = session.query(models.User).filter_by(email='premium@test.com').first()
            
            if not free_exists:
                free_user = models.User(
                    username='free_test',
                    email='free@test.com',
                    name='Free Test User',
                    membership_level='free',
                    email_confirmed=True,
                    created_at=datetime.utcnow()
                )
                
                # Set password securely
                free_user.password_salt = os.urandom(16).hex()
                password = 'password123'
                salt = free_user.password_salt
                free_user.password_hash = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
                free_user.auth_type = 'email'
                
                session.add(free_user)
                logger.info('Created free user: free@test.com / password123')
            else:
                logger.info('Free user already exists')
            
            if not premium_exists:
                premium_user = models.User(
                    username='premium_test',
                    email='premium@test.com',
                    name='Premium Test User',
                    membership_level='premium',
                    email_confirmed=True,
                    created_at=datetime.utcnow(),
                    subscription_start_date=datetime.utcnow(),
                    subscription_end_date=datetime.utcnow().replace(year=datetime.utcnow().year + 1)  # 1 year subscription
                )
                
                # Set password securely
                premium_user.password_salt = os.urandom(16).hex()
                password = 'password123'
                salt = premium_user.password_salt
                premium_user.password_hash = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
                premium_user.auth_type = 'email'
                
                session.add(premium_user)
                logger.info('Created premium user: premium@test.com / password123')
            else:
                logger.info('Premium user already exists')
            
            session.commit()
            logger.info("Users created and saved to database successfully")
            
        if __name__ == '__main__':
            create_test_users_direct()
            
    except Exception as e:
        logger.error(f"Failed to create test users: {e}")
        sys.exit(1)