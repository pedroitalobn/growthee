import asyncio
import os
from dotenv import load_dotenv
from prisma import Prisma

load_dotenv()

async def test_direct_db():
    """Test database connection directly"""
    print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")
    
    prisma = Prisma()
    
    try:
        await prisma.connect()
        print(f"Connected: {prisma.is_connected()}")
        
        # Count users
        user_count = await prisma.user.count()
        print(f"User count: {user_count}")
        
        # Get all users
        users = await prisma.user.find_many()
        print(f"Users found: {len(users)}")
        
        for user in users:
            print(f"- {user.email} ({user.fullName}) - Active: {user.isActive}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await prisma.disconnect()

if __name__ == "__main__":
    asyncio.run(test_direct_db())