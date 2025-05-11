#!/usr/bin/env python3
"""
Database Migration Script for CI/CD Pipeline

This script handles database migrations safely during the CI/CD deployment process.
It uses Flask-Migrate to apply any pending database migrations.
"""

import os
import sys
import time
import logging
from flask_migrate import Migrate, upgrade
from sqlalchemy.exc import OperationalError, ProgrammingError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('db-migration')

# Import the Flask app and models
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
try:
    from main import app, db
    import models  # noqa: F401 - Import models to ensure they are registered
except ImportError as e:
    logger.error(f"Failed to import application: {e}")
    sys.exit(1)

def wait_for_db(max_retries=5, retry_interval=5):
    """Wait for database to be available"""
    for attempt in range(1, max_retries + 1):
        try:
            # Try a simple database query
            with app.app_context():
                db.session.execute("SELECT 1")
                logger.info("Database connection successful")
                return True
        except OperationalError as e:
            logger.warning(f"Database not available yet (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                logger.info(f"Waiting {retry_interval} seconds before retry...")
                time.sleep(retry_interval)
            else:
                logger.error("Max retries reached. Database is not available.")
                return False

def run_migrations(safe_mode=True):
    """Run database migrations with Flask-Migrate"""
    try:
        with app.app_context():
            # Initialize Flask-Migrate
            migrate = Migrate(app, db)
            
            # Check if we need to create tables first (for fresh deployments)
            needs_create_all = False
            try:
                # Try to access a table to check if the schema exists
                db.session.execute("SELECT 1 FROM alembic_version")
            except ProgrammingError:
                logger.info("Alembic version table not found, will create all tables first")
                needs_create_all = True
            
            if needs_create_all:
                logger.info("Creating database tables...")
                db.create_all()
                logger.info("Database tables created successfully")
            
            # Apply migrations
            logger.info("Running database migrations...")
            upgrade()
            logger.info("Database migrations completed successfully")
            
            return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

def main():
    """Main entry point"""
    logger.info("Starting database migration script")
    
    # Wait for database to be available
    if not wait_for_db():
        logger.error("Database is not available. Aborting migration.")
        sys.exit(1)
    
    # Run migrations
    if run_migrations():
        logger.info("Migration process completed successfully")
        sys.exit(0)
    else:
        logger.error("Migration process failed")
        sys.exit(1)

if __name__ == "__main__":
    main()