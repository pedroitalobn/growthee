import asyncio
from prisma import Prisma

async def seed_plans():
    db = Prisma()
    await db.connect()
    
    plans = [
        {
            "name": "Free",
            "type": "FREE",
            "creditsIncluded": 10,
            "priceMonthly": 0.0,
            "priceYearly": 0.0,
            "features": ["10 créditos/mês", "Suporte por email", "API básica"]
        },
        {
            "name": "Starter",
            "type": "STARTER",
            "creditsIncluded": 500,
            "priceMonthly": 29.0,
            "priceYearly": 290.0,
            "features": ["500 créditos/mês", "Suporte prioritário", "API completa", "Dashboard avançado"],
            "stripePriceId": "price_starter_monthly"  # Substituir pelo ID real
        },
        {
            "name": "Professional",
            "type": "PROFESSIONAL",
            "creditsIncluded": 2000,
            "priceMonthly": 99.0,
            "priceYearly": 990.0,
            "features": ["2.000 créditos/mês", "Suporte 24/7", "API completa", "Webhooks", "Relatórios avançados"],
            "stripePriceId": "price_professional_monthly"
        },
        {
            "name": "Enterprise",
            "type": "ENTERPRISE",
            "creditsIncluded": 10000,
            "priceMonthly": 299.0,
            "priceYearly": 2990.0,
            "features": ["10.000 créditos/mês", "Suporte dedicado", "API completa", "Endpoints customizados", "SLA garantido"],
            "stripePriceId": "price_enterprise_monthly"
        }
    ]
    
    for plan_data in plans:
        await db.plan.upsert(
            where={"type": plan_data["type"]},
            data=plan_data,
            update=plan_data
        )
    
    await db.disconnect()
    print("✅ Planos criados com sucesso!")

if __name__ == "__main__":
    asyncio.run(seed_plans())


## 3. 🔧 Configuração do Stripe

### Criar Produtos no Dashboard Stripe:

1. **Acesse**: https://dashboard.stripe.com/products
2. **Crie os produtos**:
   - **Starter**: $29/mês - 500 créditos
   - **Professional**: $99/mês - 2.000 créditos  
   - **Enterprise**: $299/mês - 10.000 créditos

3. **Configure Webhooks**:
   - URL: `https://sua-api.com/api/v1/billing/webhook`
   - Eventos: `checkout.session.completed`, `invoice.payment_succeeded`, `customer.subscription.deleted`

### Script para Popular Planos:
```python
import asyncio
from prisma import Prisma

async def seed_plans():
    db = Prisma()
    await db.connect()
    
    plans = [
        {
            "name": "Free",
            "type": "FREE",
            "creditsIncluded": 10,
            "priceMonthly": 0.0,
            "priceYearly": 0.0,
            "features": ["10 créditos/mês", "Suporte por email", "API básica"]
        },
        {
            "name": "Starter",
            "type": "STARTER",
            "creditsIncluded": 500,
            "priceMonthly": 29.0,
            "priceYearly": 290.0,
            "features": ["500 créditos/mês", "Suporte prioritário", "API completa", "Dashboard avançado"],
            "stripePriceId": "price_starter_monthly"  # Substituir pelo ID real
        },
        {
            "name": "Professional",
            "type": "PROFESSIONAL",
            "creditsIncluded": 2000,
            "priceMonthly": 99.0,
            "priceYearly": 990.0,
            "features": ["2.000 créditos/mês", "Suporte 24/7", "API completa", "Webhooks", "Relatórios avançados"],
            "stripePriceId": "price_professional_monthly"
        },
        {
            "name": "Enterprise",
            "type": "ENTERPRISE",
            "creditsIncluded": 10000,
            "priceMonthly": 299.0,
            "priceYearly": 2990.0,
            "features": ["10.000 créditos/mês", "Suporte dedicado", "API completa", "Endpoints customizados", "SLA garantido"],
            "stripePriceId": "price_enterprise_monthly"
        }
    ]
    
    for plan_data in plans:
        await db.plan.upsert(
            where={"type": plan_data["type"]},
            data=plan_data,
            update=plan_data
        )
    
    await db.disconnect()
    print("✅ Planos criados com sucesso!")

if __name__ == "__main__":
    asyncio.run(seed_plans())
```