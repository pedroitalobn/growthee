import stripe
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def list_existing_webhooks():
    """Lista webhooks existentes"""
    try:
        webhooks = stripe.WebhookEndpoint.list()
        print(f"Found {len(webhooks.data)} existing webhooks:")
        for webhook in webhooks.data:
            print(f"  - {webhook.id}: {webhook.url}")
            print(f"    Events: {webhook.enabled_events}")
            print(f"    Status: {'Active' if webhook.status == 'enabled' else 'Inactive'}")
        return webhooks.data
    except Exception as e:
        print(f"Error listing webhooks: {e}")
        return []

def create_webhook():
    """Cria um novo webhook endpoint"""
    webhook_url = "http://localhost:8000/api/v1/billing/webhook"
    
    try:
        webhook = stripe.WebhookEndpoint.create(
            url=webhook_url,
            enabled_events=[
                'checkout.session.completed',
                'invoice.payment_succeeded',
                'customer.subscription.deleted',
                'payment_intent.succeeded'
            ]
        )
        
        print(f"Webhook created successfully!")
        print(f"Webhook ID: {webhook.id}")
        print(f"Webhook Secret: {webhook.secret}")
        print(f"URL: {webhook.url}")
        print(f"\nAdd this to your .env file:")
        print(f"STRIPE_WEBHOOK_SECRET={webhook.secret}")
        
        return webhook
    except Exception as e:
        print(f"Error creating webhook: {e}")
        return None

def test_webhook_with_cli():
    """Instruções para testar webhook com Stripe CLI"""
    print("\nTo test webhooks locally with Stripe CLI:")
    print("1. Install Stripe CLI: https://stripe.com/docs/stripe-cli")
    print("2. Login: stripe login")
    print("3. Forward events: stripe listen --forward-to localhost:8000/api/v1/billing/webhook")
    print("4. Trigger test event: stripe trigger checkout.session.completed")

if __name__ == "__main__":
    print("Setting up Stripe webhook...")
    
    print("\n1. Listing existing webhooks:")
    existing = list_existing_webhooks()
    
    # Verificar se já existe um webhook para localhost
    localhost_webhook = None
    for webhook in existing:
        if "localhost:8000" in webhook.url:
            localhost_webhook = webhook
            break
    
    if localhost_webhook:
        print(f"\nFound existing localhost webhook: {localhost_webhook.id}")
        print(f"Secret: {localhost_webhook.secret}")
    else:
        print("\n2. Creating new webhook:")
        create_webhook()
    
    print("\n3. Testing instructions:")
    test_webhook_with_cli()