from typing import Dict, Any, Optional
from prisma import Prisma
from fastapi import HTTPException, status
import importlib
import inspect
from datetime import datetime

class CustomEndpointService:
    def __init__(self, db: Prisma):
        self.db = db
        self.registered_endpoints = {}
    
    async def create_custom_endpoint(self, 
                                   name: str, 
                                   path: str, 
                                   method: str,
                                   handler_code: str,
                                   credit_cost: int,
                                   allowed_users: list = None,
                                   description: str = None) -> dict:
        """Cria um endpoint customizado dinamicamente"""
        
        # Validar código do handler
        try:
            compiled_code = compile(handler_code, f"<endpoint_{name}>", "exec")
        except SyntaxError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Syntax error in handler code: {str(e)}"
            )
        
        # Salvar no banco
        endpoint = await self.db.customendpoint.create(
            data={
                "name": name,
                "path": path,
                "method": method.upper(),
                "handlerCode": handler_code,
                "creditCost": credit_cost,
                "allowedUsers": allowed_users or [],
                "description": description,
                "isActive": True
            }
        )
        
        # Registrar endpoint dinamicamente
        await self._register_endpoint(endpoint)
        
        return endpoint
    
    async def _register_endpoint(self, endpoint_config: dict):
        """Registra endpoint dinamicamente no FastAPI"""
        from api.main import app
        from api.middleware.auth_middleware import check_api_key, require_credits
        
        # Criar namespace para execução do código
        namespace = {
            'HTTPException': HTTPException,
            'status': status,
            'datetime': datetime,
            # Adicionar outras dependências necessárias
        }
        
        # Executar código do handler
        exec(endpoint_config['handlerCode'], namespace)
        
        # Extrair função handler
        handler_func = None
        for name, obj in namespace.items():
            if inspect.isfunction(obj) and name.startswith('handle_'):
                handler_func = obj
                break
        
        if not handler_func:
            raise ValueError("Handler function not found. Must start with 'handle_'")
        
        # Wrapper com autenticação e créditos
        async def endpoint_wrapper(request_data: dict, current_user = Depends(check_api_key)):
            # Verificar se usuário tem acesso
            if endpoint_config['allowedUsers'] and current_user.id not in endpoint_config['allowedUsers']:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this endpoint"
                )
            
            # Verificar créditos
            credit_service = CreditService(self.db)
            has_credits = await credit_service.check_credits(
                current_user.id, 
                endpoint_config['path'], 
                1
            )
            
            if not has_credits:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Insufficient credits"
                )
            
            # Executar handler
            try:
                result = await handler_func(request_data, current_user, self.db)
                
                # Consumir créditos após sucesso
                await credit_service.consume_credits(
                    current_user.id,
                    endpoint_config['path'],
                    request_data,
                    "success",
                    1
                )
                
                return result
            except Exception as e:
                # Log do erro
                await credit_service.consume_credits(
                    current_user.id,
                    endpoint_config['path'],
                    request_data,
                    "error",
                    0  # Não cobrar créditos em caso de erro
                )
                raise
        
        # Registrar no FastAPI
        if endpoint_config['method'] == 'POST':
            app.post(endpoint_config['path'])(endpoint_wrapper)
        elif endpoint_config['method'] == 'GET':
            app.get(endpoint_config['path'])(endpoint_wrapper)
        elif endpoint_config['method'] == 'PUT':
            app.put(endpoint_config['path'])(endpoint_wrapper)
        elif endpoint_config['method'] == 'DELETE':
            app.delete(endpoint_config['path'])(endpoint_wrapper)
        
        self.registered_endpoints[endpoint_config['id']] = endpoint_wrapper
    
    async def load_existing_endpoints(self):
        """Carrega endpoints existentes na inicialização"""
        endpoints = await self.db.customendpoint.find_many(
            where={"isActive": True}
        )
        
        for endpoint in endpoints:
            try:
                await self._register_endpoint(endpoint)
            except Exception as e:
                print(f"Error loading endpoint {endpoint.name}: {str(e)}")