#!/usr/bin/env python3
import asyncio
import os
import bcrypt
from dotenv import load_dotenv
from prisma import Prisma

# Load environment variables
load_dotenv()

async def create_default_user():
    """Create default user for testing"""
    prisma = Prisma()
    
    try:
        await prisma.connect()
        print("Connected to database")
        
        # Check if user already exists
        existing_user = await prisma.user.find_unique(
            where={"email": "client@client.com"}
        )
        
        if existing_user:
            print("Default user already exists!")
            print(f"User ID: {existing_user.id}")
            print(f"Email: {existing_user.email}")
            print(f"Username: {existing_user.username}")
            return
        
        # Hash the password using bcrypt
        hashed_password = bcrypt.hashpw("client".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create the user
        user = await prisma.user.create(
            data={
                "email": "client@client.com",
                "fullName": "Client User",
                "passwordHash": hashed_password,
                "role": "USER",
                "plan": "FREE",
                "creditsRemaining": 100,
                "creditsTotal": 100,
                "isActive": True
            }
        )
        
        print("Default user created successfully!")
        print(f"User ID: {user.id}")
        print(f"Full Name: {user.fullName}")
        print(f"Email: {user.email}")
        print(f"Credits Remaining: {user.creditsRemaining}")
        print(f"Plan: {user.plan}")
        print("Password: client")
        
    except Exception as e:
        print(f"Error creating user: {e}")
    finally:
        await prisma.disconnect()
        print("Disconnected from database")

if __name__ == "__main__":
    asyncio.run(create_default_user())