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
    number = request.form['number']
    bodypart = request.form['bodypart']
    artstyle = request.form['artstyle']
    # number = 1
    # bodypart = "mouth"
    prompt = f"Create a short 100 word story with bodypart - {bodypart} adjective - {adjective} noun - {noun} verb - {verb} adverb - {adverb} number - {number} integrated in the story."
    imagePrompt = f"Create an image based off this {prompt} based off {artstyle} "
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Specify the model
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            stop=None 
           # Add max_tokens to limit the length of the completion
        )
        story = response.choices[0].message.content.strip()
        
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
