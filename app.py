from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)

api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("No OPENAI_API_KEY found in environment variables")

client = OpenAI(api_key=api_key)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    noun = request.form['noun']
    verb = request.form['verb']
    adjective = request.form['adjective']
    adverb = request.form['adverb']

    prompt = f"Create a short story with a {adjective} {noun} who loves to {verb} {adverb}."

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Specify the model
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100 
           # Add max_tokens to limit the length of the completion
        )

        print(response)
        story = response.choices[0].message.content.strip()

        return render_template('index.html', story=story)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
