import asyncio
import bcrypt
from prisma import Prisma

async def fix_test_user():
    db = Prisma()
    await db.connect()
    
    try:
        # Deletar usuário existente se existir
        existing_user = await db.user.find_unique(where={'email': 'test@test.com'})
        if existing_user:
            await db.user.delete(where={'email': 'test@test.com'})
            print('Usuário existente deletado')
            
        # Criar hash da senha
        password = 'test123'
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Criar usuário com plano correto
        user = await db.user.create({
            'email': 'test@test.com',
            'fullName': 'Test User',
            'passwordHash': password_hash,
            'role': 'user',
            'plan': 'free',
            'creditsRemaining': 1000,
            'creditsTotal': 1000,
            'isActive': True
        })
        
        print(f'✅ Usuário criado: {user.email} (ID: {user.id})')
        print(f'Plano: {user.plan}')
        print(f'Role: {user.role}')
        print(f'Senha: {password}')
        
    except Exception as e:
        print(f'Erro: {e}')
    finally:
        await db.disconnect()

if __name__ == '__main__':
    asyncio.run(fix_test_user())