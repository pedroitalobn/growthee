from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional
from pydantic import BaseModel
from prisma import Prisma
from ..database import get_db
from ..middleware.auth_middleware import get_current_user
from datetime import datetime

router = APIRouter(prefix="/api/v1/auth", tags=["profile"])

class UpdateProfileRequest(BaseModel):
    fullName: str
    companyName: Optional[str] = None
    preferences: Optional[dict] = None

class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str

@router.put("/profile")
async def update_profile(
    request: UpdateProfileRequest,
    current_user = Depends(get_current_user),
    db: Prisma = Depends(get_db)
):
    """Atualiza o perfil do usuário"""
    try:
        # Verificar se o usuário existe
        user = await db.user.find_unique(where={"id": current_user.id})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        # Atualizar dados do usuário
        updated_user = await db.user.update(
            where={"id": current_user.id},
            data={
                "fullName": request.fullName,
                "companyName": request.companyName,
                "updatedAt": datetime.utcnow()
            }
        )
        
        return {
            "id": updated_user.id,
            "email": updated_user.email,
            "fullName": updated_user.fullName,
            "companyName": updated_user.companyName,
            "role": updated_user.role,
            "plan": updated_user.plan,
            "creditsRemaining": updated_user.creditsRemaining,
            "creditsTotal": updated_user.creditsTotal,
            "status": "ACTIVE" if updated_user.isActive else "INACTIVE",
            "createdAt": updated_user.createdAt.isoformat(),
            "updatedAt": updated_user.updatedAt.isoformat() if updated_user.updatedAt else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar perfil: {str(e)}"
        )

@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user = Depends(get_current_user),
    db: Prisma = Depends(get_db)
):
    """Altera a senha do usuário"""
    try:
        import bcrypt
        
        # Verificar senha atual
        user = await db.user.find_unique(where={"id": current_user.id})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        # Verificar senha atual
        password_hash = user.passwordHash.encode('utf-8') if isinstance(user.passwordHash, str) else user.passwordHash
        password_valid = bcrypt.checkpw(request.currentPassword.encode('utf-8'), password_hash)
        
        if not password_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Senha atual incorreta"
            )
        
        # Gerar hash da nova senha
        new_password_hash = bcrypt.hashpw(request.newPassword.encode('utf-8'), bcrypt.gensalt())
        
        # Atualizar senha no banco
        await db.user.update(
            where={"id": current_user.id},
            data={
                "passwordHash": new_password_hash.decode('utf-8'),
                "updatedAt": datetime.utcnow()
            }
        )
        
        return {"message": "Senha alterada com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao alterar senha: {str(e)}"
        )

@router.delete("/account")
async def delete_account(
    current_user = Depends(get_current_user),
    db: Prisma = Depends(get_db)
):
    """Exclui a conta do usuário"""
    try:
        # Verificar se o usuário existe
        user = await db.user.find_unique(where={"id": current_user.id})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        # Deletar API Keys do usuário
        await db.apikey.delete_many(where={"userId": current_user.id})
        
        # Deletar transações de crédito
        await db.credittransaction.delete_many(where={"userId": current_user.id})
        
        # Deletar usuário
        await db.user.delete(where={"id": current_user.id})
        
        return {"message": "Conta excluída com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao excluir conta: {str(e)}"
        )