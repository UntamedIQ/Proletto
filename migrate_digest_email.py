#!/usr/bin/env python3
"""
Migrate Digest Email

This script adds the DigestEmail model to the database to 
support the Email Digest Automation feature.

Usage:
    python migrate_digest_email.py
"""

import os
import sys
import logging
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("migrate_digest_email")

# Create a base class for declarative models
Base = declarative_base()

# Define the DigestEmail model for migration
class DigestEmail(Base):
    """Tracks weekly digest emails sent to Pro subscribers"""
    __tablename__ = 'digest_email'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    opportunity_count = Column(Integer, default=0) 
    status = Column(String(20), default='sent')  # sent, failed, test
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)

def run_migration():
    """Run the migration to add the DigestEmail model"""
    try:
        # Get database URL from environment variable
        database_url = os.environ.get("DATABASE_URL")
        
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            return False
        
        # Create database engine
        engine = create_engine(database_url)
        
        # Create the table for DigestEmail model if it doesn't exist
        Base.metadata.create_all(engine, tables=[DigestEmail.__table__])
        
        logger.info("Successfully created DigestEmail table")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error creating DigestEmail table: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)