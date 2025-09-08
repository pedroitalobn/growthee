from fastapi import APIRouter, HTTPException, status, Depends, Request, Response
from typing import List, Dict, Any
from ..middleware import require_credits

router = APIRouter(prefix="/api/v1/docs", tags=["documentation"])

# Definição dos endpoints disponíveis na API
API_ENDPOINTS = [
    {
        "id": "enrich-company",
        "method": "POST",
        "path": "/api/v1/enrich/company",
        "name": "Enriquecer Empresa",
        "description": "Enriquece dados de uma empresa com informações detalhadas incluindo funcionários, tecnologias, redes sociais e dados financeiros.",
        "category": "Enrichment",
        "parameters": [
            {
                "name": "domain",
                "type": "string",
                "required": True,
                "description": "Domínio da empresa (ex: example.com)",
                "example": "example.com"
            },
            {
                "name": "include_contacts",
                "type": "boolean",
                "required": False,
                "description": "Incluir lista de contatos/funcionários da empresa",
                "example": True
            },
            {
                "name": "include_technologies",
                "type": "boolean",
                "required": False,
                "description": "Incluir tecnologias utilizadas pela empresa",
                "example": True
            }
        ],
        "requestBody": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Domínio da empresa"},
                "include_contacts": {"type": "boolean", "description": "Incluir contatos"},
                "include_technologies": {"type": "boolean", "description": "Incluir tecnologias"}
            },
            "example": {
                "domain": "example.com",
                "include_contacts": True,
                "include_technologies": True
            }
        },
        "responses": [
            {
                "status": 200,
                "description": "Dados da empresa enriquecidos com sucesso",
                "example": {
                    "company": {
                        "name": "Example Corp",
                        "domain": "example.com",
                        "industry": "Technology",
                        "size": "51-200 employees",
                        "location": "San Francisco, CA",
                        "description": "Leading technology company...",
                        "founded": "2010",
                        "website": "https://example.com",
                        "linkedin": "https://linkedin.com/company/example",
                        "twitter": "@example",
                        "technologies": ["React", "Node.js", "Python"],
                        "contacts": [
                            {
                                "name": "John Doe",
                                "position": "CEO",
                                "email": "john@example.com",
                                "linkedin": "https://linkedin.com/in/johndoe"
                            }
                        ]
                    },
                    "credits_used": 1
                }
            },
            {
                "status": 400,
                "description": "Parâmetros inválidos",
                "example": {
                    "detail": "Domain is required"
                }
            },
            {
                "status": 402,
                "description": "Créditos insuficientes",
                "example": {
                    "detail": "Insufficient credits"
                }
            }
        ],
        "creditsRequired": 1,
        "rateLimit": {
            "requests": 100,
            "period": "hour"
        }
    },
    {
        "id": "enrich-person",
        "method": "POST",
        "path": "/api/v1/enrich/person",
        "name": "Enriquecer Pessoa",
        "description": "Enriquece dados de uma pessoa com informações profissionais, educacionais e de contato.",
        "category": "Enrichment",
        "parameters": [
            {
                "name": "email",
                "type": "string",
                "required": False,
                "description": "Email da pessoa",
                "example": "john@example.com"
            },
            {
                "name": "linkedin_url",
                "type": "string",
                "required": False,
                "description": "URL do perfil LinkedIn",
                "example": "https://linkedin.com/in/johndoe"
            },
            {
                "name": "name",
                "type": "string",
                "required": False,
                "description": "Nome completo da pessoa",
                "example": "John Doe"
            },
            {
                "name": "company",
                "type": "string",
                "required": False,
                "description": "Empresa onde trabalha",
                "example": "Example Corp"
            },
            {
                "name": "domain",
                "type": "string",
                "required": False,
                "description": "Domínio da empresa",
                "example": "example.com"
            },
            {
                "name": "phone",
                "type": "string",
                "required": False,
                "description": "Número de telefone",
                "example": "+1234567890"
            }
        ],
        "requestBody": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "Email da pessoa"},
                "linkedin_url": {"type": "string", "description": "URL do LinkedIn"},
                "name": {"type": "string", "description": "Nome completo"},
                "company": {"type": "string", "description": "Empresa"},
                "domain": {"type": "string", "description": "Domínio da empresa"},
                "phone": {"type": "string", "description": "Telefone"}
            },
            "example": {
                "email": "john@example.com",
                "linkedin_url": "https://linkedin.com/in/johndoe",
                "name": "John Doe",
                "company": "Example Corp"
            }
        },
        "responses": [
            {
                "status": 200,
                "description": "Dados da pessoa enriquecidos com sucesso",
                "example": {
                    "person": {
                        "name": "John Doe",
                        "email": "john@example.com",
                        "position": "CEO",
                        "company": "Example Corp",
                        "location": "San Francisco, CA",
                        "linkedin": "https://linkedin.com/in/johndoe",
                        "twitter": "@johndoe",
                        "phone": "+1234567890",
                        "education": [
                            {
                                "school": "Stanford University",
                                "degree": "MBA",
                                "field": "Business Administration"
                            }
                        ],
                        "experience": [
                            {
                                "company": "Example Corp",
                                "position": "CEO",
                                "duration": "2020 - Present"
                            }
                        ]
                    },
                    "credits_used": 1
                }
            },
            {
                "status": 400,
                "description": "Parâmetros inválidos",
                "example": {
                    "detail": "At least one parameter is required"
                }
            },
            {
                "status": 402,
                "description": "Créditos insuficientes",
                "example": {
                    "detail": "Insufficient credits"
                }
            }
        ],
        "creditsRequired": 1,
        "rateLimit": {
            "requests": 100,
            "period": "hour"
        }
    },
    {
        "id": "dashboard-stats",
        "method": "GET",
        "path": "/api/v1/dashboard/stats",
        "name": "Estatísticas do Dashboard",
        "description": "Retorna estatísticas gerais da conta do usuário.",
        "category": "Dashboard",
        "parameters": [],
        "responses": [
            {
                "status": 200,
                "description": "Estatísticas retornadas com sucesso",
                "example": {
                    "credits_remaining": 450,
                    "credits_total": 500,
                    "api_calls_today": 25,
                    "api_calls_month": 150,
                    "success_rate": 98.5
                }
            }
        ],
        "creditsRequired": 0
    },
    {
        "id": "api-keys-list",
        "method": "GET",
        "path": "/api/v1/api-keys",
        "name": "Listar API Keys",
        "description": "Lista todas as API keys do usuário.",
        "category": "API Keys",
        "parameters": [],
        "responses": [
            {
                "status": 200,
                "description": "Lista de API keys retornada com sucesso",
                "example": {
                    "api_keys": [
                        {
                            "id": "key_123",
                            "name": "Production Key",
                            "key": "es_prod_***",
                            "created_at": "2024-01-15T10:30:00Z",
                            "last_used": "2024-01-20T15:45:00Z",
                            "is_active": True
                        }
                    ]
                }
            }
        ],
        "creditsRequired": 0
    },
    {
        "id": "api-keys-create",
        "method": "POST",
        "path": "/api/v1/api-keys",
        "name": "Criar API Key",
        "description": "Cria uma nova API key para o usuário.",
        "category": "API Keys",
        "parameters": [
            {
                "name": "name",
                "type": "string",
                "required": True,
                "description": "Nome da API key",
                "example": "Production Key"
            }
        ],
        "requestBody": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nome da API key"}
            },
            "example": {
                "name": "Production Key"
            }
        },
        "responses": [
            {
                "status": 201,
                "description": "API key criada com sucesso",
                "example": {
                    "id": "key_123",
                    "name": "Production Key",
                    "key": "es_prod_abc123def456",
                    "created_at": "2024-01-15T10:30:00Z"
                }
            }
        ],
        "creditsRequired": 0
    },
    {
        "id": "google-maps-scrape",
        "method": "POST",
        "path": "/api/v1/scrapp/google-maps",
        "name": "Scraping Google Maps",
        "description": "Extrai dados detalhados de uma empresa no Google Maps incluindo informações de contato, avaliações e horários.",
        "category": "Scraping",
        "parameters": [
            {
                "name": "url",
                "type": "string",
                "required": True,
                "description": "URL da página da empresa no Google Maps",
                "example": "https://maps.google.com/maps/place/McDonald's"
            },
            {
                "name": "use_hyperbrowser",
                "type": "boolean",
                "required": False,
                "description": "Usar Hyperbrowser para scraping avançado",
                "example": True
            }
        ],
        "requestBody": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL do Google Maps"},
                "use_hyperbrowser": {"type": "boolean", "description": "Usar Hyperbrowser"}
            },
            "example": {
                "url": "https://maps.google.com/maps/place/McDonald's",
                "use_hyperbrowser": True
            }
        },
        "responses": [
            {
                "status": 200,
                "description": "Dados extraídos com sucesso",
                "example": {
                    "business_name": "McDonald's",
                    "address": "123 Main St, New York, NY",
                    "phone": "+1-555-0123",
                    "website": "https://mcdonalds.com",
                    "rating": 4.2,
                    "reviews_count": 1250,
                    "hours": "Open 24 hours",
                    "category": "Fast food restaurant"
                }
            }
        ],
        "creditsRequired": 1
    },
    {
        "id": "google-maps-search",
        "method": "POST",
        "path": "/api/v1/scrapp/google-maps/search",
        "name": "Buscar no Google Maps",
        "description": "Busca empresas no Google Maps por nome e localização.",
        "category": "Scraping",
        "parameters": [
            {
                "name": "business_name",
                "type": "string",
                "required": True,
                "description": "Nome da empresa para buscar",
                "example": "Starbucks"
            },
            {
                "name": "location",
                "type": "string",
                "required": True,
                "description": "Localização para buscar",
                "example": "New York"
            },
            {
                "name": "use_hyperbrowser",
                "type": "boolean",
                "required": False,
                "description": "Usar Hyperbrowser para scraping avançado",
                "example": True
            }
        ],
        "requestBody": {
            "type": "object",
            "properties": {
                "business_name": {"type": "string", "description": "Nome da empresa"},
                "location": {"type": "string", "description": "Localização"},
                "use_hyperbrowser": {"type": "boolean", "description": "Usar Hyperbrowser"}
            },
            "example": {
                "business_name": "Starbucks",
                "location": "New York",
                "use_hyperbrowser": True
            }
        },
        "responses": [
            {
                "status": 200,
                "description": "Resultados da busca",
                "example": {
                    "results": [
                        {
                            "business_name": "Starbucks",
                            "address": "456 Broadway, New York, NY",
                            "phone": "+1-555-0456",
                            "rating": 4.1,
                            "url": "https://maps.google.com/maps/place/starbucks"
                        }
                    ],
                    "total_found": 25
                }
            }
        ],
        "creditsRequired": 1
    },
    {
        "id": "whatsapp-scrape",
        "method": "POST",
        "path": "/api/v1/scrapp/whatsapp",
        "name": "Scraping WhatsApp Business",
        "description": "Extrai informações de perfis do WhatsApp Business incluindo dados de contato e informações da empresa.",
        "category": "Scraping",
        "parameters": [
            {
                "name": "url",
                "type": "string",
                "required": True,
                "description": "URL ou número do WhatsApp",
                "example": "https://wa.me/5511999999999"
            },
            {
                "name": "use_hyperbrowser",
                "type": "boolean",
                "required": False,
                "description": "Usar Hyperbrowser para scraping avançado",
                "example": True
            }
        ],
        "requestBody": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL ou número do WhatsApp"},
                "use_hyperbrowser": {"type": "boolean", "description": "Usar Hyperbrowser"}
            },
            "example": {
                "url": "https://wa.me/5511999999999",
                "use_hyperbrowser": True
            }
        },
        "responses": [
            {
                "status": 200,
                "description": "Dados extraídos com sucesso",
                "example": {
                    "phone_number": "+55 11 99999-9999",
                    "business_name": "Empresa Exemplo",
                    "description": "Descrição da empresa",
                    "address": "São Paulo, SP",
                    "website": "https://exemplo.com",
                    "is_business": True,
                    "category": "Serviços"
                }
            }
        ],
        "creditsRequired": 1
    },
    {
        "id": "whatsapp-search",
        "method": "POST",
        "path": "/api/v1/scrapp/whatsapp/search",
        "name": "Buscar WhatsApp Business",
        "description": "Busca perfis do WhatsApp Business por nome da empresa e localização.",
        "category": "Scraping",
        "parameters": [
            {
                "name": "business_name",
                "type": "string",
                "required": True,
                "description": "Nome da empresa para buscar",
                "example": "McDonald's"
            },
            {
                "name": "location",
                "type": "string",
                "required": True,
                "description": "Localização para buscar",
                "example": "São Paulo"
            },
            {
                "name": "use_hyperbrowser",
                "type": "boolean",
                "required": False,
                "description": "Usar Hyperbrowser para scraping avançado",
                "example": True
            }
        ],
        "requestBody": {
            "type": "object",
            "properties": {
                "business_name": {"type": "string", "description": "Nome da empresa"},
                "location": {"type": "string", "description": "Localização"},
                "use_hyperbrowser": {"type": "boolean", "description": "Usar Hyperbrowser"}
            },
            "example": {
                "business_name": "McDonald's",
                "location": "São Paulo",
                "use_hyperbrowser": True
            }
        },
        "responses": [
            {
                "status": 200,
                "description": "Resultados da busca",
                "example": {
                    "results": [
                        {
                            "phone_number": "+55 11 88888-8888",
                            "business_name": "McDonald's Centro",
                            "location": "São Paulo, SP",
                            "whatsapp_url": "https://wa.me/5511888888888"
                        }
                    ],
                    "total_found": 5
                }
            }
        ],
        "creditsRequired": 1
    }
]

@router.get("/endpoints")
async def get_endpoints() -> List[Dict[str, Any]]:
    """
    Retorna a lista de todos os endpoints disponíveis na API com suas documentações.
    """
    return API_ENDPOINTS

@router.get("/endpoints/{endpoint_id}")
async def get_endpoint_details(endpoint_id: str) -> Dict[str, Any]:
    """
    Retorna detalhes específicos de um endpoint.
    """
    endpoint = next((ep for ep in API_ENDPOINTS if ep["id"] == endpoint_id), None)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found"
        )
    return endpoint

@router.get("/categories")
async def get_categories() -> List[str]:
    """
    Retorna todas as categorias de endpoints disponíveis.
    """
    categories = list(set(endpoint["category"] for endpoint in API_ENDPOINTS))
    return sorted(categories)

@router.post("/test/{endpoint_id}")
async def test_endpoint(endpoint_id: str, request_data: Dict[str, Any], req: Request, response: Response, auth_data: dict = Depends(require_credits)) -> Dict[str, Any]:
    """
    Testa um endpoint específico da API fazendo uma chamada real.
    """
    import httpx
    import time
    from fastapi import Request
    
    # Encontra o endpoint
    endpoint = next((ep for ep in API_ENDPOINTS if ep["id"] == endpoint_id), None)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    # Faz a chamada real para o endpoint
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient() as client:
            # Constrói a URL completa do endpoint
            base_url = "http://localhost:8000"  # ou usar uma variável de ambiente
            full_url = f"{base_url}{endpoint['path']}"
            
            # Faz a requisição baseada no método
            if endpoint["method"] == "GET":
                response = await client.get(full_url, params=request_data)
            elif endpoint["method"] == "POST":
                response = await client.post(full_url, json=request_data)
            else:
                response = await client.request(endpoint["method"], full_url, json=request_data)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return {
                "success": response.status_code < 400,
                "status": response.status_code,
                "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                "executionTime": execution_time,
                "creditsUsed": endpoint["creditsRequired"] if response.status_code < 400 else 0
            }
            
    except Exception as e:
        execution_time = int((time.time() - start_time) * 1000)
        return {
            "success": False,
            "status": 500,
            "data": {
                "error": str(e),
                "message": f"Erro ao testar endpoint {endpoint['name']}"
            },
            "executionTime": execution_time,
            "creditsUsed": 0
        }