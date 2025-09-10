from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import Dict, Any, List
from pydantic import BaseModel
from prisma import Prisma
from ..database import get_db
from ..middleware.auth_middleware import get_current_user
from ..services.billing_service import BillingService
import stripe

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

class CheckoutRequest(BaseModel):
    planId: str

class WebhookRequest(BaseModel):
    data: Dict[str, Any]
    type: str

@router.get("/plans")
async def get_plans(db: Prisma = Depends(get_db)):
    """Retorna todos os planos disponíveis"""
    plans = await db.plan.find_many(
        where={"isActive": True}
    )
    return plans

@router.post("/checkout")
async def create_checkout_session(
    request: CheckoutRequest,
    current_user = Depends(get_current_user),
    db: Prisma = Depends(get_db)
):
    """Cria sessão de checkout do Stripe"""
    billing_service = BillingService(db)
    checkout_url = await billing_service.create_checkout_session(
        user_id=current_user.id,
        plan_id=request.planId
    )
    return {"checkout_url": checkout_url}

@router.get("/subscription")
async def get_subscription(
    current_user = Depends(get_current_user),
    db: Prisma = Depends(get_db)
):
    """Retorna subscription atual do usuário"""
    subscription = await db.subscription.find_first(
        where={
            "userId": current_user.id,
            "status": "ACTIVE"
        },
        include={"plan": True}
    )
    return subscription

@router.get("/invoices")
async def get_invoices(
    current_user = Depends(get_current_user),
    db: Prisma = Depends(get_db)
):
    """Retorna faturas do usuário"""
    user = await db.user.find_unique(
        where={"id": current_user.id}
    )
    
    if not user or not user.stripeCustomerId:
        return []
    
    # Buscar invoices no Stripe
    invoices = stripe.Invoice.list(
        customer=user.stripeCustomerId,
        limit=10
    )
    
    return [
        {
            "id": invoice.id,
            "number": invoice.number,
            "status": invoice.status,
            "amount": invoice.amount_paid / 100,  # Converter de centavos
            "currency": invoice.currency.upper(),
            "date": invoice.created,
            "downloadUrl": invoice.hosted_invoice_url
        }
        for invoice in invoices.data
    ]

@router.get("/payment-methods")
async def get_payment_methods(
    current_user = Depends(get_current_user),
    db: Prisma = Depends(get_db)
):
    """Retorna métodos de pagamento do usuário"""
    user = await db.user.find_unique(
        where={"id": current_user.id}
    )
    
    if not user or not user.stripeCustomerId:
        return []
    
    # Buscar payment methods no Stripe
    payment_methods = stripe.PaymentMethod.list(
        customer=user.stripeCustomerId,
        type="card"
    )
    
    return [
        {
            "id": pm.id,
            "type": pm.type,
            "brand": pm.card.brand,
            "last4": pm.card.last4,
            "expiryMonth": pm.card.exp_month,
            "expiryYear": pm.card.exp_year,
            "isDefault": False  # TODO: implementar lógica de default
        }
        for pm in payment_methods.data
    ]

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Prisma = Depends(get_db)
):
    """Endpoint para webhooks do Stripe"""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")
    
    billing_service = BillingService(db)
    return await billing_service.handle_webhook(payload, sig_header)

@router.post("/cancel-subscription")
async def cancel_subscription(
    current_user = Depends(get_current_user),
    db: Prisma = Depends(get_db)
):
    """Cancela subscription do usuário"""
    subscription = await db.subscription.find_first(
        where={
            "userId": current_user.id,
            "status": "ACTIVE"
        }
    )
    
    if not subscription or not subscription.stripeSubscriptionId:
        raise HTTPException(status_code=404, detail="Active subscription not found")
    
    # Cancelar no Stripe
    stripe.Subscription.modify(
        subscription.stripeSubscriptionId,
        cancel_at_period_end=True
    )
    
    # Atualizar no banco
    await db.subscription.update(
        where={"id": subscription.id},
        data={"cancelAtPeriodEnd": True}
    )
    
    return {"message": "Subscription will be cancelled at the end of the current period"}