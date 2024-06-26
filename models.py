from flask_sqlalchemy import SQLAlchemy

from extensions import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    balance = db.Column(db.Float, default=0.0)
    name = db.Column(db.String(120))

    def __repr__(self):
        return f'<User {self.email}>'