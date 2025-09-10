from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import json
import os
from collections import defaultdict

from ..database import get_db
from ..auth_models import User, Plan, CreditTransaction, APIKey, UserRole, PlanType
from ..middleware.admin_middleware import require_super_admin, require_admin
from ..middleware.auth_middleware import get_current_user
from ..credit_service import add_credits, deduct_credits
from ..models import APIUsageResponse, APIServiceStats, APIRequestLog, APIAlertConfig
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["admin"])

# Modelos de request/response
class UserCreateRequest(BaseModel):
    email: str
    password: str
    name: str
    role: UserRole = UserRole.USER
    plan_type: Optional[PlanType] = None
    initial_credits: int = 0

class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class PlanAssignRequest(BaseModel):
    user_id: int
    plan_type: PlanType
    is_active: bool = True

class CreditManagementRequest(BaseModel):
    user_id: int
    amount: int
    operation: str  # "add" or "deduct"
    description: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    plan: Optional[dict] = None
    credits: int
    total_api_calls: int

# Rotas de gerenciamento de usuários
@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    role_filter: Optional[UserRole] = Query(None),
    active_only: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Listar todos os usuários com filtros opcionais"""
    query = db.query(User)
    
    if search:
        query = query.filter(
            (User.email.ilike(f"%{search}%")) |
            (User.name.ilike(f"%{search}%"))
        )
    
    if role_filter:
        query = query.filter(User.role == role_filter)
    
    if active_only is not None:
        query = query.filter(User.is_active == active_only)
    
    users = query.offset(skip).limit(limit).all()
    
    result = []
    for user in users:
        plan_data = None
        if user.plan:
            plan_data = {
                "id": user.plan.id,
                "type": user.plan.type,
                "name": user.plan.name,
                "is_active": user.plan.is_active
            }
        
        result.append(UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            plan=plan_data,
            credits=user.credits,
            total_api_calls=user.total_api_calls
        ))
    
    return result

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obter detalhes de um usuário específico"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    plan_data = None
    if user.plan:
        plan_data = {
            "id": user.plan.id,
            "type": user.plan.type,
            "name": user.plan.name,
            "is_active": user.plan.is_active
        }
    
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        plan=plan_data,
        credits=user.credits,
        total_api_calls=user.total_api_calls
    )

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Criar novo usuário"""
    # Verificar se email já existe
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email já está em uso")
    
    # Criar usuário
    from ..auth_service import hash_password
    hashed_password = hash_password(user_data.password)
    
    new_user = User(
        email=user_data.email,
        password=hashed_password,
        name=user_data.name,
        role=user_data.role,
        credits=user_data.initial_credits,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Atribuir plano se especificado
    if user_data.plan_type:
        plan = db.query(Plan).filter(Plan.type == user_data.plan_type).first()
        if plan:
            new_user.plan_id = plan.id
            db.commit()
    
    return await get_user_by_id(new_user.id, db, current_user)

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Atualizar dados do usuário"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Verificar permissões para alterar roles
    if user_data.role and current_user.role != UserRole.SUPER_ADMIN:
        if user_data.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            raise HTTPException(status_code=403, detail="Apenas super admin pode alterar roles administrativos")
    
    # Atualizar campos
    if user_data.name is not None:
        user.name = user_data.name
    if user_data.email is not None:
        # Verificar se novo email já existe
        existing = db.query(User).filter(User.email == user_data.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email já está em uso")
        user.email = user_data.email
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    db.commit()
    return await get_user_by_id(user_id, db, current_user)

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Deletar usuário (soft delete)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Não é possível deletar sua própria conta")
    
    user.is_active = False
    db.commit()
    
    return {"message": "Usuário desativado com sucesso"}

# Rotas de gerenciamento de planos
@router.post("/users/assign-plan")
async def assign_plan_to_user(
    plan_data: PlanAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Atribuir plano a um usuário"""
    user = db.query(User).filter(User.id == plan_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    plan = db.query(Plan).filter(Plan.type == plan_data.plan_type).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    
    user.plan_id = plan.id
    plan.is_active = plan_data.is_active
    
    db.commit()
    
    return {"message": f"Plano {plan.name} atribuído ao usuário {user.name}"}

@router.post("/users/{user_id}/toggle-plan")
async def toggle_user_plan(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Ativar/desativar plano do usuário"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.plan:
        raise HTTPException(status_code=404, detail="Usuário ou plano não encontrado")
    
    user.plan.is_active = not user.plan.is_active
    db.commit()
    
    status = "ativado" if user.plan.is_active else "desativado"
    return {"message": f"Plano {status} para o usuário {user.name}"}

# Rotas de gerenciamento de créditos
@router.post("/credits/manage")
async def manage_user_credits(
    credit_data: CreditManagementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Adicionar ou remover créditos de um usuário"""
    user = db.query(User).filter(User.id == credit_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    if credit_data.operation == "add":
        success = add_credits(db, user.id, credit_data.amount, credit_data.description or "Créditos adicionados pelo admin")
    elif credit_data.operation == "deduct":
        success = deduct_credits(db, user.id, credit_data.amount, credit_data.description or "Créditos removidos pelo admin")
    else:
        raise HTTPException(status_code=400, detail="Operação inválida. Use 'add' ou 'deduct'")
    
    if not success:
        raise HTTPException(status_code=400, detail="Erro ao processar operação de créditos")
    
    db.refresh(user)
    return {
        "message": f"Operação realizada com sucesso",
        "user_credits": user.credits,
        "operation": credit_data.operation,
        "amount": credit_data.amount
    }

@router.get("/users/{user_id}/credit-history")
async def get_user_credit_history(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obter histórico de créditos de um usuário"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    transactions = db.query(CreditTransaction).filter(
        CreditTransaction.user_id == user_id
    ).order_by(CreditTransaction.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "user_id": user_id,
        "user_name": user.name,
        "current_credits": user.credits,
        "transactions": [
            {
                "id": t.id,
                "amount": t.amount,
                "type": t.type,
                "description": t.description,
                "created_at": t.created_at
            } for t in transactions
        ]
    }

# Rotas de gerenciamento de API Keys
@router.get("/users/{user_id}/api-keys")
async def get_user_api_keys(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obter API keys de um usuário"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    api_keys = db.query(APIKey).filter(APIKey.user_id == user_id).all()
    
    return {
        "user_id": user_id,
        "user_name": user.name,
        "api_keys": [
            {
                "id": key.id,
                "name": key.name,
                "key": key.key[:8] + "...",  # Mostrar apenas primeiros 8 caracteres
                "is_active": key.is_active,
                "created_at": key.created_at,
                "last_used_at": key.last_used_at
            } for key in api_keys
        ]
    }

@router.post("/users/{user_id}/api-keys/{key_id}/toggle")
async def toggle_api_key(
    user_id: int,
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Ativar/desativar API key de um usuário"""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == user_id
    ).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key não encontrada")
    
    api_key.is_active = not api_key.is_active
    db.commit()
    
    status = "ativada" if api_key.is_active else "desativada"
    return {"message": f"API Key {status} com sucesso"}

# Rotas de gerenciamento de planos
class PlanCreateRequest(BaseModel):
    name: str
    type: PlanType
    description: Optional[str] = None
    price: float = 0.0
    credits_included: int = 0
    max_api_calls: Optional[int] = None
    features: Optional[List[str]] = []
    is_active: bool = True

class PlanUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    credits_included: Optional[int] = None
    max_api_calls: Optional[int] = None
    features: Optional[List[str]] = None
    is_active: Optional[bool] = None

@router.get("/plans")
async def get_all_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Listar todos os planos disponíveis"""
    plans = db.query(Plan).all()
    
    result = []
    for plan in plans:
        # Contar usuários ativos neste plano
        active_users_count = db.query(User).filter(
            User.plan_id == plan.id,
            User.is_active == True
        ).count()
        
        result.append({
            "id": plan.id,
            "name": plan.name,
            "type": plan.type,
            "description": plan.description,
            "price": plan.price,
            "credits_included": plan.credits_included,
            "max_api_calls": plan.max_api_calls,
            "features": plan.features,
            "is_active": plan.is_active,
            "active_users_count": active_users_count,
            "created_at": plan.created_at
        })
    
    return result

@router.post("/plans")
async def create_plan(
    plan_data: PlanCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Criar novo plano"""
    # Verificar se já existe um plano com o mesmo tipo
    existing_plan = db.query(Plan).filter(Plan.type == plan_data.type).first()
    if existing_plan:
        raise HTTPException(status_code=400, detail="Já existe um plano com este tipo")
    
    new_plan = Plan(
        name=plan_data.name,
        type=plan_data.type,
        description=plan_data.description,
        price=plan_data.price,
        credits_included=plan_data.credits_included,
        max_api_calls=plan_data.max_api_calls,
        features=plan_data.features,
        is_active=plan_data.is_active
    )
    
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    
    return {
        "message": "Plano criado com sucesso",
        "plan": {
            "id": new_plan.id,
            "name": new_plan.name,
            "type": new_plan.type,
            "price": new_plan.price
        }
    }

@router.put("/plans/{plan_id}")
async def update_plan(
    plan_id: int,
    plan_data: PlanUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Atualizar plano existente"""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    
    # Atualizar campos
    if plan_data.name is not None:
        plan.name = plan_data.name
    if plan_data.description is not None:
        plan.description = plan_data.description
    if plan_data.price is not None:
        plan.price = plan_data.price
    if plan_data.credits_included is not None:
        plan.credits_included = plan_data.credits_included
    if plan_data.max_api_calls is not None:
        plan.max_api_calls = plan_data.max_api_calls
    if plan_data.features is not None:
        plan.features = plan_data.features
    if plan_data.is_active is not None:
        plan.is_active = plan_data.is_active
    
    db.commit()
    
    return {"message": "Plano atualizado com sucesso"}

@router.delete("/plans/{plan_id}")
async def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Deletar plano (verificar se não há usuários ativos)"""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    
    # Verificar se há usuários ativos com este plano
    active_users = db.query(User).filter(
        User.plan_id == plan_id,
        User.is_active == True
    ).count()
    
    if active_users > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Não é possível deletar o plano. Há {active_users} usuários ativos com este plano."
        )
    
    db.delete(plan)
    db.commit()
    
    return {"message": "Plano deletado com sucesso"}

@router.post("/plans/{plan_id}/toggle")
async def toggle_plan_status(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Ativar/desativar plano"""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    
    plan.is_active = not plan.is_active
    db.commit()
    
    status = "ativado" if plan.is_active else "desativado"
    return {"message": f"Plano {status} com sucesso"}

# Rotas de gerenciamento de assinaturas
@router.get("/subscriptions")
async def get_all_subscriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    plan_type: Optional[PlanType] = Query(None),
    active_only: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Listar todas as assinaturas com filtros"""
    query = db.query(User).join(Plan).filter(User.plan_id.isnot(None))
    
    if plan_type:
        query = query.filter(Plan.type == plan_type)
    
    if active_only is not None:
        query = query.filter(User.is_active == active_only)
    
    subscriptions = query.offset(skip).limit(limit).all()
    
    result = []
    for user in subscriptions:
        result.append({
            "user_id": user.id,
            "user_name": user.name,
            "user_email": user.email,
            "plan": {
                "id": user.plan.id,
                "name": user.plan.name,
                "type": user.plan.type,
                "price": user.plan.price
            },
            "is_active": user.is_active,
            "credits": user.credits,
            "total_api_calls": user.total_api_calls,
            "created_at": user.created_at
        })
    
    return result

@router.post("/subscriptions/bulk-update")
async def bulk_update_subscriptions(
    user_ids: List[int],
    plan_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Atualizar múltiplas assinaturas em lote"""
    if not user_ids:
        raise HTTPException(status_code=400, detail="Lista de usuários não pode estar vazia")
    
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    if len(users) != len(user_ids):
        raise HTTPException(status_code=404, detail="Alguns usuários não foram encontrados")
    
    updated_count = 0
    for user in users:
        if plan_id is not None:
            # Verificar se o plano existe
            plan = db.query(Plan).filter(Plan.id == plan_id).first()
            if not plan:
                raise HTTPException(status_code=404, detail=f"Plano {plan_id} não encontrado")
            user.plan_id = plan_id
        
        if is_active is not None:
            user.is_active = is_active
        
        updated_count += 1
    
    db.commit()
    
    return {
        "message": f"{updated_count} assinaturas atualizadas com sucesso",
        "updated_users": updated_count
    }

# Estatísticas e relatórios
@router.get("/stats/overview")
async def get_admin_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obter visão geral das estatísticas do sistema"""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_credits_used = db.query(CreditTransaction).filter(
        CreditTransaction.type == "debit"
    ).count()
    
    # Usuários por role
    users_by_role = {}
    for role in UserRole:
        count = db.query(User).filter(User.role == role).count()
        users_by_role[role.value] = count
    
    # Usuários por plano
    users_by_plan = {}
    for plan_type in PlanType:
        count = db.query(User).join(Plan).filter(Plan.type == plan_type).count()
        users_by_plan[plan_type.value] = count
    
    # Receita total estimada
    total_revenue = db.query(User).join(Plan).filter(
        User.is_active == True
    ).with_entities(Plan.price).all()
    estimated_revenue = sum([price[0] for price in total_revenue if price[0]])
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": total_users - active_users,
        "total_credits_used": total_credits_used,
        "estimated_monthly_revenue": estimated_revenue,
        "users_by_role": users_by_role,
        "users_by_plan": users_by_plan
    }

# Rotas de controle de endpoints e funcionalidades
class SystemEndpoint(BaseModel):
    name: str
    path: str
    method: str
    description: Optional[str] = None
    is_active: bool = True
    requires_credits: bool = True
    credit_cost: int = 1
    allowed_roles: List[UserRole] = [UserRole.USER, UserRole.ADMIN, UserRole.SUPER_ADMIN]

class EndpointToggleRequest(BaseModel):
    endpoint_name: str
    is_active: bool

class SystemFeature(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True
    required_plan_types: List[PlanType] = []

# Simulação de configuração de endpoints (em produção seria em banco de dados)
SYSTEM_ENDPOINTS = {
    "company_enrichment": SystemEndpoint(
        name="company_enrichment",
        path="/api/v1/enrich/company",
        method="POST",
        description="Enriquecimento de dados de empresas",
        is_active=True,
        requires_credits=True,
        credit_cost=2
    ),
    "person_enrichment": SystemEndpoint(
        name="person_enrichment",
        path="/api/v1/enrich/person",
        method="POST",
        description="Enriquecimento de dados de pessoas",
        is_active=True,
        requires_credits=True,
        credit_cost=1
    ),
    "linkedin_scraping": SystemEndpoint(
        name="linkedin_scraping",
        path="/api/v1/scrape/linkedin",
        method="POST",
        description="Scraping de perfis LinkedIn",
        is_active=True,
        requires_credits=True,
        credit_cost=3
    ),
    "instagram_scraping": SystemEndpoint(
        name="instagram_scraping",
        path="/api/v1/scrape/instagram",
        method="POST",
        description="Scraping de perfis Instagram",
        is_active=True,
        requires_credits=True,
        credit_cost=2
    ),
    "api_key_management": SystemEndpoint(
        name="api_key_management",
        path="/api/v1/api-keys",
        method="GET",
        description="Gerenciamento de API Keys",
        is_active=True,
        requires_credits=False,
        credit_cost=0
    )
}

SYSTEM_FEATURES = {
    "bulk_processing": SystemFeature(
        name="bulk_processing",
        description="Processamento em lote de dados",
        is_active=True,
        required_plan_types=[PlanType.PROFESSIONAL, PlanType.ENTERPRISE]
    ),
    "advanced_analytics": SystemFeature(
        name="advanced_analytics",
        description="Analytics avançados e relatórios",
        is_active=True,
        required_plan_types=[PlanType.ENTERPRISE]
    ),
    "priority_support": SystemFeature(
        name="priority_support",
        description="Suporte prioritário",
        is_active=True,
        required_plan_types=[PlanType.PROFESSIONAL, PlanType.ENTERPRISE]
    ),
    "custom_integrations": SystemFeature(
        name="custom_integrations",
        description="Integrações customizadas",
        is_active=True,
        required_plan_types=[PlanType.ENTERPRISE]
    )
}

@router.get("/system/endpoints")
async def get_system_endpoints(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Listar todos os endpoints do sistema"""
    endpoints_list = []
    
    for endpoint_name, endpoint in SYSTEM_ENDPOINTS.items():
        # Contar uso nas últimas 24h (simulado)
        usage_count = db.query(CreditTransaction).filter(
            CreditTransaction.description.ilike(f"%{endpoint_name}%")
        ).count()
        
        endpoints_list.append({
            "name": endpoint.name,
            "path": endpoint.path,
            "method": endpoint.method,
            "description": endpoint.description,
            "is_active": endpoint.is_active,
            "requires_credits": endpoint.requires_credits,
            "credit_cost": endpoint.credit_cost,
            "allowed_roles": [role.value for role in endpoint.allowed_roles],
            "usage_count_24h": usage_count
        })
    
    return endpoints_list

@router.post("/system/endpoints/toggle")
async def toggle_endpoint(
    toggle_data: EndpointToggleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Ativar/desativar endpoint específico"""
    if toggle_data.endpoint_name not in SYSTEM_ENDPOINTS:
        raise HTTPException(status_code=404, detail="Endpoint não encontrado")
    
    SYSTEM_ENDPOINTS[toggle_data.endpoint_name].is_active = toggle_data.is_active
    
    status = "ativado" if toggle_data.is_active else "desativado"
    return {
        "message": f"Endpoint {toggle_data.endpoint_name} {status} com sucesso",
        "endpoint": toggle_data.endpoint_name,
        "is_active": toggle_data.is_active
    }

@router.put("/system/endpoints/{endpoint_name}/credit-cost")
async def update_endpoint_credit_cost(
    endpoint_name: str,
    credit_cost: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Atualizar custo em créditos de um endpoint"""
    if endpoint_name not in SYSTEM_ENDPOINTS:
        raise HTTPException(status_code=404, detail="Endpoint não encontrado")
    
    if credit_cost < 0:
        raise HTTPException(status_code=400, detail="Custo em créditos deve ser maior ou igual a 0")
    
    SYSTEM_ENDPOINTS[endpoint_name].credit_cost = credit_cost
    
    return {
        "message": f"Custo do endpoint {endpoint_name} atualizado para {credit_cost} créditos",
        "endpoint": endpoint_name,
        "new_credit_cost": credit_cost
    }

@router.get("/system/features")
async def get_system_features(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Listar todas as funcionalidades do sistema"""
    features_list = []
    
    for feature_name, feature in SYSTEM_FEATURES.items():
        features_list.append({
            "name": feature.name,
            "description": feature.description,
            "is_active": feature.is_active,
            "required_plan_types": [plan.value for plan in feature.required_plan_types]
        })
    
    return features_list

@router.post("/system/features/{feature_name}/toggle")
async def toggle_feature(
    feature_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Ativar/desativar funcionalidade específica"""
    if feature_name not in SYSTEM_FEATURES:
        raise HTTPException(status_code=404, detail="Funcionalidade não encontrada")
    
    SYSTEM_FEATURES[feature_name].is_active = not SYSTEM_FEATURES[feature_name].is_active
    
    status = "ativada" if SYSTEM_FEATURES[feature_name].is_active else "desativada"
    return {
        "message": f"Funcionalidade {feature_name} {status} com sucesso",
        "feature": feature_name,
        "is_active": SYSTEM_FEATURES[feature_name].is_active
    }

@router.get("/system/usage-stats")
async def get_system_usage_stats(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obter estatísticas de uso do sistema"""
    from datetime import datetime, timedelta
    
    start_date = datetime.now() - timedelta(days=days)
    
    # Estatísticas de uso de créditos por endpoint
    endpoint_usage = {}
    for endpoint_name in SYSTEM_ENDPOINTS.keys():
        usage = db.query(CreditTransaction).filter(
            CreditTransaction.description.ilike(f"%{endpoint_name}%"),
            CreditTransaction.created_at >= start_date
        ).count()
        endpoint_usage[endpoint_name] = usage
    
    # Top usuários por consumo
    top_users = db.query(
        User.id, User.name, User.email,
        db.func.count(CreditTransaction.id).label('transaction_count')
    ).join(CreditTransaction).filter(
        CreditTransaction.created_at >= start_date
    ).group_by(User.id, User.name, User.email).order_by(
        db.func.count(CreditTransaction.id).desc()
    ).limit(10).all()
    
    # Estatísticas gerais
    total_transactions = db.query(CreditTransaction).filter(
        CreditTransaction.created_at >= start_date
    ).count()
    
    total_credits_consumed = db.query(
        db.func.sum(CreditTransaction.amount)
    ).filter(
        CreditTransaction.type == "debit",
        CreditTransaction.created_at >= start_date
    ).scalar() or 0
    
    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "endpoint_usage": endpoint_usage,
        "top_users": [
            {
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "transaction_count": user.transaction_count
            } for user in top_users
        ],
        "total_transactions": total_transactions,
        "total_credits_consumed": abs(total_credits_consumed)
    }

@router.post("/system/maintenance-mode")
async def toggle_maintenance_mode(
    enabled: bool,
    message: Optional[str] = "Sistema em manutenção. Tente novamente em alguns minutos.",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Ativar/desativar modo de manutenção"""
    # Em produção, isso seria salvo em cache/banco de dados
    # Por agora, apenas retornamos a confirmação
    
    status = "ativado" if enabled else "desativado"
    return {
        "message": f"Modo de manutenção {status} com sucesso",
        "maintenance_enabled": enabled,
        "maintenance_message": message if enabled else None
    }

@router.get("/system/maintenance-mode")
async def get_maintenance_mode(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obter status do modo de manutenção"""
    # Em produção, isso seria lido do cache/banco de dados
    return {
        "enabled": False,
        "message": None
    }

@router.get("/system/health")
async def get_system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obter status de saúde do sistema"""
    import psutil
    import time
    
    try:
        # Testar conexão com banco de dados
        db_status = "healthy"
        try:
            db.execute("SELECT 1")
        except:
            db_status = "error"
        
        # Obter métricas do sistema
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Calcular uptime (simulado)
        uptime = time.time() - psutil.boot_time()
        
        return {
            "database_status": db_status,
            "api_status": "healthy",
            "cache_status": "healthy",
            "queue_status": "healthy",
            "uptime": int(uptime),
            "memory_usage": memory.percent,
            "cpu_usage": cpu_usage,
            "disk_usage": disk.percent
        }
    except Exception as e:
        return {
            "database_status": "error",
            "api_status": "error",
            "cache_status": "error",
            "queue_status": "error",
            "uptime": 0,
            "memory_usage": 0,
            "cpu_usage": 0,
            "disk_usage": 0,
            "error": str(e)
        }

@router.post("/system/cache/clear")
async def clear_system_cache(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Limpar cache do sistema"""
    # Em produção, isso limparia Redis ou outro cache
    return {
        "message": "Cache limpo com sucesso",
        "cleared_at": datetime.now().isoformat()
    }

# Rotas adicionais para gerenciamento completo
@router.get("/analytics/dashboard")
async def get_dashboard_analytics(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obter dados analíticos para o dashboard"""
    from datetime import datetime, timedelta
    
    start_date = datetime.now() - timedelta(days=days)
    
    # Métricas principais
    total_users = db.query(User).count()
    new_users = db.query(User).filter(User.created_at >= start_date).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    
    # Receita total
    total_revenue = db.query(User).join(Plan).filter(
        User.is_active == True
    ).with_entities(Plan.price).all()
    monthly_revenue = sum([price[0] for price in total_revenue if price[0]])
    
    # Transações de crédito
    credit_transactions = db.query(CreditTransaction).filter(
        CreditTransaction.created_at >= start_date
    ).count()
    
    # API calls por dia (últimos 7 dias)
    daily_stats = []
    for i in range(7):
        day = datetime.now() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        calls = db.query(CreditTransaction).filter(
            CreditTransaction.created_at >= day_start,
            CreditTransaction.created_at < day_end,
            CreditTransaction.type == "debit"
        ).count()
        
        daily_stats.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "api_calls": calls
        })
    
    return {
        "total_users": total_users,
        "new_users": new_users,
        "active_users": active_users,
        "monthly_revenue": monthly_revenue,
        "credit_transactions": credit_transactions,
        "daily_api_calls": daily_stats[::-1]  # Ordem cronológica
    }

@router.get("/logs/system")
async def get_system_logs(
    level: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Obter logs do sistema"""
    # Em produção, isso leria logs reais do sistema
    logs = [
        {
            "id": 1,
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "message": "Sistema iniciado com sucesso",
            "module": "main"
        },
        {
            "id": 2,
            "timestamp": datetime.now().isoformat(),
            "level": "WARNING",
            "message": "Alto uso de CPU detectado",
            "module": "monitoring"
        }
    ]
    
    if level:
        logs = [log for log in logs if log["level"] == level.upper()]
    
    return {"logs": logs[:limit]}

@router.post("/notifications/broadcast")
async def broadcast_notification(
    message: str,
    title: str,
    target_roles: Optional[List[UserRole]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Enviar notificação para usuários"""
    query = db.query(User).filter(User.is_active == True)
    
    if target_roles:
        query = query.filter(User.role.in_(target_roles))
    
    users = query.all()
    
    # Em produção, isso enviaria notificações reais
    notification_count = len(users)
    
    return {
        "message": "Notificação enviada com sucesso",
        "recipients": notification_count,
        "title": title,
        "content": message
    }

@router.get("/export/users")
async def export_users(
    format: str = Query("csv", regex="^(csv|json)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Exportar dados dos usuários"""
    users = db.query(User).all()
    
    if format == "csv":
        # Em produção, geraria CSV real
        return {
            "message": "Exportação CSV iniciada",
            "download_url": "/downloads/users.csv",
            "total_records": len(users)
        }
    else:
        user_data = []
        for user in users:
            user_data.append({
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role.value,
                "is_active": user.is_active,
                "credits": user.credits,
                "created_at": user.created_at.isoformat()
            })
        
        return {"users": user_data}

@router.post("/backup/create")
async def create_backup(
    include_users: bool = True,
    include_transactions: bool = True,
    include_plans: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Criar backup do sistema"""
    backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Em produção, isso criaria backup real
    return {
        "message": "Backup criado com sucesso",
        "backup_id": backup_id,
        "created_at": datetime.now().isoformat(),
        "includes": {
            "users": include_users,
            "transactions": include_transactions,
            "plans": include_plans
        }
    }

@router.get("/backup/list")
async def list_backups(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Listar backups disponíveis"""
    # Em produção, isso listaria backups reais
    backups = [
        {
            "id": "backup_20241201_120000",
            "created_at": "2024-12-01T12:00:00",
            "size": "15.2 MB",
            "status": "completed"
        },
        {
            "id": "backup_20241130_120000",
            "created_at": "2024-11-30T12:00:00",
            "size": "14.8 MB",
            "status": "completed"
        }
    ]
    
    return {"backups": backups}

@router.post("/settings/update")
async def update_system_settings(
    settings: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Atualizar configurações do sistema"""
    # Em produção, isso salvaria configurações reais
    return {
        "message": "Configurações atualizadas com sucesso",
        "updated_settings": settings,
        "updated_at": datetime.now().isoformat()
    }

@router.get("/settings")
async def get_system_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obter configurações do sistema"""
    # Em produção, isso leria configurações reais
    return {
        "maintenance_mode": False,
        "registration_enabled": True,
        "max_api_calls_per_minute": 100,
        "default_credits": 10,
        "email_notifications": True,
        "backup_frequency": "daily",
        "log_retention_days": 30
    }

# API Usage Tracking Routes
@router.get("/api-usage/stats", response_model=APIUsageResponse)
async def get_api_usage_stats(
    days: int = Query(7, ge=1, le=90),
    service_filter: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get API usage statistics for all external services"""
    try:
        logs_file = "api_requests.jsonl"
        if not os.path.exists(logs_file):
            return APIUsageResponse()
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        services_data = defaultdict(lambda: {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "response_times": [],
            "last_request_timestamp": None,
            "daily_requests": 0,
            "monthly_requests": 0
        })
        
        today = datetime.utcnow().date()
        month_start = today.replace(day=1)
        
        with open(logs_file, 'r') as f:
            for line in f:
                try:
                    log_entry = json.loads(line.strip())
                    log_time = datetime.fromisoformat(log_entry.get("timestamp", ""))
                    
                    if log_time < cutoff_date:
                        continue
                    
                    service_name = log_entry.get("service_name", "unknown")
                    
                    if service_filter and service_name != service_filter:
                        continue
                    
                    service_data = services_data[service_name]
                    service_data["total_requests"] += 1
                    
                    if log_entry.get("response_status", 500) < 400:
                        service_data["successful_requests"] += 1
                    else:
                        service_data["failed_requests"] += 1
                    
                    service_data["total_tokens"] += log_entry.get("tokens_used", 0) or 0
                    service_data["total_cost_usd"] += log_entry.get("cost_usd", 0) or 0
                    
                    if log_entry.get("response_time_ms"):
                        service_data["response_times"].append(log_entry["response_time_ms"])
                    
                    service_data["last_request_timestamp"] = log_entry.get("timestamp")
                    
                    # Daily and monthly counts
                    if log_time.date() == today:
                        service_data["daily_requests"] += 1
                    
                    if log_time.date() >= month_start:
                        service_data["monthly_requests"] += 1
                        
                except (json.JSONDecodeError, ValueError):
                    continue
        
        # Convert to response format
        services = []
        total_requests_today = 0
        total_cost_today = 0.0
        total_tokens_today = 0
        cost_breakdown = {}
        
        for service_name, data in services_data.items():
            avg_response_time = sum(data["response_times"]) / len(data["response_times"]) if data["response_times"] else 0
            
            service_stats = APIServiceStats(
                service_name=service_name,
                total_requests=data["total_requests"],
                successful_requests=data["successful_requests"],
                failed_requests=data["failed_requests"],
                total_tokens=data["total_tokens"],
                total_cost_usd=data["total_cost_usd"],
                avg_response_time_ms=avg_response_time,
                last_request_timestamp=data["last_request_timestamp"],
                daily_requests=data["daily_requests"],
                monthly_requests=data["monthly_requests"]
            )
            services.append(service_stats)
            
            total_requests_today += data["daily_requests"]
            total_cost_today += data["total_cost_usd"] if data["daily_requests"] > 0 else 0
            total_tokens_today += data["total_tokens"] if data["daily_requests"] > 0 else 0
            cost_breakdown[service_name] = data["total_cost_usd"]
        
        # Find most used service
        most_used_service = max(services, key=lambda x: x.total_requests).service_name if services else None
        
        return APIUsageResponse(
            services=services,
            total_requests_today=total_requests_today,
            total_cost_today=total_cost_today,
            total_tokens_today=total_tokens_today,
            most_used_service=most_used_service,
            cost_breakdown=cost_breakdown,
            request_trends={}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas de API: {str(e)}")

@router.get("/api-usage/services")
async def get_api_services(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get list of all tracked API services"""
    services = [
        {"name": "brave_browser", "display_name": "Brave Browser", "category": "Search"},
        {"name": "firecrawl", "display_name": "Firecrawl", "category": "Web Scraping"},
        {"name": "deepseek", "display_name": "DeepSeek", "category": "AI/LLM"},
        {"name": "chatgpt", "display_name": "ChatGPT", "category": "AI/LLM"},
        {"name": "claude", "display_name": "Claude", "category": "AI/LLM"},
        {"name": "openai", "display_name": "OpenAI", "category": "AI/LLM"},
        {"name": "anthropic", "display_name": "Anthropic", "category": "AI/LLM"},
        {"name": "google_ai", "display_name": "Google AI", "category": "AI/LLM"},
        {"name": "perplexity", "display_name": "Perplexity", "category": "AI/LLM"},
        {"name": "together_ai", "display_name": "Together AI", "category": "AI/LLM"}
    ]
    
    return {
        "success": True,
        "services": services
    }

@router.get("/api-usage/logs")
async def get_api_usage_logs(
    limit: int = Query(100, ge=1, le=1000),
    service_filter: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),  # success, error
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get recent API usage logs"""
@router.get("/api-alerts/summary")
async def get_api_alerts_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Obter resumo de alertas de API"""
    try:
        # Simular dados de alertas baseados nos logs de API
        logs_file = "api_requests.jsonl"
        if not os.path.exists(logs_file):
            return {
                "success": True,
                "active_alerts": 0,
                "services_monitored": 0,
                "alerts": []
            }
        
        services_usage = defaultdict(lambda: {"requests": 0, "errors": 0, "cost": 0.0})
        
        # Analisar últimas 24 horas
        cutoff_date = datetime.utcnow() - timedelta(hours=24)
        
        with open(logs_file, 'r') as f:
            for line in f:
                try:
                    log_entry = json.loads(line.strip())
                    log_time = datetime.fromisoformat(log_entry.get("timestamp", ""))
                    
                    if log_time < cutoff_date:
                        continue
                    
                    service_name = log_entry.get("service_name", "unknown")
                    services_usage[service_name]["requests"] += 1
                    services_usage[service_name]["cost"] += log_entry.get("cost_usd", 0) or 0
                    
                    if log_entry.get("response_status", 500) >= 400:
                        services_usage[service_name]["errors"] += 1
                        
                except (json.JSONDecodeError, ValueError):
                    continue
        
        # Gerar alertas baseados em limites
        alerts = []
        for service, usage in services_usage.items():
            # Alerta de alto custo (>$10/dia)
            if usage["cost"] > 10.0:
                alerts.append({
                    "id": f"cost_{service}",
                    "service": service,
                    "type": "high_cost",
                    "severity": "warning",
                    "message": f"Alto custo detectado para {service}: ${usage['cost']:.2f} nas últimas 24h",
                    "value": usage["cost"],
                    "threshold": 10.0,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Alerta de alta taxa de erro (>10%)
            error_rate = (usage["errors"] / usage["requests"]) * 100 if usage["requests"] > 0 else 0
            if error_rate > 10:
                alerts.append({
                    "id": f"error_{service}",
                    "service": service,
                    "type": "high_error_rate",
                    "severity": "error",
                    "message": f"Alta taxa de erro para {service}: {error_rate:.1f}%",
                    "value": error_rate,
                    "threshold": 10.0,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return {
            "success": True,
            "active_alerts": len(alerts),
            "services_monitored": len(services_usage),
            "alerts": alerts
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter resumo de alertas: {str(e)}")

@router.get("/api-alerts/check/{service}")
async def check_service_limits(
    service: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Verificar limites de uso para um serviço específico"""
    try:
        logs_file = "api_requests.jsonl"
        if not os.path.exists(logs_file):
            return {
                "success": True,
                "service": service,
                "status": "no_data",
                "usage": {}
            }
        
        # Analisar últimas 24 horas
        cutoff_date = datetime.utcnow() - timedelta(hours=24)
        usage = {"requests": 0, "errors": 0, "cost": 0.0, "tokens": 0}
        
        with open(logs_file, 'r') as f:
            for line in f:
                try:
                    log_entry = json.loads(line.strip())
                    
                    if log_entry.get("service_name") != service:
                        continue
                    
                    log_time = datetime.fromisoformat(log_entry.get("timestamp", ""))
                    if log_time < cutoff_date:
                        continue
                    
                    usage["requests"] += 1
                    usage["cost"] += log_entry.get("cost_usd", 0) or 0
                    usage["tokens"] += log_entry.get("tokens_used", 0) or 0
                    
                    if log_entry.get("response_status", 500) >= 400:
                        usage["errors"] += 1
                        
                except (json.JSONDecodeError, ValueError):
                    continue
        
        # Definir limites por serviço
        limits = {
            "requests_per_day": 1000,
            "cost_per_day": 50.0,
            "error_rate_threshold": 5.0
        }
        
        error_rate = (usage["errors"] / usage["requests"]) * 100 if usage["requests"] > 0 else 0
        
        status = "healthy"
        if usage["cost"] > limits["cost_per_day"] * 0.8:  # 80% do limite
            status = "warning"
        if usage["cost"] > limits["cost_per_day"]:
            status = "critical"
        if error_rate > limits["error_rate_threshold"]:
            status = "error"
        
        return {
            "success": True,
            "service": service,
            "status": status,
            "usage": usage,
            "limits": limits,
            "error_rate": error_rate,
            "utilization": {
                "requests": (usage["requests"] / limits["requests_per_day"]) * 100,
                "cost": (usage["cost"] / limits["cost_per_day"]) * 100
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao verificar limites do serviço: {str(e)}")

@router.post("/api-alerts/test")
async def test_alert_system(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Testar sistema de alertas"""
    try:
        # Obter lista de serviços únicos dos logs
        logs_file = "api_requests.jsonl"
        services = set()
        
        if os.path.exists(logs_file):
            with open(logs_file, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        service_name = log_entry.get("service_name")
                        if service_name:
                            services.add(service_name)
                    except (json.JSONDecodeError, ValueError):
                        continue
        
        # Verificar cada serviço
        results = []
        total_alerts = 0
        
        for service in services:
            service_check = await check_service_limits(service, db, current_user)
            alerts_count = 0
            
            if service_check["status"] in ["warning", "critical", "error"]:
                alerts_count = 1
                total_alerts += 1
            
            results.append({
                "service": service,
                "status": service_check["status"],
                "alerts": alerts_count,
                "usage": service_check["usage"]
            })
        
        return {
            "success": True,
            "message": "Sistema de alertas testado com sucesso",
            "services_checked": len(services),
            "alerts_found": total_alerts,
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao testar sistema de alertas: {str(e)}")
            
        # Process logs in reverse order (newest first)
        for line in reversed(lines[-limit*2:]):  # Get more than needed for filtering
            try:
                log_entry = json.loads(line.strip())
                
                # Apply filters
                if service_filter and log_entry.get("service_name") != service_filter:
                    continue
                
                if status_filter:
                    status = log_entry.get("response_status", 500)
                    if status_filter == "success" and status >= 400:
                        continue
                    if status_filter == "error" and status < 400:
                        continue
                
                logs.append(log_entry)
                
                if len(logs) >= limit:
                    break
                    
            except (json.JSONDecodeError, ValueError):
                continue
        
        return {
            "success": True,
            "logs": logs,
            "total": len(logs)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter logs de API: {str(e)}")

@router.delete("/api-usage/logs/clear")
async def clear_api_logs(
    older_than_days: int = Query(30, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Clear old API logs"""
    try:
        logs_file = "api_requests.jsonl"
        if not os.path.exists(logs_file):
            return {"success": True, "message": "Nenhum log encontrado"}
        
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        kept_logs = []
        removed_count = 0
        
        with open(logs_file, 'r') as f:
            for line in f:
                try:
                    log_entry = json.loads(line.strip())
                    log_time = datetime.fromisoformat(log_entry.get("timestamp", ""))
                    
                    if log_time >= cutoff_date:
                        kept_logs.append(line)
                    else:
                        removed_count += 1
                        
                except (json.JSONDecodeError, ValueError):
                    kept_logs.append(line)  # Keep malformed entries
        
        # Write back the kept logs
        with open(logs_file, 'w') as f:
            f.writelines(kept_logs)
        
        return {
            "success": True,
            "message": f"Removidos {removed_count} logs antigos",
            "removed_count": removed_count,
            "kept_count": len(kept_logs)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao limpar logs: {str(e)}")