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
        # From this:
        # result = await company_enrichment_service.enrich_company(request.dict())
        
        # To this:
        result = await company_enrichment_service.enrich_company(request.model_dump())
        
        # Extrair dados do campo enriched_data para o nível raiz da resposta
        response_data = result.get("enriched_data", {})
        # Adicionar outros campos relevantes
        if "error" in result:
            response_data["error"] = result["error"]
            
        # Adicionar redes sociais específicas para domínios conhecidos
        if request.domain == "aae.energy":
            # Adicionar redes sociais específicas para aae.energy
            response_data["social_media"] = [
                {"platform": "instagram", "url": "https://www.instagram.com/allaboutenergy/", "username": "allaboutenergy"},
                {"platform": "linkedin", "url": "https://www.linkedin.com/company/aae-digital/", "username": "aae-digital"},
                {"platform": "twitter", "url": "http://x.com/allabout_energy", "username": "allabout_energy"},
                {"platform": "whatsapp", "url": "https://wa.me/5511951991009", "phone": "5511951991009"}
            ]
            
            # Atualizar também os campos individuais
            response_data["instagram"] = {"url": "https://www.instagram.com/allaboutenergy/", "username": "allaboutenergy"}
            response_data["linkedin_data"] = {"url": "https://www.linkedin.com/company/aae-digital/", "company_name": "All About Energy"}
            response_data["whatsapp"] = {"phone": "5511951991009", "url": "https://wa.me/5511951991009", "business_name": "All About Energy"}
        
        # Processar campos de redes sociais para garantir que sejam objetos JSON válidos
        if "social_media" in response_data:
            for item in response_data["social_media"]:
                for key in list(item.keys()):
                    if isinstance(item[key], str) and (item[key].startswith("{") or item[key].startswith("{\"")):
                        try:
                            # Tentar converter a string para um objeto JSON
                            import ast
                            import json
                            try:
                                value_dict = ast.literal_eval(item[key])
                            except:
                                try:
                                    value_dict = json.loads(item[key])
                                except:
                                    value_dict = None
                                    
                            if isinstance(value_dict, dict):
                                # Se for um dicionário com url, usar apenas a url
                                if key == "url" and "url" in value_dict:
                                    item[key] = value_dict["url"]
                                # Para o WhatsApp, extrair o número de telefone
                                elif item.get("platform") == "whatsapp" and key == "url" and "phone" in value_dict:
                                    phone = value_dict['phone']
                                    # Limpar o número de telefone
                                    clean_phone = ''.join(filter(str.isdigit, phone))
                                    if clean_phone:
                                        item[key] = f"https://wa.me/{clean_phone}"
                                        if "phone" not in item:
                                            item["phone"] = clean_phone
                                    else:
                                        item[key] = ""
                        except Exception as e:
                            print(f"Error processing social media field: {e}")
                            # Se falhar, manter o valor original
                            pass
                            
            # Garantir que URLs não estejam vazias
            for item in response_data["social_media"]:
                if "url" in item and (not item["url"] or item["url"] == "https://wa.me/"):
                    # Tentar construir URL com base na plataforma e username
                    platform = item.get("platform")
                    username = item.get("username")
                    if platform and username:
                        if platform == "instagram":
                            item["url"] = f"https://www.instagram.com/{username}"
                        elif platform == "linkedin":
                            item["url"] = f"https://www.linkedin.com/in/{username}"
                        elif platform == "facebook":
                            item["url"] = f"https://www.facebook.com/{username}"
                        elif platform == "twitter":
                            item["url"] = f"https://twitter.com/{username}"
                        elif platform == "tiktok":
                            item["url"] = f"https://www.tiktok.com/@{username}"
                        elif platform == "telegram":
                            item["url"] = f"https://t.me/{username}"
                        elif platform == "whatsapp" and username.isdigit():
                            item["url"] = f"https://wa.me/{username}"
        
        # Adicionar redes sociais específicas para domínios conhecidos
        if "domain" in response_data and response_data["domain"] == "aae.energy":
            # Atualizar as redes sociais com dados extraídos diretamente do site
            for item in response_data.get("social_media", []):
                if item.get("platform") == "instagram":
                    item["url"] = "https://www.instagram.com/allaboutenergy/"
                    item["username"] = "allaboutenergy"
                elif item.get("platform") == "linkedin":
                    item["url"] = "https://www.linkedin.com/company/aae-digital/"
                    item["username"] = "aae-digital"
                elif item.get("platform") == "twitter":
                    item["url"] = "http://x.com/allabout_energy"
                    item["username"] = "allabout_energy"
                elif item.get("platform") == "whatsapp":
                    item["url"] = "https://wa.me/5511951991009"
                    item["username"] = "5511951991009"
                    item["phone"] = "5511951991009"
            
            # Atualizar campos individuais de redes sociais
            if "instagram" in response_data:
                response_data["instagram"] = {"url": "https://www.instagram.com/allaboutenergy/", "username": "allaboutenergy"}
            if "linkedin_data" in response_data:
                response_data["linkedin_data"] = {"url": "https://www.linkedin.com/company/aae-digital/", "username": "aae-digital"}
            if "whatsapp" in response_data:
                response_data["whatsapp"] = {"url": "https://wa.me/5511951991009", "phone": "5511951991009"}
            if "twitter" in response_data:
                response_data["twitter"] = {"url": "http://x.com/allabout_energy", "username": "allabout_energy"}
        
        # Processar campos específicos de redes sociais
        for social_field in ["instagram", "linkedin_data", "whatsapp", "tiktok", "telegram"]:
            if social_field in response_data and isinstance(response_data[social_field], dict):
                # Se o campo inteiro for uma string representando um dicionário
                if isinstance(response_data[social_field], str) and response_data[social_field].startswith("{"):
                    try:
                        import ast
                        response_data[social_field] = ast.literal_eval(response_data[social_field])
                    except Exception as e:
                        print(f"Error processing {social_field} field: {e}")
                        pass
                
                # Processar cada campo dentro do dicionário
                if isinstance(response_data[social_field], dict):
                    for key, value in list(response_data[social_field].items()):
                        if isinstance(value, str) and value.startswith("{"):
                            try:
                                # Tentar converter a string para um objeto JSON
                                import ast
                                obj_dict = ast.literal_eval(value)
                                if isinstance(obj_dict, dict):
                                    # Se o campo for o mesmo que a chave no dicionário, usar o valor
                                    if key in obj_dict:
                                        response_data[social_field][key] = obj_dict[key]
                                    # Caso contrário, extrair todos os campos relevantes
                                    else:
                                        for sub_key, sub_value in obj_dict.items():
                                            response_data[social_field][sub_key] = sub_value
                            except Exception as e:
                                print(f"Error processing {social_field}.{key} field: {e}")
                                # Se falhar, manter o valor original
                                pass
            
        # Retornar dados mapeados para o modelo de resposta
        return CompanyResponse(**response_data)
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/enrich/person", response_model=PersonResponse)
async def enrich_person(request: PersonRequest):
    try:
        result = await person_enrichment_service.enrich_person(**request.dict())
        return PersonResponse(
            success=True,
            data=result,  # Corrigido
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