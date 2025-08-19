from fastapi import APIRouter, HTTPException, status
from .auth_models import UserLogin, TokenResponse, User, UserRole
from .auth.jwt_service import JWTService

router = APIRouter(prefix="/auth", tags=["auth"])
jwt_service = JWTService()

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    try:
        # Para o bypass do admin
        if credentials.emailOrUsername == "admin" and credentials.password == "admin":
            user = User(
                id="admin-id",
                email="admin@admin.com",
                password_hash="",  # Não é necessário para o bypass
                full_name="Admin Test",
                role=UserRole.ADMIN,
                credits_remaining=9999,
                credits_total=9999
            )
            token = jwt_service.create_access_token({"sub": user.id})
            return TokenResponse(
                access_token=token,
                expires_in=30 * 60,  # 30 minutos
                user=user
            )
            
        # Aqui você implementaria a lógica real de autenticação
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas"
        )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )