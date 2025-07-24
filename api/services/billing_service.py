import stripe
import os
from typing import Dict, Any
from prisma import Prisma
from fastapi import HTTPException, status
from datetime import datetime, timedelta

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class BillingService:
    def __init__(self, db: Prisma):
        self.db = db
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    async def create_checkout_session(self, user_id: str, plan_id: str) -> Dict[str, Any]:
        """Cria sessão de checkout do Stripe"""
        user = await self.db.user.find_unique(where={"id": user_id})
        plan = await self.db.plan.find_unique(where={"id": plan_id})
        
        if not user or not plan:
            raise HTTPException(status_code=404, detail="User or plan not found")
        
        # Criar ou recuperar customer do Stripe
        if not user.stripeCustomerId:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.fullName,
                metadata={"user_id": user.id}
            )
            
            await self.db.user.update(
                where={"id": user_id},
                data={"stripeCustomerId": customer.id}
            )
        else:
            customer = stripe.Customer.retrieve(user.stripeCustomerId)
        
        # Criar sessão de checkout
        session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[{
                'price': plan.stripePriceId,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{os.getenv('FRONTEND_URL')}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{os.getenv('FRONTEND_URL')}/billing/cancel",
            metadata={
                "user_id": user_id,
                "plan_id": plan_id
            }
        )
        
        return {"sessionId": session.id, "url": session.url}
    
    async def handle_webhook(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """Processa webhooks do Stripe"""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Processar eventos
        if event['type'] == 'checkout.session.completed':
            await self._handle_checkout_completed(event['data']['object'])
        elif event['type'] == 'invoice.payment_succeeded':
            await self._handle_payment_succeeded(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            await self._handle_subscription_cancelled(event['data']['object'])
        
        return {"status": "success"}
    
    async def _handle_checkout_completed(self, session: Dict[str, Any]):
        """Processa checkout completado"""
        user_id = session['metadata']['user_id']
        plan_id = session['metadata']['plan_id']
        
        # Recuperar subscription do Stripe
        subscription = stripe.Subscription.retrieve(session['subscription'])
        plan = await self.db.plan.find_unique(where={"id": plan_id})
        
        # Criar subscription no banco
        await self.db.subscription.create(
            data={
                "userId": user_id,
                "planId": plan_id,
                "stripeSubscriptionId": subscription.id,
                "status": "ACTIVE",
                "currentPeriodStart": datetime.fromtimestamp(subscription.current_period_start),
                "currentPeriodEnd": datetime.fromtimestamp(subscription.current_period_end)
            }
        )
        
        # Atualizar usuário
        await self.db.user.update(
            where={"id": user_id},
            data={
                "plan": plan.type,
                "creditsRemaining": plan.creditsIncluded,
                "creditsTotal": plan.creditsIncluded
            }
        )
    
    async def _handle_payment_succeeded(self, invoice: Dict[str, Any]):
        """Processa pagamento bem-sucedido (renovação)"""
        subscription_id = invoice['subscription']
        
        subscription_record = await self.db.subscription.find_first(
            where={"stripeSubscriptionId": subscription_id},
            include={"user": True, "plan": True}
        )
        
        if subscription_record:
            # Renovar créditos
            await self.db.user.update(
                where={"id": subscription_record.userId},
                data={
                    "creditsRemaining": subscription_record.plan.creditsIncluded,
                    "creditsTotal": {"increment": subscription_record.plan.creditsIncluded}
                }
            )
    
    async def _handle_subscription_cancelled(self, subscription: Dict[str, Any]):
        """Processa cancelamento de subscription"""
        subscription_record = await self.db.subscription.find_first(
            where={"stripeSubscriptionId": subscription['id']}
        )
        
        if subscription_record:
            # Atualizar status
            await self.db.subscription.update(
                where={"id": subscription_record.id},
                data={"status": "CANCELED"}
            )
            
            # Downgrade para plano gratuito
            free_plan = await self.db.plan.find_first(
                where={"type": "FREE"}
            )
            
            if free_plan:
                await self.db.user.update(
                    where={"id": subscription_record.userId},
                    data={"plan": "FREE"}
                )