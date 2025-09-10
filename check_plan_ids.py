import asyncio
from prisma import Prisma

async def check_plan_ids():
    db = Prisma()
    await db.connect()
    
    plans = await db.plan.find_many()
    print('Available plans:')
    for p in plans:
        print(f'  {p.name}: {p.id}')
    
    await db.disconnect()

if __name__ == '__main__':
    asyncio.run(check_plan_ids())