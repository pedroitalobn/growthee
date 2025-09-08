#!/usr/bin/env python3
"""
Script para criar um usuário superadmin no sistema EnrichStory
"""

import asyncio
import sys
import os
from datetime import datetime
from passlib.context import CryptContext

# Adicionar o diretório raiz ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from prisma import Prisma

# Configuração de hash de senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_superadmin():
    """Cria um usuário superadmin no banco de dados"""
    
    # Conectar ao banco de dados
    prisma = Prisma()
    await prisma.connect()
    
    try:
        # Dados do superadmin
        email = "admin@admin.com"
        full_name = "Super Admin"
        password = "@Story987"
        
        # Verificar se o usuário já existe
        existing_user = await prisma.user.find_unique(
            where={"email": email}
        )
        
        if existing_user:
            print(f"❌ Usuário com email {email} já existe!")
            return
        
        # Hash da senha
        hashed_password = pwd_context.hash(password)
        
        # Criar o usuário superadmin
        superadmin = await prisma.user.create(
            data={
                "email": email,
                "fullName": full_name,
                "passwordHash": hashed_password,
                "role": "ADMIN",
                "plan": "ENTERPRISE",
                "creditsRemaining": 10000,
                "creditsTotal": 10000,
                "isActive": True,
                "companyName": "EnrichStory Admin"
            }
        )
        
        print("✅ Superadmin criado com sucesso!")
        print(f"📧 Email: {email}")
        print(f"👤 Nome: {full_name}")
        print(f"🔑 Senha: {password}")
        print(f"🆔 ID: {superadmin.id}")
        print(f"💰 Créditos: {superadmin.creditsRemaining}")
        print(f"🔐 Role: {superadmin.role}")
        print(f"📋 Plano: {superadmin.plan}")
        
    except Exception as e:
        print(f"❌ Erro ao criar superadmin: {str(e)}")
        
    finally:
        await prisma.disconnect()

if __name__ == "__main__":
    print("🚀 Criando usuário superadmin...")
    asyncio.run(create_superadmin())
    print("✨ Processo concluído!")