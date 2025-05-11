"""
Migration script to add the Feedback model to the database
"""
from main import app, db
from models import Feedback

def migrate():
    with app.app_context():
        # Create the Feedback table
        db.create_all()
        print("Feedback table created successfully")

if __name__ == "__main__":
    migrate()