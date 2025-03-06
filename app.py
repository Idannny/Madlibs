from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from openai import OpenAI
from dotenv import load_dotenv
import os
import stripe
from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy
from extensions import db
from models import User  
import requests

load_dotenv()  # Load environment variables from .env file

def create_app():
    app = Flask(__name__)

    # Determine environment from FLASK_ENV environment variable
    is_development = os.getenv('FLASK_ENV', 'development') == 'development'

    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY'),
        STRIPE_KEY=os.getenv('STRIPE_SECRET'),
        SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        
        # Use appropriate reCAPTCHA keys based on environment
        RECAPTCHA_SITE_KEY=os.getenv('RECAPTCHA_SITE_KEY_DEV' if is_development else 'RECAPTCHA_SITE_KEY_PROD'),
        RECAPTCHA_SECRET=os.getenv('RECAPTCHA_SECRET_DEV' if is_development else 'RECAPTCHA_SECRET_PROD'),
    )

    oauth = OAuth(app)
    db.init_app(app)

    # Initialize database tables if they don't exist
    with app.app_context():
        db.create_all()

    google = oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        access_token_url='https://accounts.google.com/o/oauth2/token',
        access_token_params=None,
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        authorize_params=None,
        api_base_url='https://www.googleapis.com/oauth2/v1/',
        client_kwargs={'scope': 'email profile'},
    )

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("No OPENAI_API_KEY found in environment variables")

    client = OpenAI(api_key=api_key)

    def verify_recaptcha(recaptcha_response):
        if not recaptcha_response:
            return False
        
        secret_key = os.getenv("RECAPTCHA_SECRET_DEV" if os.getenv('FLASK_ENV') == 'development' else "RECAPTCHA_SECRET_PROD")
        verify_url = "https://www.google.com/recaptcha/api/siteverify"
        data = {
            "secret": secret_key,
            "response": recaptcha_response
        }
        try:
            response = requests.post(verify_url, data=data)
            response.raise_for_status()
            result = response.json()
            app.logger.info(f"reCAPTCHA verification result: {result}")  # Add logging
            return result.get("success", False)
        except requests.RequestException as e:
            app.logger.error(f"ReCAPTCHA verification failed: {e}")
            return False


    @app.route('/login')
    def login():
        return google.authorize_redirect(url_for('authorized', _external=True))

    @app.route('/logout')
    def logout():
        session.pop('user', None)
        return redirect(url_for('index'))


    @app.before_request
    def load_google_token():
        token = session.get("google_token")
        if token:
            google.token = token

    @app.route('/callback')
    def authorized():
        token = google.authorize_access_token()
        if not token:
            return 'Access denied.'
        
        # Save the token in the session
        session['google_token'] = token

        user_info = google.get('userinfo').json()

        user = User.query.filter_by(email=user_info['email']).first()
        if user is None:
            new_user = User(email=user_info['email'], name=user_info.get('name'))
            db.session.add(new_user)
            db.session.commit()
            user = new_user

        session['user'] = user_info
        return redirect(url_for('profile'))

    @app.route('/')
    def index():
        user_info = None
        credits = 0
        is_paid = False

        if 'user' in session:
            user = User.query.filter_by(email=session['user']['email']).first()
            if user:
                user_info = session['user']
                is_paid = user.is_paid_user
                if not is_paid:
                    credits = 1 if not user.has_used_free_trial else 0
        else:
            # Anonymous user
            credits = 3 - session.get('usage_count', 0)

        return render_template('index.html', 
                             user_info=user_info, 
                             credits=credits,
                             is_paid=is_paid)


    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            try:
                name = request.form['name']
                email = request.form['email']
                password = request.form['password']
                
                # Check if user already exists
                if User.query.filter_by(email=email).first():
                    flash('Email address already registered')
                    return redirect(url_for('register'))
                
                # Create new user with one free trial
                user = User(
                    name=name, 
                    email=email, 
                    has_used_free_trial=False,
                    is_paid_user=False
                )
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                
                # Log the user in
                session['user'] = {'email': email, 'name': name}
                flash('Registration successful! You have one free trial available.')
                return redirect(url_for('index'))
                
            except Exception as e:
                db.session.rollback()
                flash('Registration failed. Please try again.')
                app.logger.error(f"Registration error: {str(e)}")
                return redirect(url_for('register'))
                
        return render_template('register.html')



    @app.route('/create-checkout-session', methods=['POST'])
    def create_checkout_session():
        try:
            stripe.api_key = app.config['STRIPE_KEY']
            
            success_url = url_for('payment_success', _external=True)
            cancel_url = url_for('payment_cancel', _external=True)

            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Unlimited Mad Libs Access',
                            'description': 'Unlimited access to AI-generated Mad Libs stories',
                        },
                        'unit_amount': 500,  # $5.00
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url,
                client_reference_id=session.get('user', {}).get('email'),  # Link payment to user
            )
            return jsonify({'id': checkout_session.id})
        except Exception as e:
            app.logger.error(f"Stripe error: {str(e)}")
            return jsonify(error=str(e)), 403

    @app.route('/payment-success')
    def payment_success():
        session_id = request.args.get('session_id')
        if session_id and 'user' in session:
            try:
                # Verify the payment with Stripe
                stripe.api_key = app.config['STRIPE_KEY']
                checkout_session = stripe.checkout.Session.retrieve(session_id)
                
                if checkout_session.payment_status == 'paid':
                    # Update user status
                    user = User.query.filter_by(email=session['user']['email']).first()
                    if user:
                        user.is_paid_user = True
                        db.session.commit()
                        flash('Thank you for your purchase! You now have unlimited access.')
            except Exception as e:
                app.logger.error(f"Payment verification error: {str(e)}")
                flash('There was an error verifying your payment.')
        
        return redirect(url_for('index'))

    @app.route('/cancel')
    def cancel():
        return render_template('cancel.html')

    @app.route('/profile')
    def profile():
        user_info = session.get('user')
        if not user_info:
            return redirect(url_for('index'))

        user = User.query.filter_by(email=user_info['email']).first()
        balance = user.balance if user else 0

        return render_template('profile.html', user=user_info, balance=balance)

    @app.route('/submit', methods=['POST'])
    def submit():
        # First verify reCAPTCHA
        recaptcha_response = request.form.get('g-recaptcha-response')
        app.logger.info(f"Received reCAPTCHA response: {recaptcha_response}")
        
        if not verify_recaptcha(recaptcha_response):
            return jsonify({"error": "Please complete the CAPTCHA."}), 400

        if 'user' in session:
            # Logged in user
            user = User.query.filter_by(email=session['user']['email']).first()
            if user is None:
                # User not found in database but exists in session
                session.pop('user', None)  # Clear invalid session
                return jsonify({
                    "error": "User session expired. Please login again.",
                    "require_login": True
                }), 401
            
            if not user.is_paid_user:
                if not user.has_used_free_trial:
                    # First time use - mark trial as used
                    user.has_used_free_trial = True
                    db.session.commit()
                else:
                    return jsonify({
                        "error": "Free trial used. Please purchase to continue.",
                        "require_payment": True
                    }), 403
        else:
            # Anonymous user
            if 'usage_count' not in session:
                session['usage_count'] = 0
            if session['usage_count'] >= 3:
                return jsonify({
                    "error": "You've reached the maximum free uses. Please sign in.",
                    "require_login": True
                }), 403
            session['usage_count'] += 1

        noun = request.form['noun']
        verb = request.form['verb']
        adjective = request.form['adjective']
        adverb = request.form['adverb']
        number = request.form['number']
        bodypart = request.form['bodypart']
        artstyle = request.form['artstyle']

        prompt = f"Create a short 100 word story with bodypart - {bodypart} adjective - {adjective} noun - {noun} verb - {verb} adverb - {adverb} number - {number} integrated in the story."

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # Specify the model
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                stop=None
            )
            story = response.choices[0].message.content.strip()

            imagePrompt = f"Based off the {artstyle} artstyle, illustrate this story: '{story}' ... "

            D3response = client.images.generate(
                model="dall-e-3",
                prompt=imagePrompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )

            image_url = D3response.data[0].url
            print("||Story ", story, "||")
            print(image_url)

            return jsonify({"story": story, "image": image_url})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
