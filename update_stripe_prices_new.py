#!/usr/bin/env python3
"""
Script para criar novos preços no Stripe com os valores atualizados:
- Starter: $19/mês
- Professional: $59/mês  
- Enterprise: $99/mês
"""

import asyncio
import stripe
import os
from prisma import Prisma
from dotenv import load_dotenv

load_dotenv()

# Configurar Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

async def create_new_stripe_prices():
    """Cria novos preços no Stripe e atualiza os planos no banco"""
    db = Prisma()
    await db.connect()
    
    try:
        # Definir os novos preços
        new_prices = {
            'Starter': {'amount': 1900, 'product_name': 'Growthee Starter Plan'},  # $19.00
            'Professional': {'amount': 5900, 'product_name': 'Growthee Professional Plan'},  # $59.00
            'Enterprise': {'amount': 9900, 'product_name': 'Growthee Enterprise Plan'}  # $99.00
        }
        
        print("Criando novos preços no Stripe...")
        
        for plan_name, price_info in new_prices.items():
            try:
                # Criar produto no Stripe
                product = stripe.Product.create(
                    name=price_info['product_name'],
                    description=f"Plano {plan_name} da Growthee"
                )
                
                # Criar preço no Stripe
                price = stripe.Price.create(
                    unit_amount=price_info['amount'],  # em centavos
                    currency='usd',
                    recurring={'interval': 'month'},
                    product=product.id,
                    nickname=f"{plan_name.lower()}_monthly_new"
                )
                
                print(f"✅ {plan_name}: Produto {product.id}, Preço {price.id} (${price_info['amount']/100})")
                
                # Atualizar o plano no banco de dados com o novo stripePriceId
                plan = await db.plan.find_first(
                    where={"name": plan_name}
                )
                
                if plan:
                    await db.plan.update(
                        where={"id": plan.id},
                        data={"stripePriceId": price.id}
                    )
                    print(f"   Plano {plan_name} atualizado no banco com stripePriceId: {price.id}")
                else:
                    print(f"⚠️  Plano {plan_name} não encontrado no banco!")
                    
            except stripe.error.StripeError as e:
                print(f"❌ Erro ao criar preço para {plan_name}: {e}")
        
        print("\n✅ Novos preços criados com sucesso!")
        
        # Verificar os planos atualizados
        print("\nPlanos com novos stripePriceIds:")
        plans = await db.plan.find_many()
        for plan in plans:
            stripe_price_id = getattr(plan, 'stripePriceId', 'N/A')
            print(f"  {plan.name}: ${plan.priceMonthly}/mês - {plan.creditsIncluded} créditos - Stripe: {stripe_price_id}")
            
    except Exception as e:
        print(f"❌ Erro geral: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(create_new_stripe_prices())