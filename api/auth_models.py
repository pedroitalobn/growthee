from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class PlanType(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class User(BaseModel):
    id: Optional[str] = None
    email: EmailStr
    password_hash: str
    full_name: str
    company_name: Optional[str] = None
    role: UserRole = UserRole.USER
    plan: PlanType = PlanType.FREE
    credits_remaining: int = 0
    credits_total: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

class Plan(BaseModel):
    id: Optional[str] = None
    name: str
    type: PlanType
    credits_included: int
    price_monthly: float
    price_yearly: float
    features: List[str]
    is_active: bool = True

class CreditTransaction(BaseModel):
    id: Optional[str] = None
    user_id: str
    endpoint: str
    credits_used: int
    request_data: dict
    response_status: str
    created_at: Optional[datetime] = None

class APIKey(BaseModel):
    id: Optional[str] = None
    user_id: str
    key: str
    name: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_used: Optional[datetime] = None

# Auth Requests/Responses
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: Optional[str] = None

class UserLogin(BaseModel):
    emailOrUsername: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User

class CreateAPIKeyRequest(BaseModel):
    name: str

class APIKeyResponse(BaseModel):
    id: str
    name: str
    key: str
    created_at: datetime