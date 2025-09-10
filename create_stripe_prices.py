import stripe
import os
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

plans = [
    {
        'name': 'Starter',
        'price_monthly': 29.00,
        'price_yearly': 290.00,
        'description': 'Perfect for small teams getting started'
    },
    {
        'name': 'Professional', 
        'price_monthly': 99.00,
        'price_yearly': 990.00,
        'description': 'Advanced features for growing businesses'
    },
    {
        'name': 'Enterprise',
        'price_monthly': 299.00,
        'price_yearly': 2990.00,
        'description': 'Full-featured solution for large organizations'
    }
]

print("Creating Stripe products and prices...")

for plan in plans:
    try:
        # Create product
        product = stripe.Product.create(
            name=f"Growthee {plan['name']}",
            description=plan['description']
        )
        print(f"✓ Created product: {product.id} - {product.name}")
        
        # Create monthly price
        monthly_price = stripe.Price.create(
            unit_amount=int(plan['price_monthly'] * 100),  # Convert to cents
            currency='usd',
            recurring={'interval': 'month'},
            product=product.id,
            lookup_key=f"price_{plan['name'].lower()}_monthly"
        )
        print(f"✓ Created monthly price: {monthly_price.id} - ${plan['price_monthly']}/month")
        
        # Create yearly price
        yearly_price = stripe.Price.create(
            unit_amount=int(plan['price_yearly'] * 100),  # Convert to cents
            currency='usd',
            recurring={'interval': 'year'},
            product=product.id,
            lookup_key=f"price_{plan['name'].lower()}_yearly"
        )
        print(f"✓ Created yearly price: {yearly_price.id} - ${plan['price_yearly']}/year")
        
        print(f"Monthly Price ID for {plan['name']}: {monthly_price.id}")
        print(f"Yearly Price ID for {plan['name']}: {yearly_price.id}")
        print("---")
        
    except Exception as e:
        print(f"✗ Error creating {plan['name']}: {e}")

print("\nDone! Update your database with the new price IDs.")