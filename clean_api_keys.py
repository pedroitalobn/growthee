#!/usr/bin/env python3

import asyncio
from prisma import Prisma

async def clean_api_keys():
    """Remove todas as API keys existentes para testes limpos"""
    db = Prisma()
    await db.connect()
    
    try:
        # Buscar todas as API keys
        api_keys = await db.apikey.find_many()
        print(f"API keys encontradas: {len(api_keys)}")
        
        # Deletar todas
        if api_keys:
            deleted = await db.apikey.delete_many()
            print(f"API keys deletadas: {deleted}")
        else:
            print("Nenhuma API key para deletar")
            
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(clean_api_keys())