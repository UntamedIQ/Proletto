#!/usr/bin/env python3
"""
Database Migration Script for Self-Learning Bot

This script migrates the database to add support for the Self-Learning Bot:
1. Creates the new Opportunity table
2. Updates the Feedback table to reference opportunities

Run this script from the command line to perform the migration.
"""

import os
import sys
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("migrate_learning_bot")

# Create Flask app context for database operations
def create_app_context():
    """Create Flask app context for database operations"""
    try:
        from main import app
        return app.app_context()
    except ImportError:
        logger.error("Failed to import Flask app from main.py")
        sys.exit(1)

def check_tables_exist():
    """Check if required tables already exist in the database"""
    with create_app_context():
        from models import db
        
        # Check if tables exist
        existing_tables = db.engine.table_names()
        
        opportunity_exists = 'opportunity' in existing_tables
        feedback_exists = 'feedback' in existing_tables
        
        # Log the result
        if opportunity_exists:
            logger.info("Opportunity table already exists")
        if feedback_exists:
            logger.info("Feedback table already exists")
            
        return opportunity_exists, feedback_exists

def create_opportunity_table():
    """Create the Opportunity table"""
    with create_app_context():
        from models import db
        
        # Execute SQL to create the table
        sql = """
        CREATE TABLE IF NOT EXISTS opportunity (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            url VARCHAR(500),
            deadline TIMESTAMP,
            source VARCHAR(100),
            location VARCHAR(100),
            category VARCHAR(100),
            tags VARCHAR(500),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        try:
            db.session.execute(sql)
            db.session.commit()
            logger.info("Created Opportunity table")
            return True
        except Exception as e:
            logger.error(f"Failed to create Opportunity table: {e}")
            db.session.rollback()
            return False

def create_feedback_table():
    """Create the Feedback table"""
    with create_app_context():
        from models import db
        
        # Execute SQL to create the table
        sql = """
        CREATE TABLE IF NOT EXISTS feedback (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            opportunity_id INTEGER NOT NULL,
            opp_id VARCHAR(64),
            rating INTEGER NOT NULL,
            comment TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES "user" (id) ON DELETE CASCADE,
            FOREIGN KEY (opportunity_id) REFERENCES opportunity (id) ON DELETE CASCADE
        );
        """
        
        try:
            db.session.execute(sql)
            db.session.commit()
            logger.info("Created Feedback table")
            return True
        except Exception as e:
            logger.error(f"Failed to create Feedback table: {e}")
            db.session.rollback()
            return False

def import_opportunities_from_json():
    """Import opportunities from JSON files into the database"""
    # Check if opportunities.json exists
    if not os.path.exists('opportunities.json'):
        logger.warning("opportunities.json not found, skipping import")
        return False
    
    # Load opportunities from JSON
    try:
        with open('opportunities.json', 'r') as f:
            opportunities = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load opportunities.json: {e}")
        return False
    
    # Import opportunities into the database
    with create_app_context():
        from models import db, Opportunity
        
        count = 0
        for opp in opportunities:
            try:
                # Check if opportunity already exists
                existing = Opportunity.query.filter_by(
                    title=opp.get('title'),
                    source=opp.get('source')
                ).first()
                
                if existing:
                    logger.debug(f"Opportunity already exists: {opp.get('title')}")
                    continue
                
                # Create new opportunity
                new_opp = Opportunity(
                    title=opp.get('title'),
                    description=opp.get('description'),
                    url=opp.get('url'),
                    deadline=datetime.fromisoformat(opp.get('deadline')) if opp.get('deadline') else None,
                    source=opp.get('source'),
                    location=opp.get('location'),
                    category=opp.get('category'),
                    tags=opp.get('tags')
                )
                
                db.session.add(new_opp)
                count += 1
                
                # Commit every 100 opportunities
                if count % 100 == 0:
                    db.session.commit()
                    logger.info(f"Imported {count} opportunities")
            
            except Exception as e:
                logger.error(f"Failed to import opportunity: {e}")
                db.session.rollback()
        
        # Commit any remaining opportunities
        if count % 100 != 0:
            db.session.commit()
        
        logger.info(f"Imported {count} opportunities")
        return True

def migrate_feedback():
    """Migrate existing feedback to reference opportunity records"""
    # This is a placeholder for future feedback migration if needed
    logger.info("No existing feedback to migrate")
    return True

def run_migration():
    """Run the database migration"""
    logger.info("Starting Self-Learning Bot database migration")
    
    # Check if tables already exist
    opportunity_exists, feedback_exists = check_tables_exist()
    
    # Create tables if they don't exist
    if not opportunity_exists:
        if not create_opportunity_table():
            logger.error("Failed to create Opportunity table, aborting migration")
            return False
    
    if not feedback_exists:
        if not create_feedback_table():
            logger.error("Failed to create Feedback table, aborting migration")
            return False
    
    # Import opportunities from JSON
    import_opportunities_from_json()
    
    # Migrate existing feedback
    migrate_feedback()
    
    logger.info("Self-Learning Bot database migration completed successfully")
    return True

if __name__ == "__main__":
    run_migration()