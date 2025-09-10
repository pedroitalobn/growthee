import asyncio
from prisma import Prisma
from api.auth.jwt_service import JWTService

async def create_test_token():
    db = Prisma()
    await db.connect()
    
    # Find a test user
    user = await db.user.find_first()
    if not user:
        print("No users found in database")
        return
    
    print(f"Creating token for user: {user.email} (ID: {user.id})")
    
    # Create JWT token
    jwt_service = JWTService()
    token = jwt_service.create_access_token(data={"sub": user.id})
    
    print(f"JWT Token: {token}")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(create_test_token())