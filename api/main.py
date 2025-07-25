# REMOVER ESTAS LINHAS:
# from twisted.internet import reactor
# import threading

# def run_reactor():
#     if not reactor.running:
#         thread = threading.Thread(target=reactor.run, args=(False,))
#         thread.daemon = True
#         thread.start()

# run_reactor()

# MANTER APENAS:
from fastapi import FastAPI, HTTPException
from .models import CompanyRequest, CompanyResponse, PersonRequest, PersonResponse
from .services import EnrichmentService, PersonEnrichmentService
import logging
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

app = FastAPI(title="Company Enrichment API", version="1.0.0")
logger = logging.getLogger(__name__)

# Inicializa os serviços de enriquecimento
enrichment_service = EnrichmentService()
person_enrichment_service = PersonEnrichmentService()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/enrich/company", response_model=CompanyResponse)
async def enrich_company(request: CompanyRequest):
    """Enriquece dados de uma empresa usando a API do Brave Search"""
    try:
        # Converte o request para dict
        company_data = request.dict(exclude_unset=True)
        
        # Valida se pelo menos um campo foi fornecido
        if not any([company_data.get('name'), company_data.get('domain'), company_data.get('linkedin_url')]):
            raise HTTPException(
                status_code=400, 
                detail="Necessário fornecer pelo menos um dos campos: name, domain ou linkedin_url"
            )
        
        # Chama o serviço de enriquecimento
        result = await enrichment_service.enrich_company(company_data)
        
        # Retorna a resposta
        return CompanyResponse(**result)
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal error: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@app.post("/enrich/companies")
async def enrich_companies(requests: list[CompanyRequest]):
    """Enriquece dados de múltiplas empresas"""
    results = []
    
    for request in requests:
        try:
            company_data = request.dict(exclude_unset=True)
            result = await enrichment_service.enrich_company(company_data)
            results.append(CompanyResponse(**result))
        except Exception as e:
            logger.error(f"Error processing company {request.name}: {str(e)}")
            results.append(CompanyResponse(
                name=request.name or "Unknown",
                error=str(e)
            ))
    
    return results

@app.post("/enrich/person", response_model=PersonResponse)
async def enrich_person(request: PersonRequest):
    """Enriquece dados de uma pessoa usando múltiplas estratégias"""
    try:
        # Converte o request para dict
        person_data = request.dict(exclude_unset=True)
        
        # Valida se pelo menos um campo foi fornecido
        if not request.has_valid_input:
            raise HTTPException(
                status_code=400, 
                detail="Necessário fornecer pelo menos um dos campos: email, linkedin_url, phone ou full_name"
            )
        
        # Chama o serviço de enriquecimento
        result = await person_enrichment_service.enrich_person(**person_data)
        
        # Retorna a resposta
        return PersonResponse(**result)
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal error: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@app.post("/enrich/people")
async def enrich_people(requests: list[PersonRequest]):
    """Enriquece dados de múltiplas pessoas"""
    results = []
    
    for request in requests:
        try:
            person_data = request.dict(exclude_unset=True)
            result = await person_enrichment_service.enrich_person(**person_data)
            results.append(PersonResponse(**result))
        except Exception as e:
            logger.error(f"Error processing person {request.full_name}: {str(e)}")
            results.append(PersonResponse(
                full_name=request.full_name or "Unknown",
                error=str(e)
            ))
    
    return results

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from prisma import Prisma
import logging
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="EnrichStory API", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "enrichstory-api", "version": "2.0.0"}

@app.get("/")
async def root():
    return {"message": "EnrichStory API", "version": "2.0.0"}

@app.post("/api/v1/enrich/company", response_model=CompanyResponse)
async def enrich_company(request: CompanyRequest):
    """Enriquece dados de uma empresa"""
    try:
        company_data = request.dict(exclude_unset=True)
        
        if not any([company_data.get('name'), company_data.get('domain'), company_data.get('linkedin_url')]):
            raise HTTPException(
                status_code=400, 
                detail="Necessário fornecer pelo menos um dos campos: name, domain ou linkedin_url"
            )
        
        result = await enrichment_service.enrich_company(company_data)
        return CompanyResponse(**result)
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal error: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@app.post("/api/v1/enrich/person", response_model=PersonResponse)
async def enrich_person(request: PersonRequest):
    """Enriquece dados de uma pessoa"""
    try:
        person_data = request.dict(exclude_unset=True)
        
        if not request.has_valid_input:
            raise HTTPException(
                status_code=400, 
                detail="Necessário fornecer pelo menos um dos campos: email, linkedin_url, phone ou full_name"
            )
        
        result = await person_enrichment_service.enrich_person(**person_data)
        return PersonResponse(**result)
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal error: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

sentry_sdk.init(
    dsn="https://seu-dsn@sentry.io/projeto",
    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0,
)