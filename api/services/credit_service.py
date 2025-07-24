from typing import Optional
from prisma import Prisma
from fastapi import HTTPException, status
from datetime import datetime
import json

class CreditService:
    def __init__(self, db: Prisma):
        self.db = db
        
        # Custo por endpoint em créditos
        self.endpoint_costs = {
            "/enrich/company": 1,
            "/enrich/person": 2,
            "/enrich/companies": 1,  # por empresa
            "/enrich/people": 2,     # por pessoa
        }
    
    async def check_credits(self, user_id: str, endpoint: str, quantity: int = 1) -> bool:
        """Verifica se o usuário tem créditos suficientes"""
        user = await self.db.user.find_unique(where={"id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        cost = self.endpoint_costs.get(endpoint, 1) * quantity
        return user.creditsRemaining >= cost
    
    async def consume_credits(self, user_id: str, endpoint: str, request_data: dict, 
                            response_status: str, quantity: int = 1, 
                            ip_address: Optional[str] = None, 
                            user_agent: Optional[str] = None) -> bool:
        """Consome créditos e registra a transação"""
        cost = self.endpoint_costs.get(endpoint, 1) * quantity
        
        # Atualiza créditos do usuário
        user = await self.db.user.update(
            where={"id": user_id},
            data={"creditsRemaining": {"decrement": cost}}
        )
        
        # Registra a transação
        await self.db.credittransaction.create(
            data={
                "userId": user_id,
                "endpoint": endpoint,
                "creditsUsed": cost,
                "requestData": request_data,
                "responseStatus": response_status,
                "ipAddress": ip_address,
                "userAgent": user_agent
            }
        )
        
        return user.creditsRemaining >= 0
    
    async def add_credits(self, user_id: str, credits: int, reason: str = "Manual addition"):
        """Adiciona créditos ao usuário"""
        await self.db.user.update(
            where={"id": user_id},
            data={
                "creditsRemaining": {"increment": credits},
                "creditsTotal": {"increment": credits}
            }
        )
    
    async def get_usage_stats(self, user_id: str, days: int = 30) -> dict:
        """Retorna estatísticas de uso dos últimos N dias"""
        from_date = datetime.utcnow() - timedelta(days=days)
        
        transactions = await self.db.credittransaction.find_many(
            where={
                "userId": user_id,
                "createdAt": {"gte": from_date}
            },
            order_by={"createdAt": "desc"}
        )
        
        total_used = sum(t.creditsUsed for t in transactions)
        by_endpoint = {}
        
        for transaction in transactions:
            endpoint = transaction.endpoint
            if endpoint not in by_endpoint:
                by_endpoint[endpoint] = {"count": 0, "credits": 0}
            by_endpoint[endpoint]["count"] += 1
            by_endpoint[endpoint]["credits"] += transaction.creditsUsed
        
        return {
            "total_credits_used": total_used,
            "total_requests": len(transactions),
            "by_endpoint": by_endpoint,
            "recent_transactions": transactions[:10]  # Últimas 10
        }