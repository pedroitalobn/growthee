from sqlalchemy.orm import Session
from .database import UserDB, CreditTransactionDB, PlanDB
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
        PlanType.FREE: 10,
        PlanType.STARTER: 1000,
        PlanType.PROFESSIONAL: 5000,
        PlanType.ENTERPRISE: 25000,
    }
    
    def __init__(self):
        pass
    
    def check_credits(self, db: Session, user: UserDB, endpoint: str, quantity: int = 1) -> bool:
        """Verifica se o usuário tem créditos suficientes"""
        cost_per_item = self.ENDPOINT_COSTS.get(endpoint, 1)
        total_cost = cost_per_item * quantity
        
        return user.credits_remaining >= total_cost
    
    def consume_credits(self, db: Session, user: UserDB, endpoint: str, request_data: dict, response_status: str, quantity: int = 1):
        """Consome créditos do usuário e registra a transação"""
        cost_per_item = self.ENDPOINT_COSTS.get(endpoint, 1)
        total_cost = cost_per_item * quantity
        
        if user.credits_remaining < total_cost:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient credits. Required: {total_cost}, Available: {user.credits_remaining}"
            )
        
        # Deduzir créditos
        user.credits_remaining -= total_cost
        
        # Registrar transação
        transaction = CreditTransactionDB(
            user_id=user.id,
            endpoint=endpoint,
            credits_used=total_cost,
            request_data=json.dumps(request_data),
            response_status=response_status
        )
        
        db.add(transaction)
        db.commit()
        db.refresh(user)
        
        return transaction
    
    def add_credits(self, db: Session, user: UserDB, credits: int, reason: str = "Manual addition"):
        """Adiciona créditos ao usuário"""
        user.credits_remaining += credits
        user.credits_total += credits
        
        # Registrar como transação positiva
        transaction = CreditTransactionDB(
            user_id=user.id,
            endpoint="credit_addition",
            credits_used=-credits,  # Negativo para indicar adição
            request_data=json.dumps({"reason": reason}),
            response_status="success"
        )
        
        db.add(transaction)
        db.commit()
        db.refresh(user)
        
        return transaction
    
    def upgrade_plan(self, db: Session, user: UserDB, new_plan: PlanType):
        """Atualiza o plano do usuário e adiciona créditos"""
        old_plan = user.plan
        user.plan = new_plan
        
        # Adicionar créditos do novo plano
        credits_to_add = self.PLAN_CREDITS.get(new_plan, 0)
        if credits_to_add > 0:
            self.add_credits(db, user, credits_to_add, f"Plan upgrade from {old_plan} to {new_plan}")
        
        db.commit()
        db.refresh(user)
        
        return user
    
    def get_usage_stats(self, db: Session, user: UserDB, days: int = 30):
        """Obtém estatísticas de uso do usuário"""
        from datetime import datetime, timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        transactions = db.query(CreditTransactionDB).filter(
            CreditTransactionDB.user_id == user.id,
            CreditTransactionDB.created_at >= start_date,
            CreditTransactionDB.credits_used > 0  # Apenas consumo, não adições
        ).all()
        
        total_credits_used = sum(t.credits_used for t in transactions)
        total_requests = len(transactions)
        
        # Agrupar por endpoint
        endpoint_usage = {}
        for transaction in transactions:
            endpoint = transaction.endpoint
            if endpoint not in endpoint_usage:
                endpoint_usage[endpoint] = {"requests": 0, "credits": 0}
            endpoint_usage[endpoint]["requests"] += 1
            endpoint_usage[endpoint]["credits"] += transaction.credits_used
        
        return {
            "period_days": days,
            "total_credits_used": total_credits_used,
            "total_requests": total_requests,
            "credits_remaining": user.credits_remaining,
            "endpoint_usage": endpoint_usage,
            "current_plan": user.plan
        }

credit_service = CreditService()