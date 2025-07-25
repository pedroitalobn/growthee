from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime
import logging

# Importações condicionais
try:
    from prisma import Prisma
    from api.auth.jwt_service import JWTService
except ImportError as e:
    logging.warning(f"Import warning in auth_middleware: {e}")
    Prisma = None
    JWTService = None

security = HTTPBearer()

def get_jwt_service():
    if JWTService is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT service not available"
        )
    return JWTService()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), 
    db: Optional[Prisma] = None
):
    """Middleware para autenticação JWT"""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not available"
        )
    
    jwt_service = get_jwt_service()
    token = credentials.credentials
    payload = jwt_service.verify_token(token)
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    try:
        user = await db.user.find_unique(where={"id": user_id})
        if not user or not user.isActive:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        return user
    except Exception as e:
        logging.error(f"Database error in auth: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )

async def check_api_key(request: Request, db: Optional[Prisma] = None):
    """Middleware para autenticação via API Key"""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not available"
        )
    
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key required"
        )
    
    try:
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
    except Exception as e:
        logging.error(f"Database error in API key auth: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )