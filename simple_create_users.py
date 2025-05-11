#!/usr/bin/env python3
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User, Base

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("DATABASE_URL environment variable not set")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def create_test_users():
    # Check if users already exist
    free_exists = session.query(User).filter_by(email='free@test.com').first()
    premium_exists = session.query(User).filter_by(email='premium@test.com').first()
    
    if not free_exists:
        free_user = User(
            username='free_test', 
            email='free@test.com',
            membership_level='free'
        )
        free_user.set_password('password123')
        session.add(free_user)
        print('Created free user: free@test.com / password123')
    else:
        print('Free user already exists')
    
    if not premium_exists:
        premium_user = User(
            username='premium_test', 
            email='premium@test.com',
            membership_level='premium'
        )
        premium_user.set_password('password123')
        session.add(premium_user)
        print('Created premium user: premium@test.com / password123')
    else:
        print('Premium user already exists')
    
    session.commit()

if __name__ == '__main__':
    create_test_users()