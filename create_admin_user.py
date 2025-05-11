#!/usr/bin/env python3
"""
Script to create an admin user account for Proletto
This admin account will have full access to all dashboard features
"""

import os
import sys
import logging
import json
from datetime import datetime
import hashlib
import uuid
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('create_admin')

# Create a simple Flask app for DB access
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Import the real User model to match our database
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    is_supporter = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Profile information
    bio = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(100), nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    
    # Authentication info
    auth_type = db.Column(db.String(20), default='email')  # 'email', 'google', 'facebook', etc.
    role = db.Column(db.String(20), default='user')  # 'user', 'admin', 'bot', etc.
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Password authentication fields
    password_hash = db.Column(db.String(128), nullable=True)
    password_salt = db.Column(db.String(32), nullable=True)
    password_reset_token = db.Column(db.String(100), nullable=True)
    password_reset_expires = db.Column(db.DateTime, nullable=True)
    email_confirmed = db.Column(db.Boolean, default=False)
    email_confirm_token = db.Column(db.String(100), nullable=True)
    
    # Subscription details
    membership_level = db.Column(db.String(20), default='free')  # 'free', 'supporter', 'premium'
    stripe_customer_id = db.Column(db.String(120), nullable=True)
    stripe_subscription_id = db.Column(db.String(120), nullable=True)
    
    # For Supporter tier - store selected states
    _selected_states = db.Column(db.Text, nullable=True)
    
    # Subscription dates
    subscription_start_date = db.Column(db.DateTime, nullable=True)
    subscription_end_date = db.Column(db.DateTime, nullable=True)
    
    # Referral system
    referral_code = db.Column(db.String(20), unique=True, nullable=True)
    referred_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    referral_credits = db.Column(db.Integer, default=0)
    
    # Portfolio and activity tracking
    portfolio_count = db.Column(db.Integer, default=0)
    opportunity_views = db.Column(db.Integer, default=0)
    application_count = db.Column(db.Integer, default=0)
    ai_uses = db.Column(db.Integer, default=0)
    
    # Badges and gamification
    _badges = db.Column(db.Text, nullable=True)
    
    # Store user interests for AI suggestions
    _interests = db.Column(db.Text, nullable=True)
    
    # Store last AI suggestions timestamp
    last_suggestion_time = db.Column(db.DateTime, nullable=True)
    
    def _hash_password(self, password, salt):
        """Hash a password with the given salt"""
        # Use a strong hashing algorithm (SHA-256)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # Number of iterations (higher is more secure but slower)
        )
        return key.hex()
        
    def set_password(self, password):
        """Set the password hash and salt for the user"""
        # Generate a random salt
        self.password_salt = os.urandom(16).hex()
        # Create password hash
        self.password_hash = self._hash_password(password, self.password_salt)
        # Set auth type to email
        self.auth_type = 'email'
        return True
    
    def verify_password(self, password):
        """Verify a password against the stored hash"""
        if not self.password_hash or not self.password_salt:
            return False
        
        hashed = self._hash_password(password, self.password_salt)
        return hashed == self.password_hash

def create_admin_user(username, email, password):
    """Create a new admin user if it doesn't already exist"""
    
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        
        if existing_user:
            if existing_user.role == 'admin':
                logger.info(f"Admin user with email '{email}' already exists.")
                return False
            else:
                # Upgrade to admin if user exists but is not admin
                existing_user.role = 'admin'
                existing_user.membership_level = 'premium'  # Give admin premium access
                db.session.commit()
                logger.info(f"User '{existing_user.name or email}' upgraded to admin.")
                return True
        
        # Create new admin user
        new_admin = User(
            name=username,
            email=email,
            auth_type='email',
            role='admin',
            membership_level='premium',  # Give admin premium access
            created_at=datetime.utcnow(),
            email_confirmed=True,
            referral_code='ADMIN',  # Special referral code for admin
            _badges='[{"id": "admin", "name": "Administrator", "description": "System administrator", "icon": "👑", "earned_at": "' + datetime.utcnow().isoformat() + '"}]'
        )
        
        # Set password securely
        new_admin.set_password(password)
        
        db.session.add(new_admin)
        try:
            db.session.commit()
            logger.info(f"Admin user '{username}' created successfully!")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create admin user: {e}")
            return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage: python create_admin_user.py [username] [email] [password]")
        print("If no arguments are provided, default admin credentials will be used.")
        sys.exit(0)
    
    # Default or provided credentials
    admin_username = sys.argv[1] if len(sys.argv) > 1 else "admin"
    admin_email = sys.argv[2] if len(sys.argv) > 2 else "admin@proletto.com"
    admin_password = sys.argv[3] if len(sys.argv) > 3 else "Untamed1Q"
    
    logger.info(f"Creating admin user '{admin_username}' with email '{admin_email}'")
    success = create_admin_user(admin_username, admin_email, admin_password)
    
    if success:
        print(f"✅ Admin user '{admin_username}' is ready to use!")
        print(f"Login with:")
        print(f"  Email: {admin_email}")
        print(f"  Password: {admin_password}")
    else:
        print("❌ Failed to create admin user. Check the logs for details.")