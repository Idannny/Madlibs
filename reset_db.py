from app import create_app
from extensions import db

app = create_app()

with app.app_context():
    # Drop all tables
    db.drop_all()
    # Create all tables
    db.create_all()
    print("Database reset complete!") 