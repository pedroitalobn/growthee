import asyncio
import bcrypt
from prisma import Prisma

async def create_admin():
    # Initialize Prisma
    prisma = Prisma()
    await prisma.connect()
    
    # Hash password using bcrypt directly
    password_bytes = 'admin'.encode('utf-8')
    hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')
    
    try:
        # Check if admin already exists
        existing_user = await prisma.user.find_unique(where={'email': 'admin@admin.com'})
        if existing_user:
            print('Admin user already exists')
            await prisma.disconnect()
            return
            
        user = await prisma.user.create(data={
            'email': 'admin@admin.com',
            'passwordHash': hashed_password,
            'fullName': 'admin',
            'role': 'ADMIN',
            'plan': 'ENTERPRISE'
        })
        print(f'Admin user created: {user.email}')
    except Exception as e:
        print(f'Error: {e}')
    finally:
        await prisma.disconnect()

if __name__ == '__main__':
    asyncio.run(create_admin())