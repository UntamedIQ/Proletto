#!/usr/bin/env python3
from models import User, db
from main import app

def create_test_users():
    with app.app_context():
        # Check if users already exist
        free_exists = User.query.filter_by(email='free@test.com').first()
        premium_exists = User.query.filter_by(email='premium@test.com').first()
        
        if not free_exists:
            free_user = User(
                username='free_test',
                email='free@test.com',
                membership_level='free'
            )
            free_user.set_password('password123')
            db.session.add(free_user)
            print(f'Created free user: free@test.com / password123')
        else:
            print('Free user already exists')
        
        if not premium_exists:
            premium_user = User(
                username='premium_test',
                email='premium@test.com',
                membership_level='premium'
            )
            premium_user.set_password('password123')
            db.session.add(premium_user)
            print(f'Created premium user: premium@test.com / password123')
        else:
            print('Premium user already exists')
        
        db.session.commit()

if __name__ == '__main__':
    create_test_users()