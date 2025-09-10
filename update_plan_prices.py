#!/usr/bin/env python3
"""
Script para atualizar os preços dos planos conforme especificação:
- Free: $0/mês - 1500 créditos
- Starter: $19/mês - 1500 créditos
- Professional: $59/mês - 5000 créditos
- Enterprise: $99/mês - 10000 créditos
"""

import asyncio
from prisma import Prisma

async def update_plan_prices():
    """Atualiza os preços e créditos dos planos"""
    db = Prisma()
    await db.connect()
    
    try:
        # Definir os novos valores dos planos
        plan_updates = {
            'Free': {'price_monthly': 0.0, 'credits_included': 250},
            'Starter': {'price_monthly': 9.0, 'credits_included': 1000},
            'Professional': {'price_monthly': 19.0, 'credits_included': 3000},
            'Enterprise': {'price_monthly': 39.0, 'credits_included': 5000}
        }
        
        print("Atualizando preços dos planos...")
        
        for plan_name, updates in plan_updates.items():
            # Buscar o plano pelo nome
            plan = await db.plan.find_first(
                where={"name": plan_name}
            )
            
            if plan:
                old_price = plan.priceMonthly
                old_credits = plan.creditsIncluded
                
                # Atualizar o plano
                updated_plan = await db.plan.update(
                    where={"id": plan.id},
                    data={
                        "priceMonthly": updates['price_monthly'],
                        "creditsIncluded": updates['credits_included']
                    }
                )
                
                print(f"{plan_name}:")
                print(f"  Preço: ${old_price} -> ${updates['price_monthly']}")
                print(f"  Créditos: {old_credits} -> {updates['credits_included']}")
            else:
                print(f"⚠️  Plano '{plan_name}' não encontrado!")
        
        print("\n✅ Preços atualizados com sucesso!")
        
        # Verificar os valores atualizados
        print("\nPlanos atualizados:")
        plans = await db.plan.find_many()
        for plan in plans:
            print(f"  {plan.name}: ${plan.priceMonthly}/mês - {plan.creditsIncluded} créditos")
            
    except Exception as e:
        print(f"❌ Erro ao atualizar planos: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(update_plan_prices())