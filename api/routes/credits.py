from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from api.middleware.auth_middleware import get_current_user
from api.services.credit_service import CreditService
from prisma import Prisma
from api.database import get_db
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

# Função auxiliar para dependência de usuário
async def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Prisma = Depends(get_db)
):
    return await get_current_user(credentials, db)

router = APIRouter(prefix="/api/v1/credits", tags=["credits"])

class AddCreditsRequest(BaseModel):
    credits: int
    reason: str = "Manual addition"

class AdminAddCreditsRequest(BaseModel):
    email: Optional[str] = None
    user_id: Optional[str] = None
    credits: int
    description: str = "Admin addition"

@router.post("/add")
async def add_credits(
    request: AddCreditsRequest,
    current_user = Depends(get_authenticated_user),
    db: Prisma = Depends(get_db)
):
    """Adiciona créditos ao usuário atual"""
    try:
        credit_service = CreditService(db)
        
        await credit_service.add_credits(
            user_id=current_user.id,
            credits=request.credits,
            reason=request.reason
        )
        
        # Buscar usuário atualizado
        updated_user = await db.user.find_unique(
            where={"id": current_user.id}
        )
        
        return {
            "message": f"{request.credits} créditos adicionados com sucesso",
            "credits_remaining": updated_user.creditsRemaining,
            "credits_total": updated_user.creditsTotal
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao adicionar créditos: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao adicionar créditos: {str(e)}"
        )

@router.post("/admin/add")
async def admin_add_credits(
    request: AdminAddCreditsRequest,
    current_user = Depends(get_authenticated_user),
    db: Prisma = Depends(get_db)
):
    """Endpoint administrativo para adicionar créditos a qualquer usuário (por email ou ID)"""
    try:
        
        # Verificar se o usuário atual é admin (opcional - você pode implementar verificação de role)
        # Por enquanto, qualquer usuário autenticado pode usar este endpoint
        
        if not request.email and not request.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="É necessário fornecer email ou user_id"
            )
        
        # Buscar usuário por email ou ID
        target_user = None
        if request.email:
            target_user = await db.user.find_unique(
                where={"email": request.email}
            )
        elif request.user_id:
            target_user = await db.user.find_unique(
                where={"id": request.user_id}
            )
        
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        credit_service = CreditService(db)
        
        await credit_service.add_credits(
            user_id=target_user.id,
            credits=request.credits,
            reason=request.description
        )
        
        # Buscar usuário atualizado
        updated_user = await db.user.find_unique(
            where={"id": target_user.id}
        )
        
        return {
            "message": f"{request.credits} créditos adicionados com sucesso ao usuário {updated_user.email}",
            "user_email": updated_user.email,
            "credits_remaining": updated_user.creditsRemaining,
            "credits_total": updated_user.creditsTotal
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao adicionar créditos: {str(e)}"
        )

@router.get("/balance")
async def get_credit_balance(
    current_user = Depends(get_authenticated_user),
    db: Prisma = Depends(get_db)
):
    """Retorna o saldo atual de créditos do usuário"""
    try:
        
        user = await db.user.find_unique(
            where={"id": current_user.id}
        )
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        return {
            "credits_remaining": user.creditsRemaining,
            "credits_total": user.creditsTotal
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar saldo: {str(e)}"
        )