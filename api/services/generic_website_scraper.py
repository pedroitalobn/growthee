from typing import Dict, Any, Optional, List, Union
import os
import re
import json
import logging
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

from ..firecrawl_client import FirecrawlApp
from ..log_service import LogService

class GenericWebsiteScraperService:
    """Serviço genérico para scraping de websites usando Firecrawl e Crawl4AI"""
    
    def __init__(self, log_service: LogService = None, firecrawl_api_key: str = None):
        """Inicializa o serviço de scraping genérico"""
        self.log_service = log_service or LogService()
        self.firecrawl_api_key = firecrawl_api_key or os.getenv("FIRECRAWL_API_KEY")
        self.firecrawl_client = FirecrawlApp(api_key=self.firecrawl_api_key) if self.firecrawl_api_key else None
        
    def normalize_url(self, url: str) -> str:
        """Normaliza a URL para garantir formato correto"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url.rstrip('/')
    
    async def scrape_website(self, url: str, extraction_schema: Dict[str, Any] = None, 
                           use_firecrawl: bool = True, use_crawl4ai: bool = True,
                           extract_links: bool = False, extract_images: bool = False) -> Dict[str, Any]:
        """Scraping genérico de website com múltiplas estratégias"""
        try:
            normalized_url = self.normalize_url(url)
            
            self.log_service.log_debug("Iniciando scraping genérico", {
                "url": normalized_url,
                "use_firecrawl": use_firecrawl,
                "use_crawl4ai": use_crawl4ai,
                "has_schema": extraction_schema is not None
            })
            
            result_data = {
                "url": normalized_url,
                "success": False,
                "data": {},
                "metadata": {}
            }
            
            # Tentar com Firecrawl primeiro
            if use_firecrawl and self.firecrawl_client:
                firecrawl_result = await self._scrape_with_firecrawl(
                    normalized_url, extraction_schema, extract_links, extract_images
                )
                if firecrawl_result and "error" not in firecrawl_result:
                    result_data["data"] = firecrawl_result
                    result_data["success"] = True
                    result_data["method"] = "firecrawl"
                    return result_data
                else:
                    self.log_service.log_debug(f"Firecrawl falhou: {firecrawl_result.get('error', 'Unknown error')}")
            
            # Fallback para Crawl4AI
            if use_crawl4ai:
                crawl4ai_result = await self._scrape_with_crawl4ai(
                    normalized_url, extraction_schema, extract_links, extract_images
                )
                if crawl4ai_result and "error" not in crawl4ai_result:
                    result_data["data"] = crawl4ai_result
                    result_data["success"] = True
                    result_data["method"] = "crawl4ai"
                    return result_data
                else:
                    self.log_service.log_debug(f"Crawl4AI falhou: {crawl4ai_result.get('error', 'Unknown error')}")
            
            # Se ambos falharam
            result_data["error"] = "Todos os métodos de scraping falharam"
            return result_data
            
        except Exception as e:
            self.log_service.log_error(f"Erro no scraping genérico: {str(e)}")
            return {
                "url": url,
                "success": False,
                "error": str(e)
            }
    
    async def _scrape_with_firecrawl(self, url: str, extraction_schema: Dict[str, Any] = None,
                                   extract_links: bool = False, extract_images: bool = False) -> Dict[str, Any]:
        """Scraping usando Firecrawl com extração estruturada opcional"""
        try:
            # Se temos um schema, usar extração estruturada
            if extraction_schema:
                structured_data = self.firecrawl_client.extract_structured_data(url, extraction_schema)
                if "error" not in structured_data:
                    return structured_data
            
            # Scraping básico
            scrape_params = {
                'formats': ['html', 'markdown'],
                'includeTags': ['div', 'span', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'img', 'meta', 'title'],
                'excludeTags': ['script', 'style', 'nav', 'footer', 'aside'],
                'waitFor': 3000,
                'timeout': 30000
            }
            
            result = self.firecrawl_client.scrape_url(url, scrape_params)
            
            if "error" in result:
                return result
            
            # Processar resultado
            processed_data = {
                "title": self._extract_title(result.get('html', '')),
                "content": result.get('markdown', ''),
                "html": result.get('html', ''),
                "metadata": result.get('metadata', {})
            }
            
            # Extrair links se solicitado
            if extract_links:
                processed_data["links"] = self._extract_links(result.get('html', ''), url)
            
            # Extrair imagens se solicitado
            if extract_images:
                processed_data["images"] = self._extract_images(result.get('html', ''), url)
            
            return processed_data
            
        except Exception as e:
            self.log_service.log_error(f"Erro no Firecrawl: {str(e)}")
            return {"error": str(e)}
    
    async def _scrape_with_crawl4ai(self, url: str, extraction_schema: Dict[str, Any] = None,
                                  extract_links: bool = False, extract_images: bool = False) -> Dict[str, Any]:
        """Scraping usando Crawl4AI como fallback"""
        try:
            from crawl4ai import AsyncWebCrawler
            
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(
                    url=url,
                    word_count_threshold=10,
                    bypass_cache=True,
                    wait_for="networkidle",
                    delay_before_return_html=3.0,
                    page_timeout=30000,
                    js_code=[
                        "window.scrollTo(0, document.body.scrollHeight/3);",
                        "await new Promise(resolve => setTimeout(resolve, 1000));",
                        "window.scrollTo(0, document.body.scrollHeight/2);",
                        "await new Promise(resolve => setTimeout(resolve, 1000));"
                    ]
                )
                
                if not result.success:
                    return {"error": "Crawl4AI failed to scrape the page"}
                
                # Processar resultado
                processed_data = {
                    "title": self._extract_title(result.html),
                    "content": result.markdown,
                    "html": result.html,
                    "metadata": {
                        "status_code": result.status_code,
                        "response_headers": dict(result.response_headers) if result.response_headers else {}
                    }
                }
                
                # Extrair links se solicitado
                if extract_links:
                    processed_data["links"] = self._extract_links(result.html, url)
                
                # Extrair imagens se solicitado
                if extract_images:
                    processed_data["images"] = self._extract_images(result.html, url)
                
                # Se temos um schema, tentar extração estruturada básica
                if extraction_schema:
                    structured_data = self._extract_structured_from_html(result.html, extraction_schema)
                    processed_data["structured_data"] = structured_data
                
                return processed_data
                
        except Exception as e:
            self.log_service.log_error(f"Erro no Crawl4AI: {str(e)}")
            return {"error": str(e)}
    
    def _extract_title(self, html_content: str) -> str:
        """Extrai o título da página"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Tentar diferentes seletores para o título
            title_selectors = [
                'title',
                'h1',
                '[property="og:title"]',
                '[name="twitter:title"]',
                '.title',
                '#title'
            ]
            
            for selector in title_selectors:
                element = soup.select_one(selector)
                if element:
                    title = element.get('content') if element.get('content') else element.get_text(strip=True)
                    if title:
                        return title
            
            return "Título não encontrado"
            
        except Exception:
            return "Erro ao extrair título"
    
    def _extract_links(self, html_content: str, base_url: str) -> List[Dict[str, str]]:
        """Extrai todos os links da página"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            links = []
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text(strip=True)
                
                # Converter links relativos em absolutos
                if href.startswith('/'):
                    href = urljoin(base_url, href)
                elif not href.startswith(('http://', 'https://')):
                    href = urljoin(base_url, href)
                
                links.append({
                    "url": href,
                    "text": text,
                    "title": link.get('title', '')
                })
            
            return links
            
        except Exception as e:
            self.log_service.log_error(f"Erro ao extrair links: {str(e)}")
            return []
    
    def _extract_images(self, html_content: str, base_url: str) -> List[Dict[str, str]]:
        """Extrai todas as imagens da página"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            images = []
            
            for img in soup.find_all('img', src=True):
                src = img['src']
                alt = img.get('alt', '')
                
                # Converter URLs relativos em absolutos
                if src.startswith('/'):
                    src = urljoin(base_url, src)
                elif not src.startswith(('http://', 'https://')):
                    src = urljoin(base_url, src)
                
                images.append({
                    "url": src,
                    "alt": alt,
                    "title": img.get('title', '')
                })
            
            return images
            
        except Exception as e:
            self.log_service.log_error(f"Erro ao extrair imagens: {str(e)}")
            return []
    
    def _extract_structured_from_html(self, html_content: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extração estruturada básica usando BeautifulSoup e regex"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            extracted_data = {}
            
            # Extrações básicas comuns
            basic_extractions = {
                "title": self._extract_title(html_content),
                "description": self._extract_meta_description(soup),
                "keywords": self._extract_meta_keywords(soup),
                "author": self._extract_author(soup),
                "published_date": self._extract_published_date(soup),
                "language": self._extract_language(soup)
            }
            
            # Adicionar extrações básicas se estão no schema
            for key, value in basic_extractions.items():
                if key in schema.get('properties', {}) and value:
                    extracted_data[key] = value
            
            return extracted_data
            
        except Exception as e:
            self.log_service.log_error(f"Erro na extração estruturada: {str(e)}")
            return {}
    
    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        """Extrai meta description"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            return meta_desc.get('content', '')
        
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc:
            return og_desc.get('content', '')
        
        return ''
    
    def _extract_meta_keywords(self, soup: BeautifulSoup) -> str:
        """Extrai meta keywords"""
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            return meta_keywords.get('content', '')
        return ''
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extrai autor da página"""
        author_selectors = [
            'meta[name="author"]',
            'meta[property="article:author"]',
            '.author',
            '.byline',
            '[rel="author"]'
        ]
        
        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                author = element.get('content') if element.get('content') else element.get_text(strip=True)
                if author:
                    return author
        
        return ''
    
    def _extract_published_date(self, soup: BeautifulSoup) -> str:
        """Extrai data de publicação"""
        date_selectors = [
            'meta[property="article:published_time"]',
            'meta[name="publish_date"]',
            'time[datetime]',
            '.published',
            '.date'
        ]
        
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                date = element.get('content') or element.get('datetime') or element.get_text(strip=True)
                if date:
                    return date
        
        return ''
    
    def _extract_language(self, soup: BeautifulSoup) -> str:
        """Extrai idioma da página"""
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            return html_tag.get('lang')
        
        meta_lang = soup.find('meta', attrs={'http-equiv': 'content-language'})
        if meta_lang:
            return meta_lang.get('content', '')
        
        return ''