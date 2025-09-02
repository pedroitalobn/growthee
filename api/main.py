from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from .models import CompanyRequest, CompanyResponse, PersonRequest, PersonResponse
from .enrichment_services import CompanyEnrichmentService, PersonEnrichmentService
from .log_service import LogService
from .services.enhanced_llm_enrichment_agent import EnhancedLLMEnrichmentAgent
from .services.enhanced_linkedin_scraper import EnhancedLinkedInScraper
from .services.social_media_extractor import SocialMediaExtractor
from .services.brave_search_service import BraveSearchService

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
enhanced_llm_agent = EnhancedLLMEnrichmentAgent()
enhanced_linkedin_scraper = EnhancedLinkedInScraper(log_service)
social_media_extractor = SocialMediaExtractor(log_service)
brave_search_service = BraveSearchService(log_service)
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
        import asyncio
        import time
        
        start_time = time.time()
        logger.info(f"Starting super enrichment for domain: {request.domain}")
        
        # Initialize results
        social_media_data = {}
        linkedin_url_from_search = None
        brave_search_data = {}
        
        # Step 1: Extract social media if enabled
        if request.extract_social_media and request.domain:
            try:
                logger.info(f"Extracting social media for {request.domain}")
                social_result = await social_media_extractor.extract_all_social_media(request.domain)
                if social_result and not social_result.get('error'):
                    social_media_data = social_result
                    logger.info(f"Social media extraction completed with confidence: {social_result.get('confidence_score', 0)}")
            except Exception as e:
                logger.error(f"Error in social media extraction: {e}")
        
        # Step 2: Brave Search for LinkedIn if enabled
        if request.use_brave_search and request.domain:
            try:
                logger.info(f"Searching for LinkedIn via Brave Search for {request.domain}")
                company_name = request.name or request.domain.split('.')[0]
                search_result = await brave_search_service.search_linkedin_company(company_name, request.domain)
                if search_result and not search_result.get('error'):
                    brave_search_data = search_result
                    linkedin_url_from_search = search_result.get('linkedin_url')
                    logger.info(f"Brave Search completed, LinkedIn URL: {linkedin_url_from_search}")
            except Exception as e:
                logger.error(f"Error in Brave Search: {e}")
        
        # Step 3: Use found LinkedIn URL or provided one
        linkedin_url_to_use = request.linkedin_url or linkedin_url_from_search
        
        # Verificar se temos LinkedIn URL para enriquecimento
        if linkedin_url_to_use:
            logger.info(f"Enriching company via LinkedIn URL: {linkedin_url_to_use}")
            
            # Use enhanced LinkedIn scraper if we found URL via search
            if linkedin_url_from_search and request.extract_linkedin:
                try:
                    logger.info(f"Using enhanced LinkedIn scraper for: {linkedin_url_from_search}")
                    linkedin_enhanced_result = await enhanced_linkedin_scraper.scrape_linkedin_data(
                        linkedin_url_from_search, request.domain
                    )
                    if linkedin_enhanced_result and linkedin_enhanced_result.get('confidence_score', 0) > 0.5:
                        # Convert to expected format and return early
                        response_data = {
                            "company_name": linkedin_enhanced_result.get('company_name'),
                            "description": linkedin_enhanced_result.get('description'),
                            "industry": linkedin_enhanced_result.get('industry'),
                            "employee_count": linkedin_enhanced_result.get('employee_count'),
                            "headquarters": linkedin_enhanced_result.get('headquarters'),
                            "website": linkedin_enhanced_result.get('website'),
                            "linkedin_data": linkedin_enhanced_result,
                            "social_media_data": social_media_data,
                            "brave_search_data": brave_search_data,
                            "enrichment_source": "enhanced_linkedin_scraper",
                            "enrich": True,
                            "processing_time": time.time() - start_time
                        }
                        return response_data
                except Exception as e:
                    logger.error(f"Error with enhanced LinkedIn scraper: {e}")
            
            # Fallback to original LinkedIn enrichment
            request_dict = request.model_dump()
            request_dict['linkedin_url'] = linkedin_url_to_use
            linkedin_result = await company_enrichment_service._enrich_by_linkedin_crawlai(request_dict)
            
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
        result = await company_enrichment_service.enrich_company(request.model_dump())
        
        # Extrair dados enriquecidos
        enriched_data = result.get("enriched_data", {})
        response_data = enriched_data if enriched_data else result
        
        # Verificar se houve erro de domínio não encontrado ou indisponível
        if result.get("error") and ("not found" in result["error"].lower() or "unavailable" in result["error"].lower()):
            logger.info(f"Domain {request.domain} not found or unavailable, trying LLM enrichment")
            
            # Usar o Enhanced LLM Enrichment Agent para enriquecer dados quando o domínio não for encontrado
            try:
                # Use enhanced LLM agent with HTML content if available
                html_content = "<html><body>No content available</body></html>"  # Fallback
                llm_result = await enhanced_llm_agent.extract_company_info_from_html(
                    html_content, request.domain
                )
                
                logger.info(f"Enhanced LLM result for {request.domain}: confidence {llm_result.confidence_score}%")
                if llm_result and llm_result.confidence_score > 0.3:
                    # Convert enhanced result to dict
                    response_data = {
                        "company_name": llm_result.name,
                        "description": llm_result.description,
                        "industry": llm_result.industry,
                        "employee_count": llm_result.employee_count,
                        "headquarters": llm_result.headquarters,
                        "founded": llm_result.founded,
                        "website": llm_result.website,
                        "products_services": llm_result.products_services,
                        "enrichment_source": "enhanced_llm",
                        "enrich": True,
                        "llm_enrichment": {
                            "confidence_score": llm_result.confidence_score,
                            "extraction_method": llm_result.extraction_method,
                            "processing_time": llm_result.processing_time
                        }
                    }
                    logger.info(f"Enhanced LLM enrichment completed successfully for {request.domain}")
                    return response_data
            except Exception as e:
                logger.error(f"Error using Enhanced LLM Enrichment Agent: {e}")
                # Continuar com os dados que já temos
        
        # Se temos dados mas eles estão incompletos, usar o LLM para complementar
        elif not result.get("error") and response_data:
            # Verificar se os dados do LinkedIn estão incompletos
            linkedin_data = response_data.get("linkedin_data", {})
            if linkedin_data and (not linkedin_data.get("description") or not linkedin_data.get("industry")):
                logger.info(f"LinkedIn data incomplete for {request.domain}, using LLM to enrich")
                
                try:
                    # Use enhanced LLM agent for missing data enrichment
                    html_content = "<html><body>No content available</body></html>"  # Fallback
                    llm_result = await enhanced_llm_agent.enrich_missing_linkedin_data(
                        response_data, html_content, request.domain
                    )
                    
                    # Convert back to enhanced result format for consistency
                    if isinstance(llm_result, dict):
                        # Create a mock result object for consistent handling
                        class MockResult:
                            def __init__(self, data):
                                self.company_name = data.get('company_name')
                                self.description = data.get('description')
                                self.industry = data.get('industry')
                                self.employee_count = data.get('employee_count')
                                self.headquarters = data.get('headquarters')
                                self.founded = data.get('founded')
                                self.website = data.get('website')
                                self.specialties = data.get('specialties')
                                self.confidence_score = data.get('llm_enrichment', {}).get('confidence_score', 0)
                                self.data_sources = ['enhanced_llm']
                                self.processing_time = data.get('llm_enrichment', {}).get('processing_time', 0)
                        
                        llm_result = MockResult(llm_result)
                    
                    logger.info(f"Enhanced LLM result for {request.domain}: confidence {llm_result.confidence_score}%")
                    if llm_result and llm_result.confidence_score > 0.3:
                        # Merge enhanced LLM data with existing data
                        if hasattr(llm_result, 'name'):  # Enhanced result object
                            llm_dict = {
                                "company_name": llm_result.name,
                                "description": llm_result.description,
                                "industry": llm_result.industry,
                                "employee_count": llm_result.employee_count,
                                "headquarters": llm_result.headquarters,
                                "founded": llm_result.founded,
                                "website": llm_result.website,
                                "products_services": llm_result.products_services
                            }
                        else:  # Mock result object
                            llm_dict = {
                                "company_name": llm_result.company_name,
                                "description": llm_result.description,
                                "industry": llm_result.industry,
                                "employee_count": llm_result.employee_count,
                                "headquarters": llm_result.headquarters,
                                "founded": llm_result.founded,
                                "website": llm_result.website,
                                "specialties": llm_result.specialties
                            }
                        
                        for key, value in llm_dict.items():
                            if value and (key not in response_data or not response_data[key]):
                                response_data[key] = value
                        
                        # Add enhanced enrichment source
                        if "enrichment_source" not in response_data:
                            response_data["enrichment_source"] = "enhanced_llm"
                        else:
                            response_data["enrichment_source"] += ",enhanced_llm"
                        
                        response_data["llm_enrichment"] = {
                            "confidence_score": llm_result.confidence_score,
                            "data_sources": getattr(llm_result, 'data_sources', ['enhanced_llm']),
                            "processing_time": llm_result.processing_time
                        }
                        
                        logger.info(f"Enhanced LLM enrichment completed successfully for {request.domain}")
                except Exception as e:
                    logger.error(f"Error using Enhanced LLM Enrichment Agent: {e}")
                    # Não definir erro no response_data para continuar com os dados que já temos
            
        # Verificar erros do Firecrawl ou Crawl4AI
        if result.get("firecrawl_error") or result.get("crawl4ai_error") or ("error" in response_data and "firecrawl" in response_data["error"].lower()):
            if not response_data.get("error"):
                error_msg = result.get("firecrawl_error") or result.get("crawl4ai_error")
                response_data["error"] = f"Crawling error: {error_msg}"
            response_data["enrich"] = False
            
        # Processar dados de redes sociais
        social_fields = ["instagram", "linkedin", "whatsapp", "facebook", "twitter", "youtube", "tiktok"]
        
        # Inicializar campos de redes sociais se não existirem ou estiverem vazios
        for social_field in social_fields:
            if social_field not in response_data or not response_data[social_field]:
                response_data[social_field] = {}
        
        for social_field in social_fields:
            if social_field in response_data and isinstance(response_data[social_field], dict):
                social_data = response_data[social_field]
                
                # Processar campos que podem ser strings representando dicionários
                items_to_update = {}
                for key, value in social_data.items():
                    if isinstance(value, str) and value.startswith('{') and value.endswith('}'):
                        try:
                            import ast
                            import json
                            try:
                                obj_dict = ast.literal_eval(value)
                            except:
                                try:
                                    obj_dict = json.loads(value)
                                except:
                                    obj_dict = None
                                    
                            if isinstance(obj_dict, dict):
                                if len(obj_dict) == 1 and key in obj_dict:
                                    # Se o dicionário tem apenas uma chave igual ao campo atual
                                    items_to_update[key] = obj_dict[key]
                                else:
                                    # Se o dicionário tem múltiplas chaves, mesclar com o objeto atual
                                    for sub_key, sub_value in obj_dict.items():
                                        items_to_update[sub_key] = sub_value
                        except Exception as e:
                            print(f"Error processing {social_field}.{key} field: {e}")
                            pass
                
                # Atualizar o dicionário após a iteração
                social_data.update(items_to_update)
                
                # Verificar se temos URLs nos logs do extrator para este campo
                if social_field == "instagram":
                    # Verificar se temos username mas não URL
                    if ("username" in social_data or "user" in social_data) and not social_data.get("url"):
                        username = social_data.get("username") or social_data.get("user")
                        if username:
                            social_data["url"] = f"https://www.instagram.com/{username}/"
                            
                elif social_field == "whatsapp":
                    # Verificar se temos phone mas não URL
                    if "phone" in social_data and not social_data.get("url"):
                        phone = social_data["phone"]
                        # Remover caracteres não numéricos, mantendo o +
                        clean_phone = re.sub(r'[^\d+]', '', phone)
                        # Garantir que o número tenha pelo menos 10 dígitos
                        if len(clean_phone.replace('+', '')) >= 10:
                            social_data["url"] = f"https://wa.me/{clean_phone}"
                    
                    # Verificar se temos números de WhatsApp extraídos do contact_info
                    if "contact_info" in response_data and isinstance(response_data["contact_info"], dict):
                        whatsapp_numbers = response_data["contact_info"].get("whatsapp_numbers", [])
                        if whatsapp_numbers and not social_data.get("url"):
                            # Usar o primeiro número válido encontrado
                            for number in whatsapp_numbers:
                                clean_number = re.sub(r'[^\d+]', '', number)
                                if len(clean_number.replace('+', '')) >= 10:
                                    social_data["phone"] = clean_number
                                    social_data["url"] = f"https://wa.me/{clean_number}"
                                    break
                
                # Manter os dados no campo específico da rede social
                response_data[social_field] = social_data
                            
        # Gerar URLs padrão para Instagram e LinkedIn se não existirem
        try:
            domain = request.domain.replace('www.', '').split('.')[0]
            
            # Atualizar URLs vazias com valores padrão baseados no domínio
            if 'instagram' in response_data and isinstance(response_data['instagram'], dict):
                if not response_data['instagram'].get('url') or response_data['instagram']['url'] == '':
                    response_data['instagram']['url'] = f"https://www.instagram.com/{domain}"
                    
            if 'linkedin_data' in response_data and isinstance(response_data['linkedin_data'], dict):
                if not response_data['linkedin_data'].get('url') or response_data['linkedin_data']['url'] == '':
                    response_data['linkedin_data']['url'] = f"https://www.linkedin.com/company/{domain}"
                    
        except Exception as e:
            logger.error(f"Error generating default URLs: {e}")
        
        # Transferir dados de localização do LinkedIn para o objeto principal
        if 'linkedin_data' in response_data and isinstance(response_data['linkedin_data'], dict):
            linkedin_location = response_data['linkedin_data'].get('location')
            if linkedin_location and not response_data.get('location'):
                response_data['location'] = linkedin_location
        
        # Step 4: Integrate social media and Brave Search data
        if social_media_data:
            # Merge social media data
            for platform, data in social_media_data.items():
                if platform != 'confidence_score' and platform != 'processing_time':
                    if platform not in response_data or not response_data[platform]:
                        response_data[platform] = data
            
            # Add social media metadata
            response_data['social_media_extraction'] = {
                'confidence_score': social_media_data.get('confidence_score', 0),
                'processing_time': social_media_data.get('processing_time', 0)
            }
        
        if brave_search_data:
            # Merge Brave Search data
            for key, value in brave_search_data.items():
                if key not in ['linkedin_url', 'confidence_score', 'processing_time'] and value:
                    if key not in response_data or not response_data[key]:
                        response_data[key] = value
            
            # Add Brave Search metadata
            response_data['brave_search_data'] = {
                'confidence_score': brave_search_data.get('confidence_score', 0),
                'processing_time': brave_search_data.get('processing_time', 0),
                'linkedin_url_found': linkedin_url_from_search
            }
        
        # Calculate overall confidence score
        confidence_scores = []
        if social_media_data.get('confidence_score'):
            confidence_scores.append(social_media_data['confidence_score'])
        if brave_search_data.get('confidence_score'):
            confidence_scores.append(brave_search_data['confidence_score'])
        if response_data.get('llm_enrichment', {}).get('confidence_score'):
            confidence_scores.append(response_data['llm_enrichment']['confidence_score'])
        
        if confidence_scores:
            response_data['overall_confidence_score'] = sum(confidence_scores) / len(confidence_scores)
        
        # Add processing time
        response_data['total_processing_time'] = time.time() - start_time
        
        # Update enrichment source
        sources = []
        if social_media_data:
            sources.append('social_media_extractor')
        if brave_search_data:
            sources.append('brave_search')
        if response_data.get('enrichment_source'):
            sources.append(response_data['enrichment_source'])
        
        if sources:
            response_data['enrichment_source'] = ','.join(sources)
        
        # Definir enrich como True se não houver erro
        if not response_data.get("error"):
            response_data["enrich"] = True
        else:
            response_data["enrich"] = False
            
        logger.info(f"Super enrichment completed for {request.domain} in {time.time() - start_time:.2f}s")
        return response_data
        
    except Exception as e:
        logger.error(f"Error enriching company {request.domain}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/v1/enrich/person", response_model=PersonResponse)
async def enrich_person(request: PersonRequest):
    try:
        result = await person_enrichment_service.enrich_person(request.model_dump())
        return result
    except Exception as e:
        logger.error(f"Error enriching person: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

app.include_router(auth_router)
app.include_router(scrapp_router)


# Configuração do Sentry
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