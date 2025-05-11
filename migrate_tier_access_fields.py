#!/usr/bin/env python3
"""
Migration script to add tier-based access fields to the Opportunity model
- state field for state-based filtering
- membership_level field for tier-based access
- type field for opportunity type categorization
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from flask import Flask
from sqlalchemy import text
import sqlalchemy
from sqlalchemy.exc import SQLAlchemyError

from db_models import db, Opportunity

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app():
    """Create a Flask app for database operations"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def detect_states_from_location(location):
    """Detect US state from location field if possible"""
    if not location:
        return None
        
    location = location.lower()
    
    # Dictionary of state names and abbreviations
    states = {
        'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR', 'california': 'CA',
        'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE', 'florida': 'FL', 'georgia': 'GA',
        'hawaii': 'HI', 'idaho': 'ID', 'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA',
        'kansas': 'KS', 'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
        'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS', 'missouri': 'MO',
        'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV', 'new hampshire': 'NH', 'new jersey': 'NJ',
        'new mexico': 'NM', 'new york': 'NY', 'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH',
        'oklahoma': 'OK', 'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
        'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT', 'vermont': 'VT',
        'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV', 'wisconsin': 'WI', 'wyoming': 'WY',
        # Add abbreviations as keys too
        'al': 'AL', 'ak': 'AK', 'az': 'AZ', 'ar': 'AR', 'ca': 'CA',
        'co': 'CO', 'ct': 'CT', 'de': 'DE', 'fl': 'FL', 'ga': 'GA',
        'hi': 'HI', 'id': 'ID', 'il': 'IL', 'in': 'IN', 'ia': 'IA',
        'ks': 'KS', 'ky': 'KY', 'la': 'LA', 'me': 'ME', 'md': 'MD',
        'ma': 'MA', 'mi': 'MI', 'mn': 'MN', 'ms': 'MS', 'mo': 'MO',
        'mt': 'MT', 'ne': 'NE', 'nv': 'NV', 'nh': 'NH', 'nj': 'NJ',
        'nm': 'NM', 'ny': 'NY', 'nc': 'NC', 'nd': 'ND', 'oh': 'OH',
        'ok': 'OK', 'or': 'OR', 'pa': 'PA', 'ri': 'RI', 'sc': 'SC',
        'sd': 'SD', 'tn': 'TN', 'tx': 'TX', 'ut': 'UT', 'vt': 'VT',
        'va': 'VA', 'wa': 'WA', 'wv': 'WV', 'wi': 'WI', 'wy': 'WY'
    }
    
    # Check for state names in the location
    words = location.replace(',', ' ').split()
    for word in words:
        if word in states:
            return states[word]
            
    # Check if the entire location contains a state name
    for state_name in states:
        if state_name in location and len(state_name) > 2:  # Only check full state names, not abbreviations
            return states[state_name]
    
    return None

def detect_opportunity_type(opportunity):
    """Determine the opportunity type based on various fields"""
    # Get relevant fields
    source = opportunity.source.lower() if opportunity.source else ''
    category = opportunity.category.lower() if opportunity.category else ''
    tags = opportunity.tags.lower() if opportunity.tags else ''
    title = opportunity.title.lower() if opportunity.title else ''
    description = opportunity.description.lower() if opportunity.description else ''
    
    # Check for social media indicators
    social_media_keywords = ['instagram', 'facebook', 'twitter', 'linkedin', 'social', 'post', 'platform']
    for keyword in social_media_keywords:
        if (keyword in source or keyword in category or keyword in tags or 
            keyword in title or keyword in description):
            return 'social_media'
    
    # Check for grant indicators
    grant_keywords = ['grant', 'funding', 'award', 'prize', 'scholarship', 'fellowship', 'financial']
    for keyword in grant_keywords:
        if (keyword in source or keyword in category or keyword in tags or 
            keyword in title or keyword in description):
            return 'grant'
    
    # Check for residency indicators
    residency_keywords = ['residency', 'resident', 'residence', 'studio']
    for keyword in residency_keywords:
        if (keyword in source or keyword in category or keyword in tags or 
            keyword in title or keyword in description):
            return 'residency'
    
    # Check for exhibition indicators
    exhibition_keywords = ['exhibition', 'exhibit', 'gallery', 'show', 'showcase', 'museum']
    for keyword in exhibition_keywords:
        if (keyword in source or keyword in category or keyword in tags or 
            keyword in title or keyword in description):
            return 'exhibition'
    
    # Check for opportunity indicators
    opportunity_keywords = ['opportunity', 'call', 'application', 'submit', 'apply']
    for keyword in opportunity_keywords:
        if (keyword in source or keyword in category or keyword in tags or 
            keyword in title or keyword in description):
            return 'opportunity'
    
    # Default type
    return 'general'

def determine_membership_level(opportunity, opportunity_type):
    """Determine appropriate membership level for an opportunity"""
    # Default premium level for most opportunities
    if not opportunity_type:
        return 'premium'
        
    # Social media opportunities are free tier
    if opportunity_type == 'social_media':
        return 'free'
    
    # General opportunities are free tier
    if opportunity_type == 'general':
        return 'free'
    
    # Grants and residencies are usually premium
    if opportunity_type in ['grant', 'residency']:
        return 'premium'
    
    # Exhibitions could be supporter tier depending on state
    if opportunity_type == 'exhibition':
        # If we have state information, it's for supporter tier
        if opportunity.state:
            return 'supporter'
        return 'premium'
    
    # Default to premium for anything else
    return 'premium'

def check_columns_exist(app):
    """Check if the necessary columns already exist"""
    with app.app_context():
        try:
            # Check if columns exist using reflection (more reliable than queries)
            inspector = sqlalchemy.inspect(db.engine)
            columns = inspector.get_columns('opportunity')
            column_names = [col['name'] for col in columns]
            
            needed_columns = ['state', 'membership_level', 'type']
            missing_columns = [col for col in needed_columns if col not in column_names]
            
            if missing_columns:
                logger.info(f"Missing columns: {', '.join(missing_columns)}")
                return False
            else:
                logger.info("All necessary columns already exist")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Unexpected database error: {str(e)}")
            raise

def add_columns_if_needed(app):
    """Add the necessary columns if they don't exist"""
    with app.app_context():
        try:
            # Check if columns exist first
            if check_columns_exist(app):
                return
                
            # Add the columns using raw SQL
            logger.info("Adding new columns to opportunity table")
            db.session.execute(text("ALTER TABLE opportunity ADD COLUMN IF NOT EXISTS state VARCHAR(50)"))
            db.session.execute(text("ALTER TABLE opportunity ADD COLUMN IF NOT EXISTS membership_level VARCHAR(20) DEFAULT 'premium'"))
            db.session.execute(text("ALTER TABLE opportunity ADD COLUMN IF NOT EXISTS type VARCHAR(50)"))
            
            # Create indexes
            logger.info("Creating indexes for new columns")
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_opportunity_state ON opportunity (state)"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_opportunity_membership_level ON opportunity (membership_level)"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_opportunity_type ON opportunity (type)"))
            
            db.session.commit()
            logger.info("Successfully added new columns and indexes")
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error adding columns: {str(e)}")
            raise

def migrate_opportunity_data(app, batch_size=500):
    """Migrate existing opportunity data to populate the new fields"""
    with app.app_context():
        try:
            # Count total records for progress reporting
            total_count = Opportunity.query.count()
            logger.info(f"Found {total_count} opportunities to process")
            
            # Process in batches to avoid memory issues
            offset = 0
            updated_count = 0
            
            while True:
                # Get a batch of opportunities
                opportunities = Opportunity.query.order_by(Opportunity.id).offset(offset).limit(batch_size).all()
                if not opportunities:
                    break
                    
                batch_updates = 0
                for opportunity in opportunities:
                    # Detect state from location
                    state = detect_states_from_location(opportunity.location)
                    if state:
                        opportunity.state = state
                    
                    # Determine opportunity type
                    opportunity_type = detect_opportunity_type(opportunity)
                    opportunity.type = opportunity_type
                    
                    # Set membership level based on type and state
                    opportunity.membership_level = determine_membership_level(opportunity, opportunity_type)
                    
                    batch_updates += 1
                
                # Commit the batch
                db.session.commit()
                updated_count += batch_updates
                offset += batch_size
                
                # Log progress
                progress = min(100, round(updated_count / total_count * 100, 1))
                logger.info(f"Processed {updated_count}/{total_count} opportunities ({progress}%)")
            
            logger.info(f"Successfully updated {updated_count} opportunities")
            return updated_count
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during migration: {str(e)}")
            raise

def main():
    """Main entry point for the migration script"""
    parser = argparse.ArgumentParser(description='Migrate the Opportunity model to add tier-based access fields')
    parser.add_argument('--check-only', action='store_true', help='Only check if migration is needed, don\'t modify data')
    parser.add_argument('--batch-size', type=int, default=500, help='Number of records to process in each batch')
    args = parser.parse_args()
    
    try:
        # Create Flask app context
        app = create_app()
        
        logger.info("Starting migration for tier-based access fields")
        
        # Check if the columns already exist
        columns_exist = check_columns_exist(app)
        
        if args.check_only:
            logger.info(f"Check only mode: Migration {'not ' if not columns_exist else ''}needed")
            return 0 if columns_exist else 1
        
        # Add columns if needed
        if not columns_exist:
            logger.info("Adding new columns to the Opportunity table")
            add_columns_if_needed(app)
        
        # Migrate data
        logger.info("Migrating existing opportunity data")
        updated_count = migrate_opportunity_data(app, args.batch_size)
        
        logger.info(f"Migration completed successfully. Updated {updated_count} opportunities.")
        return 0
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())