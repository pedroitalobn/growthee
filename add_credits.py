#!/usr/bin/env python3
"""
Script para adicionar 500 créditos ao usuário
"""

import asyncio
import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from prisma import Prisma
from api.services.credit_service import CreditService

async def add_credits_to_user():
    """Adiciona 500 créditos ao primeiro usuário encontrado"""
    db = Prisma()
    
    try:
        await db.connect()
        print("Conectado ao banco de dados")
        
        # Buscar o primeiro usuário
        user = await db.user.find_first()
        
        if not user:
            print("Nenhum usuário encontrado no banco de dados")
            return
        
        print(f"Usuário encontrado: {user.email} ({user.fullName})")
        print(f"Créditos atuais: {user.creditsRemaining}")
        
        # Adicionar 500 créditos
        credit_service = CreditService(db)
        await credit_service.add_credits(
            user_id=user.id,
            credits=500,
            reason="Créditos iniciais para teste"
        )
        
        # Buscar usuário atualizado
        updated_user = await db.user.find_unique(
            where={"id": user.id}
        )
        
        print(f"Créditos após adição: {updated_user.creditsRemaining}")
        print(f"Total de créditos: {updated_user.creditsTotal}")
        print("✅ 500 créditos adicionados com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao adicionar créditos: {e}")
    finally:
        await db.disconnect()
        print("Desconectado do banco de dados")

if __name__ == "__main__":
    asyncio.run(add_credits_to_user())