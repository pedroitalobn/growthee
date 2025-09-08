#!/usr/bin/env python3
"""
Script para verificar se o usuário superadmin foi criado
"""

import asyncio
import sys
import os

# Adicionar o diretório raiz ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from prisma import Prisma

async def check_admin():
    """Verifica se o usuário superadmin existe no banco de dados"""
    
    # Conectar ao banco de dados
    prisma = Prisma()
    await prisma.connect()
    
    try:
        # Buscar o usuário admin
        admin_user = await prisma.user.find_unique(
            where={"email": "admin@admin.com"}
        )
        
        if admin_user:
            print("✅ Usuário superadmin encontrado!")
            print(f"📧 Email: {admin_user.email}")
            print(f"👤 Nome: {admin_user.fullName}")
            print(f"🆔 ID: {admin_user.id}")
            print(f"💰 Créditos: {admin_user.creditsRemaining}")
            print(f"🔐 Role: {admin_user.role}")
            print(f"📋 Plano: {admin_user.plan}")
            print(f"✅ Ativo: {admin_user.isActive}")
        else:
            print("❌ Usuário superadmin não encontrado!")
        
    except Exception as e:
        print(f"❌ Erro ao verificar usuário: {str(e)}")
        
    finally:
        await prisma.disconnect()

if __name__ == "__main__":
    print("🔍 Verificando usuário superadmin...")
    asyncio.run(check_admin())