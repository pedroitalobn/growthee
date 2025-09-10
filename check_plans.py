import asyncio
from prisma import Prisma

async def check_plans():
    db = Prisma()
    await db.connect()
    
    plans = await db.plan.find_many()
    print('Plans in database:')
    for p in plans:
        print(f'- ID: {p.id}')
        print(f'  Name: {p.name}')
        print(f'  Stripe Price ID: {p.stripePriceId}')
        print(f'  Monthly Price: ${p.priceMonthly}')
        print(f'  Yearly Price: ${p.priceYearly}')
        print('---')
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(check_plans())