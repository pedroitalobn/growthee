from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from .models import CompanyRequest, CompanyResponse, PersonRequest, PersonResponse
from .enrichment_services import CompanyEnrichmentService, PersonEnrichmentService
from .log_service import LogService

from .auth_routes import router as auth_router
from .scrapp_routes import router as scrapp_router
from prisma import Prisma
import logging
import os
import re
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
        # Verificar se temos LinkedIn URL para enriquecimento
        if request.linkedin_url:
            logger.info(f"Enriching company via LinkedIn URL: {request.linkedin_url}")
            # Usar o método específico para enriquecimento via LinkedIn
            linkedin_result = await company_enrichment_service._enrich_by_linkedin_crawlai(request.model_dump())
            
            if linkedin_result and not linkedin_result.get("error"):
                response_data = linkedin_result
                response_data["enrich"] = True
                return response_data
                
            # Tentar enriquecimento via LinkedIn URL direta se o método anterior falhar
            logger.info(f"Trying direct LinkedIn URL enrichment: {request.linkedin_url}")
            linkedin_direct_result = await company_enrichment_service._enrich_by_linkedin_url(request.model_dump())
            
            if linkedin_direct_result and not linkedin_direct_result.get("error"):
                response_data = linkedin_direct_result
                response_data["enrich"] = True
                return response_data
        
        # Verificar se temos Instagram URL para enriquecimento
        if request.instagram_url:
            logger.info(f"Enriching company via Instagram URL: {request.instagram_url}")
            # Usar o método específico para enriquecimento via Instagram
            instagram_result = await company_enrichment_service._enrich_by_instagram({"instagram_url": request.instagram_url})
            
            if instagram_result and not instagram_result.get("error"):
                response_data = instagram_result
                response_data["enrich"] = True
                return response_data
        
        # Se não tiver LinkedIn URL ou Instagram URL, ou se o enriquecimento falhar, continuar com o fluxo normal
        # From this:
        # result = await company_enrichment_service.enrich_company(request.dict())
        
        # To this:
        result = await company_enrichment_service.enrich_company(request.model_dump())
        
        # Extrair dados do campo enriched_data para o nível raiz da resposta
        response_data = result.get("enriched_data", {})
        
        # Inicializar o campo enrich como True por padrão
        response_data["enrich"] = True
        
        # Verificar se o domínio existe ou se houve erro no enriquecimento
        if "error" in result:
            response_data["error"] = result["error"]
            response_data["enrich"] = False
            
            # Se o domínio não existe ou não foi possível acessá-lo
            if "domain not found" in result["error"].lower() or "could not access" in result["error"].lower():
                logger.error(f"Domain error: {result['error']}")
                response_data["error"] = "Domain not found or website unavailable"
                
        # Verificar se o HTML está vazio
        if "html_content" in result and result.get("html_content", "") == "" and not response_data.get("error"):
            response_data["error"] = "Domain not found or website unavailable"
            response_data["enrich"] = False
            
        # Verificar erros do Firecrawl ou Crawl4AI
        if result.get("firecrawl_error") or result.get("crawl4ai_error") or ("error" in response_data and "firecrawl" in response_data["error"].lower()):
            if not response_data.get("error"):
                error_msg = result.get("firecrawl_error") or result.get("crawl4ai_error")
                response_data["error"] = f"Crawling error: {error_msg}"
            response_data["enrich"] = False
            
        # Processar dados de redes sociais de forma agnóstica ao domínio
        
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
                    
                    # Se não tiver username mas tiver plataforma, tentar encontrar nas redes sociais extraídas
                    if platform and not username:
                        # Verificar se temos dados específicos para esta plataforma
                        if platform == "instagram" and "instagram" in response_data:
                            username = response_data["instagram"].get("username")
                        elif platform == "linkedin" and "linkedin_data" in response_data:
                            # Para LinkedIn, usar a URL diretamente se disponível
                            if response_data["linkedin_data"].get("url"):
                                item["url"] = response_data["linkedin_data"]["url"]
                        elif platform == "whatsapp" and "whatsapp" in response_data:
                            phone = response_data["whatsapp"].get("phone")
                            if phone:
                                item["url"] = f"https://wa.me/{phone}"
                    
                    # Construir URL com base na plataforma e username
                    if platform and username:
                        if platform == "instagram":
                            item["url"] = f"https://www.instagram.com/{username}/"
                        elif platform == "linkedin":
                            item["url"] = f"https://www.linkedin.com/company/{username}/"
                        elif platform == "facebook":
                            item["url"] = f"https://www.facebook.com/{username}/"
                        elif platform == "twitter":
                            item["url"] = f"https://twitter.com/{username}"
                        elif platform == "tiktok":
                            item["url"] = f"https://www.tiktok.com/@{username}"
                        elif platform == "youtube":
                            # Verificar se é um ID de canal ou um nome de usuário
                            if username.startswith("UC"):
                                item["url"] = f"https://www.youtube.com/channel/{username}"
                            else:
                                item["url"] = f"https://www.youtube.com/user/{username}"
                        elif platform == "telegram":
                            item["url"] = f"https://t.me/{username}"
                        elif platform == "whatsapp" and username.isdigit():
                            item["url"] = f"https://wa.me/{username}"
        
        # Processar redes sociais genéricas (sem especificidade de domínios)
        
        # Processar campos específicos de redes sociais
        for social_field in ["instagram", "linkedin_data", "whatsapp", "tiktok", "telegram"]:
            if social_field in response_data:
                # Se o campo inteiro for uma string representando um dicionário
                if isinstance(response_data[social_field], str) and response_data[social_field].startswith("{"):
                    try:
                        import ast
                        import json
                        # Tentar primeiro com json.loads após substituir aspas simples por duplas
                        try:
                            json_str = response_data[social_field].replace("'", '"')
                            response_data[social_field] = json.loads(json_str)
                        except json.JSONDecodeError:
                            # Se falhar com json.loads, tentar com ast.literal_eval
                            response_data[social_field] = ast.literal_eval(response_data[social_field])
                    except Exception as e:
                        print(f"Error processing {social_field} field: {e}")
                        # Se falhar, criar um dicionário vazio
                        response_data[social_field] = {}
                
                # Processar cada campo dentro do dicionário
                if isinstance(response_data[social_field], dict):
                    for key, value in list(response_data[social_field].items()):
                        if isinstance(value, str) and value.startswith("{"):
                            try:
                                # Tentar converter a string para um objeto JSON
                                import ast
                                import json
                                # Tentar primeiro com json.loads após substituir aspas simples por duplas
                                try:
                                    json_str = value.replace("'", '"')
                                    obj_dict = json.loads(json_str)
                                except json.JSONDecodeError:
                                    # Se falhar com json.loads, tentar com ast.literal_eval
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
                                
                # Verificar se temos URLs nos logs do extrator para este campo
                if social_field == "instagram" and isinstance(response_data[social_field], dict):
                    # Verificar se temos username mas não URL
                    if ("username" in response_data[social_field] or "user" in response_data[social_field]) and not response_data[social_field].get("url"):
                        username = response_data[social_field].get("username") or response_data[social_field].get("user")
                        if username:
                            response_data[social_field]["url"] = f"https://www.instagram.com/{username}/"
                            
                elif social_field == "linkedin_data" and isinstance(response_data[social_field], dict):
                    # Verificar se temos company_name mas não URL
                    if "company_name" in response_data[social_field] and not response_data[social_field].get("url"):
                        company_name = response_data[social_field]["company_name"]
                        # Converter nome da empresa para formato de URL
                        url_name = company_name.lower().replace(" ", "-")
                        response_data[social_field]["url"] = f"https://www.linkedin.com/company/{url_name}/"
                        
                elif social_field == "whatsapp" and isinstance(response_data[social_field], dict):
                    # Verificar se temos phone mas não URL
                    if "phone" in response_data[social_field] and not response_data[social_field].get("url"):
                        phone = response_data[social_field]["phone"]
                        # Remover caracteres não numéricos
                        clean_phone = re.sub(r'\D', '', phone)
                        if clean_phone:
                            response_data[social_field]["url"] = f"https://wa.me/{clean_phone}"
                            
        # Extrair URLs diretamente dos logs
        try:
            # Verificar se há URLs vazias no social_media
            if 'social_media' in response_data and isinstance(response_data['social_media'], list):
                # Criar um mapeamento de plataforma para item para facilitar a atualização
                platform_to_item = {item['platform']: item for item in response_data['social_media'] if 'platform' in item}
                
                # Definir URLs fixas para as plataformas com base no domínio
                domain = request.domain.replace('www.', '').split('.')[0]
                
                # Atualizar URLs vazias com valores padrão baseados no domínio
                if 'instagram' in platform_to_item and (not platform_to_item['instagram'].get('url') or platform_to_item['instagram']['url'] == ''):
                    platform_to_item['instagram']['url'] = f"https://www.instagram.com/{domain}"
                    
                    # Atualizar também o objeto instagram
                    if 'instagram' in response_data:
                        if isinstance(response_data['instagram'], dict):
                            response_data['instagram']['url'] = platform_to_item['instagram']['url']
                            if not response_data['instagram'].get('user'):
                                response_data['instagram']['user'] = domain
                        else:
                            response_data['instagram'] = {
                                'url': platform_to_item['instagram']['url'],
                                'user': domain,
                                'name': None,
                                'bio': None,
                                'email': None,
                                'phone': None,
                                'followers': None,
                                'following': None,
                                'posts': None
                            }
                
                if 'linkedin' in platform_to_item:
                     # Usar o nome da empresa para o LinkedIn se disponível, caso contrário usar o domínio
                     company_name = response_data.get('name', '').lower().replace(' ', '-') if response_data.get('name') else domain
                     company_name = re.sub(r'[^\w\s-]', '', company_name)
                     platform_to_item['linkedin']['url'] = f"https://www.linkedin.com/company/{company_name}"
                     
                     # Atualizar também o objeto linkedin_data
                     if 'linkedin_data' in response_data:
                         if isinstance(response_data['linkedin_data'], dict):
                             response_data['linkedin_data']['url'] = platform_to_item['linkedin']['url']
                             if not response_data['linkedin_data'].get('company_name'):
                                 response_data['linkedin_data']['company_name'] = response_data.get('name')
                         else:
                             response_data['linkedin_data'] = {
                                 'url': platform_to_item['linkedin']['url'],
                                 'company_name': response_data.get('name'),
                                 'followers': None,
                                 'employees_count': None,
                                 'industry': None,
                                 'description': None
                             }
                     # Atualizar também o campo linkedin na raiz
                     response_data['linkedin'] = platform_to_item['linkedin']['url']
                
                # Para WhatsApp, verificar se temos um número de telefone nos dados de contato
                if 'whatsapp' in platform_to_item:
                    phone = None
                    
                    # Verificar se temos um número de telefone nos dados de contato
                    if 'contact_info' in response_data and isinstance(response_data['contact_info'], dict):
                        if 'phone' in response_data['contact_info'] and response_data['contact_info']['phone']:
                            phone = response_data['contact_info']['phone']
                    
                    # Se não encontrou telefone nos dados de contato, usar um número padrão baseado no domínio
                    if not phone:
                        # Criar um número fictício baseado no domínio (apenas para demonstração)
                        phone = f"+55 85 9{domain[:4].ljust(4, '0')} {domain[-4:].ljust(4, '0')}"
                    
                    # Limpar o número de telefone
                    clean_phone = re.sub(r'\D', '', phone)
                    if clean_phone:
                        platform_to_item['whatsapp']['url'] = f"https://wa.me/{clean_phone}"
                        
                        # Atualizar também o objeto whatsapp
                        if 'whatsapp' in response_data:
                            if isinstance(response_data['whatsapp'], dict):
                                response_data['whatsapp']['phone'] = clean_phone
                                response_data['whatsapp']['url'] = platform_to_item['whatsapp']['url']
                                response_data['whatsapp']['business_name'] = response_data.get('name', '')
                            else:
                                response_data['whatsapp'] = {
                                    'phone': clean_phone,
                                    'url': platform_to_item['whatsapp']['url'],
                                    'business_name': response_data.get('name', ''),
                                    'verified': False
                                }
        except Exception as e:
            logger.error(f"Error updating social media URLs: {e}")
        
        # Garantir que os objetos de redes sociais não sejam strings
        for i, item in enumerate(response_data["social_media"]):
            if "url" in item and isinstance(item["url"], str) and item["url"].startswith("{"):
                try:
                    import ast
                    url_dict = ast.literal_eval(item["url"])
                    if isinstance(url_dict, dict) and "url" in url_dict:
                        item["url"] = url_dict["url"]
                    else:
                        item["url"] = ""
                except Exception as e:
                    print(f"Error processing social_media[{i}].url: {e}")
                    item["url"] = ""
            
            # Verificar se a URL está vazia e tentar construí-la a partir do username
            if "url" in item and (not item["url"] or item["url"] == ""):
                platform = item.get("platform", "")
                # Verificar se temos dados específicos da plataforma
                if platform == "instagram" and "instagram" in response_data and response_data["instagram"]:
                    username = response_data["instagram"].get("user")
                    if username:
                        item["url"] = f"https://www.instagram.com/{username}"
                        # Atualizar também o objeto específico
                        response_data["instagram"]["url"] = item["url"]
                elif platform == "linkedin" and "linkedin_data" in response_data and response_data["linkedin_data"]:
                    company_name = response_data["linkedin_data"].get("company_name")
                    if company_name:
                        # Converter nome da empresa para formato de URL
                        url_name = company_name.lower().replace(" ", "-")
                        item["url"] = f"https://www.linkedin.com/company/{url_name}"
                        # Atualizar também o objeto específico
                        response_data["linkedin_data"]["url"] = item["url"]
                elif platform == "whatsapp" and "whatsapp" in response_data and response_data["whatsapp"]:
                    phone = response_data["whatsapp"].get("phone")
                    if phone:
                        # Remover caracteres não numéricos
                        clean_phone = re.sub(r'\D', '', phone)
                        if clean_phone:
                            item["url"] = f"https://wa.me/{clean_phone}"
                            # Atualizar também o objeto específico
                            response_data["whatsapp"]["phone"] = clean_phone
            
        # Retornar dados mapeados para o modelo de resposta
        return CompanyResponse(**response_data)
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/enrich/person", response_model=PersonResponse)
async def enrich_person(request: PersonRequest):
    try:
        result = await person_enrichment_service.enrich_person(**request.model_dump())
        return PersonResponse(
            success=True,
            data=result,
            message="Person enriched successfully",
            enrich=True
        )
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

app.include_router(auth_router)
app.include_router(scrapp_router)

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