#!/usr/bin/env python3
"""
Test script for verifying the database-backed API key system.
This script creates test API keys in the database and then verifies them.
"""

import os
import sys
import random
import string
import hashlib
import binascii
from datetime import datetime, timedelta
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, Boolean, insert, select

# Database setup
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Define tables needed for testing (matches actual DB schema)
api_keys = Table(
    'api_key', metadata,  # Use the singular form 'api_key' since that's what our DB uses
    Column('id', Integer, primary_key=True),
    Column('key_hash', String(128), unique=True, nullable=False),
    Column('key_prefix', String(8), index=True, nullable=False),
    Column('name', String(64), nullable=False),
    Column('plan', String(32), nullable=False, default='free'),
    Column('user_id', Integer, nullable=True),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('expires_at', DateTime, nullable=True),
    Column('last_used_at', DateTime, nullable=True),
    Column('status', String(16), default='active'),
    Column('revoked_at', DateTime, nullable=True),  # Our DB uses revoked_at instead of revoked boolean
    Column('request_count', Integer, default=0),
    Column('rate_limit_hits', Integer, default=0)
)

def generate_random_key(length=32):
    """Generate a random API key of specified length"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def hash_key(raw_key: str) -> str:
    """Hash an API key using PBKDF2"""
    dk = hashlib.pbkdf2_hmac('sha256', raw_key.encode(), b'proletto_salt', 100000)
    return binascii.hexlify(dk).decode()

def create_test_tables():
    """Create the test tables in the database"""
    print("Creating API keys table if it doesn't exist...")
    metadata.create_all(engine)
    print("Tables created!")

def create_test_keys():
    """Create test API keys with different plans"""
    test_keys = []
    
    plans = ['free', 'pro', 'partner', 'admin']
    for plan in plans:
        raw_key = generate_random_key()
        key_hash = hash_key(raw_key)
        key_prefix = raw_key[:8]
        
        # Store the test key details for testing
        test_keys.append({
            'raw_key': raw_key,
            'hash': key_hash,
            'prefix': key_prefix,
            'plan': plan,
            'name': f"Test {plan.capitalize()} Key"
        })
        
        # Insert the key into the database
        with engine.connect() as conn:
            # Start a transaction for this operation
            trans = conn.begin()
            try:
                print(f"Creating test {plan} key...")
                stmt = insert(api_keys).values(
                    key_hash=key_hash,
                    key_prefix=key_prefix,
                    name=f"Test {plan.capitalize()} Key",
                    plan=plan,
                    user_id=1,  # Assuming user ID 1 exists (admin)
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=30),
                    status='active',
                    revoked_at=None,  # Use revoked_at instead of revoked
                    request_count=0,
                    rate_limit_hits=0
                    # Removed owner field as it doesn't exist in the database
                )
                result = conn.execute(stmt)
                # Explicitly commit the transaction
                trans.commit()
                print(f"Key created with ID: {result.inserted_primary_key[0]}")
            except Exception as e:
                # Roll back the transaction if there's an error
                trans.rollback()
                print(f"Error creating key: {e}")
    
    return test_keys

def test_key_verification(test_keys):
    """Test that key verification works correctly"""
    from api_key_db_service import verify_key, record_rate_limit_hit
    
    for key_data in test_keys:
        raw_key = key_data['raw_key']
        plan = key_data['plan']
        
        print(f"\nTesting {plan} key: {raw_key[:4]}...{raw_key[-4:]}")
        
        # Verify the key
        valid, key_info = verify_key(raw_key)
        print(f"Valid: {valid}")
        print(f"Key info: {key_info}")
        
        if valid:
            # Test rate limit recording
            recorded = record_rate_limit_hit(raw_key)
            print(f"Rate limit hit recorded: {recorded}")
            
            # Check if rate limit hit count was incremented
            with engine.connect() as conn:
                stmt = select(api_keys.c.rate_limit_hits).where(api_keys.c.key_hash == key_data['hash'])
                result = conn.execute(stmt).first()
                if result:
                    print(f"Rate limit hits in database: {result[0]}")
        else:
            print("Key verification failed!")

def verify_key_in_database(key_data):
    """Verify that a key exists in the database"""
    with engine.connect() as conn:
        stmt = select(api_keys).where(api_keys.c.key_hash == key_data['hash'])
        result = conn.execute(stmt).first()
        return bool(result)

def main():
    """Main test function"""
    print("Starting API key database test...")
    
    # Create the tables
    create_test_tables()
    
    # Create test keys
    test_keys = create_test_keys()
    
    # Save the keys to a file for reference
    with open('test_api_keys.txt', 'w') as f:
        f.write("=== TEST API KEYS ===\n")
        for key in test_keys:
            f.write(f"{key['plan'].upper()} KEY: {key['raw_key']}\n")
    
    print("\nTest API keys created and saved to test_api_keys.txt")
    
    # Verify keys exist in database
    for key in test_keys:
        exists = verify_key_in_database(key)
        print(f"{key['plan']} key in database: {exists}")
    
    # Test key verification
    test_key_verification(test_keys)
    
    print("\nAPI key database test completed!")

if __name__ == "__main__":
    main()