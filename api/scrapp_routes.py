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
        
        # Fazer scraping usando o serviço especializado
        result = await instagram_scraper.scrape_profile(normalized_url)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Retornar dados extraídos
        return {
            "username": result.get("username"),
            "name": result.get("name"),
            "bio": result.get("bio"),
            "posts_count": result.get("posts"),
            "reels_count": result.get("reels"),
            "followers": result.get("followers"),
            "following": result.get("following"),
            "email": result.get("email"),
            "phone": result.get("phone"),
            "website": result.get("website"),
            "location": result.get("location"),
            "business_category": result.get("business_category"),
            "profile_url": normalized_url
        }
    except Exception as e:
        logger.error(f"Erro ao fazer scraping do Instagram: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar a requisição: {str(e)}")

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
            
            if not result.success or not result.html:
                # Tentar com Firecrawl como fallback
                html_content = firecrawl_client.scrape_url(url)
                if not html_content or isinstance(html_content, str) and not html_content.strip():
                    raise HTTPException(status_code=500, detail="Falha ao extrair dados do LinkedIn")
            else:
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
            
            # Extrair dados estruturados
            structured_data = firecrawl_client.extract_structured_data_from_html(html_content, schema)
            
            # Adicionar URL original
            structured_data["profile_url"] = url
            
            return structured_data
            
    except Exception as e:
        logger.error(f"Erro ao fazer scraping do LinkedIn: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar a requisição: {str(e)}")

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
        
        # Fazer scraping usando Firecrawl
        html_content = firecrawl_client.scrape_url(url)
        
        if not html_content:
            raise HTTPException(status_code=500, detail="Falha ao extrair dados do Reddit")
        
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
        
        # Extrair dados estruturados
        structured_data = firecrawl_client.extract_structured_data_from_html(html_content, schema)
        
        # Adicionar URL original
        structured_data["url"] = url
        
        return structured_data
        
    except Exception as e:
        logger.error(f"Erro ao fazer scraping do Reddit: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar a requisição: {str(e)}")