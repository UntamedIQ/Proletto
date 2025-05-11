#!/usr/bin/env python3
import os
import hashlib
import sys
from datetime import datetime, timedelta
import psycopg2
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get database connection parameters from environment variables
try:
    db_params = {
        'dbname': os.environ.get('PGDATABASE'),
        'user': os.environ.get('PGUSER'),
        'password': os.environ.get('PGPASSWORD'),
        'host': os.environ.get('PGHOST'),
        'port': os.environ.get('PGPORT')
    }
    
    # Verify all parameters are present
    missing_params = [k for k, v in db_params.items() if not v]
    if missing_params:
        raise ValueError(f"Missing database parameters: {', '.join(missing_params)}")
        
    logger.info("Database parameters loaded successfully")
except Exception as e:
    logger.error(f"Error loading database parameters: {e}")
    sys.exit(1)

def hash_password(password, salt):
    """Hash a password with the given salt"""
    # Uses the same algorithm as in models.py for consistency
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000  # Same number of iterations as in the model
    )
    return key.hex()

def create_test_users():
    """Create test users directly in the PostgreSQL database"""
    try:
        # Connect to the database
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        logger.info("Connected to database successfully")
        
        # Check if free user exists
        cursor.execute("SELECT id FROM users WHERE email = %s", ('free@test.com',))
        free_exists = cursor.fetchone()
        
        # Check if premium user exists
        cursor.execute("SELECT id FROM users WHERE email = %s", ('premium@test.com',))
        premium_exists = cursor.fetchone()
        
        # Current timestamp
        now = datetime.utcnow()
        one_year_later = now + timedelta(days=365)
        
        # Create free user if it doesn't exist
        if not free_exists:
            salt = os.urandom(16).hex()
            password_hash = hash_password('password123', salt)
            
            cursor.execute("""
                INSERT INTO users (
                    email, name, membership_level, auth_type, 
                    password_salt, password_hash, email_confirmed, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (
                'free@test.com', 'Free Test User', 'free', 'email',
                salt, password_hash, True, now
            ))
            
            free_user_id = cursor.fetchone()[0]
            logger.info(f"Created free test user with ID {free_user_id}")
        else:
            logger.info("Free test user already exists")
        
        # Create premium user if it doesn't exist
        if not premium_exists:
            salt = os.urandom(16).hex()
            password_hash = hash_password('password123', salt)
            
            cursor.execute("""
                INSERT INTO users (
                    email, name, membership_level, auth_type, 
                    password_salt, password_hash, email_confirmed, created_at,
                    subscription_start_date, subscription_end_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (
                'premium@test.com', 'Premium Test User', 'premium', 'email',
                salt, password_hash, True, now, now, one_year_later
            ))
            
            premium_user_id = cursor.fetchone()[0]
            logger.info(f"Created premium test user with ID {premium_user_id}")
        else:
            logger.info("Premium test user already exists")
        
        # Commit the transaction
        conn.commit()
        logger.info("All test users created successfully")
        
    except Exception as e:
        logger.error(f"Error creating test users: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    create_test_users()