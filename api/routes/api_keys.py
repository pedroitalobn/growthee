from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from prisma import Prisma
from ..database import get_db
from ..auth_models import APIKeyResponse, CreateAPIKeyRequest
from ..middleware.auth_middleware import get_current_user
from ..database import get_db
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import secrets
import string
from datetime import datetime

security = HTTPBearer()

# Função auxiliar para dependência de usuário
async def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Prisma = Depends(get_db)
):
    return await get_current_user(credentials, db)

router = APIRouter(prefix="/api/v1/auth", tags=["api-keys"])

def generate_api_key() -> str:
    """Gera uma chave de API segura"""
    # Prefixo para identificar as chaves
    prefix = "es_"
    # Gera 32 caracteres aleatórios
    key_part = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    return f"{prefix}{key_part}"

@router.get("/api-keys", response_model=List[APIKeyResponse])
async def get_api_keys(
    db: Prisma = Depends(get_db),
    current_user = Depends(get_authenticated_user)
):
    """Lista todas as API Keys do usuário"""
    try:
        api_keys = await db.apikey.find_many(
            where={"userId": current_user.id},
            order={"createdAt": "desc"}
        )
        
        # Contar usos de cada chave (simulado por enquanto)
        result = []
        for key in api_keys:
            result.append({
                "id": key.id,
                "name": key.name,
                "key": key.key,
                "isActive": key.isActive,
                "createdAt": key.createdAt,
                "lastUsed": key.lastUsed,
                "usageCount": 0  # TODO: implementar contagem real
            })
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar API Keys: {str(e)}"
        )

@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    request: CreateAPIKeyRequest,
    db: Prisma = Depends(get_db),
    current_user = Depends(get_authenticated_user)
):
    """Cria uma nova API Key"""
    try:
        # Verificar se já existe uma chave com o mesmo nome
        existing_key = await db.apikey.find_first(
            where={
                "userId": current_user.id,
                "name": request.name
            }
        )
        
        if existing_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma API Key com este nome"
            )
        
        # Gerar nova chave
        api_key = generate_api_key()
        
        # Criar no banco
        new_key = await db.apikey.create(
            data={
                "userId": current_user.id,
                "name": request.name,
                "key": api_key,
                "isActive": True
            }
        )
        
        return {
            "id": new_key.id,
            "name": new_key.name,
            "key": new_key.key,
            "isActive": new_key.isActive,
            "createdAt": new_key.createdAt,
            "lastUsed": new_key.lastUsed,
            "usageCount": 0
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar API Key: {str(e)}"
        )

@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    db: Prisma = Depends(get_db),
    current_user = Depends(get_authenticated_user)
):
    """Deleta uma API Key"""
    try:
        # Verificar se a chave existe e pertence ao usuário
        api_key = await db.apikey.find_first(
            where={
                "id": key_id,
                "userId": current_user.id
            }
        )
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API Key não encontrada"
            )
        
        # Deletar a chave
        await db.apikey.delete(
            where={"id": key_id}
        )
        
        return {"message": "API Key deletada com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar API Key: {str(e)}"
        )

@router.patch("/api-keys/{key_id}/toggle")
async def toggle_api_key(
    key_id: str,
    db: Prisma = Depends(get_db),
    current_user = Depends(get_authenticated_user)
):
    """Ativa/desativa uma API Key"""
    try:
        # Verificar se a chave existe e pertence ao usuário
        api_key = await db.apikey.find_first(
            where={
                "id": key_id,
                "userId": current_user.id
            }
        )
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API Key não encontrada"
            )
        
        # Alternar status
        updated_key = await db.apikey.update(
            where={"id": key_id},
            data={"isActive": not api_key.isActive}
        )
        
        return {
            "message": f"API Key {'ativada' if updated_key.isActive else 'desativada'} com sucesso",
            "isActive": updated_key.isActive
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao alterar status da API Key: {str(e)}"
        )