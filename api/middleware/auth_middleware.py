from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from prisma import Prisma
from api.auth.jwt_service import JWTService
from api.services.credit_service import CreditService

security = HTTPBearer()
jwt_service = JWTService()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), 
                          db: Prisma = Depends()):
    """Middleware para autenticação JWT"""
    token = credentials.credentials
    payload = jwt_service.verify_token(token)
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user = await db.user.find_unique(where={"id": user_id})
    if not user or not user.isActive:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user

async def get_current_active_user(current_user = Depends(get_current_user)):
    """Verifica se o usuário está ativo"""
    if not current_user.isActive:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

async def check_api_key(request: Request, db: Prisma = Depends()):
    """Middleware para autenticação via API Key"""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key required"
        )
    
    key_record = await db.apikey.find_unique(
        where={"key": api_key},
        include={"user": True}
    )
    
    if not key_record or not key_record.isActive or not key_record.user.isActive:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API Key"
        )
    
    # Atualiza último uso
    await db.apikey.update(
        where={"id": key_record.id},
        data={"lastUsed": datetime.utcnow()}
    )
    
    return key_record.user

async def require_credits(endpoint: str, quantity: int = 1):
    """Decorator para verificar créditos antes da execução"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extrair usuário do contexto
            user = kwargs.get('current_user') or kwargs.get('user')
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Verificar créditos
            credit_service = CreditService(kwargs.get('db'))
            has_credits = await credit_service.check_credits(user.id, endpoint, quantity)
            
            if not has_credits:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Insufficient credits"
                )
            
            # Executar função
            result = await func(*args, **kwargs)
            
            # Consumir créditos após sucesso
            await credit_service.consume_credits(
                user.id, endpoint, 
                kwargs.get('request_data', {}),
                "success", quantity
            )
            
            return result
        return wrapper
    return decorator