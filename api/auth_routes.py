from fastapi import APIRouter, HTTPException, status, Depends
from .auth_models import UserLogin, TokenResponse, User, UserRole, PlanType
from .auth.jwt_service import JWTService
from .database import get_db
from prisma import Prisma
import bcrypt
from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["auth"])
jwt_service = JWTService()

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    fullName: str
    companyName: Optional[str] = None
    planId: Optional[str] = None

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Prisma = Depends(get_db)):
    try:
        print(f"Login attempt for: {credentials.emailOrUsername}")
        print(f"Database instance: {db}")
        print(f"Database instance type: {type(db)}")
        print(f"Database connected: {db.is_connected() if db else 'db is None'}")
        
        # Test if we can access the user table
        try:
            print("Testing database access...")
            user_count = await db.user.count()
            print(f"Total users in database: {user_count}")
        except Exception as count_error:
            print(f"Error counting users: {count_error}")
        
        # Buscar usuário no banco de dados por email
        print(f"Executing query: db.user.find_unique(where={{'email': '{credentials.emailOrUsername}'}})")
        user = await db.user.find_unique(
            where={"email": credentials.emailOrUsername}
        )
        print(f"User query result: {user}")
        
        # Se não encontrou por email, buscar por username
        if not user:
            user = await db.user.find_unique(
                where={"username": credentials.emailOrUsername}
            )
            print(f"User query by username result: {user}")
        
        # Se ainda não encontrou, buscar por fullName (fallback)
        if not user:
            user = await db.user.find_first(
                where={"fullName": credentials.emailOrUsername}
            )
            print(f"User query by fullName result: {user}")
        
        if not user:
            print("User not found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas"
            )
        
        print(f"User found: {user.email}, active: {user.isActive}")
        
        # Verificar senha
        password_hash = user.passwordHash.encode('utf-8') if isinstance(user.passwordHash, str) else user.passwordHash
        password_valid = bcrypt.checkpw(credentials.password.encode('utf-8'), password_hash)
        print(f"Password valid: {password_valid}")
        
        if not password_valid:
            print("Password verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas"
            )
        
        # Verificar se usuário está ativo
        if not user.isActive:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário inativo"
            )
        
        # Atualizar último login
        from datetime import datetime
        await db.user.update(
            where={"id": user.id},
            data={"lastLogin": datetime.now()}
        )
        
        # Criar token JWT
        token = jwt_service.create_access_token({"sub": user.id})
        
        # Converter para modelo de resposta
        user_response = User(
            id=user.id,
            email=user.email,
            password_hash=user.passwordHash,
            full_name=user.fullName,
            company_name=user.companyName,
            role=UserRole(user.role.lower()),
            plan=user.plan.lower(),
            credits_remaining=user.creditsRemaining,
            credits_total=user.creditsTotal,
            is_active=user.isActive,
            created_at=user.createdAt,
            updated_at=user.updatedAt,
            last_login=user.lastLogin
        )
        
        return TokenResponse(
            access_token=token,
            expires_in=3600,  # 1 hour
            user=user_response
        )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister, db: Prisma = Depends(get_db)):
    try:
        # Verificar se o usuário já existe
        existing_user = await db.user.find_unique(
            where={"email": user_data.email}
        )
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já está em uso"
            )
        
        # Hash da senha
        password_hash = bcrypt.hashpw(
            user_data.password.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
        
        # Criar usuário no banco
        new_user = await db.user.create(
            data={
                "id": str(uuid.uuid4()),
                "email": user_data.email,
                "passwordHash": password_hash,
                "fullName": user_data.fullName,
                "companyName": user_data.companyName,
                "role": "user",
                "plan": "free",
                "creditsRemaining": 500,  # 500 créditos iniciais
                "creditsTotal": 500,
                "isActive": True,
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow()
            }
        )
        
        # Gerar token JWT
        token = jwt_service.create_access_token(
            data={"sub": new_user.email, "user_id": new_user.id}
        )
        
        # Preparar dados do usuário para resposta
        user_response = User(
            id=new_user.id,
            email=new_user.email,
            password_hash=new_user.passwordHash,
            full_name=new_user.fullName,
            company_name=new_user.companyName,
            role=UserRole(new_user.role.lower()),
            plan=PlanType(new_user.plan.lower()),
            credits_remaining=new_user.creditsRemaining,
            credits_total=new_user.creditsTotal,
            is_active=new_user.isActive,
            created_at=new_user.createdAt,
            updated_at=new_user.updatedAt,
            last_login=new_user.lastLogin
        )
        
        return TokenResponse(
            access_token=token,
            expires_in=3600,  # 1 hour
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao criar usuário"
        )