from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from pydantic import BaseModel
from prisma import Prisma
from ..database import get_db
from ..middleware.auth_middleware import get_current_user
from ..services.credit_service import CreditService
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime

security = HTTPBearer()
router = APIRouter(prefix="/api/v1/auth", tags=["auth-credits"])

class CreditTransaction(BaseModel):
    id: str
    type: str
    amount: int
    description: str
    createdAt: datetime
    metadata: dict = {}

class UsageStats(BaseModel):
    totalCreditsUsed: int
    totalRequests: int
    averageCreditsPerRequest: float
    mostUsedEndpoint: str
    dailyUsage: List[dict]
    endpointUsage: List[dict]

async def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Prisma = Depends(get_db)
):
    return await get_current_user(credentials, db)

@router.get("/credits/history", response_model=List[CreditTransaction])
async def get_credit_history(
    db: Prisma = Depends(get_db),
    current_user = Depends(get_authenticated_user)
):
    """Obtém o histórico de transações de créditos do usuário"""
    try:
        transactions = await db.credittransaction.find_many(
            where={"userId": current_user.id},
            order={"createdAt": "desc"},
            take=100  # Limitar a 100 transações mais recentes
        )
        
        return [
            CreditTransaction(
                id=t.id,
                type="USAGE" if t.creditsUsed > 0 else "PURCHASE",
                amount=t.creditsUsed if t.creditsUsed > 0 else t.creditsAdded,
                description=t.description or f"Uso do endpoint {t.endpoint}",
                createdAt=t.createdAt,
                metadata={
                    "endpoint": t.endpoint,
                    "status": t.status
                }
            )
            for t in transactions
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar histórico de créditos: {str(e)}"
        )

@router.get("/credits/usage-stats", response_model=UsageStats)
async def get_usage_stats(
    db: Prisma = Depends(get_db),
    current_user = Depends(get_authenticated_user)
):
    """Obtém estatísticas de uso de créditos do usuário"""
    try:
        credit_service = CreditService(db)
        stats = await credit_service.get_usage_stats(current_user.id, days=30)
        
        # Calcular endpoint mais usado
        most_used_endpoint = "/enrich/company"  # Default
        max_usage = 0
        
        endpoint_usage_list = []
        total_requests = stats.get("total_requests", 0)
        
        for endpoint, data in stats.get("by_endpoint", {}).items():
            credits = data.get("credits", 0)
            requests = data.get("count", 0)
            
            if credits > max_usage:
                max_usage = credits
                most_used_endpoint = endpoint
            
            endpoint_usage_list.append({
                "endpoint": endpoint,
                "credits": credits,
                "requests": requests,
                "percentage": (credits / stats.get("total_credits_used", 1)) * 100 if stats.get("total_credits_used", 0) > 0 else 0
            })
        
        # Gerar dados diários simulados (em uma implementação real, você buscaria do banco)
        daily_usage = []
        from datetime import datetime, timedelta
        for i in range(7):  # Últimos 7 dias
            date = datetime.now() - timedelta(days=i)
            daily_usage.append({
                "date": date.isoformat(),
                "credits": max(0, stats.get("total_credits_used", 0) // 7 + (i % 3)),
                "requests": max(0, total_requests // 7 + (i % 2))
            })
        
        return UsageStats(
            totalCreditsUsed=stats.get("total_credits_used", 0),
            totalRequests=total_requests,
            averageCreditsPerRequest=stats.get("total_credits_used", 0) / max(1, total_requests),
            mostUsedEndpoint=most_used_endpoint,
            dailyUsage=daily_usage,
            endpointUsage=endpoint_usage_list
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar estatísticas de uso: {str(e)}"
        )