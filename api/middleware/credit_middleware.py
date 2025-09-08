from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Callable, Any
from ..services.credit_service import CreditService
from ..auth.jwt_service import JWTService
from ..database import get_db
from prisma import Prisma
import json
import logging

logger = logging.getLogger(__name__)
security = HTTPBearer()
jwt_service = JWTService()

class CreditMiddleware:
    def __init__(self):
        self.endpoint_mapping = {
            "/api/v1/enrich/company": "/enrich/company",
            "/api/v1/enrich/person": "/enrich/person",
            "/api/v1/enrich/companies": "/enrich/companies",
            "/api/v1/enrich/people": "/enrich/people"
        }
    
    async def verify_credits_and_consume(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Prisma = Depends(get_db)
    ):
        """Middleware para verificar autenticação e consumir créditos"""
        try:
            # Verificar token JWT
            token_data = jwt_service.verify_token(credentials.credentials)
            user_id = token_data.get("sub")
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
            
            # Obter endpoint normalizado
            endpoint_path = str(request.url.path)
            normalized_endpoint = self.endpoint_mapping.get(endpoint_path)
            
            if not normalized_endpoint:
                # Se não é um endpoint que consome créditos, apenas retorna o user_id
                return {"user_id": user_id, "skip_credits": True}
            
            # Inicializar serviço de créditos
            credit_service = CreditService(db)
            
            # Verificar se tem créditos suficientes
            has_credits = await credit_service.check_credits(user_id, normalized_endpoint)
            
            if not has_credits:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Insufficient credits"
                )
            
            # Retornar dados para consumo posterior
            return {
                "user_id": user_id,
                "endpoint": normalized_endpoint,
                "credit_service": credit_service,
                "skip_credits": False
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in credit middleware: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication error"
            )
    
    async def consume_credits_after_request(
        self,
        auth_data: dict,
        request: Request,
        response_status: str = "success",
        quantity: int = 1
    ):
        """Consome créditos após a execução da requisição"""
        if auth_data.get("skip_credits"):
            return
        
        try:
            # Obter dados da requisição
            request_body = {}
            if hasattr(request, '_body'):
                try:
                    request_body = json.loads(request._body.decode())
                except:
                    request_body = {"raw_body": str(request._body)}
            
            # Obter informações do cliente
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            
            # Consumir créditos
            await auth_data["credit_service"].consume_credits(
                user_id=auth_data["user_id"],
                endpoint=auth_data["endpoint"],
                request_data=json.dumps(request_body) if request_body else "{}",
                response_status=response_status,
                quantity=quantity,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(f"Credits consumed for user {auth_data['user_id']} on {auth_data['endpoint']}")
            
        except Exception as e:
            logger.error(f"Error consuming credits: {e}")
            # Não falha a requisição se houver erro no consumo de créditos

# Instância global do middleware
credit_middleware = CreditMiddleware()

# Função de dependência para usar nos endpoints
async def require_credits(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Prisma = Depends(get_db)
):
    """Dependência para endpoints que requerem créditos"""
    return await credit_middleware.verify_credits_and_consume(request, credentials, db)