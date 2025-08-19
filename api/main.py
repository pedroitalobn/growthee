from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from .models import CompanyRequest, CompanyResponse, PersonRequest, PersonResponse
from .services import CompanyEnrichmentService, PersonEnrichmentService
from .log_service import LogService

from .auth_routes import router as auth_router
from prisma import Prisma
import logging
import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="EnrichStory API", version="2.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializa o Prisma
prisma = Prisma()

# Inicializa os serviços
log_service = LogService()
company_enrichment_service = CompanyEnrichmentService(db_session=prisma, log_service=log_service)
person_enrichment_service = PersonEnrichmentService()

# Eventos de inicialização e encerramento
@app.on_event("startup")
async def startup():
    await prisma.connect()
    logger.info("Prisma connected successfully")

@app.on_event("shutdown")
async def shutdown():
    await prisma.disconnect()
    logger.info("Prisma disconnected")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"message": "EnrichStory API v2.0.0"}

@app.post("/api/v1/enrich/company", response_model=CompanyResponse)
async def enrich_company(request: CompanyRequest):
    try:
        result = await company_enrichment_service.enrich_company(request.dict())
        # Retornar diretamente os dados extraídos
        return CompanyResponse(**result)
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/enrich/person", response_model=PersonResponse)
async def enrich_person(request: PersonRequest):
    try:
        result = await person_enrichment_service.enrich_person(**request.dict())
        return PersonResponse(
            success=True,
            data=result,
            message="Person enriched successfully"
        )
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

app.include_router(auth_router)

# Sentry configuration
sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[FastApiIntegration()],
        traces_sample_rate=1.0,
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)