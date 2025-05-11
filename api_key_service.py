#!/usr/bin/env python3
"""
API Key Verification Service

This module provides functions for verifying API keys against the database.
It handles key hashing, verification, and status checks.
"""

import os
import hashlib
import binascii
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import create_engine, text

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL')
engine = create_engine(DATABASE_URL) if DATABASE_URL else None

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
    
    # For hardcoded legacy keys during transition
    legacy_keys = {
        "freekey123": {"plan": "free", "name": "Free Test Key"},
        "prokey456": {"plan": "pro", "name": "Pro Test Key"},
        "partner789": {"plan": "partner", "name": "Partner Test Key"},
    }
    
    if api_key in legacy_keys:
        return True, {
            'plan': legacy_keys[api_key]['plan'],
            'status': 'active',
            'name': legacy_keys[api_key]['name'],
            'id': 0,
            'user_id': 1,  # Assume admin user has ID 1
            'is_legacy': True
        }
    
    # New database verification
    try:
        # First try prefix lookup for performance 
        key_prefix = api_key[:8]  # First 8 chars are stored for quick lookups
        
        with engine.connect() as conn:
            # Look up the key by prefix first
            stmt = text('SELECT id, key_hash, name, plan, status, user_id, expires_at FROM "api_key" WHERE key_prefix = :prefix')
            result = conn.execute(stmt, {"prefix": key_prefix})
            key_records = result.fetchall()
            
            # If we found potential matches by prefix, verify full hash
            key_hash = hash_key(api_key)
            
            for record in key_records:
                if record['key_hash'] == key_hash:
                    # Found a match, check if it's active and not expired
                    if record['status'] != 'active':
                        return False, None
                        
                    # Check expiration
                    if record['expires_at'] and record['expires_at'] < datetime.utcnow():
                        return False, None
                        
                    # Update request count (for analytics)
                    update_stmt = text('UPDATE "api_key" SET request_count = request_count + 1 WHERE id = :id')
                    conn.execute(update_stmt, {"id": record['id']})
                    
                    # Return key info
                    return True, {
                        'id': record['id'],
                        'name': record['name'],
                        'plan': record['plan'],
                        'status': record['status'],
                        'user_id': record['user_id'],
                        'is_db': True
                    }
                    
        # No matching key found
        return False, None
        
    except Exception as e:
        print(f"Error verifying API key: {e}")
        # Fallback to legacy keys if DB verification fails
        if api_key in legacy_keys:
            return True, {
                'plan': legacy_keys[api_key]['plan'],
                'status': 'active',
                'name': legacy_keys[api_key]['name'],
                'id': 0,
                'user_id': 1,
                'is_legacy': True
            }
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
        
    try:
        key_prefix = api_key[:8]
        
        with engine.connect() as conn:
            # First find the key
            stmt = text('SELECT id FROM "api_key" WHERE key_prefix = :prefix')
            result = conn.execute(stmt, {"prefix": key_prefix})
            key_record = result.fetchone()
            
            if key_record:
                # Increment the rate limit hit counter
                update_stmt = text('UPDATE "api_key" SET rate_limit_hits = rate_limit_hits + 1 WHERE id = :id')
                conn.execute(update_stmt, {"id": key_record['id']})
                return True
                
        return False
        
    except Exception as e:
        print(f"Error recording rate limit hit: {e}")
        return False

# Simple testing function to verify the module works
def test_key_verification():
    """Test key verification with a known key"""
    # Test the master key
    master_key = os.environ.get('API_KEY', 'master_key_abc')
    valid, info = verify_key(master_key)
    print(f"Master key valid: {valid}, info: {info}")
    
    # Test a legacy key
    legacy_key = "prokey456"
    valid, info = verify_key(legacy_key)
    print(f"Legacy key valid: {valid}, info: {info}")
    
    # Test a random key (should fail)
    invalid_key = "invalid_key_123"
    valid, info = verify_key(invalid_key)
    print(f"Invalid key valid: {valid}, info: {info}")
    
    # Test a database key (would need to be inserted first)
    try:
        with open('api_keys_created.json', 'r') as f:
            import json
            keys = json.load(f)
            if keys:
                db_key = keys[0]['key']
                valid, info = verify_key(db_key)
                print(f"DB key valid: {valid}, info: {info}")
    except Exception as e:
        print(f"Error testing DB key: {e}")


if __name__ == "__main__":
    test_key_verification()