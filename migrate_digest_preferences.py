"""
User Digest Preferences Migration

This script adds digest preference fields to the User model:
- digest_enabled: Boolean flag to enable/disable digest emails
- digest_day_of_week: Integer (0-6) representing preferred day (0=Monday, 6=Sunday)
- digest_failure_count: Count of consecutive failures when sending emails
- last_digest_sent: Timestamp of last successful digest email
"""

import sys
import os
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('digest_migration')

# Get database URL from environment
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    logger.error("DATABASE_URL environment variable not set")
    sys.exit(1)

# Import database models (after setting environment variables)
from flask import Flask
from db_models import db, User
from sqlalchemy import text

def run_migration():
    """Run the database migration to add digest preference fields"""
    # Create a temporary Flask app to use application context
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database with the app
    db.init_app(app)
    
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            existing_columns = [column['name'] for column in inspector.get_columns('users')]
            
            # Build list of missing columns
            columns_to_add = []
            migration_statements = []
            
            # Check for each new column
            if 'digest_enabled' not in existing_columns:
                columns_to_add.append('digest_enabled')
                migration_statements.append(
                    text("ALTER TABLE users ADD COLUMN digest_enabled BOOLEAN DEFAULT TRUE")
                )
                
            if 'digest_day_of_week' not in existing_columns:
                columns_to_add.append('digest_day_of_week')
                migration_statements.append(
                    text("ALTER TABLE users ADD COLUMN digest_day_of_week INTEGER DEFAULT 0")
                )
                
            if 'digest_failure_count' not in existing_columns:
                columns_to_add.append('digest_failure_count')
                migration_statements.append(
                    text("ALTER TABLE users ADD COLUMN digest_failure_count INTEGER DEFAULT 0")
                )
                
            if 'last_digest_sent' not in existing_columns:
                columns_to_add.append('last_digest_sent')
                migration_statements.append(
                    text("ALTER TABLE users ADD COLUMN last_digest_sent TIMESTAMP")
                )
            
            if not columns_to_add:
                logger.info("All digest preference columns already exist. No migration needed.")
                return True
                
            # Execute each migration statement
            logger.info(f"Adding columns: {', '.join(columns_to_add)}")
            for statement in migration_statements:
                db.session.execute(statement)
            
            # Commit the changes
            db.session.commit()
            logger.info("Migration completed successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during migration: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    logger.info("Starting digest preferences migration")
    success = run_migration()
    if success:
        logger.info("Migration completed successfully")
        sys.exit(0)
    else:
        logger.error("Migration failed")
        sys.exit(1)