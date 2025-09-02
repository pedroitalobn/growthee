from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any, Optional
from pydantic import BaseModel, HttpUrl
from .services.hyperbrowser_instagram_scraper import HyperbrowserInstagramScraperService
from .log_service import LogService
from .firecrawl_client import FirecrawlApp
import logging
import re

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicialização do router
router = APIRouter(prefix="/scrapp", tags=["scrapp"])

# Inicialização dos serviços
log_service = LogService()
instagram_scraper = HyperbrowserInstagramScraperService(log_service=log_service)
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
    url: HttpUrl

class LinkedInScrapeRequest(BaseModel):
    url: HttpUrl

class RedditScrapeRequest(BaseModel):
    url: HttpUrl

@router.post("/instagram", response_model=Dict[str, Any])
async def scrape_instagram(request: InstagramScrapeRequest):
    """Endpoint para extrair dados de perfis do Instagram"""
    try:
        # Extrair username da URL
        url = str(request.url)
        username = re.search(r'instagram\.com/([^/?]+)', url)
        if not username:
            raise HTTPException(status_code=400, detail="URL inválida do Instagram")
        
        # Normalizar URL
        normalized_url = f"https://www.instagram.com/{username.group(1)}/"
        
        # Inicializar resultado padrão
        result_data = {"profile_url": normalized_url, "username": username.group(1)}
        
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
        
        try:
            # Primeiro tentar com Crawl4AI
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
                        structured_data = firecrawl_client.extract_structured_data_from_html(html_content, instagram_schema, use_deepseek=True)
                        
                        if "error" not in structured_data:
                            # Processar dados numéricos
                            structured_data["followers_count"] = _convert_to_int(structured_data.get("followers"))
                            structured_data["following_count"] = _convert_to_int(structured_data.get("following"))
                            structured_data["posts_count"] = _convert_to_int(structured_data.get("posts"))
                            
                            # Adicionar URL original
                            structured_data["profile_url"] = normalized_url
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
            
            # Se Crawl4AI falhar, tentar com Firecrawl
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
                    return structured_data
                else:
                    logger.error(f"Erro na extração estruturada com Firecrawl V2: {structured_data.get('error')}")
                    result_data["error"] = structured_data.get("error")
                    
                    # Tentar com scrape_url + extract_structured_data_from_html como fallback
                    try:
                        html_content = firecrawl_client.scrape_url(normalized_url)
                        
                        if html_content and isinstance(html_content, str) and html_content.strip():
                            # Extrair dados estruturados do HTML
                            html_structured_data = firecrawl_client.extract_structured_data_from_html(html_content, instagram_schema, use_deepseek=True)
                            
                            if "error" not in html_structured_data:
                                # Processar dados numéricos
                                html_structured_data["followers_count"] = _convert_to_int(html_structured_data.get("followers"))
                                html_structured_data["following_count"] = _convert_to_int(html_structured_data.get("following"))
                                html_structured_data["posts_count"] = _convert_to_int(html_structured_data.get("posts"))
                                
                                # Adicionar URL original
                                html_structured_data["profile_url"] = normalized_url
                                return html_structured_data
                        else:
                            logger.error("Falha ao extrair HTML com Firecrawl")
                    except Exception as html_extract_error:
                        logger.error(f"Erro no fallback de extração HTML: {str(html_extract_error)}")
            except Exception as firecrawl_error:
                logger.error(f"Erro no Firecrawl: {str(firecrawl_error)}")
                result_data["error"] = f"Erro no Firecrawl: {str(firecrawl_error)}"
            
            # Se ambos falharem, tentar com Hyperbrowser como último recurso
            try:
                # Usar o serviço especializado de scraping do Instagram
                instagram_data = await instagram_scraper.scrape_profile(normalized_url)
                
                if instagram_data and "error" not in instagram_data:
                    # Processar dados numéricos
                    instagram_data["followers_count"] = _convert_to_int(instagram_data.get("followers"))
                    instagram_data["following_count"] = _convert_to_int(instagram_data.get("following"))
                    instagram_data["posts_count"] = _convert_to_int(instagram_data.get("posts"))
                    
                    # Adicionar URL original
                    instagram_data["profile_url"] = normalized_url
                    return instagram_data
                else:
                    logger.error(f"Erro no scraper especializado do Instagram: {instagram_data.get('error')}")
                    result_data["error"] = instagram_data.get("error")
            except Exception as instagram_scraper_error:
                logger.error(f"Erro no scraper especializado do Instagram: {str(instagram_scraper_error)}")
                result_data["error"] = f"Erro no scraper especializado do Instagram: {str(instagram_scraper_error)}"
             
             # Retornar os dados coletados até agora, mesmo que incompletos
            return result_data
        except Exception as e:
                logger.error(f"Erro geral na extração de dados do Instagram: {str(e)}")
                result_data["error"] = f"Erro geral na extração de dados do Instagram: {str(e)}"
                return result_data
    except Exception as outer_e:
        logger.error(f"Erro crítico na rota de Instagram: {str(outer_e)}")
        return {
                    "username": None,
                    "name": None,
                    "bio": None,
                    "posts_count": None,
                    "followers": None,
                    "following": None,
                    "email": None,
                    "phone": None,
                    "website": None,
                    "location": None,
                    "business_category": None,
                    "profile_url": url,
                    "error": f"Erro crítico na rota de Instagram: {str(outer_e)}"
                }
                # Fim da implementação

@router.post("/linkedin", response_model=Dict[str, Any])
async def scrape_linkedin(request: LinkedInScrapeRequest):
    """Endpoint para extrair dados de perfis/empresas do LinkedIn"""
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
                        structured_data = firecrawl_client.extract_structured_data(url, schema, use_deepseek=True)
                        
                        if "error" not in structured_data:
                            # Adicionar URL original
                            structured_data["profile_url"] = url
                            return structured_data
                        else:
                            # Tentar extrair dados estruturados do HTML com Firecrawl
                            logger.info(f"Tentando extrair dados do HTML com Firecrawl após falha na extração direta")
                            structured_data = firecrawl_client.extract_structured_data_from_html(html_content, schema, use_deepseek=True)
                            
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
async def scrape_reddit(request: RedditScrapeRequest):
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