from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from datetime import datetime, timedelta
import secrets

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    credits = db.Column(db.Integer, default=0)
    free_tries_left = db.Column(db.Integer, default=3)
    is_paid_user = db.Column(db.Boolean, default=False)
    is_email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(100), unique=True)
    email_verification_expires = db.Column(db.DateTime)
    is_oauth_user = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_verification_token(self):
        self.email_verification_token = secrets.token_urlsafe(32)
        self.email_verification_expires = datetime.utcnow() + timedelta(hours=24)
        return self.email_verification_token

    def verify_email(self, token):
        if (self.email_verification_token == token and 
            self.email_verification_expires > datetime.utcnow()):
            self.is_email_verified = True
            self.email_verification_token = None
            self.email_verification_expires = None
            return True
        return False

    def add_credits(self, amount):
        self.credits += amount
        db.session.commit()

    def use_credit(self):
        if self.credits > 0:
            self.credits -= 1
            db.session.commit()
            return True
        return False

    def use_free_try(self):
        if self.free_tries_left > 0:
            self.free_tries_left -= 1
            db.session.commit()
            return True
        return False

    def has_free_tries(self):
        return self.free_tries_left > 0

    def __repr__(self):
        return f'<User {self.email}>'
