#!/usr/bin/env python3
"""
Simple, self-contained migration script to create and populate
the API key table for Proletto.
"""
import os
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, MetaData, Table, ForeignKey, inspect, text
from sqlalchemy.exc import OperationalError

# Configure the database connection
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)
metadata = MetaData()

# We'll define the table in create_table() instead to avoid the foreign key issue

def generate_key():
    """Generate a new random API key"""
    return secrets.token_urlsafe(32)

def hash_key(key):
    """Hash an API key for secure storage"""
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

def create_table():
    """Create the API key table if it doesn't exist"""
    inspector = inspect(engine)
    
    if 'api_key' not in inspector.get_table_names():
        print("Creating api_key table...")
        # Define the table without the foreign key constraint
        api_key_table = Table(
            'api_key',
            MetaData(),
            Column('id', Integer, primary_key=True),
            Column('key_hash', String(128), unique=True, nullable=False),
            Column('key_prefix', String(8), unique=True, nullable=False),
            Column('name', String(100), nullable=False),
            Column('user_id', Integer, nullable=False),  # No FK constraint, just a column
            Column('status', String(20), default='active'),
            Column('plan', String(20), default='free'),
            Column('created_at', DateTime, default=datetime.utcnow),
            Column('expires_at', DateTime, nullable=True),
            Column('last_used_at', DateTime, nullable=True),
            Column('revoked_at', DateTime, nullable=True),
            Column('request_count', Integer, default=0),
            Column('rate_limit_hits', Integer, default=0),
        )
        
        # Create just this table
        api_key_table.create(bind=engine)
        print("api_key table created successfully.")
    else:
        print("api_key table already exists.")

def get_admin_user_id():
    """Get an admin user ID from the database"""
    try:
        with engine.connect() as conn:
            # First try to find an admin user - use double quotes for the table name since it's a reserved word
            result = conn.execute(text('SELECT "id" FROM "user" WHERE "role" = \'admin\' LIMIT 1'))
            user = result.fetchone()
            
            if user:
                print(f"Found admin user with ID: {user[0]}")
                return user[0]
            
            # If no admin user, get any user
            result = conn.execute(text('SELECT "id" FROM "user" LIMIT 1'))
            user = result.fetchone()
            
            if user:
                print(f"No admin user found. Using user with ID: {user[0]}")
                return user[0]
            
            print("No users found in the database.")
            return None
    except Exception as e:
        print(f"Error fetching admin user: {e}")
        return None

def check_existing_keys():
    """Check if there are already API keys in the database"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text('SELECT COUNT(*) FROM "api_key"'))
            count = result.fetchone()[0]
            return count
    except Exception as e:
        print(f"Error checking existing keys: {e}")
        return 0

def create_initial_keys(user_id):
    """Create initial API keys for testing"""
    # Check if we already have keys
    existing_keys = check_existing_keys()
    if existing_keys > 0:
        print(f"Database already has {existing_keys} API keys. Skipping creation.")
        return
        
    if not user_id:
        print("No user ID available. Cannot create API keys.")
        return
        
    keys_created = []
    
    # Create a key for each plan
    plans = ['free', 'pro', 'partner', 'admin']
    
    try:
        with engine.connect() as conn:
            # In newer versions of SQLAlchemy, we need to start a transaction
            trans = conn.begin()
            
            for plan in plans:
                # Create a key with this plan
                key_name = f"{plan.capitalize()} Tier Test Key"
                api_key_value = generate_key()
                prefix = api_key_value[:8]
                key_hash = hash_key(api_key_value)
                expires_at = datetime.utcnow() + timedelta(days=365)
                
                # Insert the key using SQL
                sql = text("""
                    INSERT INTO "api_key" 
                    (key_hash, key_prefix, name, user_id, plan, status, created_at, expires_at, request_count, rate_limit_hits) 
                    VALUES (:key_hash, :key_prefix, :name, :user_id, :plan, :status, :created_at, :expires_at, :request_count, :rate_limit_hits)
                """)
                
                conn.execute(sql, {
                    'key_hash': key_hash,
                    'key_prefix': prefix,
                    'name': key_name,
                    'user_id': user_id,
                    'plan': plan,
                    'status': 'active',
                    'created_at': datetime.utcnow(),
                    'expires_at': expires_at,
                    'request_count': 0,
                    'rate_limit_hits': 0
                })
                
                # Save for display
                keys_created.append({
                    "plan": plan,
                    "key": api_key_value,
                    "prefix": prefix,
                    "expires_at": expires_at.isoformat()
                })
            
            # Add hardcoded test keys
            hardcoded_keys = [
                {"key": "freekey123", "plan": "free", "name": "Free Test Key"},
                {"key": "prokey456", "plan": "pro", "name": "Pro Test Key"},
                {"key": "partner789", "plan": "partner", "name": "Partner Test Key"},
            ]
            
            for key_info in hardcoded_keys:
                key_hash = hash_key(key_info["key"])
                key_prefix = key_info["key"][:8]
                expires_at = datetime.utcnow() + timedelta(days=365)
                
                # Insert hardcoded key
                sql = text("""
                    INSERT INTO "api_key" 
                    (key_hash, key_prefix, name, user_id, plan, status, created_at, expires_at, request_count, rate_limit_hits) 
                    VALUES (:key_hash, :key_prefix, :name, :user_id, :plan, :status, :created_at, :expires_at, :request_count, :rate_limit_hits)
                """)
                
                conn.execute(sql, {
                    'key_hash': key_hash,
                    'key_prefix': key_prefix,
                    'name': key_info["name"],
                    'user_id': user_id,
                    'plan': key_info["plan"],
                    'status': 'active',
                    'created_at': datetime.utcnow(),
                    'expires_at': expires_at,
                    'request_count': 0,
                    'rate_limit_hits': 0
                })
                
                keys_created.append({
                    "plan": key_info["plan"],
                    "key": key_info["key"],
                    "prefix": key_prefix,
                    "name": key_info["name"]
                })
            
            # Add the admin master key
            master_key = os.environ.get("API_KEY", "master_key_abc")
            key_hash = hash_key(master_key)
            key_prefix = master_key[:8] if len(master_key) >= 8 else master_key
            expires_at = datetime.utcnow() + timedelta(days=365)
            
            # Insert admin master key
            sql = text("""
                INSERT INTO "api_key" 
                (key_hash, key_prefix, name, user_id, plan, status, created_at, expires_at, request_count, rate_limit_hits) 
                VALUES (:key_hash, :key_prefix, :name, :user_id, :plan, :status, :created_at, :expires_at, :request_count, :rate_limit_hits)
            """)
            
            conn.execute(sql, {
                'key_hash': key_hash,
                'key_prefix': key_prefix,
                'name': "Admin Master Key",
                'user_id': user_id,
                'plan': "admin",
                'status': 'active',
                'created_at': datetime.utcnow(),
                'expires_at': expires_at,
                'request_count': 0,
                'rate_limit_hits': 0
            })
            
            keys_created.append({
                "plan": "admin",
                "key": master_key,
                "prefix": key_prefix,
                "name": "Admin Master Key"
            })
            
            # Commit changes
            trans.commit()
            
            # Success!
            print(f"Created {len(keys_created)} API keys:")
            for key in keys_created:
                print(f"  - {key.get('name', key['plan'].capitalize())}: {key['key']} (Prefix: {key['prefix']})")
            
            # Save keys to file for reference (in real app, you'd email to users)
            with open('api_keys_created.json', 'w') as f:
                json.dump(keys_created, f, indent=2)
            
            print("API keys created successfully. Keys saved to api_keys_created.json")
            
    except Exception as e:
        print(f"Error creating API keys: {e}")

def main():
    """Run the migration"""
    try:
        # Step 1: Create the table
        create_table()
        
        # Step 2: Get admin user ID
        user_id = get_admin_user_id()
        
        # Step 3: Create initial keys
        if user_id:
            create_initial_keys(user_id)
        
        print("Migration completed successfully.")
        return 0
    except Exception as e:
        print(f"Error during migration: {e}")
        return 1

if __name__ == "__main__":
    exit(main())