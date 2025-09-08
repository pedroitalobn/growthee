import asyncio
from prisma import Prisma

async def check_tables():
    db = Prisma()
    await db.connect()
    
    try:
        # Verificar tabelas existentes
        tables = await db.query_raw('SELECT name FROM sqlite_master WHERE type="table";')
        print('Tabelas existentes:')
        for table in tables:
            print(f"  - {table['name']}")
        
        # Verificar se a tabela api_keys existe
        if any(t['name'] == 'api_keys' for t in tables):
            print('\n✅ Tabela api_keys encontrada')
            
            # Verificar estrutura da tabela
            columns = await db.query_raw('PRAGMA table_info(api_keys);')
            print('\nEstrutura da tabela api_keys:')
            for col in columns:
                print(f"  - {col['name']}: {col['type']}")
        else:
            print('\n❌ Tabela api_keys NÃO encontrada')
            
    except Exception as e:
        print(f'Erro: {e}')
    finally:
        await db.disconnect()

if __name__ == '__main__':
    asyncio.run(check_tables())