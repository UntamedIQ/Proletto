#!/usr/bin/env python3
"""
Migration script to update the Opportunity table schema
Adds scraped_at and engine fields, along with indexes for better performance
"""

import os
import sys
import json
from datetime import datetime
from flask import Flask
from sqlalchemy import Column, DateTime, String, text, Index
from db_models import db, Opportunity

# Create a simple Flask app for this migration
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def migrate_opportunity_schema():
    """Migrate Opportunity table schema"""
    with app.app_context():
        try:
            # Get a new connection with autocommit=True to avoid transaction issues
            conn = db.engine.connect().execution_options(isolation_level="AUTOCOMMIT")
            
            # Add scraped_at column if it doesn't exist
            try:
                conn.execute(text("SELECT scraped_at FROM opportunity LIMIT 1"))
                print("✓ scraped_at column already exists")
            except Exception:
                print("→ Adding scraped_at column")
                conn.execute(text(
                    "ALTER TABLE opportunity ADD COLUMN scraped_at TIMESTAMP"
                ))
                # Set initial values for existing rows
                conn.execute(text(
                    "UPDATE opportunity SET scraped_at = updated_at"
                ))
                
            # Add engine column if it doesn't exist
            try:
                conn.execute(text("SELECT engine FROM opportunity LIMIT 1"))
                print("✓ engine column already exists")
            except Exception:
                print("→ Adding engine column")
                conn.execute(text(
                    "ALTER TABLE opportunity ADD COLUMN engine VARCHAR(100)"
                ))
                # Set initial values for existing rows based on source
                conn.execute(text(
                    "UPDATE opportunity SET engine = CASE "
                    "WHEN source LIKE '%instagram%' THEN 'instagram_ads' "
                    "WHEN source LIKE '%california%' THEN 'california' "
                    "WHEN source LIKE '%new_york%' THEN 'new_york' "
                    "ELSE 'unknown' END"
                ))
            
            # Add indexes if they don't exist
            for idx_name, column in [
                ('idx_opportunity_source', 'source'),
                ('idx_opportunity_category', 'category'),
                ('idx_opportunity_scraped_at', 'scraped_at'),
                ('idx_opportunity_engine', 'engine')
            ]:
                try:
                    # Check if index exists
                    result = conn.execute(text(
                        f"SELECT 1 FROM pg_indexes WHERE indexname = '{idx_name}'"
                    )).fetchone()
                    
                    if result:
                        print(f"✓ Index {idx_name} already exists")
                    else:
                        print(f"→ Creating index {idx_name}")
                        conn.execute(text(
                            f"CREATE INDEX {idx_name} ON opportunity ({column})"
                        ))
                except Exception as e:
                    print(f"! Error checking/creating index {idx_name}: {str(e)}")
            
            print("✓ Migration completed successfully")
        except Exception as e:
            print(f"! Migration failed: {str(e)}")
            return False
        
        return True

def seed_opportunities_from_json():
    """Populate the opportunities table from the JSON file"""
    # Skip if this is a production environment
    if os.environ.get('FLASK_ENV') == 'production':
        print("⚠️ Skipping opportunity seeding in production")
        return
        
    print("→ Seeding opportunities from JSON file")
    json_file = 'opportunities.json'
    
    if not os.path.exists(json_file):
        print(f"! JSON file not found: {json_file}")
        return
        
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if not isinstance(data, list):
            print(f"! Invalid JSON format in {json_file}")
            return
            
        with app.app_context():
            # First, check if we already have data
            count = db.session.query(Opportunity).count()
            if count > 0:
                print(f"✓ Database already has {count} opportunities, skipping seed")
                return
                
            # Create a list of opportunity objects
            print(f"→ Processing {len(data)} opportunities")
            batch_size = 100
            for i in range(0, len(data), batch_size):
                batch = data[i:i+batch_size]
                print(f"→ Adding batch {i//batch_size + 1} ({len(batch)} opportunities)")
                
                # Convert to Opportunity objects and add to session
                for item in batch:
                    # Skip if missing required fields
                    if not item.get('title'):
                        continue
                        
                    # Create opportunity from JSON data
                    opportunity = Opportunity.from_json(item)
                    db.session.add(opportunity)
                
                # Commit each batch
                db.session.commit()
                
            final_count = db.session.query(Opportunity).count()
            print(f"✓ Added {final_count} opportunities to database")
    except Exception as e:
        print(f"! Error seeding opportunities: {str(e)}")

if __name__ == '__main__':
    if not os.environ.get('DATABASE_URL'):
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)
        
    print("Starting opportunity table migration and seeding process...")
    migrate_opportunity_schema()
    seed_opportunities_from_json()
    print("Process completed.")