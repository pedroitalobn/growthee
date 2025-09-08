import asyncio
import bcrypt
from prisma import Prisma

async def check_password():
    db = Prisma()
    await db.connect()
    
    try:
        user = await db.user.find_unique(where={'email': 'admin@admin.com'})
        if user:
            print(f'User: {user.email}')
            print(f'Hash: {user.passwordHash}')
            
            # Testar senhas comuns
            test_passwords = ['admin123', 'admin', 'password', '123456']
            
            for password in test_passwords:
                if bcrypt.checkpw(password.encode('utf-8'), user.passwordHash.encode('utf-8')):
                    print(f'✅ Senha correta: {password}')
                    break
            else:
                print('❌ Nenhuma senha testada funcionou')
                
        else:
            print('Usuário não encontrado')
            
    except Exception as e:
        print(f'Erro: {e}')
    finally:
        await db.disconnect()

if __name__ == '__main__':
    asyncio.run(check_password())