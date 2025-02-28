from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from openai import OpenAI
from dotenv import load_dotenv
import os
import stripe
from config import Config
from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy
from extensions import db
from models import User  
import requests

load_dotenv()  # Load environment variables from .env file

# Use reCAPTCHA's test keys:
# Google provides a set of test keys that you can use during developme
# Site key: 6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI
# Secret key: 6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4Wif

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    app.secret_key = app.config['SECRET_KEY']
    app.stripekey = app.config['STRIPE_SECRET']
    stripe.api_key = app.stripekey

    oauth = OAuth(app)
    db.init_app(app)

    google = oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
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

    # Register routes and blueprints
    with app.app_context():
        db.create_all()

    def verify_recaptcha(recaptcha_response):
        secret_key = os.getenv("RECAPTCHA_SECRET", "default_test_key")
        verify_url = "https://www.google.com/recaptcha/api/siteverify"
        data = {
            "secret": secret_key,
            "response": recaptcha_response
        }
        try:
            response = requests.post(verify_url, data=data)
            response.raise_for_status()
            result = response.json()
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
        return render_template('index.html')

    @app.route('/create-checkout-session', methods=['POST'])
    def create_checkout_session():
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Story Generation',
                        },
                        'unit_amount': 500,  # Make sure this is dynamically set if necessary
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=url_for('success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=url_for('index', _external=True),
            )
            return jsonify({'id': session.id})
        except Exception as e:
            return jsonify(error=str(e)), 403


    @app.route('/success')
    def success():
        return render_template('success.html')

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
        # recaptcha_response = request.form.get('g-recaptcha-response')
        # if not verify_recaptcha(recaptcha_response):
        #     return jsonify({"error": "Please complete the CAPTCHA."}), 400

        if 'user' not in session:
            if 'usage_count' not in session:
                session['usage_count'] = 0
            if session['usage_count'] >= 3:
                return jsonify({"error": "You have reached the maximum number of free uses."}), 403
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
