#!/usr/bin/env python3
"""
Database-backed API Key Service

This module provides functions for verifying API keys against the database.
It handles key hashing, verification, and status checks using SQLAlchemy Core.
"""

import os
import hashlib
import binascii
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
from sqlalchemy import create_engine, Table, Column, Integer, String, DateTime, Boolean, MetaData, select, text, update

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL) if DATABASE_URL else None
metadata = MetaData()

# Define the api_key table (note: singular, not plural)
api_keys = Table(
    'api_key', metadata,  # Changed from 'api_keys' to 'api_key' to match the actual database table
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
    Column('revoked_at', DateTime, nullable=True),  # Note: using revoked_at instead of revoked boolean
    Column('request_count', Integer, default=0),
    Column('rate_limit_hits', Integer, default=0)
)

def hash_key(raw_key: str) -> str:
    """
    Hash an API key for secure storage using PBKDF2
    
    Args:
        raw_key: The raw API key string
        
    Returns:
        The hashed key as a hex string
    """
    dk = hashlib.pbkdf2_hmac('sha256', raw_key.encode(), b'proletto_salt', 100000)
    return binascii.hexlify(dk).decode()


def verify_key(api_key: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Verify an API key against the database
    
    Args:
        api_key: The raw API key to verify
        
    Returns:
        Tuple containing (is_valid, key_info)
        where key_info contains plan, status, etc. if valid, None otherwise
    """
    if not api_key or not engine:
        return False, None
    
    # Special case: environment variable master key
    master_key = os.environ.get('API_KEY')
    if master_key and api_key == master_key:
        return True, {
            'plan': 'admin',
            'status': 'active',
            'name': 'Master API Key',
            'id': 0,
            'user_id': 1,  # Assume admin user has ID 1
            'is_master': True
        }
    
    # Hash the key for comparison
    key_hash = hash_key(api_key)
    key_prefix = api_key[:8] if len(api_key) >= 8 else api_key
    now = datetime.utcnow()
    
    try:
        with engine.connect() as conn:
            # Print debug info about what we're looking for
            print(f"Looking for key with hash: {key_hash[:10]}... and prefix: {key_prefix}")
            
            # First check if the key exists and is valid
            stmt = (
                select(
                    api_keys.c.id,
                    api_keys.c.name,
                    api_keys.c.plan,
                    api_keys.c.status,
                    api_keys.c.revoked_at,  # Changed from revoked to revoked_at
                    api_keys.c.expires_at,
                    api_keys.c.user_id
                )
                .where(
                    (api_keys.c.key_hash == key_hash) &
                    (api_keys.c.key_prefix == key_prefix)
                )
            )
            row = conn.execute(stmt).first()
            
            if not row:
                # Debug: Check if key exists by prefix only to help diagnose the issue
                prefix_stmt = select(api_keys).where(api_keys.c.key_prefix == key_prefix)
                prefix_row = conn.execute(prefix_stmt).first()
                if prefix_row:
                    print(f"Found key with matching prefix but different hash")
                else:
                    print(f"No key found with prefix: {key_prefix}")
                return False, None
                
            key_id, name, plan, status, revoked_at, expires_at, user_id = row
            
            # Check if key is revoked or expired
            if revoked_at is not None:  # Changed from revoked to revoked_at is not None
                return False, None
                
            if status != 'active':
                return False, None
                
            if expires_at and expires_at < now:
                # Update key status to expired
                update_stmt = update(api_keys).where(api_keys.c.id == key_id).values(status='expired')
                conn.execute(update_stmt)
                return False, None
            
            # Update usage information
            update_stmt = update(api_keys).where(api_keys.c.id == key_id).values(
                request_count=api_keys.c.request_count + 1,
                last_used_at=now
            )
            conn.execute(update_stmt)
            
            # Return key info
            return True, {
                'id': key_id,
                'name': name,
                'plan': plan,
                'status': status,
                'user_id': user_id,
                'expires_at': expires_at
            }
    except Exception as e:
        print(f"Error verifying API key: {e}")
        return False, None


def record_rate_limit_hit(api_key: str) -> bool:
    """
    Record a rate limit hit for metrics tracking
    
    Args:
        api_key: The API key that hit a rate limit
        
    Returns:
        True if recorded successfully, False otherwise
    """
    if not api_key or not engine:
        return False
    
    # Skip recording for master key
    master_key = os.environ.get('API_KEY')
    if master_key and api_key == master_key:
        return True
    
    try:
        # Get key prefix for lookup
        key_prefix = api_key[:8] if len(api_key) >= 8 else api_key
        key_hash = hash_key(api_key)
        
        with engine.connect() as conn:
            # Update rate limit hit counter
            update_stmt = update(api_keys).where(
                (api_keys.c.key_hash == key_hash) &
                (api_keys.c.key_prefix == key_prefix)
            ).values(
                rate_limit_hits=api_keys.c.rate_limit_hits + 1
            )
            result = conn.execute(update_stmt)
            return result.rowcount > 0
    except Exception as e:
        print(f"Error recording rate limit hit: {e}")
        return False


if __name__ == "__main__":
    # Test the API key verification
    test_key = input("Enter an API key to test: ")
    valid, info = verify_key(test_key)
    print(f"Key valid: {valid}")
    if valid:
        print(f"Key info: {info}")