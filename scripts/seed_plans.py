import asyncio
from prisma import Prisma

async def seed_plans():
    db = Prisma()
    await db.connect()
    
    plans = [
        {
            "name": "Free",
            "type": "FREE",
            "creditsIncluded": 250,
            "priceMonthly": 0.0,
            "priceYearly": 0.0,
            "features": "250 créditos/mês, Suporte por email, API básica"
        },
        {
            "name": "Starter",
            "type": "STARTER",
            "creditsIncluded": 1000,
            "priceMonthly": 9.0,
            "priceYearly": 90.0,
            "features": "1.000 créditos/mês, Suporte prioritário, API completa, Dashboard avançado",
            "stripePriceId": "price_starter_monthly"  # Substituir pelo ID real
        },
        {
            "name": "Professional",
            "type": "PROFESSIONAL",
            "creditsIncluded": 3000,
            "priceMonthly": 19.0,
            "priceYearly": 190.0,
            "features": "3.000 créditos/mês, Suporte 24/7, API completa, Webhooks, Relatórios avançados",
            "stripePriceId": "price_professional_monthly"
        },
        {
            "name": "Enterprise",
            "type": "ENTERPRISE",
            "creditsIncluded": 5000,
            "priceMonthly": 39.0,
            "priceYearly": 390.0,
            "features": "5.000 créditos/mês + $9 por 1.000 créditos extras, Suporte dedicado, API completa, Endpoints customizados, SLA garantido",
            "stripePriceId": "price_enterprise_monthly"
        }
    ]
    
    for plan_data in plans:
        existing_plan = await db.plan.find_first(
            where={"type": plan_data["type"]}
        )
        
        if existing_plan:
            await db.plan.update(
                where={"id": existing_plan.id},
                data=plan_data
            )
        else:
            await db.plan.create(data=plan_data)
    
    await db.disconnect()
    print("✅ Planos criados com sucesso!")

if __name__ == "__main__":
    asyncio.run(seed_plans())

# INSTRUÇÕES PARA CONFIGURAR STRIPE:
# 1. Acesse: https://dashboard.stripe.com/products
# 2. Crie os produtos:
#    - Starter: $29/mês - 500 créditos
#    - Professional: $99/mês - 2.000 créditos  
#    - Enterprise: $299/mês - 10.000 créditos
# 3. Configure Webhooks:
#    - URL: https://sua-api.com/api/v1/billing/webhook
#    - Eventos: checkout.session.completed, invoice.payment_succeeded, customer.subscription.deleted