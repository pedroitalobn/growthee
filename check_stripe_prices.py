import stripe
import os
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

prices_to_check = [
    'price_starter_monthly',
    'price_professional_monthly', 
    'price_enterprise_monthly'
]

print("Checking Stripe prices...")
for price_id in prices_to_check:
    try:
        price = stripe.Price.retrieve(price_id)
        print(f"✓ {price_id}: ${price.unit_amount/100} {price.currency} - {price.recurring.interval}")
    except stripe.error.InvalidRequestError as e:
        print(f"✗ {price_id}: {e}")
    except Exception as e:
        print(f"✗ {price_id}: Error - {e}")

print("\nListing all prices in Stripe:")
try:
    prices = stripe.Price.list(limit=10)
    for price in prices.data:
        print(f"- {price.id}: ${price.unit_amount/100 if price.unit_amount else 'N/A'} {price.currency}")
except Exception as e:
    print(f"Error listing prices: {e}")