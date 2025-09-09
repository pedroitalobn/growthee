import asyncio
from prisma import Prisma
import bcrypt

async def check_user():
    prisma = Prisma()
    await prisma.connect()
    
    try:
        # Buscar usuário por email
        user = await prisma.user.find_first(
            where={"email": "client@client.com"}
        )
        
        if user:
            print(f"Usuário encontrado:")
            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Username: {user.username}")
            print(f"Full Name: {user.full_name}")
            print(f"Password Hash: {user.password_hash[:20]}...")
            
            # Testar se a senha 'client' bate com o hash
            password_matches = bcrypt.checkpw("client".encode('utf-8'), user.password_hash.encode('utf-8'))
            print(f"Senha 'client' confere: {password_matches}")
        else:
            print("Usuário client@client.com não encontrado no banco de dados")
            
            # Listar todos os usuários
            all_users = await prisma.user.find_many()
            print(f"\nTotal de usuários no banco: {len(all_users)}")
            for u in all_users:
                print(f"- {u.email} ({u.username})")
                
    finally:
        await prisma.disconnect()

if __name__ == "__main__":
    asyncio.run(check_user())