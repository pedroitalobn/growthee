from fastapi import APIRouter, HTTPException, Depends, Request, Response
from typing import Dict, Any, Optional
from pydantic import BaseModel, HttpUrl, model_validator
from .services.hyperbrowser_instagram_scraper import HyperbrowserInstagramScraperService
from .services.tiktok_scraper import TikTokScraperService
from .services.generic_website_scraper import GenericWebsiteScraperService
from .services.google_maps_scraper import GoogleMapsScraperService
from .services.whatsapp_scraper import WhatsAppScraperService
from .log_service import LogService
from .firecrawl_client import FirecrawlApp
from .middleware import require_credits
from .mcp_client import run_mcp
import logging
import re
import asyncio

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicialização do router
router = APIRouter(prefix="/scrapp", tags=["scrapp"])

# Inicialização dos serviços
log_service = LogService()
instagram_scraper = HyperbrowserInstagramScraperService(log_service=log_service)
generic_scraper = GenericWebsiteScraperService(log_service=log_service)
google_maps_scraper = GoogleMapsScraperService(log_service=log_service)
whatsapp_scraper = WhatsAppScraperService(log_service=log_service)
firecrawl_client = FirecrawlApp()

# Função auxiliar para converter strings de números para inteiros
def _convert_to_int(value: Optional[str]) -> Optional[int]:
    """Converte strings de números (ex: '1.2k', '3,400') para inteiros"""
    if not value or not isinstance(value, str):
        return None
        
    try:
        # Remover caracteres não numéricos, exceto pontos e vírgulas
        clean_value = re.sub(r'[^0-9.,]', '', value)
        
        # Converter abreviações como 'k', 'm'
        if 'k' in value.lower():
            # Converter para milhares
            multiplier = 1000
            clean_value = clean_value.replace(',', '.')
        elif 'm' in value.lower():
            # Converter para milhões
            multiplier = 1000000
            clean_value = clean_value.replace(',', '.')
        else:
            # Número normal
            multiplier = 1
            clean_value = clean_value.replace(',', '')
        
        # Converter para float e depois para int
        return int(float(clean_value) * multiplier)
        
    except (ValueError, TypeError):
        return None

# Modelos de dados
class InstagramScrapeRequest(BaseModel):
    url: Optional[HttpUrl] = None
    username: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_input(self):
        if not self.url and not self.username:
            raise ValueError('Deve fornecer url ou username')
        return self

class LinkedInScrapeRequest(BaseModel):
    url: HttpUrl

class GenericWebsiteScrapeRequest(BaseModel):
    url: HttpUrl
    extraction_schema: Optional[Dict[str, Any]] = None
    use_firecrawl: bool = True
    use_crawl4ai: bool = True
    extract_links: bool = False
    extract_images: bool = False

class GoogleMapsScrapeRequest(BaseModel):
    url: HttpUrl
    use_hyperbrowser: bool = True

class GoogleMapsSearchRequest(BaseModel):
    business_name: str
    location: Optional[str] = None
    use_hyperbrowser: bool = True

class WhatsAppScrapeRequest(BaseModel):
    url: HttpUrl
    use_hyperbrowser: bool = True

class WhatsAppSearchRequest(BaseModel):
    business_name: str
    location: Optional[str] = None
    use_hyperbrowser: bool = True

class RedditScrapeRequest(BaseModel):
    url: HttpUrl

@router.post("/instagram", response_model=Dict[str, Any])
async def scrape_instagram(request: InstagramScrapeRequest, req: Request, response: Response, auth_data: dict = Depends(require_credits)):
    """Endpoint para extrair dados de perfis do Instagram"""
    return await _scrape_instagram_internal(request, req, response)

@router.post("/instagram/test", response_model=Dict[str, Any])
async def scrape_instagram_test(request: InstagramScrapeRequest, req: Request, response: Response):
    """Endpoint de teste para extrair dados de perfis do Instagram (sem autenticação)"""
    return await _scrape_instagram_internal(request, req, response)

class TikTokRequest(BaseModel):
    url: HttpUrl

@router.post("/tiktok")
async def scrape_tiktok(request: TikTokRequest, user=Depends(require_credits)):
    """Endpoint para scraping de perfis do TikTok"""
    return await _scrape_tiktok_internal(str(request.url))

@router.post("/tiktok/test")
async def scrape_tiktok_test(request: TikTokRequest):
    """Endpoint de teste para scraping do TikTok sem autenticação"""
    return await _scrape_tiktok_internal(str(request.url))

async def _scrape_tiktok_internal(url: str):
    """Lógica interna de scraping do TikTok"""
    try:
        log_service = LogService()
        tiktok_scraper = TikTokScraperService(log_service)
        
        result = await tiktok_scraper.scrape_profile(url)
        
        if "error" in result:
            return {"success": False, "error": result["error"]}
        
        return {
            "success": True,
            "data": result,
            "source": "tiktok_scraper"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Erro interno no scraping do TikTok: {str(e)}"
        }

async def _scrape_instagram_internal(request: InstagramScrapeRequest, req: Request, response: Response):
    """Endpoint para extrair dados completos de perfis do Instagram incluindo contatos"""
    # Determinar username - pode vir da URL ou do campo username
    username_str = None
    
    if request.username:
        # Remove @ se presente
        username_str = request.username.lstrip('@')
    elif request.url:
        # Extrair username da URL
        import re as regex_module
        url = str(request.url)
        username_match = regex_module.search(r'instagram\.com/([^/?]+)', url)
        if username_match:
            username_str = username_match.group(1)
    
    if not username_str:
        raise HTTPException(status_code=400, detail="Username ou URL válida do Instagram é obrigatório")
    
    # Normalizar URL
    normalized_url = f"https://www.instagram.com/{username_str}/"
    
    # Usar o novo serviço aprimorado para extração completa
    try:
        from api.services.enhanced_instagram_scraper import EnhancedInstagramScraperService
        
        enhanced_scraper = EnhancedInstagramScraperService()
        result = await enhanced_scraper.scrape_profile_complete(normalized_url)
        
        if result.get("success"):
            data = result["data"]
            
            # Adicionar raw_markdown para compatibilidade
            final_data = {
                "success": True,
                "username": data.get("username", username_str),
                "name": data.get("name"),
                "bio": data.get("bio"),
                "followers": data.get("followers"),
                "following": data.get("following"),
                "posts": data.get("posts"),
                "followers_count": data.get("followers_count"),
                "following_count": data.get("following_count"),
                "posts_count": data.get("posts_count"),
                "email": data.get("email"),
                "phone": data.get("phone"),
                "whatsapp": data.get("whatsapp"),  # Campo específico para WhatsApp
                "website": data.get("website"),
                "location": data.get("location"),
                "business_category": data.get("business_category"),
                "profile_url": normalized_url,
                "url": normalized_url,
                "raw_markdown": result.get("raw_content", "")[:500]  # Para debug
            }
            
            logger.info(f"Enhanced Instagram data extracted successfully: {final_data.get('username')} - WhatsApp: {bool(final_data.get('whatsapp'))} - Email: {bool(final_data.get('email'))}")
            return final_data
        else:
            logger.error(f"Enhanced scraper failed: {result.get('error')}")
            # Fallback para o método anterior se o novo falhar
            pass
            
    except Exception as enhanced_error:
        logger.error(f"Enhanced scraper error: {str(enhanced_error)}")
        # Fallback para o método anterior
        pass
    
    # FALLBACK: Usar método anterior se o enhanced falhar
    # Inicializar resultado padrão
    result_data = {"profile_url": normalized_url, "username": username_str}
    
    # Definir schema para extração estruturada
    instagram_schema = {
        "type": "object",
        "properties": {
            "username": {"type": "string", "description": "Nome de usuário (@username) sem o @"},
            "name": {"type": "string", "description": "Nome de exibição do perfil"},
            "bio": {"type": "string", "description": "Biografia/descrição do perfil"},
            "followers": {"type": "string", "description": "Número de seguidores"},
            "following": {"type": "string", "description": "Número de pessoas seguindo"},
            "posts": {"type": "string", "description": "Número de posts"},
            "email": {"type": "string", "description": "Email encontrado na bio (se houver)"},
            "phone": {"type": "string", "description": "Telefone encontrado na bio (se houver)"},
            "website": {"type": "string", "description": "Website/link encontrado na bio (se houver)"},
            "location": {"type": "string", "description": "Localização mencionada na bio (se houver)"},
            "business_category": {"type": "string", "description": "Categoria do negócio (se for conta business)"}
        },
        "required": ["username", "name"]
    }
    
    # Usar Hyperbrowser com Claude agent para extração completa (método anterior)
    try:
        claude_result = await run_mcp(
            server_name="mcp.config.usrlocalmcp.Hyperbrowser",
            tool_name="scrape_webpage",
            args={
                "url": normalized_url,
                "outputFormat": ["markdown"]
            }
        )
        
        if claude_result and "result" in claude_result:
            # Parse the extracted data from Claude's response (markdown format)
            extracted_text = claude_result["result"]
            
            # Use regex and parsing to extract structured data
            import re
            
            # Extract follower count
            followers_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?[KMB]?)\s*(?:followers?|seguidores?)', extracted_text, re.IGNORECASE)
            followers = followers_match.group(1) if followers_match else None
            
            # Extract following count
            following_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?[KMB]?)\s*(?:following|seguindo)', extracted_text, re.IGNORECASE)
            following = following_match.group(1) if following_match else None
            
            # Extract posts count
            posts_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?[KMB]?)\s*(?:posts?|publicações?)', extracted_text, re.IGNORECASE)
            posts = posts_match.group(1) if posts_match else None
            
            # Extract email
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', extracted_text)
            email = email_match.group(1) if email_match else None
            
            # Extract phone
            phone_match = re.search(r'(\+?\d{1,4}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,9})', extracted_text)
            phone = phone_match.group(1) if phone_match else None
            
            # Extract website/URL
            url_match = re.search(r'(https?://[^\s]+|www\.[^\s]+)', extracted_text)
            website = url_match.group(1) if url_match else None
            
            # Extract name and bio from markdown content
            lines = extracted_text.split('\n')
            name = None
            bio = None
            
            # Try to extract name from markdown headers first
            header_match = re.search(r'^#+\s*([^\n]+)', extracted_text, re.MULTILINE)
            if header_match:
                name = header_match.group(1).strip()
            
            # Extract bio from non-header lines
            for i, line in enumerate(lines):
                line = line.strip()
                if line and not line.startswith('#') and not any(keyword in line.lower() for keyword in ['followers', 'following', 'posts', 'http']):
                    if not name and len(line) < 50:  # Likely the name if not found in headers
                        name = line
                    elif not bio and len(line) > 10:  # Likely the bio
                        bio = line
                        break
            
            final_data = {
                "success": True,
                "username": username_str,
                "name": name,
                "bio": bio,
                "followers": followers,
                "following": following,
                "posts": posts,
                "followers_count": _convert_to_int(followers) if followers else None,
                "following_count": _convert_to_int(following) if following else None,
                "posts_count": _convert_to_int(posts) if posts else None,
                "email": email,
                "phone": phone,
                "website": website,
                "location": None,
                "business_category": None,
                "profile_url": normalized_url,
                "url": normalized_url,
                "raw_markdown": extracted_text[:500]  # First 500 chars for debugging
            }
            
            logger.info(f"Instagram data extracted successfully with Hyperbrowser: {final_data.get('username')}")
            return final_data
        else:
            logger.error(f"Erro no Hyperbrowser: {claude_result.get('error') if claude_result else 'Dados não extraídos'}")
            result_data["error"] = claude_result.get("error") if claude_result else "Dados não extraídos pelo Hyperbrowser"
    except Exception as hyperbrowser_error:
        logger.error(f"Erro no Hyperbrowser: {str(hyperbrowser_error)}")
        result_data["error"] = f"Erro no Hyperbrowser: {str(hyperbrowser_error)}"
            
    # Se Hyperbrowser falhar, tentar com Firecrawl
    try:
        # Tentar extração estruturada diretamente com Firecrawl V2
        structured_data = firecrawl_client.extract_structured_data(
            normalized_url, 
            instagram_schema, 
            use_deepseek=True
        )
        
        if "error" not in structured_data:
            # Processar dados numéricos
            structured_data["followers_count"] = _convert_to_int(structured_data.get("followers"))
            structured_data["following_count"] = _convert_to_int(structured_data.get("following"))
            structured_data["posts_count"] = _convert_to_int(structured_data.get("posts"))
            
            # Adicionar URL original
            structured_data["profile_url"] = normalized_url
            structured_data["success"] = True
            return structured_data
        else:
            logger.error(f"Erro na extração estruturada com Firecrawl V2: {structured_data.get('error')}")
            result_data["error"] = structured_data.get("error")
    except Exception as firecrawl_error:
        logger.error(f"Erro no Firecrawl: {str(firecrawl_error)}")
        result_data["error"] = f"Erro no Firecrawl: {str(firecrawl_error)}"
            
    # Se ambos falharem, tentar com Crawl4AI como último recurso
    try:
        from crawl4ai import AsyncWebCrawler
        
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(
                url=normalized_url,
                word_count_threshold=10,
                bypass_cache=True,
                wait_for="css:.x9f619.x1n2onr6",  # Seletor comum em perfis do Instagram
                delay_before_return_html=5.0,
                page_timeout=45000,
                js_code=[
                    "window.scrollTo(0, document.body.scrollHeight/3);",
                    "await new Promise(resolve => setTimeout(resolve, 2000));",
                    "window.scrollTo(0, document.body.scrollHeight/2);",
                    "await new Promise(resolve => setTimeout(resolve, 2000));"
                ]
            )
            
            if result.success and result.html:
                html_content = result.html
                
                # Extrair dados estruturados usando Firecrawl com DeepSeek como LLM
                structured_data = firecrawl_client.extract_structured_data_from_html(html_content, instagram_schema)
                
                if "error" not in structured_data:
                    # Processar dados numéricos
                    structured_data["followers_count"] = _convert_to_int(structured_data.get("followers"))
                    structured_data["following_count"] = _convert_to_int(structured_data.get("following"))
                    structured_data["posts_count"] = _convert_to_int(structured_data.get("posts"))
                    
                    # Adicionar URL original
                    structured_data["profile_url"] = normalized_url
                    structured_data["success"] = True
                    return structured_data
                else:
                    logger.error(f"Erro na extração estruturada com Crawl4AI+Firecrawl: {structured_data['error']}")
                    result_data["error"] = structured_data["error"]
            else:
                logger.error("Falha ao extrair HTML com Crawl4AI")
                result_data["error"] = "Falha ao extrair HTML com Crawl4AI"
    except Exception as crawl4ai_error:
        logger.error(f"Erro no Crawl4AI: {str(crawl4ai_error)}")
        result_data["error"] = f"Erro no Crawl4AI: {str(crawl4ai_error)}"
    
    # Retornar os dados coletados até agora, mesmo que incompletos
    result_data["success"] = False
    return result_data

# Fim da implementação do Instagram

@router.post("/linkedin", response_model=Dict[str, Any])
async def scrape_linkedin(request: LinkedInScrapeRequest, req: Request, response: Response, auth_data: dict = Depends(require_credits)):
    """Endpoint para extrair dados de perfis/empresas do LinkedIn"""
    return await _scrape_linkedin_internal(request, req, response)

@router.post("/linkedin/test", response_model=Dict[str, Any])
async def scrape_linkedin_test(request: LinkedInScrapeRequest, req: Request, response: Response):
    """Endpoint de teste para extrair dados de perfis/empresas do LinkedIn (sem autenticação)"""
    return await _scrape_linkedin_internal(request, req, response)

async def _scrape_linkedin_internal(request: LinkedInScrapeRequest, req: Request, response: Response):
    """Lógica interna para scraping do LinkedIn"""
    try:
        # Implementação básica usando Crawl4AI
        from crawl4ai import AsyncWebCrawler
        
        url = str(request.url)
        
        # Verificar se é uma URL válida do LinkedIn
        if not re.search(r'linkedin\.com/(company|in)/', url):
            raise HTTPException(status_code=400, detail="URL inválida do LinkedIn")
        
        # Determinar se é perfil de pessoa ou empresa
        is_company = "/company/" in url
        
        # Configurar parâmetros específicos para o tipo de perfil
        wait_for = "css:.org-top-card-summary-info-list" if is_company else "css:.pv-top-card"
        
        # Inicializar resultado padrão
        result_data = {"profile_url": url}
        
        try:
            # Fazer scraping usando Crawl4AI
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(
                    url=url,
                    word_count_threshold=10,
                    bypass_cache=True,
                    wait_for=wait_for,
                    delay_before_return_html=5.0,
                    page_timeout=45000,
                    js_code=[
                        "window.scrollTo(0, document.body.scrollHeight/3);",
                        "await new Promise(resolve => setTimeout(resolve, 2000));",
                        "window.scrollTo(0, document.body.scrollHeight/2);",
                        "await new Promise(resolve => setTimeout(resolve, 2000));"
                    ]
                )
                
                if result.success and result.html:
                    html_content = result.html
                    
                    # Extrair dados estruturados usando Firecrawl
                    if is_company:
                        schema = {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Nome da empresa"},
                                "tagline": {"type": "string", "description": "Slogan ou descrição curta"},
                                "about": {"type": "string", "description": "Descrição completa da empresa"},
                                "website": {"type": "string", "description": "Website da empresa"},
                                "industry": {"type": "string", "description": "Indústria/setor da empresa"},
                                "company_size": {"type": "string", "description": "Tamanho da empresa (número de funcionários)"},
                                "headquarters": {"type": "string", "description": "Localização da sede"},
                                "founded": {"type": "string", "description": "Ano de fundação"},
                                "specialties": {"type": "array", "items": {"type": "string"}, "description": "Especialidades da empresa"}
                            }
                        }
                    else:
                        schema = {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Nome completo da pessoa"},
                                "headline": {"type": "string", "description": "Título profissional/headline"},
                                "location": {"type": "string", "description": "Localização"},
                                "about": {"type": "string", "description": "Descrição sobre a pessoa"},
                                "experience": {"type": "array", "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "company": {"type": "string"},
                                        "duration": {"type": "string"}
                                    }
                                }},
                                "education": {"type": "array", "items": {
                                    "type": "object",
                                    "properties": {
                                        "school": {"type": "string"},
                                        "degree": {"type": "string"},
                                        "field": {"type": "string"}
                                    }
                                }}
                            }
                        }
                    
                    try:
                        # Tentar extrair dados estruturados diretamente com Firecrawl V2
                        structured_data = firecrawl_client.extract_structured_data(url, schema)
                        
                        if "error" not in structured_data:
                            # Adicionar URL original
                            structured_data["profile_url"] = url
                            return structured_data
                        else:
                            # Tentar extrair dados estruturados do HTML com Firecrawl
                            logger.info(f"Tentando extrair dados do HTML com Firecrawl após falha na extração direta")
                            structured_data = firecrawl_client.extract_structured_data_from_html(html_content, schema)
                            
                            if "error" not in structured_data:
                                # Adicionar URL original
                                structured_data["profile_url"] = url
                                return structured_data
                            else:
                                # Registrar erro e continuar com dados básicos
                                logger.error(f"Erro na extração estruturada: {structured_data['error']}")
                                result_data["error"] = structured_data["error"]
                    except Exception as extract_error:
                        logger.error(f"Erro na extração estruturada: {str(extract_error)}")
                        result_data["error"] = f"Erro na extração estruturada: {str(extract_error)}"
                else:
                    logger.error("Falha ao extrair HTML com Crawl4AI")
                    result_data["error"] = "Falha ao extrair HTML com Crawl4AI"
        except Exception as crawl_error:
            logger.error(f"Erro no Crawl4AI: {str(crawl_error)}")
            result_data["error"] = f"Erro no Crawl4AI: {str(crawl_error)}"
        
        # Se chegou aqui, retornar os dados básicos com erro
        return result_data
            
    except Exception as e:
        logger.error(f"Erro ao fazer scraping do LinkedIn: {str(e)}")
        return {"error": f"Erro ao processar a requisição: {str(e)}", "profile_url": url}

@router.post("/reddit", response_model=Dict[str, Any])
async def scrape_reddit(request: RedditScrapeRequest, req: Request, response: Response, auth_data: dict = Depends(require_credits)):
    """Endpoint para extrair dados de perfis/posts do Reddit"""
    try:
        url = str(request.url)
        
        # Verificar se é uma URL válida do Reddit
        if not re.search(r'reddit\.com/(?:r|user)/', url):
            raise HTTPException(status_code=400, detail="URL inválida do Reddit")
        
        # Determinar se é subreddit, post ou perfil
        is_subreddit = "/r/" in url and not re.search(r'/comments/', url)
        is_post = re.search(r'/comments/', url) is not None
        is_user = "/user/" in url
        
        # Inicializar resultado padrão
        result_data = {"url": url}
        
        try:
            # Fazer scraping usando Firecrawl
            html_content = firecrawl_client.scrape_url(url)
            
            if html_content and isinstance(html_content, str) and html_content.strip():
                # Definir schema baseado no tipo de conteúdo
                if is_subreddit:
                    schema = {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Nome do subreddit"},
                            "description": {"type": "string", "description": "Descrição do subreddit"},
                            "members": {"type": "string", "description": "Número de membros"},
                            "online": {"type": "string", "description": "Número de usuários online"},
                            "created": {"type": "string", "description": "Data de criação"},
                            "rules": {"type": "array", "items": {"type": "string"}, "description": "Regras do subreddit"}
                        }
                    }
                elif is_post:
                    schema = {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Título do post"},
                            "author": {"type": "string", "description": "Autor do post"},
                            "content": {"type": "string", "description": "Conteúdo do post"},
                            "upvotes": {"type": "string", "description": "Número de upvotes"},
                            "comments_count": {"type": "string", "description": "Número de comentários"},
                            "posted_time": {"type": "string", "description": "Quando foi postado"},
                            "top_comments": {"type": "array", "items": {
                                "type": "object",
                                "properties": {
                                    "author": {"type": "string"},
                                    "content": {"type": "string"},
                                    "upvotes": {"type": "string"}
                                }
                            }}
                        }
                    }
                else:  # is_user
                    schema = {
                        "type": "object",
                        "properties": {
                            "username": {"type": "string", "description": "Nome de usuário"},
                            "karma": {"type": "string", "description": "Karma total"},
                            "cake_day": {"type": "string", "description": "Data de criação da conta"},
                            "description": {"type": "string", "description": "Descrição do perfil"},
                            "recent_posts": {"type": "array", "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "subreddit": {"type": "string"},
                                    "upvotes": {"type": "string"}
                                }
                            }}
                        }
                    }
                
                try:
                    # Tentar extrair dados estruturados diretamente com Firecrawl V2
                    structured_data = firecrawl_client.extract_structured_data(url, schema, use_deepseek=True)
                    
                    if "error" not in structured_data:
                        # Adicionar URL original
                        structured_data["url"] = url
                        return structured_data
                    else:
                        # Tentar extrair dados estruturados do HTML com Firecrawl
                        logger.info(f"Tentando extrair dados do HTML com Firecrawl após falha na extração direta")
                        structured_data = firecrawl_client.extract_structured_data_from_html(html_content, schema, use_deepseek=True)
                        
                        if "error" not in structured_data:
                            # Adicionar URL original
                            structured_data["url"] = url
                            return structured_data
                        else:
                            # Registrar erro e continuar com dados básicos
                            logger.error(f"Erro na extração estruturada: {structured_data['error']}")
                            result_data["error"] = structured_data["error"]
                except Exception as extract_error:
                    logger.error(f"Erro na extração estruturada: {str(extract_error)}")
                    result_data["error"] = f"Erro na extração estruturada: {str(extract_error)}"
            else:
                logger.error("Falha ao extrair HTML com Firecrawl")
                result_data["error"] = "Falha ao extrair HTML com Firecrawl"
        except Exception as scrape_error:
            logger.error(f"Erro no Firecrawl: {str(scrape_error)}")
            result_data["error"] = f"Erro no Firecrawl: {str(scrape_error)}"
        
        # Se chegou aqui, retornar os dados básicos com erro
        return result_data
        
    except Exception as e:
        logger.error(f"Erro ao fazer scraping do Reddit: {str(e)}")
        return {"error": f"Erro ao processar a requisição: {str(e)}", "url": url}

@router.post("/website", response_model=Dict[str, Any])
async def scrape_website(request: GenericWebsiteScrapeRequest, req: Request, response: Response, auth_data: dict = Depends(require_credits)):
    """Endpoint para scraping genérico de websites com autenticação"""
    return await _scrape_website_internal(request, req, response)

@router.post("/website/test", response_model=Dict[str, Any])
async def scrape_website_test(request: GenericWebsiteScrapeRequest, req: Request, response: Response):
    """Endpoint de teste para scraping genérico de websites sem autenticação"""
    return await _scrape_website_internal(request, req, response)

async def _scrape_website_internal(request: GenericWebsiteScrapeRequest, req: Request, response: Response):
    """Lógica interna para scraping genérico de websites"""
    try:
        url = str(request.url)
        logger.info(f"Iniciando scraping genérico para: {url}")
        
        # Configurações de scraping
        scrape_config = {
            'use_firecrawl': request.use_firecrawl,
            'use_crawl4ai': request.use_crawl4ai,
            'extract_links': request.extract_links,
            'extract_images': request.extract_images,
            'extraction_schema': request.extraction_schema
        }
        
        # Executar scraping
        result = await generic_scraper.scrape_website(url, **scrape_config)
        
        if result.get('success'):
            logger.info(f"Scraping genérico concluído com sucesso para: {url}")
            return {
                "success": True,
                "url": url,
                "data": result.get('data', {}),
                "metadata": result.get('metadata', {}),
                "links": result.get('links', []) if request.extract_links else [],
                "images": result.get('images', []) if request.extract_images else [],
                "structured_data": result.get('structured_data', {}) if request.extraction_schema else {}
            }
        else:
            logger.error(f"Falha no scraping genérico para: {url} - {result.get('error')}")
            return {
                "success": False,
                "url": url,
                "error": result.get('error', 'Erro desconhecido no scraping')
            }
            
    except Exception as e:
        logger.error(f"Erro no scraping genérico: {str(e)}")
        return {
            "success": False,
            "url": str(request.url),
            "error": f"Erro ao processar a requisição: {str(e)}"
        }

@router.post("/google-maps", response_model=Dict[str, Any])
async def scrape_google_maps(request: GoogleMapsScrapeRequest, req: Request, response: Response, auth_data: dict = Depends(require_credits)):
    """Endpoint para scraping de dados de empresas do Google Maps com autenticação"""
    return await _scrape_google_maps_internal(request, req, response)

@router.post("/google-maps/test", response_model=Dict[str, Any])
async def scrape_google_maps_test(request: GoogleMapsScrapeRequest, req: Request, response: Response):
    """Endpoint de teste para scraping do Google Maps sem autenticação"""
    return await _scrape_google_maps_internal(request, req, response)

@router.post("/google-maps/search", response_model=Dict[str, Any])
async def search_google_maps_business(request: GoogleMapsSearchRequest, req: Request, response: Response, auth_data: dict = Depends(require_credits)):
    """Endpoint para buscar empresas no Google Maps por nome com autenticação"""
    return await _search_google_maps_business_internal(request, req, response)

@router.post("/google-maps/search/test", response_model=Dict[str, Any])
async def search_google_maps_business_test(request: GoogleMapsSearchRequest, req: Request, response: Response):
    """Endpoint de teste para buscar empresas no Google Maps por nome sem autenticação"""
    return await _search_google_maps_business_internal(request, req, response)

async def _scrape_google_maps_internal(request: GoogleMapsScrapeRequest, req: Request, response: Response) -> Dict[str, Any]:
    """Lógica interna para scraping do Google Maps"""
    try:
        url = str(request.url)
        
        # Validar se é uma URL do Google Maps
        if not re.search(r'(maps\.google\.|google\.com/maps|maps\.app\.goo\.gl)', url):
            raise HTTPException(status_code=400, detail="URL inválida do Google Maps")
        
        # Fazer scraping usando o serviço
        result = await google_maps_scraper.scrape_google_maps_business(
            url=url,
            use_hyperbrowser=request.use_hyperbrowser
        )
        
        if result.get("success"):
            logger.info(f"Scraping do Google Maps bem-sucedido: {url}")
            return result
        else:
            logger.error(f"Falha no scraping do Google Maps: {result.get('error')}")
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no scraping do Google Maps: {str(e)}")
        return {
            "success": False,
            "url": str(request.url),
            "error": f"Erro ao processar a requisição: {str(e)}"
        }

async def _search_google_maps_business_internal(request: GoogleMapsSearchRequest, req: Request, response: Response) -> Dict[str, Any]:
    """Lógica interna para busca de empresas no Google Maps"""
    try:
        # Fazer busca usando o serviço
        result = await google_maps_scraper.search_business_by_name(
            business_name=request.business_name,
            location=request.location or ""
        )
        
        if result.get("success"):
            logger.info(f"Busca no Google Maps bem-sucedida: {request.business_name}")
            return result
        else:
            logger.error(f"Falha na busca do Google Maps: {result.get('error')}")
            return result
            
    except Exception as e:
        logger.error(f"Erro na busca do Google Maps: {str(e)}")
        return {
            "success": False,
            "query": request.business_name,
            "error": f"Erro ao processar a requisição: {str(e)}"
        }

# Endpoints do WhatsApp
@router.post("/whatsapp", response_model=Dict[str, Any])
async def scrape_whatsapp(request: WhatsAppScrapeRequest, req: Request, response: Response, auth_data: dict = Depends(require_credits)):
    return await _scrape_whatsapp_internal(request, req, response)

@router.post("/whatsapp/test", response_model=Dict[str, Any])
async def scrape_whatsapp_test(request: WhatsAppScrapeRequest, req: Request, response: Response):
    return await _scrape_whatsapp_internal(request, req, response)

@router.post("/whatsapp/search", response_model=Dict[str, Any])
async def search_whatsapp_business(request: WhatsAppSearchRequest, req: Request, response: Response, auth_data: dict = Depends(require_credits)):
    return await _search_whatsapp_business_internal(request, req, response)

@router.post("/whatsapp/search/test", response_model=Dict[str, Any])
async def search_whatsapp_business_test(request: WhatsAppSearchRequest, req: Request, response: Response):
    return await _search_whatsapp_business_internal(request, req, response)

async def _scrape_whatsapp_internal(request: WhatsAppScrapeRequest, req: Request, response: Response) -> Dict[str, Any]:
    """Lógica interna para scraping do WhatsApp"""
    try:
        url = str(request.url)
        
        # Validar se é uma URL válida do WhatsApp
        if not whatsapp_scraper.validate_whatsapp_url(url):
            raise HTTPException(status_code=400, detail="URL inválida do WhatsApp")
        
        # Fazer scraping usando o serviço
        result = await whatsapp_scraper.scrape_whatsapp_profile(
            url=url,
            use_hyperbrowser=request.use_hyperbrowser
        )
        
        if result.get("success"):
            logger.info(f"Scraping do WhatsApp bem-sucedido: {url}")
            return result
        else:
            logger.warning(f"Falha no scraping do WhatsApp: {result.get('error', 'Erro desconhecido')}")
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no scraping do WhatsApp: {str(e)}")
        return {
            "success": False,
            "error": f"Erro no scraping: {str(e)}",
            "url": str(request.url)
        }

async def _search_whatsapp_business_internal(request: WhatsAppSearchRequest, req: Request, response: Response) -> Dict[str, Any]:
    """Lógica interna para busca de WhatsApp Business"""
    try:
        # Fazer busca usando o serviço
        result = await whatsapp_scraper.search_whatsapp_business(
            business_name=request.business_name,
            location=request.location,
            use_hyperbrowser=request.use_hyperbrowser
        )
        
        if result.get("success"):
            logger.info(f"Busca do WhatsApp Business bem-sucedida: {request.business_name}")
            return result
        else:
            logger.warning(f"Falha na busca do WhatsApp Business: {result.get('error', 'Erro desconhecido')}")
            return result
            
    except Exception as e:
        logger.error(f"Erro na busca do WhatsApp Business: {str(e)}")
        return {
            "success": False,
            "error": f"Erro na busca: {str(e)}",
            "business_name": request.business_name
        }