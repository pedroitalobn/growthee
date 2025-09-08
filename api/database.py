from prisma import Prisma
from typing import AsyncGenerator
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global Prisma instance - will be set by main.py
prisma = None

def set_prisma_instance(prisma_instance: Prisma):
    """Set the global prisma instance"""
    global prisma
    prisma = prisma_instance

async def connect_db():
    """Connect to the database"""
    if not prisma.is_connected():
        print(f"Database.py connecting with DATABASE_URL: {os.getenv('DATABASE_URL', 'Not set')}")
        await prisma.connect()

async def disconnect_db():
    """Disconnect from the database"""
    if prisma.is_connected():
        await prisma.disconnect()

async def get_db():
    """Get database session"""
    if prisma is None:
        raise RuntimeError("Prisma instance not set. Call set_prisma_instance() first.")
    
    if not prisma.is_connected():
        await prisma.connect()
    
    try:
        yield prisma
    finally:
        pass  # Keep connection alive for reuse

# Initialize database connection on startup
async def init_db():
    """Initialize database connection"""
    await connect_db()
    print("Database connected successfully")

# Cleanup on shutdown
async def close_db():
    """Close database connection"""
    await disconnect_db()
    print("Database disconnected")