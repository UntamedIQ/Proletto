#!/usr/bin/env python3
"""
API Key Management Script

This script provides functions to:
1. Create new API keys for different plans
2. View existing API keys
3. Revoke API keys
4. Check API key status
"""

import os
import sys
import random
import string
from datetime import datetime, timedelta

from sqlalchemy import create_engine, MetaData, Table, select, insert, update
from sqlalchemy.orm import sessionmaker

# Import from our custom modules
from api_key_db_service import hash_key

# Database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("Error: DATABASE_URL environment variable not set")
    sys.exit(1)

# Create engine and metadata
engine = create_engine(DATABASE_URL)
metadata = MetaData()
api_keys = Table('api_key', metadata, autoload_with=engine)

# Create session
Session = sessionmaker(bind=engine)

def generate_random_key(length=32):
    """Generate a random API key of the specified length"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def create_api_key(user_id, plan='free', name=None, days_valid=365):
    """
    Create a new API key for the specified user and plan
    
    Args:
        user_id (int): The user ID to associate with the key
        plan (str): The plan level ('free', 'pro', 'partner', 'admin')
        name (str, optional): A descriptive name for the key
        days_valid (int): Number of days until the key expires
        
    Returns:
        tuple: (raw_key, key_id) if successful, (None, None) otherwise
    """
    if plan not in ['free', 'pro', 'partner', 'admin']:
        print(f"Error: Invalid plan '{plan}'. Must be one of: free, pro, partner, admin")
        return None, None
        
    raw_key = generate_random_key()
    key_hash = hash_key(raw_key)
    key_prefix = raw_key[:8]
    
    if name is None:
        name = f"{plan.capitalize()} API Key for User {user_id}"
    
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                stmt = insert(api_keys).values(
                    key_hash=key_hash,
                    key_prefix=key_prefix,
                    name=name,
                    plan=plan,
                    user_id=user_id,
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=days_valid),
                    status='active',
                    revoked_at=None,
                    request_count=0,
                    rate_limit_hits=0
                )
                result = conn.execute(stmt)
                key_id = result.inserted_primary_key[0]
                trans.commit()
                return raw_key, key_id
            except Exception as e:
                trans.rollback()
                print(f"Error creating API key: {e}")
                return None, None
    except Exception as e:
        print(f"Database connection error: {e}")
        return None, None

def list_user_api_keys(user_id):
    """
    List all API keys for a specific user
    
    Args:
        user_id (int): The user ID to get keys for
        
    Returns:
        list: List of dictionaries containing key information
    """
    try:
        with engine.connect() as conn:
            stmt = select(
                api_keys.c.id,
                api_keys.c.key_prefix,
                api_keys.c.name,
                api_keys.c.plan,
                api_keys.c.status,
                api_keys.c.created_at,
                api_keys.c.expires_at,
                api_keys.c.last_used_at,
                api_keys.c.request_count,
                api_keys.c.rate_limit_hits
            ).where(api_keys.c.user_id == user_id)
            
            results = []
            for row in conn.execute(stmt):
                results.append({
                    'id': row.id,
                    'key_prefix': row.key_prefix,
                    'name': row.name,
                    'plan': row.plan,
                    'status': row.status,
                    'created_at': row.created_at,
                    'expires_at': row.expires_at,
                    'last_used_at': row.last_used_at,
                    'request_count': row.request_count,
                    'rate_limit_hits': row.rate_limit_hits
                })
            return results
    except Exception as e:
        print(f"Error listing API keys: {e}")
        return []

def revoke_api_key(key_id):
    """
    Revoke an API key by its ID
    
    Args:
        key_id (int): The ID of the key to revoke
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                stmt = update(api_keys).where(
                    api_keys.c.id == key_id
                ).values(
                    status='revoked',
                    revoked_at=datetime.utcnow()
                )
                result = conn.execute(stmt)
                trans.commit()
                return result.rowcount > 0
            except Exception as e:
                trans.rollback()
                print(f"Error revoking API key: {e}")
                return False
    except Exception as e:
        print(f"Database connection error: {e}")
        return False

def get_key_details(key_prefix):
    """
    Get details for a specific API key by its prefix
    
    Args:
        key_prefix (str): The 8-character prefix of the key
        
    Returns:
        dict: Key details if found, None otherwise
    """
    try:
        with engine.connect() as conn:
            stmt = select(
                api_keys.c.id,
                api_keys.c.name,
                api_keys.c.plan,
                api_keys.c.status,
                api_keys.c.user_id,
                api_keys.c.created_at,
                api_keys.c.expires_at,
                api_keys.c.last_used_at,
                api_keys.c.request_count,
                api_keys.c.rate_limit_hits
            ).where(api_keys.c.key_prefix == key_prefix)
            
            row = conn.execute(stmt).first()
            if row:
                return {
                    'id': row.id,
                    'name': row.name,
                    'plan': row.plan,
                    'status': row.status,
                    'user_id': row.user_id,
                    'created_at': row.created_at,
                    'expires_at': row.expires_at,
                    'last_used_at': row.last_used_at,
                    'request_count': row.request_count,
                    'rate_limit_hits': row.rate_limit_hits
                }
            return None
    except Exception as e:
        print(f"Error getting key details: {e}")
        return None

def promote_key_plan(key_id, new_plan):
    """
    Upgrade or downgrade an API key's plan
    
    Args:
        key_id (int): The ID of the key to upgrade
        new_plan (str): The new plan level ('free', 'pro', 'partner', 'admin')
        
    Returns:
        bool: True if successful, False otherwise
    """
    if new_plan not in ['free', 'pro', 'partner', 'admin']:
        print(f"Error: Invalid plan '{new_plan}'. Must be one of: free, pro, partner, admin")
        return False
        
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                stmt = update(api_keys).where(
                    api_keys.c.id == key_id
                ).values(
                    plan=new_plan
                )
                result = conn.execute(stmt)
                trans.commit()
                return result.rowcount > 0
            except Exception as e:
                trans.rollback()
                print(f"Error updating API key plan: {e}")
                return False
    except Exception as e:
        print(f"Database connection error: {e}")
        return False

def extend_key_expiration(key_id, days_to_add=365):
    """
    Extend the expiration date of an API key
    
    Args:
        key_id (int): The ID of the key to extend
        days_to_add (int): Number of days to add to the current expiration
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            # First get the current expiration date
            stmt = select(api_keys.c.expires_at).where(api_keys.c.id == key_id)
            row = conn.execute(stmt).first()
            
            if not row:
                print(f"Error: API key with ID {key_id} not found")
                return False
                
            current_expiry = row.expires_at
            new_expiry = current_expiry + timedelta(days=days_to_add)
            
            # Now update the expiration date
            trans = conn.begin()
            try:
                stmt = update(api_keys).where(
                    api_keys.c.id == key_id
                ).values(
                    expires_at=new_expiry
                )
                result = conn.execute(stmt)
                trans.commit()
                return result.rowcount > 0
            except Exception as e:
                trans.rollback()
                print(f"Error extending API key expiration: {e}")
                return False
    except Exception as e:
        print(f"Database connection error: {e}")
        return False

def main():
    """Main function for CLI interaction"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python manage_api_keys.py create <user_id> [plan] [name] [days]")
        print("  python manage_api_keys.py list <user_id>")
        print("  python manage_api_keys.py revoke <key_id>")
        print("  python manage_api_keys.py details <key_prefix>")
        print("  python manage_api_keys.py promote <key_id> <new_plan>")
        print("  python manage_api_keys.py extend <key_id> [days]")
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == 'create':
        if len(sys.argv) < 3:
            print("Error: Missing user_id")
            sys.exit(1)
            
        user_id = int(sys.argv[2])
        plan = sys.argv[3] if len(sys.argv) > 3 else 'free'
        name = sys.argv[4] if len(sys.argv) > 4 else None
        days = int(sys.argv[5]) if len(sys.argv) > 5 else 365
        
        raw_key, key_id = create_api_key(user_id, plan, name, days)
        if raw_key:
            print(f"API key created successfully!")
            print(f"Key ID: {key_id}")
            print(f"Plan: {plan}")
            print(f"Raw Key: {raw_key}")
            print("\nIMPORTANT: This is the only time the full key will be displayed. Save it now!")
        else:
            print("Failed to create API key")
            
    elif command == 'list':
        if len(sys.argv) < 3:
            print("Error: Missing user_id")
            sys.exit(1)
            
        user_id = int(sys.argv[2])
        keys = list_user_api_keys(user_id)
        
        if not keys:
            print(f"No API keys found for user {user_id}")
        else:
            print(f"API keys for user {user_id}:")
            for key in keys:
                print(f"  ID: {key['id']}")
                print(f"  Prefix: {key['key_prefix']}...")
                print(f"  Name: {key['name']}")
                print(f"  Plan: {key['plan']}")
                print(f"  Status: {key['status']}")
                print(f"  Created: {key['created_at']}")
                print(f"  Expires: {key['expires_at']}")
                print(f"  Requests: {key['request_count']}")
                print(f"  Rate Limit Hits: {key['rate_limit_hits']}")
                print("")
                
    elif command == 'revoke':
        if len(sys.argv) < 3:
            print("Error: Missing key_id")
            sys.exit(1)
            
        key_id = int(sys.argv[2])
        success = revoke_api_key(key_id)
        
        if success:
            print(f"API key {key_id} revoked successfully")
        else:
            print(f"Failed to revoke API key {key_id}")
            
    elif command == 'details':
        if len(sys.argv) < 3:
            print("Error: Missing key_prefix")
            sys.exit(1)
            
        key_prefix = sys.argv[2]
        details = get_key_details(key_prefix)
        
        if details:
            print(f"Details for API key with prefix {key_prefix}:")
            for key, value in details.items():
                print(f"  {key}: {value}")
        else:
            print(f"No API key found with prefix {key_prefix}")
            
    elif command == 'promote':
        if len(sys.argv) < 4:
            print("Error: Missing key_id or new_plan")
            sys.exit(1)
            
        key_id = int(sys.argv[2])
        new_plan = sys.argv[3]
        success = promote_key_plan(key_id, new_plan)
        
        if success:
            print(f"API key {key_id} promoted to {new_plan} plan successfully")
        else:
            print(f"Failed to promote API key {key_id}")
            
    elif command == 'extend':
        if len(sys.argv) < 3:
            print("Error: Missing key_id")
            sys.exit(1)
            
        key_id = int(sys.argv[2])
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 365
        success = extend_key_expiration(key_id, days)
        
        if success:
            print(f"API key {key_id} expiration extended by {days} days successfully")
        else:
            print(f"Failed to extend API key {key_id}")
            
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()