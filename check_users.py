import asyncio
from prisma import Prisma

async def check_users():
    db = Prisma()
    await db.connect()
    
    users = await db.user.find_many()
    print('Usuários encontrados:')
    for user in users:
        print(f'- Email: {user.email} (ID: {user.id})')
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(check_users())