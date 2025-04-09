import os
from flask_talisman import Talisman

class Config:
    # Common settings
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STRIPE_KEY = os.getenv('STRIPE_SECRET')
    STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
    
    # CSP Settings
    CSP = {
        'default-src': ["'self'"],
        'script-src': [
            "'self'",
            'https://www.google.com/recaptcha/',
            'https://www.gstatic.com/recaptcha/',
            'https://js.stripe.com',
            'https://cdn.jsdelivr.net'
        ],
        'style-src': [
            "'self'",
            'https://fonts.googleapis.com'
        ],
        'font-src': [
            "'self'",
            'https://fonts.gstatic.com'
        ],
        'img-src': [
            "'self'",
            'data:',
            'https://lh3.googleusercontent.com',
            'https://*.stripe.com',
            'https://*.openai.com'
        ],
        'frame-src': [
            'https://www.google.com/recaptcha/',
            'https://js.stripe.com',
            'https://hooks.stripe.com'
        ],
        'form-action': ["'self'"],
        'frame-ancestors': ["'none'"],
        'base-uri': ["'self'"],
        'object-src': ["'none'"],
        'upgrade-insecure-requests': True
    }

class DevelopmentConfig(Config):
    DEBUG = True
    CSP = {
        'connect-src': [
            "'self'",
            'http://localhost:5000',
            'https://www.google.com/recaptcha/',
            'https://api.stripe.com',
            'https://api.openai.com',
            'https://*.stripe.com'
        ]
    }

class ProductionConfig(Config):
    DEBUG = False
    CSP = {
        'connect-src': [
            "'self'",
            'https://madapp.io',
            'https://www.google.com/recaptcha/',
            'https://api.stripe.com',
            'https://api.openai.com',
            'https://*.stripe.com'
        ]
    }

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 