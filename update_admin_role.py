import asyncio
from api.database import get_db
from prisma import Prisma

async def update_admin_role():
    """Atualiza o papel do usuário admin@admin.com para SUPER_ADMIN"""
    db = Prisma()
    await db.connect()
    
    try:
        # Buscar o usuário
        user = await db.user.find_unique(where={'email': 'admin@admin.com'})
        
        if not user:
            print('❌ Usuário admin@admin.com não encontrado!')
            return
        
        print(f'📧 Usuário encontrado: {user.email}')
        print(f'🔐 Papel atual: {user.role}')
        
        # Atualizar para SUPER_ADMIN
        updated_user = await db.user.update(
            where={'email': 'admin@admin.com'},
            data={'role': 'SUPER_ADMIN'}
        )
        
        print(f'✅ Papel atualizado com sucesso!')
        print(f'🔐 Novo papel: {updated_user.role}')
        
    except Exception as e:
        print(f'❌ Erro ao atualizar papel: {str(e)}')
        
    finally:
        await db.disconnect()

if __name__ == "__main__":
    print('🚀 Atualizando papel do usuário admin@admin.com para SUPER_ADMIN...')
    asyncio.run(update_admin_role())
    print('✨ Processo concluído!')