import asyncio
import bcrypt
from prisma import Prisma

async def create_test_user():
    db = Prisma()
    await db.connect()
    
    try:
        # Verificar se usuário já existe
        existing_user = await db.user.find_unique(where={'email': 'test@test.com'})
        if existing_user:
            print('Usuário test@test.com já existe')
            await db.disconnect()
            return
            
        # Criar hash da senha
        password = 'test123'
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Criar usuário
        user = await db.user.create({
            'email': 'test@test.com',
            'fullName': 'Test User',
            'passwordHash': password_hash,
            'role': 'USER',
            'plan': 'free',
            'creditsRemaining': 1000,
            'creditsTotal': 1000,
            'isActive': True
        })
        
        print(f'✅ Usuário criado: {user.email} (ID: {user.id})')
        print(f'Senha: {password}')
        
    except Exception as e:
        print(f'Erro: {e}')
    finally:
        await db.disconnect()

if __name__ == '__main__':
    asyncio.run(create_test_user())