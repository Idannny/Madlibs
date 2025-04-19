from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from openai import OpenAI
from dotenv import load_dotenv
import os
import stripe
from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy
from extensions import db, migrate, limiter
from models import User, Story  
import requests
from flask_mail import Mail, Message
import logging
from datetime import datetime, timedelta
import secrets
from flask_wtf.csrf import CSRFProtect, validate_csrf
from flask_talisman import Talisman
import bleach
from forms import RegistrationForm
import traceback
from config import config
import logging

load_dotenv()  


def create_app():
    env = os.getenv('FLASK_ENV', 'development')
    app = Flask(__name__)
    app.config.from_object(config[env])
    csrf = CSRFProtect(app)
    logging.basicConfig(level=logging.INFO)

    Talisman(
        app,
        content_security_policy=app.config['CSP'],
        content_security_policy_nonce_in=['script-src'],
        force_https=True,
        strict_transport_security=True,
        session_cookie_secure=True,
        session_cookie_http_only=True,
        session_cookie_samesite='Lax'
    )
    
    is_development = env == 'development'

    app.secret_key = os.getenv('CSRF_TOKEN')

    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY'),
        STRIPE_KEY=os.getenv('STRIPE_SECRET'),
        STRIPE_PUBLISHABLE_KEY=os.getenv('STRIPE_PUBLISHABLE_KEY'),
        RECAPTCHA_SITE_KEY=os.getenv('RECAPTCHA_SITE_KEY_DEV' if is_development else 'RECAPTCHA_SITE_KEY_PROD'),
        RECAPTCHA_SECRET=os.getenv('RECAPTCHA_SECRET_DEV' if is_development else 'RECAPTCHA_SECRET_PROD'),
        MAIL_SERVER=os.getenv('MAIL_SERVER'),
        MAIL_PORT=os.getenv('MAIL_PORT'),
        MAIL_USE_TLS=os.getenv('MAIL_USE_TLS'),
        MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
        MAIL_PASSWORD=os.getenv('MAIL_PASSWORD')
    )

    oauth = OAuth(app)
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

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

    # Initialize Flask-Mail
    mail = Mail(app)

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

    def send_verification_email(user):
        try:

            print(f"Attempting to send email to {user.email}")

            token = user.generate_verification_token()
            db.session.commit()
            verification_url = url_for('verify_email', token=token, _external=True)
            print("Sending Verification Email")

            msg = Message('Verify Your Email',
                        sender=os.getenv('MAIL_USERNAME'),
                        recipients=[user.email])
            msg.body = f'''Please click the following link to verify your email:
                        {verification_url}
                        This link will expire in 24 hours.
                        If you did not create an account, please ignore this email.
                        '''
            mail.send(msg)

            print("Email sent successfully")

        except Exception as e:
            print(f"Error sending email: {str(e)}")
            # Log the full exception for debugging
            
            traceback.print_exc()

    def sanitize_input(text):
    # Remove any HTML tags or dangerous characters
        return bleach.clean(text, tags=[], strip=True)

    @app.route('/')
    def landing():
        user_info = None
        if 'user' in session:
            user = User.query.filter_by(email=session['user']['email']).first()
            if user:
                user_info = session['user']
        return render_template('landing.html', user_info=user_info)

    @app.route('/app')
    def index():
        user_info = None
        credits = 0
        free_tries = 0

        if 'user' in session:
            user = User.query.filter_by(email=session['user']['email']).first()
            if user:
                user_info = session['user']
                credits = user.credits
                free_tries = user.free_tries_left
        else:
            # Anonymous user    
            free_tries = 1 - session.get('usage_count', 0)  # Only 1 free try for non-signed-in users

            print("User Name: ", user_info)
        return render_template('index.html', 
                             user_info=user_info, 
                             credits=credits,
                             free_tries=free_tries)

    @app.route('/login', methods=['GET', 'POST'])
    @limiter.limit("10 per hour")  # Limit login attempts
    def login():
        form = RegistrationForm()

        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(password):
                if not user.is_email_verified:
                    flash('Please verify your email before logging in.')
                    return redirect(url_for('login'))
                
                session['user'] = {
                    'id': user.id,
                    'name': user.name,
                    'email': user.email
                }
                return redirect(url_for('index'))
            
            flash('Invalid email or password.')
            return redirect(url_for('login'))
        
        return render_template('login.html', form=form)

    @app.route('/google-login')
    def google_login():
        redirect_uri = url_for('authorized', _external=True)
        return google.authorize_redirect(redirect_uri)

    @app.route('/callback')
    def authorized():
        token = google.authorize_access_token()
        if not token:
            return 'Access denied.'
        
        session['google_token'] = token
        user_info = google.get('userinfo').json()

        user = User.query.filter_by(email=user_info['email']).first()
        if user is None:
            # Create new user with Google OAuth
            new_user = User(
                email=user_info['email'],
                name=user_info.get('name'),
                is_oauth_user=True,
                free_tries_left=3,  # Initialize with 3 free tries
                credits=0
            )
            db.session.add(new_user)
            db.session.commit()
            user = new_user

        session['user'] = user_info
        return redirect(url_for('index'))

    @app.route('/logout')
    def logout():
        session.pop('user', None)
        session.pop('google_token', None)
        return redirect(url_for('index'))

    @app.before_request
    def load_google_token():
        token = session.get("google_token")
        if token:
            google.token = token

    @app.route('/register', methods=['GET', 'POST'])
    @limiter.limit("15 per hour")  # Limit registration attempts
    def register():
        # print("CSRF in register : ",request.headers.get('X-CSRFToken'))
        
        form = RegistrationForm()
        if request.method == 'POST':
            
            csrf_token = request.headers.get('X-CSRFToken')
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')

            try:
                validate_csrf(csrf_token)
            except Exception as e:
                return jsonify({"error": "Invalid CSRF token"}), 403


            if User.query.filter_by(email=email).first():
                flash('Email already registered. Please login or use a different email.')
                return redirect(url_for('register'))
            
            user = User(name=name, email=email)
            user.set_password(password)

            db.session.add(user)
            db.session.commit()
            
            # Send verification email
            send_verification_email(user)
            if form.validate_on_submit():

                flash('Account created successfully, check your email!', 'success')
                return redirect(url_for('login'))
        
        return render_template('register.html', form=form)

    @app.route('/verify-email/<token>')
    def verify_email(token):
        user = User.query.filter_by(email_verification_token=token).first()
        
        if not user:
            flash('Invalid or expired verification link.')
            return redirect(url_for('login'))
        
        if user.verify_email(token):
            db.session.commit()
            flash('Email verified successfully! You can now log in.')
            return redirect(url_for('login'))
        
        flash('Verification link has expired. Please request a new one.')
        return redirect(url_for('login'))

    @app.route('/resend-verification', methods=['POST'])
    def resend_verification():
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash('Email not found.')
            return redirect(url_for('login'))
        
        if user.is_email_verified:
            flash('Email is already verified.')
            return redirect(url_for('login'))
        
        send_verification_email(user)
        flash('Verification email has been resent. Please check your inbox.')
        return redirect(url_for('login'))

    @app.route('/profile')
    def profile():
        if 'user' not in session:
            return redirect(url_for('login'))

        user = User.query.filter_by(email=session['user']['email']).first()
        if not user:
            session.pop('user', None)
            return redirect(url_for('login'))

        stories = Story.query.filter_by(user_id=user.id).order_by(Story.created_at.desc()).all()
        
        return render_template('profile.html',
                             user=session['user'],
                             credits=user.credits,
                             free_tries=user.free_tries_left,
                             stories=stories,
                             stripe_key=app.config['STRIPE_PUBLISHABLE_KEY'])

    @app.route('/submit', methods=['POST'])
    @limiter.limit("10 per hour")  # Limit story generation
    def submit():
        csrf_token = request.form.get('csrf_token')
        try:
            validate_csrf(csrf_token)
            
        except Exception as e:
            return jsonify({"error": "Invalid CSRF token"}), 403

        recaptcha_response = request.form.get('g-recaptcha-response')
        
        # app.logger.info(f"Received reCAPTCHA response: {recaptcha_response}")
        
        if not verify_recaptcha(recaptcha_response):
            return jsonify({"error": "Please complete the CAPTCHA."}), 400

        if 'user' in session:
            # Logged in user
            user = User.query.filter_by(email=session['user']['email']).first()
            if user is None:
                session.pop('user', None)
                return jsonify({
                    "error": "User session expired. Please login again.",
                    "require_login": True
                }), 401
            
            # Try to use a credit first, then fall back to free tries
            if not user.use_credit():
                if not user.use_free_try():
                    return jsonify({
                        "error": "You've used all your free tries. Please purchase credits to continue.",
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

        noun = sanitize_input(request.form['noun'])
        verb = sanitize_input(request.form['verb'])
        adjective = sanitize_input(request.form['adjective'])
        adverb = sanitize_input(request.form['adverb'])
        number = sanitize_input(request.form['number'])
        bodypart = sanitize_input(request.form['bodypart'])
        artstyle = sanitize_input(request.form['artstyle'])

        prompt = f"Create a short 100 word story with bodypart - {bodypart} adjective - {adjective} noun - {noun} verb - {verb} adverb - {adverb} number - {number} integrated in the story."

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                stop=None
            )
            story_content = response.choices[0].message.content.strip()

            imagePrompt = f"Based off the {artstyle} artstyle, illustrate this story: '{story_content}' ... "

            D3response = client.images.generate(
                model="dall-e-3",
                prompt=imagePrompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )

            image_url = D3response.data[0].url

            # Save the story if user is logged in
            if 'user' in session and user:
                story = Story(
                    content=story_content,
                    image_url=image_url,
                    user_id=user.id,
                    noun=noun,
                    verb=verb,
                    adjective=adjective,
                    adverb=adverb,
                    number=int(number),
                    bodypart=bodypart,
                    artstyle=artstyle
                )
                db.session.add(story)
                db.session.commit()
                print("story: ",story_content)
            return jsonify({"story": story_content, "image": image_url})

        except Exception as e:
            app.logger.error(f"Error generating story: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/story/<int:story_id>')
    def view_story(story_id):
        if 'user' not in session:
            return redirect(url_for('login'))

        story = Story.query.get_or_404(story_id)
        if story.user_id != User.query.filter_by(email=session['user']['email']).first().id:
            abort(403)  # Forbidden

        return render_template('story.html', story=story)

    @app.route('/create-checkout-session', methods=['POST'])
    @limiter.limit("10 per hour") 
    def create_checkout_session():
        print("in checkout session")

        csrf_token = request.headers.get('X-CSRFToken')
        try:
            validate_csrf(csrf_token)
        except Exception as e:
            return jsonify({"error": "Invalid CSRF token"}), 403


        if 'user' not in session:
            return jsonify({"error": "Please log in to purchase credits"}), 401

        try:
            stripe.api_key = app.config['STRIPE_KEY']
            print("stipeKey", app.config['STRIPE_KEY'])
            # Get the number of credits to purchase from the request

            credits = int(request.json.get('credits', 1))
            

            # Calculate the total amount (1 credit = $1)
            amount = credits * 100  # Convert to cents
            
            success_url = url_for('payment_success', _external=True)
            cancel_url = url_for('payment_cancel', _external=True)

            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'{credits} Mad Libs Credits',
                            'description': f'Purchase {credits} credits for AI-generated Mad Libs stories',
                        },
                        'unit_amount': 100,  # $1.00 per credit
                    },
                    'quantity': credits,
                }],
                mode='payment',
                success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url,
                client_reference_id=session['user']['email'],  # Link payment to user
                metadata={
                    'credits': credits,
                    'user_email': session['user']['email']
                }
            )
            return jsonify({'id': checkout_session.id})
        except Exception as e:
            app.logger.error(f"Stripe error: {str(e)}")
            return jsonify(error=str(e)), 403

    @app.route('/payment-success')
    def payment_success():
        session_id = request.args.get('session_id')
        if not session_id or 'user' not in session:
            flash('Invalid payment session')
            return redirect(url_for('index'))

        try:
            # Verify the payment with Stripe
            stripe.api_key = app.config['STRIPE_KEY']
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            
            if checkout_session.payment_status == 'paid':
                # Get the number of credits from metadata
                credits = int(checkout_session.metadata.get('credits', 1))
                
                # Update user credits
                user = User.query.filter_by(email=session['user']['email']).first()
                if user:
                    user.add_credits(credits)
                    flash(f'Thank you for your purchase! {credits} credits have been added to your account.')
                else:
                    flash('Error: User not found')
            else:
                flash('Payment was not successful')
        except Exception as e:
            app.logger.error(f"Payment verification error: {str(e)}")
            flash('There was an error verifying your payment.')
        
        return redirect(url_for('profile'))

    @app.route('/payment-cancel')
    def payment_cancel():
        flash('Payment was cancelled')
        return redirect(url_for('profile'))

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
