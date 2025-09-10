import asyncio
from prisma import Prisma

# New Stripe price IDs from the creation script
price_updates = {
    'Starter': 'price_1S5YNQ4YExb8U97O5ySz95IK',
    'Professional': 'price_1S5YNS4YExb8U97ObSscBw4W', 
    'Enterprise': 'price_1S5YNT4YExb8U97Otngqf2XS'
}

async def update_prices():
    db = Prisma()
    await db.connect()
    
    print("Updating Stripe price IDs in database...")
    
    for plan_name, price_id in price_updates.items():
        try:
            # First find the plan by name
            plan = await db.plan.find_first(
                where={'name': plan_name}
            )
            if plan:
                updated_plan = await db.plan.update(
                    where={'id': plan.id},
                    data={'stripePriceId': price_id}
                )
            else:
                print(f"✗ Plan {plan_name} not found")
            print(f"✓ Updated {plan_name}: {price_id}")
        except Exception as e:
            print(f"✗ Error updating {plan_name}: {e}")
    
    # Verify updates
    print("\nVerifying updates:")
    plans = await db.plan.find_many()
    for plan in plans:
        print(f"- {plan.name}: {plan.stripePriceId}")
    
    await db.disconnect()
    print("\nDatabase updated successfully!")

if __name__ == "__main__":
    asyncio.run(update_prices())