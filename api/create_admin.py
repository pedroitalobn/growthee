import asyncio
from api.database import get_db
from passlib.context import CryptContext

async def create_admin():
    db = await get_db().__anext__()
    pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
    hashed_password = pwd_context.hash('admin123')
    
    try:
        # Check if admin already exists
        existing_user = await db.user.find_unique(where={'email': 'admin@example.com'})
        if existing_user:
            print('Admin user already exists')
            return
            
        user = await db.user.create(data={
            'email': 'admin@example.com',
            'password': hashed_password,
            'name': 'Admin User',
            'role': 'ADMIN'
        })
        print(f'Admin user created: {user.email}')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    asyncio.run(create_admin())