from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any
from prisma import Prisma
from ..database import get_db
from ..middleware.auth_middleware import get_current_user
from ..services.credit_service import CreditService
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

@router.get("/stats")
async def get_dashboard_stats(
    current_user = Depends(get_current_user),
    db: Prisma = Depends(get_db)
) -> Dict[str, Any]:
    """Retorna estatísticas do dashboard para o usuário atual"""
    try:
        credit_service = CreditService(db)
        
        # Obter estatísticas de uso dos últimos 30 dias
        usage_stats = await credit_service.get_usage_stats(current_user.id, 30)
        
        # Obter transações recentes
        recent_transactions = await db.credittransaction.find_many(
            where={
                "userId": current_user.id
            },
            order={"createdAt": "desc"},
            take=10
        )
        
        # Formatar transações para o frontend
        formatted_transactions = []
        for transaction in recent_transactions:
            formatted_transactions.append({
                "id": transaction.id,
                "endpoint": transaction.endpoint,
                "credits_used": transaction.creditsUsed,
                "status": transaction.status,
                "created_at": transaction.createdAt.isoformat(),
                "request_data": transaction.requestData
            })
        
        # Preparar dados de uso por endpoint
        endpoint_usage = {}
        for endpoint, data in usage_stats["by_endpoint"].items():
            endpoint_usage[endpoint] = {
                "count": data["count"],
                "credits": data["credits"]
            }
        
        return {
            "usage": {
                "total_requests": usage_stats["total_requests"],
                "total_credits_used": usage_stats["total_credits_used"],
                "by_endpoint": endpoint_usage,
                "recent_transactions": formatted_transactions
            },
            "user": {
                "credits_remaining": current_user.creditsRemaining,
                "credits_total": current_user.creditsTotal,
                "plan": current_user.plan
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching dashboard stats: {str(e)}"
        )