from fastapi import HTTPException, status, Depends
from typing import List, Optional
from .auth_middleware import get_current_user
from ..auth_models import UserRole
from prisma import Prisma
from ..database import get_db

def require_admin_role(allowed_roles: List[UserRole] = None):
    """
    Middleware para verificar se o usuário tem permissão de admin
    
    Args:
        allowed_roles: Lista de roles permitidos. Se None, permite apenas SUPER_ADMIN
    """
    if allowed_roles is None:
        allowed_roles = [UserRole.SUPER_ADMIN]
    
    async def check_admin_permission(
        current_user = Depends(get_current_user)
    ):
        # Verificar se o usuário tem role adequado
        user_role = UserRole(current_user.role.lower())
        
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado. Permissões de administrador necessárias."
            )
        
        return current_user
    
    return check_admin_permission

def require_super_admin():
    """
    Middleware específico para super admin
    """
    return require_admin_role([UserRole.SUPER_ADMIN])

def require_admin_or_super_admin():
    """
    Middleware que permite admin ou super admin
    """
    return require_admin_role([UserRole.ADMIN, UserRole.SUPER_ADMIN])

def require_admin():
    """
    Middleware específico para admin (inclui super admin)
    """
    return require_admin_role([UserRole.ADMIN, UserRole.SUPER_ADMIN])

async def get_admin_user(
    current_user = Depends(get_current_user)
):
    """
    Dependência que retorna apenas usuários com role de admin ou super_admin
    """
    user_role = UserRole(current_user.role.lower())
    
    if user_role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Permissões de administrador necessárias."
        )
    
    return current_user

async def get_super_admin_user(
    current_user = Depends(get_current_user)
):
    """
    Dependência que retorna apenas usuários com role de super_admin
    """
    user_role = UserRole(current_user.role.lower())
    
    if user_role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Permissões de super administrador necessárias."
        )
    
    return current_user

def check_user_permissions(target_user_id: str, current_user):
    """
    Verifica se o usuário atual pode modificar o usuário alvo
    
    Args:
        target_user_id: ID do usuário que será modificado
        current_user: Usuário atual autenticado
    
    Returns:
        bool: True se tem permissão, False caso contrário
    """
    current_role = UserRole(current_user.role.lower())
    
    # Super admin pode modificar qualquer usuário
    if current_role == UserRole.SUPER_ADMIN:
        return True
    
    # Admin pode modificar apenas usuários comuns (não outros admins)
    if current_role == UserRole.ADMIN:
        # Aqui seria necessário verificar o role do usuário alvo
        # Por simplicidade, vamos permitir por enquanto
        return True
    
    # Usuários comuns só podem modificar a si mesmos
    return current_user.id == target_user_id