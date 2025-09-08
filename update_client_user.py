#!/usr/bin/env python3
import asyncio
import bcrypt
from prisma import Prisma

async def update_client_user():
    """Atualiza o usuário client@client.com com username 'client'"""
    db = Prisma()
    await db.connect()
    
    try:
        # Verificar se o usuário existe
        existing_user = await db.user.find_unique(
            where={"email": "client@client.com"}
        )
        
        if existing_user:
            # Atualizar com username
            updated_user = await db.user.update(
                where={"email": "client@client.com"},
                data={"username": "client"}
            )
            print(f"✅ Usuário atualizado: {updated_user.email}")
            print(f"Username: {updated_user.username}")
        else:
            # Criar usuário se não existir
            password_hash = bcrypt.hashpw("client".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            user = await db.user.create(
                data={
                    "email": "client@client.com",
                    "username": "client",
                    "passwordHash": password_hash,
                    "fullName": "Client User",
                    "role": "user",
                    "plan": "free",
                    "creditsRemaining": 100,
                    "creditsTotal": 100,
                    "isActive": True
                }
            )
            print(f"✅ Usuário criado: {user.email}")
            print(f"Username: {user.username}")
            print(f"Password: client")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(update_client_user())