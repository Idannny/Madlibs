import os
import sys
from pathlib import Path

# Add the parent directory to Python path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app import create_app
from extensions import db

def reset_db():
    """Reset the development database"""
    app = create_app()
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        print("Creating all tables...")
        db.create_all()
        print("Database reset complete!")

def init_dev_data():
    """Initialize development database with sample data"""
    app = create_app()
    with app.app_context():
        # Add any initial development data you need
        from models import User
        
        # Create a test user
        test_user = User(
            email='test@example.com',
            name='Test User',
            has_used_free_trial=False,
            is_paid_user=False
        )
        test_user.set_password('password123')
        
        db.session.add(test_user)
        db.session.commit()
        print("Development data initialized!")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'reset':
            reset_db()
        elif sys.argv[1] == 'init':
            init_dev_data()
        elif sys.argv[1] == 'reset-all':
            reset_db()
            init_dev_data()
    else:
        print("Available commands:")
        print("python db_dev.py reset      - Reset the database")
        print("python db_dev.py init       - Initialize development data")
        print("python db_dev.py reset-all  - Reset and initialize") 