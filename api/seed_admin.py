#!/usr/bin/env python3
import asyncio
import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from prisma import Prisma
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_admin_user():
    """Create an admin user for testing"""
    prisma = Prisma()
    
    try:
        await prisma.connect()
        print("Connected to database")
        
        # Check if admin user already exists
        existing_user = await prisma.user.find_first(
            where={"email": "admin@example.com"}
        )
        
        if existing_user:
            print("Admin user already exists")
            return
        
        # Hash the password
        hashed_password = pwd_context.hash("admin123")
        
        # Create admin user
        admin_user = await prisma.user.create(
            data={
                "email": "admin@example.com",
                "fullName": "Admin User",
                "hashedPassword": hashed_password,
                "role": "ADMIN",
                "isActive": True,
                "totalCredits": 1000,
                "remainingCredits": 1000
            }
        )
        
        print(f"Admin user created successfully: {admin_user.email}")
        print(f"Login credentials:")
        print(f"Email: admin@example.com")
        print(f"Password: admin123")
        
    except Exception as e:
        print(f"Error creating admin user: {e}")
    finally:
        await prisma.disconnect()

if __name__ == "__main__":
    asyncio.run(create_admin_user())