from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from openai import OpenAI
from dotenv import load_dotenv
import os

from config import Config
from flask_oauthlib.client import OAuth

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']
oauth = OAuth(app)

google = oauth.remote_app(
    'google',
    consumer_key=app.config['GOOGLE_CLIENT_ID'],
    consumer_secret=app.config['GOOGLE_CLIENT_SECRET'],
    request_token_params={
        'scope': 'email',
    },
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)

api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("No OPENAI_API_KEY found in environment variables")

client = OpenAI(api_key=api_key)

@app.route('/login')
def login():
    return google.authorize(callback=url_for('authorized', _external=True))

@app.route('/logout')
def logout():
    session.pop('google_token', None)
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/callback')
def authorized():
    response = google.authorized_response()
    if response is None or response.get('access_token') is None:
        return 'Access denied: reason={} error={}'.format(
            request.args['error_reason'],
            request.args['error_description']
        )

    session['google_token'] = (response['access_token'], '')
    user_info = google.get('userinfo').data
    session['user'] = user_info  # Store user info in session

    return redirect(url_for('profile'))  # Redirect to profile page

@google.tokengetter
def get_google_oauth_token():
    return session.get('google_token')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/profile')
def profile():
    user_info = session.get('user')
    if not user_info:
        return redirect(url_for('index'))
    return render_template('profile.html', user=user_info)

@app.route('/submit', methods=['POST'])
def submit():
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
           # Add max_tokens to limit the length of the completion
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
        print("||Story " , story, "||")
        print(image_url)

        return render_template('index.html', story=story, image=image_url, adjective=adjective, noun=noun, verb=verb, adverb=adverb)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
