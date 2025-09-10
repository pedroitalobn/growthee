from prisma import Prisma
from .auth_models import PlanType
from fastapi import HTTPException, status
import json
from datetime import datetime

class CreditService:
    # Definir custos por endpoint
    ENDPOINT_COSTS = {
        "/enrich/company": 1,
        "/enrich/person": 2,
        "/enrich/companies": 1,  # por empresa
        "/enrich/people": 2,     # por pessoa
    }
    
    # Planos e créditos inclusos
    PLAN_CREDITS = {
        PlanType.FREE: 250,
        PlanType.STARTER: 1000,
        PlanType.PROFESSIONAL: 3000,
        PlanType.ENTERPRISE: 5000,
    }
    
    def __init__(self):
        pass
    
    async def check_credits(self, db: Prisma, user, endpoint: str, quantity: int = 1) -> bool:
        """Verifica se o usuário tem créditos suficientes"""
        cost_per_item = self.ENDPOINT_COSTS.get(endpoint, 1)
        total_cost = cost_per_item * quantity
        
        return user.creditsRemaining >= total_cost
    
    async def consume_credits(self, db: Prisma, user, endpoint: str, request_data: dict, response_status: str, quantity: int = 1):
        """Consome créditos do usuário e registra a transação"""
        cost_per_item = self.ENDPOINT_COSTS.get(endpoint, 1)
        total_cost = cost_per_item * quantity
        
        if user.creditsRemaining < total_cost:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient credits. Required: {total_cost}, Available: {user.creditsRemaining}"
            )
        
        # Deduzir créditos
        await db.user.update(
            where={"id": user.id},
            data={"creditsRemaining": user.creditsRemaining - total_cost}
        )
        
        # Registrar transação
        transaction = await db.credittransaction.create(
            data={
                "userId": user.id,
                "endpoint": endpoint,
                "creditsUsed": total_cost,
                "requestData": json.dumps(request_data),
                "responseStatus": response_status,
                "createdAt": datetime.utcnow()
            }
        )
        
        return transaction
    
    async def add_credits(self, db: Prisma, user, credits: int, reason: str = "Manual addition"):
        """Adiciona créditos ao usuário"""
        # Atualizar créditos do usuário
        updated_user = await db.user.update(
            where={"id": user.id},
            data={
                "creditsRemaining": user.creditsRemaining + credits,
                "creditsTotal": user.creditsTotal + credits
            }
        )
        
        # Registrar como transação positiva
        transaction = await db.credittransaction.create(
            data={
                "userId": user.id,
                "endpoint": "credit_addition",
                "creditsUsed": -credits,  # Negativo para indicar adição
                "requestData": json.dumps({"reason": reason}),
                "responseStatus": "success",
                "createdAt": datetime.utcnow()
            }
        )
        
        return transaction
    
    async def upgrade_plan(self, db: Prisma, user, new_plan: PlanType):
        """Atualiza o plano do usuário e adiciona créditos"""
        old_plan = user.plan
        
        # Atualizar plano do usuário
        updated_user = await db.user.update(
            where={"id": user.id},
            data={"plan": new_plan}
        )
        
        # Adicionar créditos do novo plano
        credits_to_add = self.PLAN_CREDITS.get(new_plan, 0)
        if credits_to_add > 0:
            await self.add_credits(db, updated_user, credits_to_add, f"Plan upgrade from {old_plan} to {new_plan}")
        
        return updated_user
    
    async def get_usage_stats(self, db: Prisma, user, days: int = 30):
        """Obtém estatísticas de uso do usuário"""
        from datetime import datetime, timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        transactions = await db.credittransaction.find_many(
            where={
                "userId": user.id,
                "createdAt": {"gte": start_date},
                "creditsUsed": {"gt": 0}  # Apenas consumo, não adições
            }
        )
        
        total_credits_used = sum(t.creditsUsed for t in transactions)
        total_requests = len(transactions)
        
        # Agrupar por endpoint
        endpoint_usage = {}
        for transaction in transactions:
            endpoint = transaction.endpoint
            if endpoint not in endpoint_usage:
                endpoint_usage[endpoint] = {"requests": 0, "credits": 0}
            endpoint_usage[endpoint]["requests"] += 1
            endpoint_usage[endpoint]["credits"] += transaction.creditsUsed
        
        return {
            "period_days": days,
            "total_credits_used": total_credits_used,
            "total_requests": total_requests,
            "credits_remaining": user.credits_remaining,
            "endpoint_usage": endpoint_usage,
            "current_plan": user.plan
        }

credit_service = CreditService()

# Funções auxiliares para compatibilidade
async def add_credits(db: Prisma, user, credits: int, reason: str = "Manual addition"):
    """Função auxiliar para adicionar créditos"""
    return await credit_service.add_credits(db, user, credits, reason)

async def deduct_credits(db: Prisma, user, credits: int, reason: str = "Manual deduction"):
    """Função auxiliar para deduzir créditos"""
    return await credit_service.add_credits(db, user, -credits, reason)