import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') 
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    STRIPE_SECRET= os.environ.get('STRIPE_SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://flask_user:password@localhost/mad_app'
    SQLALCHEMY_TRACK_MODIFICATIONS = False