from flask import Flask, request, jsonify
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Get the API key from the environment variable
api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    raise ValueError("No OPENAI_API_KEY found in environment variables")

client = OpenAI(api_key=api_key)
app = Flask(__name__)

# openai.api_key = os.getenv(OPENAI_API_KEY)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get("message")

    try:
        response = client.chat.completions.create(model="gpt-3.5-turbo",  # or the model you are using
        messages=[{"role": "user", "content": user_message}])
        return jsonify(response.choices[0].message.content.strip())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
