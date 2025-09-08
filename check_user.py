#!/usr/bin/env python3
import asyncio
from dotenv import load_dotenv
from prisma import Prisma

load_dotenv()

async def check_user():
    prisma = Prisma()
    try:
        await prisma.connect()
        print("Connected to database")
        
        user = await prisma.user.find_unique(
            where={"email": "client@client.com"}
        )
        
        if user:
            print(f"User found: {user.email}")
            print(f"Full Name: {user.fullName}")
            print(f"Password Hash: {user.passwordHash[:20]}...")
            print(f"Role: {user.role}")
            print(f"Plan: {user.plan}")
            print(f"Active: {user.isActive}")
        else:
            print("User not found!")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await prisma.disconnect()

if __name__ == "__main__":
    asyncio.run(check_user())