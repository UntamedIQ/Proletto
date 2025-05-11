#!/usr/bin/env python3
"""
Database migration script to create the APIKey table for API key management.
This script creates the table and adds initial API keys for testing.
"""

import os
import sys
from datetime import datetime, timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import logging

# We need to import the models directly to avoid circular imports
db = SQLAlchemy()

# Define the User model (simplified)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), default='user')  # 'user', 'admin', 'bot', etc.
    
# Define the APIKey model (same as in models.py)
class APIKey(db.Model):
    """API Key model for tracking and managing API access keys"""
    id = db.Column(db.Integer, primary_key=True)
    
    # The actual API key (hashed for security)
    key_hash = db.Column(db.String(128), nullable=False, unique=True)
    
    # Key prefix (first 8 chars) for display/reference purposes (not hashed)
    key_prefix = db.Column(db.String(8), nullable=False, unique=True)
    
    # Name/description of this API key
    name = db.Column(db.String(100), nullable=False)
    
    # Who this key belongs to
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Key status
    status = db.Column(db.String(20), default='active')  # active, revoked, expired
    
    # Subscription plan tied to this key
    plan = db.Column(db.String(20), default='free')  # free, pro, partner, admin
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    
    # Usage tracking
    request_count = db.Column(db.Integer, default=0)
    rate_limit_hits = db.Column(db.Integer, default=0)
    
    # Define relationship with User
    user = db.relationship('User', backref='api_keys')
    
    @classmethod
    def generate_key(cls):
        """Generate a new random API key"""
        # Generate a random 32-character API key
        import secrets
        return secrets.token_urlsafe(32)
    
    @classmethod
    def hash_key(cls, key):
        """Hash an API key for secure storage"""
        # Use SHA-256 for hashing
        import hashlib
        return hashlib.sha256(key.encode('utf-8')).hexdigest()
    
    @classmethod
    def create_for_user(cls, user_id, name, plan='free', expires_in_days=None):
        """Create a new API key for a user"""
        # Generate a random API key
        api_key = cls.generate_key()
        
        # Get the first 8 characters for prefix reference
        prefix = api_key[:8]
        
        # Hash the key for storage
        hashed_key = cls.hash_key(api_key)
        
        # Create expiration date if specified
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Create the new API key record
        key_record = cls(
            key_hash=hashed_key,
            key_prefix=prefix,
            name=name,
            user_id=user_id,
            plan=plan,
            expires_at=expires_at
        )
        
        # Return both the API key (to show to user once) and the DB record
        return api_key, key_record

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("migrate_api_keys")

def create_app():
    """Create a minimal Flask app for database operations"""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    return app

def create_table():
    """Create the APIKey table if it doesn't exist"""
    with app.app_context():
        # We'll use a different approach to check if the table exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        
        if 'api_key' not in inspector.get_table_names():
            logger.info("Creating APIKey table...")
            db.create_all()
            logger.info("APIKey table created successfully.")
        else:
            logger.info("APIKey table already exists.")

def create_initial_keys():
    """Create initial API keys for testing"""
    with app.app_context():
        # Get or create an admin user
        admin = User.query.filter(User.role == 'admin').first()
        if not admin:
            logger.info("No admin user found. Looking for any user...")
            admin = User.query.first()
            if not admin:
                logger.error("No users found in the database. Cannot create API keys.")
                return
            logger.info(f"Using user {admin.email} to create API keys.")
        
        # Check if we already have keys in the database
        existing_keys = APIKey.query.count()
        if existing_keys > 0:
            logger.info(f"Database already has {existing_keys} API keys. Skipping creation.")
            return
        
        # Create sample keys for each plan
        plans = ['free', 'pro', 'partner', 'admin']
        keys_created = []
        
        for plan in plans:
            # Create a key with this plan
            key_name = f"{plan.capitalize()} Tier Test Key"
            api_key, key_record = APIKey.create_for_user(
                user_id=admin.id,
                name=key_name,
                plan=plan,
                expires_in_days=365  # 1 year expiration
            )
            
            # Store the record in the database
            db.session.add(key_record)
            
            # Save the API key for display (in a real app, you'd email this to the user)
            keys_created.append({
                "plan": plan,
                "key": api_key,
                "prefix": key_record.key_prefix,
                "expires_at": key_record.expires_at
            })
        
        # Hardcode the test keys from our rate limit test script
        hardcoded_keys = [
            {"key": "freekey123", "plan": "free", "name": "Free Test Key"},
            {"key": "prokey456", "plan": "pro", "name": "Pro Test Key"},
            {"key": "partner789", "plan": "partner", "name": "Partner Test Key"},
        ]
        
        # Also create the hardcoded test keys for our test script
        for key_info in hardcoded_keys:
            # Hash the key for storage
            key_hash = APIKey.hash_key(key_info["key"])
            key_prefix = key_info["key"][:8]
            
            # Create the new API key record
            key_record = APIKey(
                key_hash=key_hash,
                key_prefix=key_prefix,
                name=key_info["name"],
                user_id=admin.id,
                plan=key_info["plan"],
                expires_at=datetime.utcnow() + timedelta(days=365)
            )
            
            db.session.add(key_record)
            
            keys_created.append({
                "plan": key_info["plan"],
                "key": key_info["key"],
                "prefix": key_prefix,
                "name": key_info["name"]
            })
            
        # Try to get the admin master key from environment
        master_key = os.environ.get("API_KEY", "master_key_abc")
        
        # Add the admin master key
        key_hash = APIKey.hash_key(master_key)
        key_prefix = master_key[:8] if len(master_key) >= 8 else master_key
        
        key_record = APIKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            name="Admin Master Key",
            user_id=admin.id,
            plan="admin",
            expires_at=datetime.utcnow() + timedelta(days=365)
        )
        
        db.session.add(key_record)
        
        keys_created.append({
            "plan": "admin",
            "key": master_key,
            "prefix": key_prefix,
            "name": "Admin Master Key"
        })
        
        # Commit all changes
        db.session.commit()
        
        # Log the created keys
        logger.info(f"Created {len(keys_created)} API keys:")
        for key in keys_created:
            logger.info(f"  - {key['name'] if 'name' in key else key['plan'].capitalize()}: {key['key']} (Prefix: {key['prefix']})")
        
        logger.info("API keys created successfully.")

if __name__ == "__main__":
    app = create_app()
    
    try:
        create_table()
        create_initial_keys()
        logger.info("API key migration completed successfully.")
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        sys.exit(1)