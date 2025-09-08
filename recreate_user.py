#!/usr/bin/env python3
import asyncio
from prisma import Prisma
from passlib.context import CryptContext

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def recreate_user():
    prisma = Prisma()
    await prisma.connect()
    
    try:
        # Delete existing user if exists
        existing_user = await prisma.user.find_unique(
            where={"email": "client@client.com"}
        )
        
        if existing_user:
            await prisma.user.delete(
                where={"email": "client@client.com"}
            )
            print("Deleted existing user")
        
        # Create the client user
        user = await prisma.user.create(
            data={
                "email": "client@client.com",
                "passwordHash": "$2b$12$SzzpgO.Ey1d8ectg9BqT1u4TFg0yXdPJ8F/MV1G/smRKnYuwgDxvi",  # "client"
                "fullName": "Client User",
                "role": "user",
                "plan": "free",
                "creditsRemaining": 100,
                "creditsTotal": 100,
                "isActive": True
            }
        )
        print(f"Created user: {user.email} with ID: {user.id}")
        
        # Verify the user was created
        found_user = await prisma.user.find_unique(
            where={"email": "client@client.com"}
        )
        print(f"Verification - Found user: {found_user.email if found_user else 'None'}")
        
    except Exception as e:
        print(f"Error creating user: {e}")
    finally:
        await prisma.disconnect()

if __name__ == "__main__":
    asyncio.run(recreate_user())