import os
import stripe
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve the Stripe API key from environment variables
stripe.api_key = os.getenv('STRIPE_KEY')

def test_stripe_api():
    try:
        # Make a simple API call to list products
        products = stripe.Product.list(limit=1)
        print("Stripe API is working. Here is a sample product:")
        print(products)
    except stripe.error.AuthenticationError as e:
        print("Authentication error: Invalid API Key")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_stripe_api()