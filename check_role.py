import asyncio
from api.database import get_db
from prisma import Prisma

async def check_user():
    db = Prisma()
    await db.connect()
    user = await db.user.find_unique(where={'email': 'admin@admin.com'})
    print(f'User role in DB: {user.role}')
    print(f'User role type: {type(user.role)}')
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(check_user())