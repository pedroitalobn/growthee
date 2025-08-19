import os
import logging
import asyncio
import time
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

import requests
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from firecrawl import FirecrawlApp
from thefuzz import fuzz
from bs4 import BeautifulSoup

from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from crawl4ai.chunking_strategy import RegexChunking

from .log_service import LogService
from .models import CompanyRequest, CompanyResponse, SocialMedia, Employee

class BraveSearchRateLimiter:
    """Rate limiter para API do Brave Search"""
    
    def __init__(self, requests_per_second: float = 1.0, requests_per_month: int = 2000):
        self.requests_per_second = requests_per_second
        self.requests_per_month = requests_per_month
        self.last_request_time = 0
        self.monthly_count_file = 'logs/brave_monthly_count.json'
        self._ensure_log_directory()
        
    def _ensure_log_directory(self):
        """Garante que o diretório de logs existe"""
        os.makedirs('logs', exist_ok=True)
        
    def _get_monthly_count(self) -> Dict[str, Any]:
        """Obtém contagem mensal de requisições"""
        try:
            if os.path.exists(self.monthly_count_file):
                with open(self.monthly_count_file, 'r') as f:
                    data = json.load(f)
                    
                # Verifica se é um novo mês
                current_month = datetime.now().strftime('%Y-%m')
                if data.get('month') != current_month:
                    return {'month': current_month, 'count': 0}
                    
                return data
            else:
                current_month = datetime.now().strftime('%Y-%m')
                return {'month': current_month, 'count': 0}
        except Exception:
            current_month = datetime.now().strftime('%Y-%m')
            return {'month': current_month, 'count': 0}
            
    def _save_monthly_count(self, data: Dict[str, Any]):
        """Salva contagem mensal de requisições"""
        try:
            with open(self.monthly_count_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logging.warning(f"Erro ao salvar contagem mensal: {e}")
            
    async def wait_if_needed(self) -> bool:
        """Aguarda se necessário para respeitar rate limits. Retorna False se limite mensal atingido."""
        # Verificar limite mensal
        monthly_data = self._get_monthly_count()
        if monthly_data['count'] >= self.requests_per_month:
            logging.warning(f"Limite mensal de {self.requests_per_month} requisições atingido")
            return False
            
        # Verificar limite por segundo
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 1.0 / self.requests_per_second
        
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            logging.info(f"Rate limiting: aguardando {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            
        self.last_request_time = time.time()
        
        # Incrementar contador mensal
        monthly_data['count'] += 1
        self._save_monthly_count(monthly_data)
        
        return True

class CrawlAIService:
    """Serviço de scraping avançado usando Crawl4AI para enriquecimento de dados"""
    
    def __init__(self, log_service: LogService):
        self.log_service = log_service
        self.crawler = None
        
    def _get_llm_config(self) -> Dict[str, str]:
        """Configura o provedor LLM dinamicamente baseado nas variáveis de ambiente"""
        # Prioridade: DeepSeek > OpenAI > Anthropic > Ollama
        if os.getenv("DEEPSEEK_API_KEY"):
            return {
                "provider": "openai/deepseek-chat",
                "api_token": os.getenv("DEEPSEEK_API_KEY"),
                "base_url": "https://api.deepseek.com"
            }
        elif os.getenv("OPENAI_API_KEY"):
            return {
                "provider": "openai/gpt-4o-mini",
                "api_token": os.getenv("OPENAI_API_KEY"),
                "base_url": None
            }
        elif os.getenv("ANTHROPIC_API_KEY"):
            return {
                "provider": "anthropic/claude-3-haiku-20240307",
                "api_token": os.getenv("ANTHROPIC_API_KEY"),
                "base_url": None
            }
        else:
            # Fallback para Ollama local
            return {
                "provider": "ollama/llama3.2",
                "api_token": None,
                "base_url": "http://localhost:11434"
            }
        
    async def __aenter__(self):
        """Context manager para inicializar o crawler"""
        self.crawler = AsyncWebCrawler(verbose=True)
        await self.crawler.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager para fechar o crawler"""
        if self.crawler:
            await self.crawler.__aexit__(exc_type, exc_val, exc_tb)
    
    async def scrape_company_website(self, url: str) -> Dict[str, Any]:
        """Scraping avançado de website de empresa usando Crawl4AI"""
        try:
            if not self.crawler:
                raise Exception("Crawler not initialized. Use async context manager.")
            
            # Obter configuração LLM dinâmica
            llm_config = self._get_llm_config()
            
            # Estratégia de extração LLM para dados de empresa
            extraction_strategy = LLMExtractionStrategy(
                provider=llm_config["provider"],
                api_token=llm_config["api_token"],
                base_url=llm_config["base_url"],
                schema={
                    "type": "object",
                    "properties": {
                        "company_name": {"type": "string", "description": "Nome oficial da empresa"},
                        "description": {"type": "string", "description": "Descrição detalhada da empresa"},
                        "industry": {"type": "string", "description": "Setor/indústria da empresa"},
                        "services": {"type": "array", "items": {"type": "string"}, "description": "Serviços oferecidos"},
                        "products": {"type": "array", "items": {"type": "string"}, "description": "Produtos oferecidos"},
                        "contact_info": {
                            "type": "object",
                            "properties": {
                                "email": {"type": "string"},
                                "phone": {"type": "string"},
                                "address": {"type": "string"}
                            }
                        },
                        "social_media": {
                            "type": "object",
                            "properties": {
                                "linkedin": {"type": "string"},
                                "twitter": {"type": "string"},
                                "facebook": {"type": "string"},
                                "instagram": {"type": "string"}
                            }
                        },
                        "team_size": {"type": "string", "description": "Tamanho da equipe/empresa"},
                        "founded_year": {"type": "string", "description": "Ano de fundação"},
                        "headquarters": {"type": "string", "description": "Sede da empresa"},
                        "key_people": {"type": "array", "items": {"type": "string"}, "description": "Pessoas-chave da empresa"},
                        "certifications": {"type": "array", "items": {"type": "string"}, "description": "Certificações da empresa"},
                        "awards": {"type": "array", "items": {"type": "string"}, "description": "Prêmios recebidos"},
                        "news_mentions": {"type": "array", "items": {"type": "string"}, "description": "Menções na mídia"}
                    },
                    "required": ["company_name", "description"]
                },
                extraction_type="schema",
                instruction="""Extraia informações abrangentes sobre esta empresa do conteúdo da página. 
                Foque em dados factuais e verificáveis. Se alguma informação não estiver disponível, 
                não invente dados. Seja preciso e detalhado nas descrições."""
            )
            
            # Configuração de chunking para páginas grandes
            chunking_strategy = RegexChunking()
            
            self.log_service.log_debug("Starting Crawl4AI scraping", {"url": url})
            
            # Executar o crawling
            result = await self.crawler.arun(
                url=url,
                extraction_strategy=extraction_strategy,
                chunking_strategy=chunking_strategy,
                bypass_cache=True,
                js_code=[
                    "window.scrollTo(0, document.body.scrollHeight);",  # Scroll para carregar conteúdo lazy
                    "await new Promise(resolve => setTimeout(resolve, 2000));",  # Aguardar carregamento
                ],
                wait_for="networkidle",
                page_timeout=30000
            )
            
            if result.success and result.extracted_content:
                extracted_data = json.loads(result.extracted_content)
                
                # Adicionar metadados do crawling
                crawl_metadata = {
                    "url": url,
                    "title": result.metadata.get("title", ""),
                    "description": result.metadata.get("description", ""),
                    "keywords": result.metadata.get("keywords", []),
                    "crawl_timestamp": datetime.now().isoformat(),
                    "content_length": len(result.markdown) if result.markdown else 0,
                    "extraction_method": "crawl4ai_llm"
                }
                
                # Combinar dados extraídos com metadados
                final_result = {
                    **extracted_data,
                    "_metadata": crawl_metadata,
                    "raw_markdown": result.markdown[:5000] if result.markdown else "",  # Primeiros 5k chars
                    "quality_score": self._assess_extraction_quality(extracted_data)
                }
                
                self.log_service.log_debug("Crawl4AI extraction successful", {
                    "url": url,
                    "extracted_fields": list(extracted_data.keys()),
                    "quality_score": final_result["quality_score"]
                })
                
                return final_result
            else:
                self.log_service.log_debug("Crawl4AI extraction failed", {
                    "url": url,
                    "error": result.error_message if hasattr(result, 'error_message') else "Unknown error"
                })
                return {"error": "Extraction failed", "url": url}
                
        except Exception as e:
            self.log_service.log_debug("Crawl4AI scraping error", {
                "url": url,
                "error": str(e)
            })
            return {"error": str(e), "url": url}
    
    async def scrape_company_website_complete(self, url: str) -> Dict[str, Any]:
        """Scraping completo de website corporativo usando CrawlAI"""
        try:
            if not self.crawler:
                raise Exception("Crawler not initialized. Use async context manager.")
            
            # Obter configuração LLM dinâmica
            llm_config = self._get_llm_config()
            
            extraction_strategy = LLMExtractionStrategy(
                provider=llm_config["provider"],
                api_token=llm_config["api_token"],
                base_url=llm_config["base_url"],
                schema={
                    "type": "object",
                    "properties": {
                        "company_name": {"type": "string"},
                        "description": {"type": "string"},
                        "social_media": {
                            "type": "object",
                            "properties": {
                                "linkedin": {"type": "string"},
                                "twitter": {"type": "string"},
                                "facebook": {"type": "string"},
                                "instagram": {"type": "string"}
                            }
                        },
                        "contact_info": {
                            "type": "object",
                            "properties": {
                                "email": {"type": "string"},
                                "phone": {"type": "string"},
                                "address": {"type": "string"}
                            }
                        },
                        "team_info": {"type": "array", "items": {"type": "string"}},
                        "products_services": {"type": "array", "items": {"type": "string"}},
                        "company_values": {"type": "array", "items": {"type": "string"}},
                        "certifications": {"type": "array", "items": {"type": "string"}},
                        "news_updates": {"type": "array", "items": {"type": "string"}}
                    }
                },
                extraction_type="schema",
                instruction="Extract comprehensive company information including social media, contact details, team, products, values, and recent news."
            )
            
            result = await self.crawler.arun(
                url=url,
                extraction_strategy=extraction_strategy,
                bypass_cache=True,
                js_code=[
                    "window.scrollTo(0, document.body.scrollHeight);",
                    "await new Promise(resolve => setTimeout(resolve, 2000));"
                ],
                wait_for="networkidle",
                page_timeout=30000
            )
            
            if result.success and result.extracted_content:
                extracted_data = json.loads(result.extracted_content)
                
                # Adicionar metadados do crawling
                crawl_metadata = {
                    "url": url,
                    "title": result.metadata.get("title", ""),
                    "crawl_timestamp": datetime.now().isoformat(),
                    "extraction_method": "crawl4ai_website_complete"
                }
                
                # Combinar dados extraídos com metadados
                final_result = {
                    **extracted_data,
                    "_metadata": crawl_metadata,
                    "quality_score": self._assess_extraction_quality(extracted_data)
                }
                
                return final_result
            else:
                return {"error": "Website extraction failed", "url": url}
                
        except Exception as e:
            self.log_service.log_debug("Website complete scraping error", {
                "url": url,
                "error": str(e)
            })
            return {"error": str(e), "url": url}
    
    async def scrape_linkedin_company_advanced(self, linkedin_url: str) -> Dict[str, Any]:
        """Scraping avançado de página do LinkedIn usando Crawl4AI com DeepSeek"""
        try:
            if not self.crawler:
                raise Exception("Crawler not initialized. Use async context manager.")
            
            # Obter configuração LLM dinâmica
            llm_config = self._get_llm_config()
            
            # Schema específico para LinkedIn
            linkedin_schema = {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string", "description": "Nome oficial da empresa no LinkedIn"},
                    "tagline": {"type": "string", "description": "Tagline/slogan da empresa"},
                    "description": {"type": "string", "description": "Descrição completa da empresa"},
                    "industry": {"type": "string", "description": "Setor de atuação"},
                    "company_size": {"type": "string", "description": "Tamanho da empresa (ex: 11-50 funcionários)"},
                    "headquarters": {"type": "string", "description": "Sede da empresa"},
                    "founded": {"type": "string", "description": "Ano de fundação"},
                    "website": {"type": "string", "description": "Website oficial"},
                    "specialties": {"type": "array", "items": {"type": "string"}, "description": "Especialidades da empresa"},
                    "followers_count": {"type": "string", "description": "Número de seguidores no LinkedIn"},
                    "employees_count": {"type": "string", "description": "Número de funcionários"},
                    "recent_posts": {"type": "array", "items": {"type": "string"}, "description": "Posts recentes da empresa"},
                    "leadership": {"type": "array", "items": {"type": "string"}, "description": "Liderança da empresa"}
                },
                "required": ["company_name"]
            }
            
            extraction_strategy = LLMExtractionStrategy(
                provider=llm_config["provider"],
                api_token=llm_config["api_token"],
                base_url=llm_config["base_url"],
                schema=linkedin_schema,
                extraction_type="schema",
                instruction="""Extraia informações detalhadas desta página do LinkedIn da empresa. 
                Foque em dados visíveis na página como nome, descrição, setor, tamanho, sede, 
                ano de fundação, website, especialidades, contagem de seguidores e funcionários."""
            )
            
            self.log_service.log_debug("Starting Crawl4AI LinkedIn scraping", {"url": linkedin_url})
            
            result = await self.crawler.arun(
                url=linkedin_url,
                extraction_strategy=extraction_strategy,
                bypass_cache=True,
                js_code=[
                    "window.scrollTo(0, document.body.scrollHeight/2);",
                    "await new Promise(resolve => setTimeout(resolve, 3000));",
                    "window.scrollTo(0, document.body.scrollHeight);",
                    "await new Promise(resolve => setTimeout(resolve, 2000));"
                ],
                wait_for="networkidle",
                page_timeout=45000,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            if result.success and result.extracted_content:
                extracted_data = json.loads(result.extracted_content)
                
                # Normalizar dados para formato padrão
                normalized_data = self._normalize_linkedin_data(extracted_data)
                
                self.log_service.log_debug("Crawl4AI LinkedIn extraction successful", {
                    "url": linkedin_url,
                    "company_name": normalized_data.get("name", "Unknown"),
                    "data_quality": self._assess_extraction_quality(normalized_data)
                })
                
                return normalized_data
            else:
                self.log_service.log_debug("Crawl4AI LinkedIn extraction failed", {
                    "url": linkedin_url,
                    "error": result.error_message if hasattr(result, 'error_message') else "Unknown error"
                })
                return {"error": "LinkedIn extraction failed", "url": linkedin_url}
                
        except Exception as e:
            self.log_service.log_debug("Crawl4AI LinkedIn scraping error", {
                "url": linkedin_url,
                "error": str(e)
            })
            return {"error": str(e), "url": linkedin_url}
            
    async def scrape_linkedin_person(self, linkedin_url: str) -> Dict[str, Any]:
        """Scraping de perfil pessoal LinkedIn usando CrawlAI"""
        try:
            if not self.crawler:
                raise Exception("Crawler not initialized. Use async context manager.")
            
            # Obter configuração LLM dinâmica
            llm_config = self._get_llm_config()
            
            extraction_strategy = LLMExtractionStrategy(
                provider=llm_config["provider"],
                api_token=llm_config["api_token"],
                base_url=llm_config["base_url"],
                schema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "headline": {"type": "string"},
                        "location": {"type": "string"},
                        "current_company": {"type": "string"},
                        "current_title": {"type": "string"},
                        "profile_image": {"type": "string"},
                        "connections": {"type": "string"},
                        "skills": {"type": "array", "items": {"type": "string"}},
                        "experience": {"type": "array", "items": {"type": "object", "properties": {
                            "company": {"type": "string"},
                            "title": {"type": "string"},
                            "duration": {"type": "string"}
                        }}},
                        "education": {"type": "array", "items": {"type": "object", "properties": {
                            "institution": {"type": "string"},
                            "degree": {"type": "string"},
                            "duration": {"type": "string"}
                        }}}
                    }
                },
                extraction_type="schema",
                instruction="Extract complete LinkedIn profile information including experience, education, skills, and current position."
            )
            
            result = await self.crawler.arun(
                url=linkedin_url,
                extraction_strategy=extraction_strategy,
                bypass_cache=True,
                js_code=[
                    "window.scrollTo(0, document.body.scrollHeight/2);",
                    "await new Promise(resolve => setTimeout(resolve, 2000));",
                    "window.scrollTo(0, document.body.scrollHeight);",
                    "await new Promise(resolve => setTimeout(resolve, 2000));"
                ],
                wait_for="networkidle",
                page_timeout=30000,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            if result.success and result.extracted_content:
                extracted_data = json.loads(result.extracted_content)
                
                # Adicionar metadados
                extracted_data["linkedin_url"] = linkedin_url
                extracted_data["extraction_quality"] = self._calculate_person_confidence_score(extracted_data)
                extracted_data["extraction_timestamp"] = datetime.now().isoformat()
                
                self.log_service.log_debug("LinkedIn person extraction successful", {
                    "url": linkedin_url,
                    "name": extracted_data.get("name", "Unknown"),
                    "quality": extracted_data.get("extraction_quality", 0)
                })
                
                return extracted_data
            else:
                self.log_service.log_debug("LinkedIn person extraction failed", {
                    "url": linkedin_url,
                    "error": result.error_message if hasattr(result, 'error_message') else "Unknown error"
                })
                return {"error": "LinkedIn person extraction failed", "url": linkedin_url}
                
        except Exception as e:
            self.log_service.log_debug("LinkedIn person scraping error", {
                "url": linkedin_url,
                "error": str(e)
            })
            return {"error": str(e), "url": linkedin_url}
            
    async def find_linkedin_on_website(self, website_url: str) -> Optional[str]:
        """Busca URLs do LinkedIn em websites usando CrawlAI com LLM"""
        try:
            llm_config = self._get_llm_config()
            
            extraction_strategy = LLMExtractionStrategy(
                provider=llm_config["provider"],
                api_token=llm_config["api_token"],
                schema={
                    "type": "object",
                    "properties": {
                        "linkedin_urls": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Lista de URLs do LinkedIn encontradas no site"
                        },
                        "company_linkedin": {
                            "type": "string",
                            "description": "URL principal do LinkedIn da empresa"
                        }
                    }
                },
                extraction_type="schema",
                instruction="Encontre todos os links do LinkedIn nesta página, especialmente o link oficial da empresa. Procure por links que contenham 'linkedin.com/company/' ou 'linkedin.com/in/'. Retorne o link principal da empresa se encontrado."
            )
            
            async with AsyncWebCrawler(verbose=True) as crawler:
                result = await crawler.arun(
                    url=website_url,
                    extraction_strategy=extraction_strategy,
                    bypass_cache=True
                )
                
                if result.success and result.extracted_content:
                    try:
                        data = json.loads(result.extracted_content)
                        
                        # Prioriza o link da empresa
                        if data.get('company_linkedin'):
                            return data['company_linkedin']
                        
                        # Senão, pega o primeiro link válido
                        linkedin_urls = data.get('linkedin_urls', [])
                        for url in linkedin_urls:
                            if 'linkedin.com/company/' in url:
                                return url
                        
                        # Se não encontrou da empresa, retorna qualquer LinkedIn
                        if linkedin_urls:
                            return linkedin_urls[0]
                            
                    except json.JSONDecodeError:
                        pass
                        
        except Exception as e:
            self.log_service.log_debug("Error finding LinkedIn on website with CrawlAI", {
                "error": str(e),
                "url": website_url
            })
        
        return None

    async def extract_company_data_from_html(self, html_content: str, url: str = None) -> Dict[str, Any]:
        """Extrai dados da empresa de conteúdo HTML usando LLM"""
        try:
            llm_config = self._get_llm_config()
            
            extraction_strategy = LLMExtractionStrategy(
                provider=llm_config["provider"],
                api_token=llm_config["api_token"],
                schema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Nome da empresa"},
                        "description": {"type": "string", "description": "Descrição da empresa"},
                        "industry": {"type": "string", "description": "Setor/indústria da empresa"},
                        "size": {"type": "string", "description": "Tamanho da empresa (número de funcionários)"},
                        "website": {"type": "string", "description": "Website oficial da empresa"},
                        "headquarters": {"type": "string", "description": "Sede/localização da empresa"},
                        "founded": {"type": "string", "description": "Ano de fundação da empresa"},
                        "social_media": {
                            "type": "object",
                            "properties": {
                                "linkedin": {"type": "string"},
                                "twitter": {"type": "string"},
                                "facebook": {"type": "string"},
                                "instagram": {"type": "string"}
                            }
                        },
                        "contact_info": {
                            "type": "object",
                            "properties": {
                                "email": {"type": "string"},
                                "phone": {"type": "string"},
                                "address": {"type": "string"}
                            }
                        },
                        "products_services": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Lista de produtos ou serviços oferecidos"
                        },
                        "company_values": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Valores da empresa"
                        },
                        "certifications": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Certificações da empresa"
                        }
                    }
                },
                extraction_type="schema",
                instruction="Extraia informações detalhadas sobre esta empresa do conteúdo HTML fornecido. Seja preciso e extraia apenas informações que estão claramente presentes no conteúdo."
            )
            
            # Simula um crawl com o HTML fornecido
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text(separator=' ', strip=True)
            
            # Usa o LLM para extrair dados estruturados
            async with AsyncWebCrawler(verbose=True) as crawler:
                # Como não podemos passar HTML diretamente, vamos processar o texto
                result = await extraction_strategy.extract(text_content, url or "")
                
                if result:
                    try:
                        if isinstance(result, str):
                            data = json.loads(result)
                        else:
                            data = result
                        
                        # Adiciona metadados
                        data['extraction_method'] = 'crawlai_llm'
                        data['source_url'] = url
                        data['confidence_score'] = self._assess_extraction_quality(data)
                        
                        return data
                        
                    except (json.JSONDecodeError, TypeError):
                        pass
                        
        except Exception as e:
            self.log_service.log_debug("Error extracting company data from HTML", {
                "error": str(e),
                "url": url
            })
        
        return {}

    def extract_data_with_selectors(self, html_content: str, selectors: List[str], field_name: str) -> Optional[str]:
        """Extrai dados usando seletores CSS como fallback"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            for selector in selectors:
                try:
                    element = soup.select_one(selector)
                    if element:
                        text = element.get_text(strip=True)
                        if text and text.lower() not in ['unknown', 'n/a', '-', '']:
                            return text
                except Exception:
                    continue
                    
        except Exception as e:
            self.log_service.log_debug(f"Error extracting {field_name} with selectors", {
                "error": str(e)
            })
        
        return None
            
    async def find_linkedin_on_website(self, website_url: str) -> Optional[str]:
        """Busca URLs do LinkedIn em websites usando CrawlAI com LLM"""
        try:
            llm_config = self._get_llm_config()
            
            extraction_strategy = LLMExtractionStrategy(
                provider=llm_config["provider"],
                api_token=llm_config["api_token"],
                schema={
                    "type": "object",
                    "properties": {
                        "linkedin_urls": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Lista de URLs do LinkedIn encontradas no site"
                        },
                        "company_linkedin": {
                            "type": "string",
                            "description": "URL principal do LinkedIn da empresa"
                        }
                    }
                },
                extraction_type="schema",
                instruction="Encontre todos os links do LinkedIn nesta página, especialmente o link oficial da empresa. Procure por links que contenham 'linkedin.com/company/' ou 'linkedin.com/in/'. Retorne o link principal da empresa se encontrado."
            )
            
            async with AsyncWebCrawler(verbose=True) as crawler:
                result = await crawler.arun(
                    url=website_url,
                    extraction_strategy=extraction_strategy,
                    bypass_cache=True
                )
                
                if result.success and result.extracted_content:
                    try:
                        data = json.loads(result.extracted_content)
                        
                        # Prioriza o link da empresa
                        if data.get('company_linkedin'):
                            return data['company_linkedin']
                        
                        # Senão, pega o primeiro link válido
                        linkedin_urls = data.get('linkedin_urls', [])
                        for url in linkedin_urls:
                            if 'linkedin.com/company/' in url:
                                return url
                        
                        # Se não encontrou da empresa, retorna qualquer LinkedIn
                        if linkedin_urls:
                            return linkedin_urls[0]
                            
                    except json.JSONDecodeError:
                        pass
                        
        except Exception as e:
            self.log_service.log_debug("Error finding LinkedIn on website with CrawlAI", {
                "error": str(e),
                "url": website_url
            })
        
        return None

    async def extract_company_data_from_html(self, html_content: str, url: str = None) -> Dict[str, Any]:
        """Extrai dados da empresa de conteúdo HTML usando LLM"""
        try:
            llm_config = self._get_llm_config()
            
            extraction_strategy = LLMExtractionStrategy(
                provider=llm_config["provider"],
                api_token=llm_config["api_token"],
                schema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Nome da empresa"},
                        "description": {"type": "string", "description": "Descrição da empresa"},
                        "industry": {"type": "string", "description": "Setor/indústria da empresa"},
                        "size": {"type": "string", "description": "Tamanho da empresa (número de funcionários)"},
                        "website": {"type": "string", "description": "Website oficial da empresa"},
                        "headquarters": {"type": "string", "description": "Sede/localização da empresa"},
                        "founded": {"type": "string", "description": "Ano de fundação da empresa"},
                        "social_media": {
                            "type": "object",
                            "properties": {
                                "linkedin": {"type": "string"},
                                "twitter": {"type": "string"},
                                "facebook": {"type": "string"},
                                "instagram": {"type": "string"}
                            }
                        },
                        "contact_info": {
                            "type": "object",
                            "properties": {
                                "email": {"type": "string"},
                                "phone": {"type": "string"},
                                "address": {"type": "string"}
                            }
                        },
                        "products_services": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Lista de produtos ou serviços oferecidos"
                        },
                        "company_values": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Valores da empresa"
                        },
                        "certifications": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Certificações da empresa"
                        }
                    }
                },
                extraction_type="schema",
                instruction="Extraia informações detalhadas sobre esta empresa do conteúdo HTML fornecido. Seja preciso e extraia apenas informações que estão claramente presentes no conteúdo."
            )
            
            # Simula um crawl com o HTML fornecido
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text(separator=' ', strip=True)
            
            # Usa o LLM para extrair dados estruturados
            async with AsyncWebCrawler(verbose=True) as crawler:
                # Como não podemos passar HTML diretamente, vamos processar o texto
                result = await extraction_strategy.extract(text_content, url or "")
                
                if result:
                    try:
                        if isinstance(result, str):
                            data = json.loads(result)
                        else:
                            data = result
                        
                        # Adiciona metadados
                        data['extraction_method'] = 'crawlai_llm'
                        data['source_url'] = url
                        data['confidence_score'] = self._assess_extraction_quality(data)
                        
                        return data
                        
                    except (json.JSONDecodeError, TypeError):
                        pass
                        
        except Exception as e:
            self.log_service.log_debug("Error extracting company data from HTML", {
                "error": str(e),
                "url": url
            })
        
        return {}

    def extract_data_with_selectors(self, html_content: str, selectors: List[str], field_name: str) -> Optional[str]:
        """Extrai dados usando seletores CSS como fallback"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            for selector in selectors:
                try:
                    element = soup.select_one(selector)
                    if element:
                        text = element.get_text(strip=True)
                        if text and text.lower() not in ['unknown', 'n/a', '-', '']:
                            return text
                except Exception:
                    continue
                    
        except Exception as e:
            self.log_service.log_debug(f"Error extracting {field_name} with selectors", {
                "error": str(e)
            })
        
        return None
            
    def _calculate_person_confidence_score(self, data: Dict[str, Any]) -> float:
        """Calcula score de confiança dos dados de pessoa"""
        score = 0.0
        
        # Nome (peso 30%)
        if data.get('name') and data['name'] != 'Unknown':
            score += 0.3
        
        # Headline/título (peso 20%)
        if data.get('headline') and data['headline'] != 'Unknown':
            score += 0.2
        
        # Empresa atual (peso 20%)
        if data.get('current_company') and data['current_company'] != 'Unknown':
            score += 0.2
        
        # Localização (peso 10%)
        if data.get('location') and data['location'] != 'Unknown':
            score += 0.1
        
        # Experiência (peso 10%)
        if data.get('experience') and len(data['experience']) > 0:
            score += 0.1
        
        # Educação (peso 5%)
        if data.get('education') and len(data['education']) > 0:
            score += 0.05
        
        # Skills (peso 5%)
        if data.get('skills') and len(data['skills']) > 0:
            score += 0.05
        
        return min(score, 1.0)
    
    def _normalize_linkedin_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza dados extraídos do LinkedIn para formato padrão"""
        normalized = {
            "name": raw_data.get("company_name", ""),
            "description": raw_data.get("description", ""),
            "tagline": raw_data.get("tagline", ""),
            "industry": raw_data.get("industry", ""),
            "size": raw_data.get("company_size", ""),
            "headquarters": raw_data.get("headquarters", ""),
            "founded": raw_data.get("founded", ""),
            "website": raw_data.get("website", ""),
            "specialties": raw_data.get("specialties", []),
            "followers": raw_data.get("followers_count", ""),
            "employees": raw_data.get("employees_on_linkedin", ""),
            "recent_updates": raw_data.get("recent_updates", []),
            "leadership": raw_data.get("leadership", []),
            "company_type": raw_data.get("company_type", ""),
            "stock_symbol": raw_data.get("stock_symbol", ""),
            "funding_info": raw_data.get("funding_info", ""),
            "extraction_quality": self._assess_extraction_quality(raw_data),
            "extraction_method": "crawl4ai_advanced",
            "extraction_timestamp": datetime.now().isoformat()
        }
        
        return normalized
    
    def _assess_extraction_quality(self, data: Dict[str, Any]) -> float:
        """Avalia a qualidade dos dados extraídos pelo Crawl4AI"""
        if not data:
            return 0.0
        
        score = 0.0
        max_score = 100.0
        
        # Campos essenciais (peso maior)
        essential_fields = {
            'company_name': 20,
            'description': 15,
            'industry': 10
        }
        
        # Campos importantes (peso médio)
        important_fields = {
            'headquarters': 8,
            'website': 8,
            'company_size': 7,
            'founded': 7
        }
        
        # Campos adicionais (peso menor)
        additional_fields = {
            'specialties': 5,
            'followers_count': 5,
            'employees_count': 5,
            'recent_posts': 5,
            'leadership': 5
        }
        
        all_fields = {**essential_fields, **important_fields, **additional_fields}
        
        for field, weight in all_fields.items():
            if field in data and data[field]:
                if isinstance(data[field], str) and len(data[field].strip()) > 0:
                    score += weight
                elif isinstance(data[field], list) and len(data[field]) > 0:
                    score += weight
                elif isinstance(data[field], dict) and data[field]:
                    score += weight
        
        return min(score / max_score, 1.0)

class CompanyEnrichmentService:

    def __init__(self, db_session: Session, log_service: LogService):
        self.db_session = db_session
        self.log_service = log_service
        self.firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
        self.brave_api_key = os.getenv("BRAVE_API_KEY")
        self.rate_limiter = BraveSearchRateLimiter(requests_per_second=3)
        # Inicializar CrawlAI service
        self.crawl4ai_service = CrawlAIService(log_service)

    async def enrich_company(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Enriquecimento principal usando apenas CrawlAI e Firecrawl"""
        try:
            company_data = request.copy()
            result = {"enriched_data": {}, "sources_used": [], "confidence_score": 0.0}
            
            # Estratégia 1: Enriquecimento por LinkedIn URL (se disponível)
            if company_data.get("linkedin_url"):
                linkedin_result = await self._enrich_by_linkedin_crawlai(company_data)
                if linkedin_result and linkedin_result.get("name"):
                    result["enriched_data"].update(linkedin_result)
                    result["sources_used"].append("linkedin_crawlai")
                    self.log_service.log_debug("LinkedIn enrichment successful", {
                        "company": linkedin_result.get("name", "Unknown")
                    })
            
            # Estratégia 2: Enriquecimento por domínio/website
            if company_data.get("domain") or company_data.get("website"):
                domain_result = await self._enrich_by_domain_crawlai_firecrawl(company_data)
                if domain_result:
                    # Merge com dados existentes
                    for key, value in domain_result.items():
                        if key not in result["enriched_data"] or not result["enriched_data"][key]:
                            result["enriched_data"][key] = value
                    
                    if domain_result.get("_sources"):
                        result["sources_used"].extend(domain_result["_sources"])
            
            # Estratégia 3: Busca com Brave Search (fallback)
            if not result["enriched_data"].get("name") and company_data.get("name"):
                brave_result = await self._search_company_with_brave(
                    company_data["name"],
                    region=company_data.get("region"),
                    country=company_data.get("country")
                )
                if brave_result and brave_result.get("name"):
                    # Merge dados do Brave Search
                    for key, value in brave_result.items():
                        if key not in result["enriched_data"] or not result["enriched_data"][key]:
                            result["enriched_data"][key] = value
                    result["sources_used"].append("brave_search")
            
            # Calcular score de confiança
            result["confidence_score"] = self._calculate_overall_confidence(
                result["enriched_data"], 
                result["sources_used"]
            )
            
            # Remover metadados internos
            if "_sources" in result["enriched_data"]:
                del result["enriched_data"]["_sources"]
            
            return result
            
        except Exception as e:
            self.log_service.log_debug("Company enrichment error", {"error": str(e)})
            return {
                "enriched_data": {},
                "sources_used": [],
                "confidence_score": 0.0,
                "error": str(e)
            }

    async def _safe_extract_text_async(self, page: Page, selector: str) -> Optional[str]:
        """Extrai texto de forma segura usando Playwright"""
        try:
            element = await page.query_selector(selector)
            if element:
                text = await element.inner_text()
                return text.strip() if text and text.strip() not in ['Unknown', 'N/A', '-', ''] else None
        except:
            pass
        return None
        
    def _safe_extract_text_from_html(self, html_content: str, selectors: List[str]) -> Optional[str]:
        """Extrai texto de forma segura usando seletores CSS em HTML"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            for selector in selectors:
                try:
                    element = soup.select_one(selector)
                    if element:
                        text = element.get_text(strip=True)
                        if text and text.strip() not in ['Unknown', 'N/A', '-', '']:
                            return text.strip()
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def _safe_extract_text(self, soup_or_element, selectors: List[str]) -> Optional[str]:
        """Extrai texto de forma segura usando múltiplos seletores (versão síncrona para BeautifulSoup)"""
        for selector in selectors:
            try:
                element = soup_or_element.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if text and text.lower() not in ['unknown', 'n/a', '-', '']:
                        return text
            except:
                continue
        return None

    def _extract_company_name_from_domain(self, domain: str) -> Optional[str]:
        """Extrai o nome da empresa do domínio"""
        try:
            # Remove www. se presente
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Pega a parte antes do primeiro ponto
            company_name = domain.split('.')[0]
            
            # Capitaliza adequadamente
            if company_name:
                # Se contém hífen, capitaliza cada parte
                if '-' in company_name:
                    parts = company_name.split('-')
                    company_name = ' '.join([part.capitalize() for part in parts])
                else:
                    company_name = company_name.capitalize()
                
                return company_name
            
            return {}
        except Exception as e:
            self.log_service.log_debug("Error extracting company name from domain", {"error": str(e)})
            return None

    def _is_domain(self, text: str) -> bool:
        """Verifica se o texto é um domínio"""
        import re
        # Padrão simples para detectar domínios
        domain_pattern = r'^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*\.[a-zA-Z]{2,}$'
        return bool(re.match(domain_pattern, text.strip()))   

    async def _enrich_by_linkedin_crawlai(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enriquecimento de LinkedIn usando apenas CrawlAI"""
        try:
            linkedin_url = company_data.get("linkedin_url")
            if not linkedin_url:
                return {}
            
            async with CrawlAIService(self.log_service) as crawl_service:
                linkedin_data = await crawl_service.scrape_linkedin_company_advanced(linkedin_url)
                
                if linkedin_data and not linkedin_data.get("error"):
                    # Normalizar dados do LinkedIn
                    normalized_data = crawl_service._normalize_linkedin_data(linkedin_data)
                    normalized_data["_source"] = "crawl4ai_linkedin"
                    return normalized_data
            
            return {}
            
        except Exception as e:
            self.log_service.log_debug("LinkedIn CrawlAI enrichment error", {
                "linkedin_url": company_data.get("linkedin_url"),
                "error": str(e)
            })
            return {}
            
    async def _enrich_by_domain_crawlai_firecrawl(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enriquecimento por domínio usando CrawlAI e Firecrawl"""
        try:
            domain = company_data.get("domain") or company_data.get("website")
            if not domain:
                return {}
            
            # Normalizar URL
            if not domain.startswith(("http://", "https://")):
                website_url = f"https://{domain}"
            else:
                website_url = domain
            
            result = {"_sources": []}
            
            # Estratégia 1: CrawlAI para scraping completo do website
            async with CrawlAIService(self.log_service) as crawl_service:
                website_data = await crawl_service.scrape_company_website(website_url)
                
                if website_data and not website_data.get("error"):
                    result.update(website_data)
                    result["_sources"].append("crawl4ai_website")
                    
                    # Tentar encontrar LinkedIn no website
                    linkedin_url = await self._find_linkedin_on_website_firecrawl(website_url)
                    if linkedin_url:
                        result["linkedin_url"] = linkedin_url
                        
                        # Enriquecer com dados do LinkedIn
                        linkedin_data = await crawl_service.scrape_linkedin_company_advanced(linkedin_url)
                        if linkedin_data and not linkedin_data.get("error"):
                            # Merge dados do LinkedIn
                            normalized_linkedin = crawl_service._normalize_linkedin_data(linkedin_data)
                            for key, value in normalized_linkedin.items():
                                if key not in result or not result[key]:
                                    result[key] = value
                            result["_sources"].append("crawl4ai_linkedin")
                
                # Estratégia 2: Firecrawl como fallback se qualidade for baixa
                quality_score = website_data.get("quality_score", 0) if website_data else 0
                if quality_score < 0.6:  # Qualidade baixa
                    firecrawl_data = await self._scrape_with_firecrawl(website_url)
                    if firecrawl_data and not firecrawl_data.get("error"):
                        # Merge dados do Firecrawl
                        for key, value in firecrawl_data.items():
                            if key not in result or not result[key]:
                                result[key] = value
                        result["_sources"].append("firecrawl")
                        
                        # Buscar LinkedIn no Firecrawl se não encontrado
                        if not result.get("linkedin_url"):
                            linkedin_url = await self._find_linkedin_on_website_firecrawl(website_url)
                            if linkedin_url:
                                result["linkedin_url"] = linkedin_url
            
            return result
            
        except Exception as e:
            self.log_service.log_debug("Domain enrichment error", {
                "domain": company_data.get("domain"),
                "error": str(e)
            })
            return {}

    async def _find_linkedin_on_website(self, website_url: str) -> Optional[str]:
        """Busca LinkedIn no website usando CrawlAI com fallback para Firecrawl"""
        try:
            # Primeiro tenta com CrawlAI
            linkedin_url = await self.crawlai_service.find_linkedin_on_website(website_url)
            
            if linkedin_url:
                self.log_service.log_debug("LinkedIn found with CrawlAI", {
                    "url": website_url,
                    "linkedin_url": linkedin_url
                })
                return linkedin_url
            
            # Fallback para Firecrawl
            linkedin_url = await self._find_linkedin_on_website_firecrawl(website_url)
            
            if linkedin_url:
                self.log_service.log_debug("LinkedIn found with Firecrawl", {
                    "url": website_url,
                    "linkedin_url": linkedin_url
                })
                return linkedin_url
            
        except Exception as e:
            self.log_service.log_debug("Error finding LinkedIn on website", {
                "error": str(e),
                "url": website_url
            })
        
        return None
            
    async def _find_linkedin_on_website_firecrawl(self, website_url: str) -> Optional[str]:
        """Busca URLs do LinkedIn usando Firecrawl"""
        try:
            firecrawl = FirecrawlApp(api_key=os.getenv('FIRECRAWL_API_KEY'))
            
            # Scraping com Firecrawl
            scrape_result = firecrawl.scrape_url(
                website_url,
                params={
                    'formats': ['markdown', 'links'],
                    'includeTags': ['a'],
                    'excludeTags': ['script', 'style'],
                    'timeout': 15000
                }
            )
            
            if scrape_result.get('success') and scrape_result.get('data'):
                # Buscar links do LinkedIn
                links = scrape_result['data'].get('links', [])
                
                for link in links:
                    href = link.get('href', '')
                    if 'linkedin.com/company/' in href:
                        return href
                
                # Buscar no markdown também
                markdown = scrape_result['data'].get('markdown', '')
                linkedin_pattern = r'https?://(?:www\.)?linkedin\.com/company/[\w-]+/?'
                matches = re.findall(linkedin_pattern, markdown)
                if matches:
                    return matches[0]
            
            return None
            
        except Exception as e:
            self.log_service.log_debug("Error finding LinkedIn with Firecrawl", {
                "url": website_url,
                "error": str(e)
            })
            return None

    async def _add_website_enrichment(self, result: Dict[str, Any], company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Adiciona enriquecimento de dados do website da empresa"""
        try:
            website_url = result.get('website') or company_data.get('domain')
            if website_url:
                if not website_url.startswith(('http://', 'https://')):
                    website_url = f'https://{website_url}'
                
                website_data = await self._scrape_company_website(website_url)
                if website_data:
                    # Mesclar dados do website com dados existentes
                    result = self._merge_website_data(result, website_data)
            
            return result
        except Exception as e:
            self.log_service.log_debug("Website enrichment failed", {"error": str(e)})
            return result

    def _parse_linkedin_markdown(self, markdown_content: str) -> Dict[str, Any]:
        """Parse aprimorado de markdown content do LinkedIn"""
        try:
            import re
            
            result = {}
            
            # Extrair nome da empresa (primeiro h1 ou título principal)
            name_patterns = [
                r'^#\s+(.+)$',
                r'# (.+?)\n',
                r'## (.+?)\n',
                r'\*\*(.+?)\*\*.*(?:followers|employees)',
                r'^(.+?)\n[=\-]+\n',  # Formato alternativo de título
                r'<h1[^>]*>([^<]+)</h1>',  # Tag HTML h1
                r'Company:\s*(.+?)(?=\n|$)'  # Formato "Company: Nome"
            ]
            
            for pattern in name_patterns:
                name_match = re.search(pattern, markdown_content, re.MULTILINE | re.IGNORECASE)
                if name_match:
                    result['name'] = name_match.group(1).strip()
                    break
            
            # Extrair descrição (múltiplos padrões)
            desc_patterns = [
                r'(?:About|Overview|Description)\s*\n+(.+?)(?=\n#{1,3}|\n\n[A-Z]|$)',
                r'## About\s*\n(.+?)(?=\n##|$)',
                r'\*\*About\*\*\s*\n(.+?)(?=\n\*\*|$)',
                r'(?:About|Overview|Description)[:\s]*\n?(.+?)(?=\n#|\n\*\*|\n\n[A-Z]|$)',  # Formato mais flexível
                r'<p[^>]*>([^<]{30,})</p>',  # Parágrafos HTML longos (possível descrição)
                r'(?<=\n\n)([^#\*\n][^\n]{50,})(?=\n\n)'  # Parágrafos longos sem formatação
            ]
            
            for pattern in desc_patterns:
                desc_match = re.search(pattern, markdown_content, re.DOTALL | re.IGNORECASE)
                if desc_match:
                    result['description'] = desc_match.group(1).strip()
                    break
            
            # Extrair informações estruturadas
            info_patterns = {
                'industry': r'(?:Industry|Sector)[:\s]*(.+?)(?=\n|$)',
                'size': r'(?:Company size|Employees|Size)[:\s]*(.+?)(?=\n|$)',
                'headquarters': r'(?:Headquarters|Location|Based in|Address)[:\s]*(.+?)(?=\n|$)',
                'founded': r'(?:Founded|Established|Since|Year)[:\s]*(\d{4})',
                'website': r'(?:Website|Site|Web|URL)[:\s]*(.+?)(?=\n|$)',
                'specialties': r'(?:Specialties|Expertise|Skills|Focus areas)[:\s]*(.+?)(?=\n|$)',
                'followers': r'(\d+(?:,\d+)*(?:\.\d+)?[KMB]?)\s*(?:followers|seguidores)',
                'employees': r'(\d+(?:,\d+)*(?:\.\d+)?[KMB]?)\s*(?:employees|funcionários|staff|people)',
                'revenue': r'(?:Revenue|Annual revenue|Sales)[:\s]*(.+?)(?=\n|$)',
                'type': r'(?:Company type|Type|Organization)[:\s]*(.+?)(?=\n|$)',
                'funding': r'(?:Funding|Investment|Capital)[:\s]*(.+?)(?=\n|$)'
            }
            
            for key, pattern in info_patterns.items():
                match = re.search(pattern, markdown_content, re.IGNORECASE)
                if match:
                    result[key] = match.group(1).strip()
            
            # Extrair posts recentes
            posts_pattern = r'(?:Recent|Latest)\s+(?:posts|updates|news|activity)\s*:?\s*\n(.+?)(?=\n\n|$)'
            posts_match = re.search(posts_pattern, markdown_content, re.DOTALL | re.IGNORECASE)
            if posts_match:
                posts_text = posts_match.group(1)
                result['recent_posts'] = [post.strip() for post in posts_text.split('\n') if post.strip()]
            
            # Extrair liderança/equipe
            leadership_pattern = r'(?:Leadership|Team|Management|Key people)[:\s]*\n(.+?)(?=\n#|\n\*\*|$)'
            leadership_match = re.search(leadership_pattern, markdown_content, re.DOTALL | re.IGNORECASE)
            if leadership_match:
                leadership_text = leadership_match.group(1)
                # Tentar extrair nomes e cargos
                leaders = []
                for line in leadership_text.split('\n'):
                    if line.strip():
                        # Tentar identificar padrões de "Nome - Cargo" ou "Nome, Cargo"
                        leader_match = re.search(r'([^,\-:]+)(?:[,\-:]\s*(.+))?', line.strip())
                        if leader_match:
                            name = leader_match.group(1).strip()
                            title = leader_match.group(2).strip() if leader_match.group(2) else None
                            leaders.append({'name': name, 'title': title})
                if leaders:
                    result['leadership'] = leaders
            
            # Extrair especialidades como lista se for uma string separada por vírgulas
            if 'specialties' in result and ',' in result['specialties']:
                result['specialties'] = [s.strip() for s in result['specialties'].split(',') if s.strip()]
            
            # Normalizar números (converter K, M, B para valores numéricos)
            for key in ['followers', 'employees']:
                if key in result:
                    try:
                        value = result[key].upper()
                        multiplier = 1
                        if 'K' in value:
                            multiplier = 1000
                            value = value.replace('K', '')
                        elif 'M' in value:
                            multiplier = 1000000
                            value = value.replace('M', '')
                        elif 'B' in value:
                            multiplier = 1000000000
                            value = value.replace('B', '')
                        
                        # Remover caracteres não numéricos exceto ponto decimal
                        value = re.sub(r'[^0-9.]', '', value)
                        result[key] = str(int(float(value) * multiplier))
                    except:
                        # Manter o valor original se a conversão falhar
                        pass
            
            self.log_service.log_debug("Markdown parsing completed", {
                "extracted_fields": list(result.keys()),
                "quality": self._assess_data_quality(result)
            })
            
            return result
            
        except Exception as e:
            self.log_service.log_debug("Markdown parsing failed", {"error": str(e)})
            return {}

    async def _scrape_with_firecrawl(self, url: str) -> Dict[str, Any]:
        """Faz scraping de uma URL usando a API do Firecrawl com configuração otimizada."""
        if not self.firecrawl_api_key:
            self.log_service.log_debug("Firecrawl API key not configured.", {})
            return {"error": "Firecrawl not configured"}

        try:
            app = FirecrawlApp(api_key=self.firecrawl_api_key)
            
            # Configuração otimizada para LinkedIn
            scrape_options = {
                'formats': ['markdown', 'html'],
                'includeTags': ['h1', 'h2', 'h3', 'p', 'div', 'span', 'a', 'section'],
                'excludeTags': ['script', 'style', 'nav', 'footer', 'header'],
                'waitFor': 3000,
                'extractorOptions': {
                    'mode': 'llm-extraction',
                    'extractionPrompt': '''Extract comprehensive company information from this LinkedIn company page:
                    
                    REQUIRED FIELDS:
                    - Company name (exact name as shown)
                    - Description/About section (full text)
                    - Industry/Sector
                    - Company size (number of employees)
                    - Headquarters/Location
                    - Founded year
                    - Website URL
                    - Specialties (comma-separated)
                    - Follower count
                    - Employee count on LinkedIn
                    
                    ADDITIONAL FIELDS (if available):
                    - Recent posts/updates (last 3)
                    - Key executives/leadership
                    - Company type (Public, Private, etc.)
                    - Revenue information
                    - Funding information
                    - Associated organizations
                    
                    Return as clean JSON with these exact keys: name, description, industry, size, headquarters, founded, website, specialties, followers, employees, recent_posts, leadership, company_type, revenue, funding, associated_orgs''',
                    'extractionSchema': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'description': {'type': 'string'},
                            'industry': {'type': 'string'},
                            'size': {'type': 'string'},
                            'headquarters': {'type': 'string'},
                            'founded': {'type': 'string'},
                            'website': {'type': 'string'},
                            'specialties': {'type': 'string'},
                            'followers': {'type': 'string'},
                            'employees': {'type': 'string'},
                            'recent_posts': {'type': 'array', 'items': {'type': 'string'}},
                            'leadership': {'type': 'array', 'items': {'type': 'string'}},
                            'company_type': {'type': 'string'},
                            'revenue': {'type': 'string'},
                            'funding': {'type': 'string'},
                            'associated_orgs': {'type': 'array', 'items': {'type': 'string'}}
                        }
                    }
                }
            }
            
            self.log_service.log_debug("Starting Firecrawl scraping with enhanced config", {"url": url})
            scraped_data = app.scrape_url(url, scrape_options)
            
            if scraped_data and 'llm_extraction' in scraped_data:
                extracted = scraped_data['llm_extraction']
                self.log_service.log_debug("Firecrawl extraction successful", {
                    "url": url, 
                    "extracted_keys": list(extracted.keys()),
                    "data_quality": self._assess_data_quality(extracted)
                })
                return extracted
            elif scraped_data and 'markdown' in scraped_data:
                # Fallback para markdown se LLM extraction falhar
                self.log_service.log_debug("Using markdown fallback", {"url": url})
                return self._parse_linkedin_markdown(scraped_data['markdown'])
            else:
                self.log_service.log_debug("Firecrawl did not return structured data.", {
                    "url": url, 
                    "available_keys": list(scraped_data.keys()) if scraped_data else []
                })
                return {}
                
        except Exception as e:
            self.log_service.log_debug("Firecrawl scraping failed", {"url": url, "error": str(e)})
            return {"error": str(e)}

    async def _scrape_linkedin_company(self, linkedin_url: str) -> Dict[str, Any]:
        """Faz scraping de dados da empresa no LinkedIn usando Firecrawl."""
        self.log_service.log_debug("Starting LinkedIn scraping with Firecrawl", {"url": linkedin_url})
        
        company_data = await self._scrape_linkedin_company_with_retry(linkedin_url)

        if not company_data or company_data.get("error"):
            return self._get_default_company_data(linkedin_url, "Failed to scrape with Firecrawl")

        # Adicionar metadados e retornar
        company_data['linkedin_url'] = linkedin_url
        company_data['data_source'] = 'firecrawl_linkedin'
        company_data['confidence_score'] = self._calculate_company_confidence_score(company_data)
        return company_data
        
    async def _scrape_linkedin_company_with_retry(self, linkedin_url: str, max_retries: int = 2) -> Dict[str, Any]:
        """Scraping do LinkedIn com retry logic"""
        for attempt in range(max_retries + 1):
            try:
                self.log_service.log_debug(f"LinkedIn scraping attempt {attempt + 1}", {"url": linkedin_url})
                
                result = await self._scrape_with_firecrawl(linkedin_url)
                
                if result and not result.get('error'):
                    quality = self._assess_data_quality(result)
                    
                    # Se a qualidade for boa, retornar
                    if quality['quality_percentage'] >= 40:
                        result['linkedin_url'] = linkedin_url
                        result['data_source'] = 'firecrawl_linkedin'
                        result['confidence_score'] = self._calculate_company_confidence_score(result)
                        result['data_quality'] = quality
                        return result
                    
                    # Se qualidade baixa, tentar novamente
                    self.log_service.log_debug(f"Low quality data, retrying", {
                        "attempt": attempt + 1,
                        "quality": quality
                    })
                
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)  # Backoff exponencial
                    
            except Exception as e:
                self.log_service.log_debug(f"Scraping attempt {attempt + 1} failed", {
                    "error": str(e),
                    "url": linkedin_url
                })
                
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
        
        # Se todas as tentativas falharam
        return self._get_default_company_data(linkedin_url, "Failed to scrape after retries")

    async def _extract_company_data_optimized(self, html_content: str, url: str = None) -> Dict[str, Any]:
        """Extração otimizada de dados da empresa usando CrawlAI"""
        try:
            # Usa o método principal do CrawlAI
            data = await self.crawl4ai_service.extract_company_data_from_html(html_content, url)
            
            if data:
                return {
                    'name': data.get('name'),
                    'description': data.get('description'),
                    'industry': data.get('industry'),
                    'size': data.get('size'),
                    'website': data.get('website'),
                    'headquarters': data.get('headquarters'),
                    'founded': data.get('founded'),
                    'social_media': data.get('social_media', {}),
                    'contact_info': data.get('contact_info', {}),
                    'products_services': data.get('products_services', []),
                    'company_values': data.get('company_values', []),
                    'certifications': data.get('certifications', []),
                    'extraction_method': 'crawlai_optimized',
                    'confidence_score': data.get('confidence_score', 0.7)
                }
            
        except Exception as e:
            self.log_service.log_debug("Error in optimized company data extraction", {
                "error": str(e),
                "url": url
            })
        
        return {}

    async def _extract_name_from_html(self, html_content: str, url: str = None) -> Optional[str]:
        """Extrai nome da empresa usando CrawlAI LLM e seletores como fallback"""
        # Primeiro tenta com LLM
        try:
            data = await self.crawlai_service.extract_company_data_from_html(html_content, url)
            if data.get('name'):
                return data['name']
        except Exception:
            pass
        
        # Fallback com seletores
        selectors = [
            'h1[data-test-id="org-name"]',
            'h1.org-top-card-summary__title',
            'h1.top-card-layout__title',
            'h1',
            '.org-top-card-summary__title',
            '.top-card-layout__title'
        ]
        
        return self._safe_extract_text_from_html(html_content, selectors)

    async def _extract_description_from_html(self, html_content: str, url: str = None) -> Optional[str]:
        """Extrai descrição da empresa usando CrawlAI LLM e seletores como fallback"""
        # Primeiro tenta com LLM
        try:
            data = await self.crawlai_service.extract_company_data_from_html(html_content, url)
            if data.get('description') and len(data['description']) > 10:
                return data['description']
        except Exception:
            pass
        
        # Fallback com seletores
        selectors = [
            '[data-test-id="about-us__description"]',
            '.org-about-us-organization-description__text',
            '.break-words p',
            '.org-top-card-summary__tagline'
        ]
        
        return self._safe_extract_text_from_html(html_content, selectors)

    async def _extract_industry_from_html(self, html_content: str, url: str = None) -> Optional[str]:
        """Extrai indústria da empresa usando CrawlAI LLM e seletores como fallback"""
        # Primeiro tenta com LLM
        try:
            data = await self.crawlai_service.extract_company_data_from_html(html_content, url)
            if data.get('industry'):
                return data['industry']
        except Exception:
            pass
        
        # Fallback com seletores
        selectors = [
            '[data-test-id="about-us__industry"]',
            '.org-about-us-organization-description__industry',
            '.org-top-card-summary__industry'
        ]
        
        return self._safe_extract_text_from_html(html_content, selectors)

    async def _extract_size_from_html(self, html_content: str, url: str = None) -> Optional[str]:
        """Extrai tamanho da empresa usando CrawlAI LLM e seletores como fallback"""
        # Primeiro tenta com LLM
        try:
            data = await self.crawlai_service.extract_company_data_from_html(html_content, url)
            if data.get('size'):
                return data['size']
        except Exception:
            pass
        
        # Fallback com seletores
        selectors = [
            '[data-test-id="about-us__size"]',
            '.org-about-us-organization-description__company-size',
            '.org-top-card-summary__company-size'
        ]
        
        return self._safe_extract_text_from_html(html_content, selectors)

    async def _extract_website_from_html(self, html_content: str, url: str = None) -> Optional[str]:
        """Extrai website da empresa usando CrawlAI LLM e seletores como fallback"""
        # Primeiro tenta com LLM
        try:
            data = await self.crawlai_service.extract_company_data_from_html(html_content, url)
            if data.get('website'):
                return data['website']
        except Exception:
            pass
        
        # Fallback com seletores
        selectors = [
            '[data-test-id="about-us__website"] a',
            '.org-about-us-organization-description__website a',
            '.org-top-card-summary__website a'
        ]
        
        return self._safe_extract_text_from_html(html_content, selectors)

    async def _resolve_linkedin_redirect(self, linkedin_url: str) -> str:
        """Resolve redirecionamentos do LinkedIn"""
        try:
            # Se já é uma URL completa do LinkedIn, retorna como está
            if 'linkedin.com/company/' in linkedin_url:
                return linkedin_url
            
            # Se é um redirecionamento, tenta resolver
            if 'linkedin.com' in linkedin_url and '/redir/' in linkedin_url:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    
                    try:
                        response = await page.goto(linkedin_url, wait_until='networkidle', timeout=10000)
                        final_url = page.url
                        await browser.close()
                        return final_url
                    except:
                        await browser.close()
                        return linkedin_url
            
            return linkedin_url
            
        except Exception as e:
            self.log_service.log_debug("Error resolving LinkedIn redirect", {"error": str(e)})
            return linkedin_url

    async def _extract_headquarters_from_html(self, html_content: str, url: str = None) -> Optional[str]:
        """Extrai sede da empresa usando CrawlAI LLM e seletores como fallback"""
        # Primeiro tenta com LLM
        try:
            data = await self.crawlai_service.extract_company_data_from_html(html_content, url)
            if data.get('headquarters'):
                return data['headquarters']
        except Exception:
            pass
        
        # Fallback com seletores
        selectors = [
            '[data-test-id="about-us__headquarters"]',
            '.org-about-us-organization-description__headquarters',
            '.org-top-card-summary__headquarters'
        ]
        
        return self._safe_extract_text_from_html(html_content, selectors)

    async def _extract_founded_from_html(self, html_content: str, url: str = None) -> Optional[str]:
        """Extrai ano de fundação usando CrawlAI LLM e seletores como fallback"""
        # Primeiro tenta com LLM
        try:
            data = await self.crawlai_service.extract_company_data_from_html(html_content, url)
            if data.get('founded'):
                return data['founded']
        except Exception:
            pass
        
        # Fallback com seletores
        selectors = [
            '[data-test-id="about-us__founded"]',
            '.org-about-us-organization-description__founded',
            '.org-top-card-summary__founded'
        ]
        
        founded = self._safe_extract_text_from_html(html_content, selectors)
        
        # Extrair apenas o ano se houver texto adicional
        if founded:
            import re
            year_match = re.search(r'\b(19|20)\d{2}\b', founded)
            if year_match:
                return year_match.group()
        
        return founded

    def _get_default_company_data(self, linkedin_url: str = None, error: str = None) -> Dict[str, Any]:
        """Retorna dados padrão da empresa em caso de erro"""
        return {
            'name': 'Unknown',
            'description': '',
            'industry': '',
            'size': '',
            'website': '',
            'headquarters': '',
            'founded': '',
            'linkedin_url': linkedin_url or '',
            'confidence_score': 0.0,
            'data_source': 'error',
            'error': error or 'Unknown error during extraction'
        }

    async def _extract_company_data(self, page: Page) -> Dict[str, Any]:
        """Extrai dados da empresa do LinkedIn (método alternativo)"""
        try:
            # Nome da empresa
            name = await self._safe_extract_text_async(page, 'h1[data-test-id="org-name"]') or \
                   await self._safe_extract_text_async(page, 'h1.org-top-card-summary__title') or \
                   await self._safe_extract_text_async(page, 'h1.top-card-layout__title') or \
                   await self._safe_extract_text_async(page, 'h1')
            
            # Descrição
            description = await self._safe_extract_text_async(page, '[data-test-id="about-us__description"]') or \
                         await self._safe_extract_text_async(page, '.org-about-us-organization-description__text') or \
                         await self._safe_extract_text_async(page, '.break-words p')
            
            # Indústria
            industry = await self._safe_extract_text_async(page, '[data-test-id="about-us__industry"]') or \
                       await self._safe_extract_text_async(page, '.org-about-us-organization-description__industry')
            
            # Tamanho da empresa
            size = await self._safe_extract_text_async(page, '[data-test-id="about-us__size"]') or \
                   await self._safe_extract_text_async(page, '.org-about-us-organization-description__company-size')
            
            # Website
            website = await self._safe_extract_attribute(page, 'a[data-test-id="about-us__website"]', 'href') or \
                     await self._safe_extract_attribute(page, '.org-about-us-organization-description__website a', 'href')
            
            # Sede
            headquarters = await self._safe_extract_text_async(page, '[data-test-id="about-us__headquarters"]') or \
                          await self._safe_extract_text_async(page, '.org-about-us-organization-description__headquarters')
            
            # Ano de fundação
            founded = await self._safe_extract_text_async(page, '[data-test-id="about-us__founded"]') or \
                     await self._safe_extract_text_async(page, '.org-about-us-organization-description__founded')
            
            # Extrair apenas o ano se houver texto adicional
            if founded:
                import re
                year_match = re.search(r'\b(19|20)\d{2}\b', founded)
                if year_match:
                    founded = year_match.group()
            
            # Calcular score de confiança
            confidence_score = self._calculate_confidence_score([
                name, description, industry, size, website, headquarters, founded
            ])
            
            return {
                'name': name or 'Unknown',
                'description': description or '',
                'industry': industry or '',
                'size': size or '',
                'website': website or '',
                'headquarters': headquarters or '',
                'founded': founded or '',
                'confidence_score': confidence_score
            }
            
        except Exception as e:
            self.log_service.log_debug("Error extracting company data", {"error": str(e)})
            return {
                'name': 'Unknown',
                'description': '',
                'industry': '',
                'size': '',
                'website': '',
                'headquarters': '',
                'founded': '',
                'confidence_score': 0.0,
                'error': str(e)
            }

    async def _safe_extract_attribute(self, page: Page, selector: str, attribute: str) -> Optional[str]:
        """Extrai atributo de forma segura usando Playwright"""
        try:
            element = await page.query_selector(selector)
            if element:
                attr_value = await element.get_attribute(attribute)
                return attr_value.strip() if attr_value and attr_value.strip() not in ['Unknown', 'N/A', '-', ''] else None
        except:
            pass
        return None

    async def _search_company_with_brave(self, search_term: str, region: Optional[str] = None, country: Optional[str] = None) -> Dict[str, Any]:
        """Busca empresa usando Brave Search com estratégias otimizadas"""
        try:
            self.log_service.log_debug("Starting Brave search for company", {
                "search_term": search_term,
                "region": region,
                "country": country
            })
            
            # Aguardar rate limiting se necessário
            can_proceed = await self.rate_limiter.wait_if_needed()
            if not can_proceed:
                self.log_service.log_debug("Rate limit exceeded for Brave Search", {})
                return self._get_default_company_data(error="Rate limit exceeded")
            
            # Estratégias de busca otimizadas e mais específicas
            search_strategies = [
                f'"{search_term}" official linkedin company profile',
                f'site:linkedin.com/company "{search_term}"'
            ]
            if self._is_domain(search_term):
                company_name_from_domain = search_term.split('.')[0]
                search_strategies.append(f'site:linkedin.com/company "{company_name_from_domain}"')

            if region:
                search_strategies.append(f'site:linkedin.com/company "{search_term}" "{region}"')
            if country:
                search_strategies.append(f'site:linkedin.com/company "{search_term}" "{country}"')

            best_result = None
            best_score = 0
            
            for strategy in search_strategies:
                try:
                    self.log_service.log_debug("Trying search strategy", {"strategy": strategy})
                    
                    # Parâmetros corretos da API Brave Search
                    params = {
                        'q': strategy,
                        'count': 10
                        # Removidos: 'mkt', 'safesearch', 'cc' (parâmetros inválidos)
                    }
                    
                    # Adicionar país se fornecido (formato correto: código de 2 letras)
                    if country:
                        country_code = self._get_country_code(country)
                        if country_code:
                            params['country'] = country_code

                    response = requests.get(
                        "https://api.search.brave.com/res/v1/web/search",
                        headers={
                            'x-subscription-token': self.brave_token,
                            'Accept': 'application/json',
                            'Accept-Encoding': 'gzip',
                            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        },
                        params=params,
                        timeout=15
                    )
                    
                    self.log_service.log_debug("Brave API response", {
                        "status_code": response.status_code,
                        "strategy": strategy
                    })
                    self.log_service.log_debug("Brave API response", {
                        "status_code": response.status_code,
                        "url": response.url,
                        "params": params
                    })
                    if response.status_code == 200:
                        data = response.json()
                        
                        if 'web' in data and 'results' in data['web']:
                            results = data['web']['results']
                            
                            max_linkedin_attempts = 2  # Limitar tentativas de scraping do LinkedIn
                            linkedin_attempts = 0
                            
                            # Processar resultados com scoring e validação
                            for result in results[:3]: # Limitar a 3 resultados
                                url = result.get('url', '')
                                title = result.get('title', '')
                                description = result.get('description', '')
                                
                                # Priorizar URLs do LinkedIn
                                if 'linkedin.com/company/' in url:
                                    if linkedin_attempts >= max_linkedin_attempts:
                                        continue
                                        
                                    linkedin_attempts += 1
                                    
                                    # >>> ADICIONAR ESTE BLOCO DE VALIDAÇÃO <<<
                                    if not self._validate_company_relevance(title, search_term):
                                        self.log_service.log_debug("Brave result not relevant based on title", {"title": title, "search_term": search_term})
                                        continue
                                    
                                    self.log_service.log_debug("Relevant LinkedIn URL found", {"url": url})
                                    
                                    linkedin_data = await self._scrape_linkedin_company(url)
                                    
                                    if linkedin_data and not linkedin_data.get('error'):
                                        # Calcular score de relevância
                                        relevance_score = self._calculate_search_relevance(
                                            linkedin_data, search_term, title, description
                                        )
                                        
                                        if relevance_score > best_score:
                                            linkedin_data['brave_search_title'] = title
                                            linkedin_data['brave_search_description'] = description
                                            linkedin_data['data_source'] = 'brave_linkedin'
                                            linkedin_data['search_relevance_score'] = relevance_score
                                            best_result = linkedin_data
                                            best_score = relevance_score
                                
                                # Avaliar outros resultados se não há LinkedIn
                                elif not best_result:
                                    relevance_score = self._calculate_general_relevance(
                                        title, description, search_term
                                    )
                                    
                                    if relevance_score > best_score:
                                        company_name = self._extract_company_name(title, search_term)
                                        best_result = {
                                            'name': company_name,
                                            'description': description,
                                            'website': url,
                                            'brave_search_title': title,
                                            'brave_search_description': description,
                                            'data_source': 'brave_search_only',
                                            'search_relevance_score': relevance_score,
                                            'confidence_score': min(relevance_score * 0.8, 0.7)
                                        }
                                        best_score = relevance_score
                    
                    elif response.status_code == 422:
                        # Log detalhado do erro 422
                        try:
                            error_data = response.json()
                            self.log_service.log_debug("Brave Search 422 error details", {
                                "strategy": strategy,
                                "error_data": error_data,
                                "params": params
                            })
                        except:
                            self.log_service.log_debug("Brave Search 422 error", {
                                "strategy": strategy,
                                "response_text": response.text[:500],
                                "params": params
                            })
                        continue
                    
                    elif response.status_code == 429:
                        self.log_service.log_debug("Brave Search rate limited", {"strategy": strategy})
                        await asyncio.sleep(2)  # Aguardar antes da próxima tentativa
                        continue
                    
                    else:
                        self.log_service.log_debug("Brave Search API error", {
                            "status_code": response.status_code,
                            "strategy": strategy
                        })
                        
                except Exception as e:
                    self.log_service.log_debug("Error in search strategy", {
                        "error": str(e), 
                        "strategy": strategy
                    })
                    continue
            
            # Retornar melhor resultado encontrado
            if best_result:
                self.log_service.log_debug("Best result found", {
                    "name": best_result.get('name'),
                    "score": best_score,
                    "source": best_result.get('data_source')
                })
                return best_result
            
            # Se nenhum resultado foi encontrado
            return {
                'error': f'Não foi possível encontrar dados para: {search_term}',
                'name': 'Unknown',
                'search_term': search_term,
                'data_source': 'brave_search_failed',
                'confidence_score': 0.0
            }
            
        except Exception as e:
            self.log_service.log_debug("Brave Search failed", {"error": str(e)})
            return {
                'error': f'Erro na busca: {str(e)}',
                'name': 'Unknown',
                'search_term': search_term,
                'data_source': 'brave_search_error',
                'confidence_score': 0.0
            }

    def _validate_company_relevance(self, result_title: str, search_term: str) -> bool:
        """Valida se o título do resultado da busca é relevante para o termo pesquisado."""
        similarity_ratio = fuzz.token_set_ratio(result_title.lower(), search_term.lower())
        self.log_service.log_debug("Validating company relevance", {
            "title": result_title,
            "search_term": search_term,
            "similarity": similarity_ratio
        })
        # Usamos um limiar de 70 para considerar relevante
        return similarity_ratio > 70
    
    def _extract_company_name(self, title: str, fallback: str) -> str:
        """Extrai nome da empresa do título"""
        try:
            if not title:
                return fallback
            
            # Remover texto comum do LinkedIn
            clean_title = title.replace(' | LinkedIn', '').replace(' - LinkedIn', '')
            clean_title = clean_title.replace(' on LinkedIn', '').replace(' LinkedIn', '')
            
            # Se o título limpo não está vazio, usar ele
            if clean_title.strip():
                return clean_title.strip()
            
            return fallback
            
        except:
            return fallback
    
    def _calculate_search_relevance(self, linkedin_data: Dict[str, Any], search_term: str, title: str, description: str) -> float:
        """Calcula score de relevância para resultados do LinkedIn"""
        score = 0.0
        search_lower = search_term.lower()
        
        # Nome da empresa no LinkedIn (peso 40%)
        company_name = linkedin_data.get('name', '').lower()
        if company_name and company_name != 'unknown':
            if search_lower in company_name or company_name in search_lower:
                score += 0.4
            elif self._fuzzy_match(search_lower, company_name):
                score += 0.3
        
        # Título do resultado de busca (peso 30%)
        title_lower = title.lower()
        if search_lower in title_lower:
            score += 0.3
        elif self._fuzzy_match(search_lower, title_lower):
            score += 0.2
        
        # Descrição (peso 20%)
        desc_lower = description.lower()
        if search_lower in desc_lower:
            score += 0.2
        elif self._fuzzy_match(search_lower, desc_lower):
            score += 0.1
        
        # Qualidade dos dados extraídos (peso 10%)
        data_quality = linkedin_data.get('confidence_score', 0)
        score += data_quality * 0.1
        
        return min(score, 1.0)
    
    def _calculate_general_relevance(self, title: str, description: str, search_term: str) -> float:
        """Calcula score de relevância para resultados gerais"""
        score = 0.0
        search_lower = search_term.lower()
        
        # Título (peso 60%)
        title_lower = title.lower()
        if search_lower in title_lower:
            score += 0.6
        elif self._fuzzy_match(search_lower, title_lower):
            score += 0.4
        
        # Descrição (peso 40%)
        desc_lower = description.lower()
        if search_lower in desc_lower:
            score += 0.4
        elif self._fuzzy_match(search_lower, desc_lower):
            score += 0.2
        
        return min(score, 1.0)
    
    def _fuzzy_match(self, term1: str, term2: str, threshold: float = 0.7) -> bool:
        """Verifica se dois termos são similares usando algoritmo simples"""
        try:
            # Usa fuzzywuzzy para uma comparação mais robusta
            return fuzz.token_set_ratio(term1, term2) >= (threshold * 100)
            
        except:
                return False

    # === MÉTODOS DE SCRAPING AVANÇADO ===
    async def _scrape_company_website(self, website_url: str) -> Dict[str, Any]:
        """Scraping aprimorado de website usando CrawlAI com fallback para Firecrawl"""
        try:
            # Primeiro tenta com CrawlAI
            result = await self.crawlai_service.scrape_company_website_complete(website_url)
            
            if result.get('success') and result.get('confidence_score', 0) > 0.6:
                return {
                    'success': True,
                    'data': result,
                    'source': 'crawlai',
                    'confidence_score': result.get('confidence_score', 0.7)
                }
            
            # Fallback para Firecrawl se CrawlAI não teve boa qualidade
            self.log_service.log_debug("CrawlAI quality low, trying Firecrawl", {
                "url": website_url,
                "crawlai_confidence": result.get('confidence_score', 0)
            })
            
            firecrawl_result = await self._scrape_with_firecrawl(website_url)
            
            if firecrawl_result.get('success'):
                return {
                    'success': True,
                    'data': firecrawl_result.get('data', {}),
                    'source': 'firecrawl',
                    'confidence_score': 0.8
                }
            
            # Se ambos falharam, retorna o melhor resultado disponível
            if result:
                return {
                    'success': True,
                    'data': result,
                    'source': 'crawlai_fallback',
                    'confidence_score': result.get('confidence_score', 0.5)
                }
            
        except Exception as e:
            self.log_service.log_debug("Error in enhanced website scraping", {
                "error": str(e),
                "url": website_url
            })
        
        return {
            'success': False,
            'data': {},
            'source': 'none',
            'confidence_score': 0.0
        }

    async def _extract_social_media_links(self, page: Page) -> dict:
        """Extrai links de redes sociais da página"""
        try:
            social_media = []
            
            # Seletores para diferentes redes sociais
            social_selectors = {
                'linkedin': [
                    'a[href*="linkedin.com"]',
                    'a[href*="linkedin.com/company"]',
                    'a[href*="linkedin.com/in"]'
                ],
                'twitter': [
                    'a[href*="twitter.com"]',
                    'a[href*="x.com"]'
                ],
                'facebook': [
                    'a[href*="facebook.com"]',
                    'a[href*="fb.com"]'
                ],
                'instagram': [
                    'a[href*="instagram.com"]'
                ]
            }
            
            for platform, selectors in social_selectors.items():
                for selector in selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        for element in elements:
                            href = await element.get_attribute('href')
                            if href and href.startswith('http'):
                                # Validar e limpar a URL
                                cleaned_url = self._clean_social_url(href)
                                if cleaned_url and cleaned_url not in [item['url'] for item in social_media]:
                                    social_media.append({
                                        'platform': platform,
                                        'url': cleaned_url,
                                        'followers': await self._extract_followers_count(element)
                                    })
                    except Exception as e:
                        self.log_service.log_debug(f"Error with selector {selector}", {"error": str(e)})
                        continue
            
            return {'social_media_extended': social_media}
            
        except Exception as e:
            self.log_service.log_debug("Error extracting social media links", {"error": str(e)})
            return []
    def _clean_social_url(self, url: str) -> Optional[str]:
        """Limpa e valida URLs de redes sociais"""
        try:
            if not url or not url.startswith('http'):
                return None
                
            # Remove parâmetros de tracking comuns
            url = url.split('?')[0].split('#')[0]
            
            # Validações específicas para LinkedIn
            if 'linkedin.com' in url:
                # Garantir que é uma URL válida do LinkedIn
                if '/company/' in url or '/in/' in url or '/school/' in url:
                    return url
                # Se é apenas linkedin.com sem path específico, ignorar
                elif url.endswith('linkedin.com') or url.endswith('linkedin.com/'):
                    return None
                    
            # Para outras redes sociais, retornar a URL limpa
            return url
            
        except Exception as e:
            self.log_service.log_debug("Error cleaning social URL", {"error": str(e), "url": url})
            return None
            
    async def _extract_followers_count(self, element) -> Optional[int]:
        """Tenta extrair número de seguidores se visível"""
        try:
            # Buscar texto próximo que pode conter número de seguidores
            parent = await element.query_selector('..')
            if parent:
                text = await parent.inner_text()
                # Regex para encontrar números seguidos de "seguidores", "followers", etc.
                import re
                match = re.search(r'([0-9,\.]+)\s*(seguidores|followers|k|m)', text.lower())
                if match:
                    number_str = match.group(1).replace(',', '').replace('.', '')
                    multiplier = match.group(2)
                    number = int(number_str)
                    
                    if multiplier == 'k':
                        number *= 1000
                    elif multiplier == 'm':
                        number *= 1000000
                        
                    return number
            return None
        except Exception as e:
            self.log_service.log_debug("Error extracting followers count", {"error": str(e)})
            return None

    async def _extract_company_history(self, page: Page) -> dict:
        """Extrai história da empresa"""
        try:
            history_selectors = [
                'section[id*="historia"]',
                'section[id*="history"]',
                'div[class*="historia"]',
                'div[class*="history"]',
                'section[id*="sobre"]',
                'section[id*="about"]',
                'div[class*="about"]',
                '.company-history',
                '.nossa-historia',
                '.our-story'
            ]
            
            for selector in history_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        if text and len(text.strip()) > 100:  # Apenas textos substanciais
                            return {'company_history': text.strip()}
                except:
                    continue
            
            return None
            
        except Exception as e:
            self.log_service.log_debug("Error extracting company history", {"error": str(e)})
            return {}

    async def _extract_news_and_updates(self, page: Page) -> dict:
        """Extrai notícias e atualizações recentes"""
        try:
            news = []
            
            news_selectors = [
                'section[id*="noticias"]',
                'section[id*="news"]',
                'div[class*="noticias"]',
                'div[class*="news"]',
                '.blog-posts',
                '.news-section',
                '.updates'
            ]
            
            for selector in news_selectors:
                try:
                    section = await page.query_selector(selector)
                    if section:
                        # Buscar artigos/posts dentro da seção
                        articles = await section.query_selector_all('article, .post, .news-item, .blog-item')
                        
                        for article in articles[:5]:  # Máximo 5 notícias
                            title_elem = await article.query_selector('h1, h2, h3, h4, .title, .headline')
                            date_elem = await article.query_selector('.date, .published, time')
                            link_elem = await article.query_selector('a')
                            
                            if title_elem:
                                title = await title_elem.inner_text()
                                date = await date_elem.inner_text() if date_elem else None
                                link = await link_elem.get_attribute('href') if link_elem else None
                                
                                news.append({
                                    'title': title.strip(),
                                    'date': date.strip() if date else None,
                                    'link': link
                                })
                        break
                except:
                    continue
            
            return {'news_and_updates': news}
            
        except Exception as e:
            self.log_service.log_debug("Error extracting news and updates", {"error": str(e)})
            return {}

    async def _extract_contact_info(self, page: Page) -> dict:
        """Extrai informações de contato"""
        try:
            contact = {}
            
            # Buscar telefones
            phone_selectors = ['a[href^="tel:"]', '.phone', '.telefone', '.contact-phone']
            for selector in phone_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        if selector.startswith('a[href^="tel:"]'):
                            contact['phone'] = await element.get_attribute('href')
                            contact['phone'] = contact['phone'].replace('tel:', '')
                        else:
                            contact['phone'] = await element.inner_text()
                        break
                except:
                    continue
            
            # Buscar emails
            email_selectors = ['a[href^="mailto:"]', '.email', '.contact-email']
            for selector in email_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        if selector.startswith('a[href^="mailto:"]'):
                            contact['email'] = await element.get_attribute('href')
                            contact['email'] = contact['email'].replace('mailto:', '')
                        else:
                            contact['email'] = await element.inner_text()
                        break
                except:
                    continue
            
            # Buscar endereço
            address_selectors = ['.address', '.endereco', '.contact-address', '.location']
            for selector in address_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        contact['address'] = await element.inner_text()
                        break
                except:
                    continue
            
            return {'contact_info': contact}
            
        except Exception as e:
            self.log_service.log_debug("Error extracting contact info", {"error": str(e)})
            return {}

    async def _extract_team_info(self, page: Page) -> dict:
        """Extrai informações sobre a equipe/liderança"""
        try:
            team_info = {'leadership': [], 'team_size_estimate': None}
            
            # Seletores para seção de equipe
            team_selectors = [
                '.team-member',
                '.leadership',
                '[class*="team"]',
                '[class*="founder"]',
                '[class*="ceo"]',
                '[class*="director"]'
            ]
            
            for selector in team_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements[:10]:  # Limita a 10 membros
                        name_elem = await element.query_selector('.name, h3, h4, .title')
                        role_elem = await element.query_selector('.role, .position, .title')
                        
                        if name_elem:
                            name = await name_elem.inner_text()
                            role = await role_elem.inner_text() if role_elem else None
                            
                            team_info['leadership'].append({
                                'name': name.strip(),
                                'role': role.strip() if role else None
                            })
                except:
                    continue
            
            return {'team_info': team_info}
            
        except Exception as e:
            self.log_service.log_debug("Error extracting team info", {"error": str(e)})
            return {}

    async def _extract_products_services(self, page: Page) -> dict:
        """Extrai informações sobre produtos e serviços"""
        try:
            products_services = []
            
            # Seletores para produtos/serviços
            product_selectors = [
                '.product',
                '.service',
                '[class*="product"]',
                '[class*="service"]',
                '.offering'
            ]
            
            for selector in product_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements[:10]:  # Limita a 10 itens
                        title_elem = await element.query_selector('h1, h2, h3, h4, .title, .name')
                        desc_elem = await element.query_selector('.description, .desc, p')
                        
                        if title_elem:
                            title = await title_elem.inner_text()
                            description = await desc_elem.inner_text() if desc_elem else None
                            
                            products_services.append({
                                'name': title.strip(),
                                'description': description.strip() if description else None
                            })
                except:
                    continue
            
            return {'products_services': products_services}
            
        except Exception as e:
            self.log_service.log_debug("Error extracting products/services", {"error": str(e)})
            return {}

    async def _extract_company_values(self, page: Page) -> dict:
        """Extrai valores e missão da empresa"""
        try:
            values = []
            
            # Seletores para valores/missão
            values_selectors = [
                '.value',
                '.mission',
                '.vision',
                '[class*="value"]',
                '[class*="mission"]',
                '[class*="vision"]'
            ]
            
            for selector in values_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        text = await element.inner_text()
                        if text and len(text.strip()) > 20:
                            values.append(text.strip())
                except:
                    continue
            
            return {'company_values': values}
            
        except Exception as e:
            self.log_service.log_debug("Error extracting company values", {"error": str(e)})
            return {}

    async def _extract_certifications_from_html(self, html_content: str, url: str = None) -> dict:
        """Extrai certificações usando CrawlAI LLM"""
        try:
            data = await self.crawlai_service.extract_company_data_from_html(html_content, url)
            certifications = data.get('certifications', [])
            
            return {
                'certifications': certifications,
                'extraction_method': 'crawlai_llm'
            }
            
        except Exception:
            pass
        
        return {
            'certifications': [],
            'extraction_method': 'failed'
        }

    async def _extract_certifications(self, page: Page) -> dict:
        """Extrai certificações e prêmios da empresa"""
        try:
            certifications = []
            
            # Seletores para certificações
            cert_selectors = [
                '.certification',
                '.award',
                '.certificate',
                '[class*="cert"]',
                '[class*="award"]',
                '[class*="badge"]'
            ]
            
            for selector in cert_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        text = await element.inner_text()
                        if text and len(text.strip()) > 5:
                            certifications.append(text.strip())
                except:
                    continue
            
            return {'certifications': certifications}
            
        except Exception as e:
            self.log_service.log_debug("Error extracting certifications", {"error": str(e)})
            return {}



    def _calculate_company_confidence_score(self, data: Dict[str, Any]) -> float:
        """Calcula score de confiança para dados da empresa"""
        score = 0.0
        
        # Nome da empresa (peso 25%)
        if data.get('name') and data['name'] not in ['Unknown', '', None]:
            score += 0.25
        
        # Descrição (peso 20%)
        if data.get('description') and len(str(data['description'])) > 20:
            score += 0.20
        
        # Website (peso 15%)
        if data.get('website') and data['website'] not in ['Unknown', '', None]:
            score += 0.15
        
        # Indústria (peso 10%)
        if data.get('industry') and data['industry'] not in ['Unknown', '', None]:
            score += 0.10
        
        # Tamanho da empresa (peso 10%)
        if data.get('size') and data['size'] not in ['Unknown', '', None]:
            score += 0.10
        
        # Sede (peso 10%)
        if data.get('headquarters') and data['headquarters'] not in ['Unknown', '', None]:
            score += 0.10
        
        # Ano de fundação (peso 10%)
        if data.get('founded') and data['founded'] not in ['Unknown', '', None]:
            score += 0.10
        
        return min(score, 1.0)
        
    def _calculate_overall_confidence(self, data: Dict[str, Any], sources: List[str]) -> float:
        """Calcula score de confiança geral baseado em múltiplos fatores"""
        base_score = 0.0
        
        # Fator 1: Completude dos dados (40%)
        completeness_fields = ['name', 'description', 'industry', 'website']
        filled_fields = sum(1 for field in completeness_fields if data.get(field))
        completeness_score = (filled_fields / len(completeness_fields)) * 0.4
        
        # Fator 2: Confiabilidade da fonte (30%)
        source_weights = {
            'crawl4ai': 0.9,
            'linkedin': 0.8,
            'firecrawl': 0.7,
            'brave_search': 0.6,
            'website_only': 0.4
        }
        
        source_score = 0.0
        for source in sources:
            source_score = max(source_score, source_weights.get(source, 0.3))
        source_score *= 0.3
        
        # Fator 3: Qualidade da extração (20%)
        quality_score = data.get('extraction_quality', 0.5) * 0.2
        
        # Fator 4: Consistência dos dados (10%)
        consistency_score = 0.1
        if data.get('website') and data.get('name'):
            consistency_score = 0.1
        
        return min(1.0, completeness_score + source_score + quality_score + consistency_score)
        
    def _assess_data_quality(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Avalia a qualidade dos dados extraídos"""
        quality_score = 0
        total_fields = 0
        filled_fields = 0
        
        essential_fields = ['name', 'description', 'industry', 'size', 'headquarters']
        bonus_fields = ['founded', 'website', 'specialties', 'followers', 'employees']
        
        for field in essential_fields:
            total_fields += 2  # Campos essenciais valem 2 pontos
            if data.get(field) and str(data[field]).strip() not in ['', 'Unknown', 'N/A', 'null']:
                filled_fields += 2
                quality_score += 2
        
        for field in bonus_fields:
            total_fields += 1  # Campos bônus valem 1 ponto
            if data.get(field) and str(data[field]).strip() not in ['', 'Unknown', 'N/A', 'null']:
                filled_fields += 1
                quality_score += 1
        
        quality_percentage = (quality_score / total_fields) * 100 if total_fields > 0 else 0
        
        return {
            'quality_score': quality_score,
            'total_possible': total_fields,
            'filled_fields': filled_fields,
            'quality_percentage': round(quality_percentage, 2),
            'quality_level': 'High' if quality_percentage >= 70 else 'Medium' if quality_percentage >= 40 else 'Low'
        }

    # === MÉTODOS DE GEOLOCALIZAÇÃO (GEONAMES API) ===
    async def _extract_location_data(self, headquarters: str) -> Dict[str, Optional[str]]:
        """Extrai país, código do país, região, código da região, cidade e código de discagem internacional usando API do GeoNames"""
        self.log_service.log_debug("Starting location extraction", {"headquarters": headquarters})
        
        if not headquarters:
            self.log_service.log_debug("No headquarters data provided for location extraction", {})
            return {
                "country": None,
                "country_code": None,
                "region": None,
                "region_code": None,
                "city": None,
                "country_dial_code": None
            }
        
        try:
            # Divide o headquarters em partes (cidade, estado/região, país)
            parts = [part.strip() for part in headquarters.split(',')]
            self.log_service.log_debug("Headquarters parts extracted", {"parts": parts})
            
            country = None
            country_code = None
            region = None
            region_code = None
            city = None
            country_dial_code = None
            
            if len(parts) >= 1:
                city = parts[0]
                self.log_service.log_debug("Extracted city", {"city": city})
            
            if len(parts) >= 2:
                region = parts[1]
                self.log_service.log_debug("Extracted region", {"region": region})
            
            if len(parts) >= 3:
                potential_country = parts[2]
            else:
                potential_country = parts[-1] if parts else None
            
            self.log_service.log_debug("Potential country identified", {"potential_country": potential_country})
            
            # Busca o país usando a API do GeoNames
            if potential_country:
                self.log_service.log_debug("Searching country data", {"potential_country": potential_country})
                country_data = await self._get_country_from_geonames(potential_country)
                if country_data:
                    country = country_data.get('countryName')
                    country_code = country_data.get('countryCode')
                    country_dial_code = self._get_country_dial_code(country_code)
                    self.log_service.log_debug("Found country data", {
                        "country": country,
                        "country_code": country_code,
                        "dial_code": country_dial_code
                    })
                else:
                    self.log_service.log_debug("No country data found", {"potential_country": potential_country})
            
            # Se não encontrou o país, tenta buscar por cidade
            if not country and city:
                self.log_service.log_debug("Searching city data", {"city": city, "region": region})
                city_data = await self._get_city_from_geonames(city, region)
                if city_data:
                    country = city_data.get('countryName')
                    country_code = city_data.get('countryCode')
                    country_dial_code = self._get_country_dial_code(country_code)
                    region_code = city_data.get('adminCode1')  # Código da região/estado
                    if not region:
                        region = city_data.get('adminName1')  # Estado/Província
                    self.log_service.log_debug("Found city data", {
                        "city": city,
                        "country": country,
                        "country_code": country_code,
                        "region": region,
                        "region_code": region_code,
                        "dial_code": country_dial_code
                    })
                else:
                    self.log_service.log_debug("No city data found", {"city": city})
            
            result = {
                "country": country,
                "country_code": country_code,
                "region": region,
                "region_code": region_code,
                "city": city,
                "country_dial_code": country_dial_code
            }
            
            self.log_service.log_debug("Final location data", result)
            return result
            
        except Exception as e:
            self.log_service.log_debug("Error extracting location data", {"error": str(e)})
            # Fallback para dados básicos sem API
            parts = [part.strip() for part in headquarters.split(',')]
            fallback_result = {
                "country": parts[-1] if parts else None,
                "country_code": None,
                "region": parts[1] if len(parts) >= 2 else None,
                "region_code": None,
                "city": parts[0] if parts else None,
                "country_dial_code": None
            }
            self.log_service.log_debug("Fallback location data", fallback_result)
            return fallback_result

    async def _get_country_from_geonames(self, country_name: str) -> Optional[Dict[str, str]]:
        """Busca dados do país usando API do GeoNames"""
        try:
            self.log_service.log_debug("Making GeoNames API request for country", {"country_name": country_name})
            # API do GeoNames para buscar países
            response = requests.get(
                "http://api.geonames.org/searchJSON",
                params={
                    'q': country_name.strip(),
                    'featureClass': 'A',  # Administrative areas (países)
                    'featureCode': 'PCLI',  # Independent political entity (país)
                    'maxRows': 1,
                    'username': os.getenv('GEONAMES_USERNAME', 'mrstory')
                },
                timeout=5
            )
            
            self.log_service.log_debug("GeoNames country response", {"status_code": response.status_code})
            
            if response.status_code == 200:
                data = response.json()
                self.log_service.log_debug("GeoNames country response data", {"data": data})
                if data.get('geonames') and len(data['geonames']) > 0:
                    country_info = data['geonames'][0]
                    result = {
                        'countryName': country_info.get('name', country_name),
                        'countryCode': country_info.get('countryCode', ''),
                        'geonameId': country_info.get('geonameId', '')
                    }
                    self.log_service.log_debug("Returning country data", {"result": result})
                    return result
        except Exception as e:
            self.log_service.log_debug("Error fetching country data from GeoNames", {
                "country_name": country_name,
                "error": str(e)
            })
        
        return None
    
    async def _get_city_from_geonames(self, city_name: str, region_name: str = None) -> Optional[Dict[str, str]]:
        """Busca dados da cidade usando API do GeoNames"""
        try:
            # Constrói a query de busca
            query = city_name.strip()
            if region_name:
                query += f" {region_name.strip()}"
            
            self.log_service.log_debug("Making GeoNames API request for city", {"query": query})
            
            # API do GeoNames para buscar cidades
            response = requests.get(
                "http://api.geonames.org/searchJSON",
                params={
                    'q': query,
                    'featureClass': 'P',  # Populated places (cidades)
                    'maxRows': 1,
                    'username': os.getenv('GEONAMES_USERNAME', 'mrstory')
                },
                timeout=5
            )
            
            self.log_service.log_debug("GeoNames city response", {"status_code": response.status_code})
            
            if response.status_code == 200:
                data = response.json()
                self.log_service.log_debug("GeoNames city response data", {"data": data})
                if data.get('geonames') and len(data['geonames']) > 0:
                    city_info = data['geonames'][0]
                    result = {
                        'cityName': city_info.get('name', city_name),
                        'countryName': city_info.get('countryName', ''),
                        'countryCode': city_info.get('countryCode', ''),
                        'adminName1': city_info.get('adminName1', ''),  # Estado/Província
                        'adminCode1': city_info.get('adminCode1', ''),  # Código da região/estado
                        'geonameId': city_info.get('geonameId', '')
                    }
                    self.log_service.log_debug("Returning city data", {"result": result})
                    return result
        except Exception as e:
            self.log_service.log_debug("Error fetching city data from GeoNames", {
                "city_name": city_name,
                "error": str(e)
            })
        
        return None
    
    # === MÉTODOS AUXILIARES ===
    def _clean_field_text(self, text: str, prefixes_to_remove: list) -> Optional[str]:
        """Remove prefixos indesejados do texto extraído"""
        if not text:
            return None
            
        cleaned_text = text.strip()
        
        # Remove cada prefixo da lista
        for prefix in prefixes_to_remove:
            if cleaned_text.startswith(prefix):
                cleaned_text = cleaned_text[len(prefix):].strip()
                break
        
        return cleaned_text if cleaned_text else None

    def _get_country_code(self, country: str) -> Optional[str]:
        """Retorna o código de país de 2 letras para um nome de país"""
        if not country:
            return None
        
        # Mapeamento de nomes de países para códigos ISO 3166-1 alpha-2
        country_codes = {
            'brasil': 'BR', 'brazil': 'BR', 'argentina': 'AR', 'chile': 'CL', 'colombia': 'CO',
            'peru': 'PE', 'uruguay': 'UY', 'paraguay': 'PY', 'bolivia': 'BO', 'ecuador': 'EC',
            'venezuela': 'VE', 'guyana': 'GY', 'suriname': 'SR', 'french guiana': 'GF',
            'mexico': 'MX', 'guatemala': 'GT', 'belize': 'BZ', 'el salvador': 'SV',
            'honduras': 'HN', 'nicaragua': 'NI', 'costa rica': 'CR', 'panama': 'PA',
            'cuba': 'CU', 'jamaica': 'JM', 'haiti': 'HT', 'dominican republic': 'DO',
            'puerto rico': 'PR', 'trinidad and tobago': 'TT', 'barbados': 'BB',
            'united states': 'US', 'usa': 'US', 'canada': 'CA', 'united kingdom': 'GB',
            'uk': 'GB', 'ireland': 'IE', 'france': 'FR', 'spain': 'ES', 'portugal': 'PT',
            'italy': 'IT', 'germany': 'DE', 'austria': 'AT', 'switzerland': 'CH',
            'netherlands': 'NL', 'belgium': 'BE', 'luxembourg': 'LU', 'denmark': 'DK',
            'sweden': 'SE', 'norway': 'NO', 'finland': 'FI', 'iceland': 'IS',
            'poland': 'PL', 'czech republic': 'CZ', 'slovakia': 'SK', 'hungary': 'HU',
            'slovenia': 'SI', 'croatia': 'HR', 'bosnia and herzegovina': 'BA',
            'serbia': 'RS', 'montenegro': 'ME', 'north macedonia': 'MK', 'albania': 'AL',
            'greece': 'GR', 'bulgaria': 'BG', 'romania': 'RO', 'moldova': 'MD',
            'ukraine': 'UA', 'belarus': 'BY', 'lithuania': 'LT', 'latvia': 'LV',
            'estonia': 'EE', 'russia': 'RU', 'kazakhstan': 'KZ', 'china': 'CN',
            'japan': 'JP', 'south korea': 'KR', 'india': 'IN', 'pakistan': 'PK',
            'bangladesh': 'BD', 'sri lanka': 'LK', 'maldives': 'MV', 'nepal': 'NP',
            'bhutan': 'BT', 'myanmar': 'MM', 'thailand': 'TH', 'laos': 'LA',
            'vietnam': 'VN', 'cambodia': 'KH', 'malaysia': 'MY', 'singapore': 'SG',
            'brunei': 'BN', 'indonesia': 'ID', 'philippines': 'PH', 'east timor': 'TL',
            'australia': 'AU', 'new zealand': 'NZ', 'fiji': 'FJ', 'papua new guinea': 'PG',
            'solomon islands': 'SB', 'vanuatu': 'VU', 'new caledonia': 'NC',
            'french polynesia': 'PF', 'samoa': 'WS', 'tonga': 'TO', 'kiribati': 'KI',
            'nauru': 'NR', 'palau': 'PW', 'micronesia': 'FM', 'marshall islands': 'MH',
            'tuvalu': 'TV', 'south africa': 'ZA', 'namibia': 'NA', 'botswana': 'BW',
            'zimbabwe': 'ZW', 'zambia': 'ZM', 'malawi': 'MW', 'mozambique': 'MZ',
            'eswatini': 'SZ', 'lesotho': 'LS', 'madagascar': 'MG', 'mauritius': 'MU',
            'seychelles': 'SC', 'comoros': 'KM', 'mayotte': 'YT', 'reunion': 'RE',
            'egypt': 'EG', 'libya': 'LY', 'tunisia': 'TN', 'algeria': 'DZ', 'morocco': 'MA',
            'western sahara': 'EH', 'sudan': 'SD', 'south sudan': 'SS', 'ethiopia': 'ET',
            'eritrea': 'ER', 'djibouti': 'DJ', 'somalia': 'SO', 'kenya': 'KE',
            'uganda': 'UG', 'tanzania': 'TZ', 'rwanda': 'RW', 'burundi': 'BI',
            'democratic republic of congo': 'CD', 'congo': 'CG', 'central african republic': 'CF',
            'cameroon': 'CM', 'chad': 'TD', 'niger': 'NE', 'nigeria': 'NG',
            'benin': 'BJ', 'togo': 'TG', 'ghana': 'GH', 'ivory coast': 'CI',
            'liberia': 'LR', 'sierra leone': 'SL', 'guinea': 'GN', 'guinea-bissau': 'GW',
            'gambia': 'GM', 'senegal': 'SN', 'mauritania': 'MR', 'mali': 'ML',
            'burkina faso': 'BF', 'cape verde': 'CV', 'sao tome and principe': 'ST',
            'equatorial guinea': 'GQ', 'gabon': 'GA', 'angola': 'AO', 'israel': 'IL',
            'palestine': 'PS', 'jordan': 'JO', 'syria': 'SY', 'lebanon': 'LB',
            'iraq': 'IQ', 'iran': 'IR', 'turkey': 'TR', 'cyprus': 'CY', 'georgia': 'GE',
            'armenia': 'AM', 'azerbaijan': 'AZ', 'kuwait': 'KW', 'saudi arabia': 'SA',
            'bahrain': 'BH', 'qatar': 'QA', 'united arab emirates': 'AE', 'oman': 'OM',
            'yemen': 'YE', 'afghanistan': 'AF', 'uzbekistan': 'UZ', 'turkmenistan': 'TM',
            'tajikistan': 'TJ', 'kyrgyzstan': 'KG', 'mongolia': 'MN'
        }
        
        return country_codes.get(country.lower())

    def _get_country_dial_code(self, country_code: str) -> Optional[str]:
        """Retorna o código de discagem internacional (DDI) para um código de país"""
        if not country_code:
            return None
        
        # Mapeamento de códigos de país para códigos de discagem internacional
        dial_codes = {
            'US': '+1', 'CA': '+1', 'BR': '+55', 'AR': '+54', 'CL': '+56', 'CO': '+57',
            'PE': '+51', 'UY': '+598', 'PY': '+595', 'BO': '+591', 'EC': '+593', 'VE': '+58',
            'GY': '+592', 'SR': '+597', 'GF': '+594', 'FK': '+500', 'MX': '+52', 'GT': '+502',
            'BZ': '+501', 'SV': '+503', 'HN': '+504', 'NI': '+505', 'CR': '+506', 'PA': '+507',
            'CU': '+53', 'JM': '+1876', 'HT': '+509', 'DO': '+1809', 'PR': '+1787', 'TT': '+1868',
            'BB': '+1246', 'GD': '+1473', 'LC': '+1758', 'VC': '+1784', 'AG': '+1268', 'DM': '+1767',
            'KN': '+1869', 'BS': '+1242', 'GB': '+44', 'IE': '+353', 'FR': '+33', 'ES': '+34',
            'PT': '+351', 'IT': '+39', 'DE': '+49', 'AT': '+43', 'CH': '+41', 'NL': '+31',
            'BE': '+32', 'LU': '+352', 'DK': '+45', 'SE': '+46', 'NO': '+47', 'FI': '+358',
            'IS': '+354', 'PL': '+48', 'CZ': '+420', 'SK': '+421', 'HU': '+36', 'SI': '+386',
            'HR': '+385', 'BA': '+387', 'RS': '+381', 'ME': '+382', 'MK': '+389', 'AL': '+355',
            'GR': '+30', 'BG': '+359', 'RO': '+40', 'MD': '+373', 'UA': '+380', 'BY': '+375',
            'LT': '+370', 'LV': '+371', 'EE': '+372', 'RU': '+7', 'KZ': '+7', 'CN': '+86',
            'JP': '+81', 'KR': '+82', 'IN': '+91', 'PK': '+92', 'BD': '+880', 'LK': '+94',
            'MV': '+960', 'NP': '+977', 'BT': '+975', 'MM': '+95', 'TH': '+66', 'LA': '+856',
            'VN': '+84', 'KH': '+855', 'MY': '+60', 'SG': '+65', 'BN': '+673', 'ID': '+62',
            'PH': '+63', 'TL': '+670', 'AU': '+61', 'NZ': '+64', 'FJ': '+679', 'PG': '+675',
            'SB': '+677', 'VU': '+678', 'NC': '+687', 'PF': '+689', 'WS': '+685', 'TO': '+676',
            'KI': '+686', 'NR': '+674', 'PW': '+680', 'FM': '+691', 'MH': '+692', 'TV': '+688',
            'ZA': '+27', 'NA': '+264', 'BW': '+267', 'ZW': '+263', 'ZM': '+260', 'MW': '+265',
            'MZ': '+258', 'SZ': '+268', 'LS': '+266', 'MG': '+261', 'MU': '+230', 'SC': '+248',
            'KM': '+269', 'YT': '+262', 'RE': '+262', 'EG': '+20', 'LY': '+218', 'TN': '+216',
            'DZ': '+213', 'MA': '+212', 'EH': '+212', 'SD': '+249', 'SS': '+211', 'ET': '+251',
            'ER': '+291', 'DJ': '+253', 'SO': '+252', 'KE': '+254', 'UG': '+256', 'TZ': '+255',
            'RW': '+250', 'BI': '+257', 'CD': '+243', 'CG': '+242', 'CF': '+236', 'CM': '+237',
            'TD': '+235', 'NE': '+227', 'NG': '+234', 'BJ': '+229', 'TG': '+228', 'GH': '+233',
            'CI': '+225', 'LR': '+231', 'SL': '+232', 'GN': '+224', 'GW': '+245', 'GM': '+220',
            'SN': '+221', 'MR': '+222', 'ML': '+223', 'BF': '+226', 'CV': '+238', 'ST': '+239',
            'GQ': '+240', 'GA': '+241', 'AO': '+244', 'IL': '+972', 'PS': '+970', 'JO': '+962',
            'SY': '+963', 'LB': '+961', 'IQ': '+964', 'IR': '+98', 'TR': '+90', 'CY': '+357',
            'GE': '+995', 'AM': '+374', 'AZ': '+994', 'KW': '+965', 'SA': '+966', 'BH': '+973',
            'QA': '+974', 'AE': '+971', 'OM': '+968', 'YE': '+967', 'AF': '+93', 'UZ': '+998',
            'TM': '+993', 'TJ': '+992', 'KG': '+996', 'MN': '+976'
        }
        
        return dial_codes.get(country_code.upper())

    def _extract_linkedin_from_social_media(self, website_data: Dict[str, Any]) -> Optional[str]:
        """Extrai URL do LinkedIn das redes sociais encontradas no site"""
        if not website_data or 'social_media_extended' not in website_data:
            return None
            
        for social in website_data.get('social_media_extended', []):
            if (social.get('platform') == 'linkedin' and 
                social.get('url') and 
                '/company/' in social.get('url')):
                
                linkedin_url = social.get('url')
                self.log_service.log_debug("LinkedIn URL extracted from social media", {"url": linkedin_url})
                return linkedin_url
        
        return None

    def _merge_website_data(self, linkedin_data: Dict[str, Any], website_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mescla dados do LinkedIn com dados do site"""
        if not website_data:
            return linkedin_data
            
        # Combinar redes sociais
        linkedin_social = linkedin_data.get('social_media', [])
        website_social = website_data.get('social_media_extended', [])
        
        all_social = linkedin_social.copy()
        for social in website_social:
            if not any(s.get('url') == social.get('url') for s in all_social):
                all_social.append(social)
        
        # Mesclar dados
        merged_data = linkedin_data.copy()
        merged_data.update({
            'social_media': all_social,
            'company_history': website_data.get('company_history') or linkedin_data.get('company_history'),
            'news_and_updates': website_data.get('news_and_updates', []),
            'contact_info': website_data.get('contact_info', {}),
            'team_info': website_data.get('team_info', {'leadership': [], 'team_size_estimate': None}),
            'products_services': website_data.get('products_services', []),
            'company_values': website_data.get('company_values', []),
            'certifications': website_data.get('certifications', [])
        })
        
        return merged_data

class PersonEnrichmentService:
    def __init__(self):
        load_dotenv()
        self.brave_limiter = BraveSearchRateLimiter()
        self.session = None
        self.browser = None
        self.context = None
        self.page = None
        self.linkedin_session = None
        self.linkedin_browser = None
        self.linkedin_context = None
        self.linkedin_page = None
        self.log_service = LogService()
        self.brave_token = os.getenv('BRAVE_SEARCH_API_KEY') or os.getenv('BRAVE_API_KEY')
        self.rate_limiter = BraveSearchRateLimiter()
        
        if not self.brave_token:
            raise ValueError("BRAVE_SEARCH_API_KEY não encontrado no arquivo .env")

    async def enrich_person(self, **kwargs) -> Dict[str, Any]:
        """
        Enriquece dados de pessoa usando múltiplas estratégias
        """
        self.log_service.log_debug("Starting person enrichment", {"params": kwargs})
        
        strategies = [
            self._enrich_by_linkedin_url,
            self._enrich_by_email,
            self._enrich_by_name_company,
            self._enrich_by_phone,
            self._enrich_by_general_search
        ]
        
        for strategy in strategies:
            try:
                self.log_service.log_debug(f"Trying strategy: {strategy.__name__}", {})
                result = await strategy(kwargs)
                if result and result.get('confidence_score', 0) > 0.6:
                    self.log_service.log_debug(f"Strategy {strategy.__name__} successful", {
                        "confidence_score": result.get('confidence_score'),
                        "name": result.get('full_name')
                    })
                    return result
            except Exception as e:
                self.log_service.log_debug(f"Strategy {strategy.__name__} failed", {"error": str(e)})
                continue
        
        return self._create_empty_result()
    
    async def _enrich_by_linkedin_url(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Enriquecimento por LinkedIn URL usando CrawlAI"""
        try:
            linkedin_url = data.get("linkedin_url")
            if not linkedin_url:
                return None
            
            async with CrawlAIService(self.log_service) as crawl_service:
                person_data = await crawl_service.scrape_linkedin_person(linkedin_url)
                
                if person_data and not person_data.get("error"):
                    person_data['linkedin_url'] = linkedin_url
                    # Formatar resultado
                    formatted_result = self._format_person_result(person_data, source="crawl4ai_linkedin")
                    return formatted_result
            
            # Fallback para método tradicional se CrawlAI falhar
            person_data = await self._scrape_linkedin_person(linkedin_url)
            if person_data:
                person_data['linkedin_url'] = linkedin_url
                return self._format_person_result(person_data, source='linkedin_direct')
            return None
            
        except Exception as e:
            self.log_service.log_debug(f"Error in LinkedIn URL enrichment", {"error": str(e)})
            return None

    async def _enrich_by_email(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Estratégia 2: Busca por email"""
        email = data.get('email')
        if not email:
            return None
            
        # Extrair domínio do email
        domain = email.split('@')[1] if '@' in email else None
        if not domain:
            return None
        
        # Buscar pessoa no LinkedIn usando email domain
        search_queries = [
            f"site:linkedin.com/in {email.split('@')[0]} {domain}",
            f"{email.split('@')[0]} {domain} linkedin",
            f"{data.get('full_name', '')} {domain} site:linkedin.com"
        ]
        
        return await self._search_and_scrape(search_queries, data)

    async def _enrich_by_name_company(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Estratégia 3: Nome + Empresa"""
        full_name = data.get('full_name')
        company_name = data.get('company_name')
        
        if not full_name:
            return None
            
        search_queries = []
        
        if company_name:
            search_queries.extend([
                f'"{full_name}" "{company_name}" site:linkedin.com/in',
                f'{full_name} {company_name} linkedin',
                f'"{full_name}" {company_name} site:linkedin.com'
            ])
        
        # Adicionar busca com região se disponível
        if data.get('region'):
            search_queries.append(f'"{full_name}" {data.get("region")} site:linkedin.com/in')
        
        # Busca básica por nome
        search_queries.append(f'"{full_name}" site:linkedin.com/in')
        
        return await self._search_and_scrape(search_queries, data)
    
    async def _enrich_by_phone(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Estratégia 4: Busca por telefone"""
        phone = data.get('phone')
        if not phone:
            return None
            
        # Limpar telefone para busca
        clean_phone = re.sub(r'[^0-9]', '', phone)
        
        search_queries = [
            f'"{phone}" site:linkedin.com/in',
            f'{clean_phone} site:linkedin.com',
            f'{data.get("full_name", "")} {phone} linkedin'
        ]
        
        return await self._search_and_scrape(search_queries, data)
    
    async def _enrich_by_general_search(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Estratégia 5: Busca geral"""
        full_name = data.get('full_name')
        if not full_name:
            return None
            
        search_queries = [
            f'{full_name} linkedin profile',
            f'{full_name} professional profile',
            f'{full_name} {data.get("country", "")} linkedin'
        ]
        
        return await self._search_and_scrape(search_queries, data)

    async def _search_and_scrape(self, search_queries: List[str], original_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Busca no Brave e scraping com Playwright"""
        for query in search_queries:
            try:
                # Buscar no Brave
                search_results = await self._brave_search_person(query)
                
                # Filtrar URLs do LinkedIn
                linkedin_urls = self._filter_linkedin_person_urls(search_results)
                
                max_linkedin_attempts = 2  # Reduzir de 3 para 2
                for url in linkedin_urls[:max_linkedin_attempts]:  # Testar top 2
                    person_data = await self._scrape_linkedin_person(url)
                    if person_data and self._validate_person_match(person_data, original_data):
                        person_data['linkedin_url'] = url
                        return self._format_person_result(person_data, source='brave_linkedin')
                        
            except Exception as e:
                self.log_service.log_debug(f"Search query failed: {query}", {"error": str(e)})
                continue
        
        return None
    
    def _merge_crawl4ai_data(self, base_data: Dict[str, Any], crawl4ai_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mescla dados do Crawl4AI com dados base, priorizando valores mais completos"""
        merged = base_data.copy()
        
        # Campos prioritários do Crawl4AI (mais confiáveis)
        priority_fields = {
            'name': 'company_name',
            'description': 'description', 
            'industry': 'industry',
            'website': 'website',
            'size': 'company_size',
            'founded': 'founded_year'
        }
        
        # Aplicar campos prioritários se mais completos
        for merged_key, crawl4ai_key in priority_fields.items():
            crawl4ai_value = crawl4ai_data.get(crawl4ai_key)
            base_value = merged.get(merged_key, '')
            
            if crawl4ai_value and (not base_value or len(str(crawl4ai_value)) > len(str(base_value))):
                merged[merged_key] = crawl4ai_value
        
        # Combinar arrays (serviços, produtos, etc.)
        array_fields = {
            'services': 'services',
            'products': 'products',
            'certifications': 'certifications',
            'awards': 'awards',
            'news_mentions': 'news_mentions'
        }
        
        for merged_key, crawl4ai_key in array_fields.items():
            base_array = merged.get(merged_key, [])
            crawl4ai_array = crawl4ai_data.get(crawl4ai_key, [])
            
            if crawl4ai_array:
                # Combinar arrays removendo duplicatas
                combined = base_array.copy()
                for item in crawl4ai_array:
                    if item not in combined:
                        combined.append(item)
                merged[merged_key] = combined
        
        # Mesclar informações de contato
        if crawl4ai_data.get('contact_info'):
            contact_base = merged.get('contact_info', {})
            contact_crawl4ai = crawl4ai_data['contact_info']
            
            merged_contact = contact_base.copy()
            for key, value in contact_crawl4ai.items():
                if value and (not merged_contact.get(key) or len(str(value)) > len(str(merged_contact.get(key, '')))):
                    merged_contact[key] = value
            
            merged['contact_info'] = merged_contact
        
        # Mesclar redes sociais
        if crawl4ai_data.get('social_media'):
            social_base = merged.get('social_media', {})
            social_crawl4ai = crawl4ai_data['social_media']
            
            merged_social = social_base.copy()
            for platform, url in social_crawl4ai.items():
                if url and not merged_social.get(platform):
                    merged_social[platform] = url
            
            merged['social_media'] = merged_social
        
        # Adicionar pessoas-chave se disponível
        if crawl4ai_data.get('key_people') and not merged.get('key_people'):
            merged['key_people'] = crawl4ai_data['key_people']
        
        # Atualizar qualidade de extração
        if crawl4ai_data.get('quality_score'):
            merged['extraction_quality'] = crawl4ai_data['quality_score']
        
        # Adicionar metadados de fonte
        if not merged.get('data_sources'):
            merged['data_sources'] = []
        if 'crawl4ai' not in merged['data_sources']:
            merged['data_sources'].append('crawl4ai')
        
        return merged
        
    def _merge_crawl4ai_website_data(self, result: Dict[str, Any], website_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge dados do website obtidos via Crawl4AI com dados do LinkedIn"""
        merged = result.copy()
        
        # Campos que podem ser enriquecidos do website
        website_fields = {
            'services': 'services',
            'products': 'products', 
            'contact_info': 'contact_info',
            'certifications': 'certifications',
            'awards': 'awards',
            'news_mentions': 'news_mentions',
            'key_people': 'key_people'
        }
        
        for website_key, merged_key in website_fields.items():
            if website_data.get(website_key) and not merged.get(merged_key):
                merged[merged_key] = website_data[website_key]
        
        # Enriquecer descrição se a do website for mais detalhada
        if (website_data.get('description') and 
            len(website_data['description']) > len(merged.get('description', ''))):
            merged['description_extended'] = website_data['description']
        
        # Adicionar informações de contato se não existirem
        if website_data.get('contact_info'):
            contact = website_data['contact_info']
            if contact.get('email') and not merged.get('email'):
                merged['email'] = contact['email']
            if contact.get('phone') and not merged.get('phone'):
                merged['phone'] = contact['phone']
            if contact.get('address') and not merged.get('address'):
                merged['address'] = contact['address']
        
        # Merge social media
        if website_data.get('social_media'):
            if not merged.get('social_media'):
                merged['social_media'] = {}
            for platform, url in website_data['social_media'].items():
                if url and not merged['social_media'].get(platform):
                    merged['social_media'][platform] = url
        
        return merged
    
    def _get_services_used(self, result: Dict[str, Any]) -> List[str]:
        """Identifica quais serviços foram usados no enriquecimento"""
        services = []
        
        if result.get('extraction_method') == 'crawl4ai_advanced':
            services.append('crawl4ai')
        if 'firecrawl' in str(result.get('_metadata', {})):
            services.append('firecrawl')
        if 'brave_search' in str(result.get('source', '')):
            services.append('brave_search')
        
        return services or ['unknown']
    
    def _identify_data_sources(self, result: Dict[str, Any]) -> List[str]:
        """Identifica as fontes de dados usadas"""
        sources = []
        
        if 'linkedin' in str(result.get('source', '')) or result.get('linkedin_url'):
            sources.append('linkedin')
        if result.get('website'):
            sources.append('company_website')
        if 'brave_search' in str(result.get('source', '')):
            sources.append('search_engine')
        
        return sources or ['unknown']
        
    async def _brave_search_person(self, query: str) -> List[Dict[str, Any]]:
        """Busca no Brave Search para pessoas com rate limiting"""
        try:
            # Verificar rate limiting
            if not await self.rate_limiter.wait_if_needed():
                self.log_service.log_debug("Brave search skipped - monthly limit reached", {"query": query})
                return []
                
            headers = {
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip',
                'x-subscription-token': self.brave_api_key
            }
            
            params = {
                'q': query,
                'count': 10
            }
            
            response = requests.get(
                'https://api.search.brave.com/res/v1/web/search',
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_service.log_debug("Brave search successful", {
                    "query": query,
                    "results_count": len(data.get('web', {}).get('results', []))
                })
                return data.get('web', {}).get('results', [])
            elif response.status_code == 429:
                self.log_service.log_debug("Brave search rate limited by API", {
                    "status_code": response.status_code,
                    "query": query
                })
                # Aguardar mais tempo em caso de rate limiting da API
                await asyncio.sleep(60)  # Aguardar 1 minuto
                return []
            else:
                self.log_service.log_debug("Brave search failed", {
                    "status_code": response.status_code,
                    "query": query
                })
                return []
                
        except Exception as e:
            self.log_service.log_debug("Brave search error", {"error": str(e), "query": query})
            return []
    
    def _filter_linkedin_person_urls(self, search_results: List[Dict[str, Any]]) -> List[str]:
        """Filtra URLs de perfis pessoais do LinkedIn"""
        linkedin_urls = []
        
        for result in search_results:
            url = result.get('url', '')
            if ('linkedin.com/in/' in url and 
                '/company/' not in url and
                '/school/' not in url and
                '/jobs/' not in url):
                linkedin_urls.append(url)
        
        return linkedin_urls



    async def _scrape_linkedin_person(self, linkedin_url: str) -> Optional[Dict[str, Any]]:
        """Scraping de perfil pessoal do LinkedIn usando CrawlAI"""
        try:
            # Usa o método do CrawlAIService
            async with CrawlAIService(self.log_service) as crawl_service:
                result = await crawl_service.scrape_linkedin_person(linkedin_url)
                
                if result and not result.get('error'):
                    # Formata o resultado no padrão esperado
                    formatted_result = {
                        'name': result.get('name'),
                        'headline': result.get('headline'),
                        'location': result.get('location'),
                        'current_company': result.get('current_company'),
                        'current_title': result.get('current_title'),
                        'profile_image': result.get('profile_image'),
                        'connections': result.get('connections'),
                        'skills': result.get('skills', []),
                        'experience': result.get('experience', []),
                        'education': result.get('education', []),
                        'source': 'crawlai',
                        'confidence_score': result.get('extraction_quality', 0.7)
                    }
                    
                    return formatted_result
            
        except Exception as e:
            self.log_service.log_debug("Error scraping LinkedIn person with CrawlAI", {
                "error": str(e),
                "url": linkedin_url
            })
        
        return None

    def _extract_person_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai nome da pessoa"""
        selectors = [
            'h1.text-heading-xlarge',
            '.pv-text-details__left-panel h1',
            '.top-card-layout__title',
            'h1[data-generated-suggestion-target]',
            '.pv-top-card--list li:first-child'
        ]
        return self._safe_extract_text(soup, selectors)
    
    def _extract_person_headline(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai headline/título profissional"""
        selectors = [
            '.text-body-medium.break-words',
            '.pv-text-details__left-panel .text-body-medium',
            '.top-card-layout__headline',
            '.pv-top-card--list li:nth-child(2)'
        ]
        return self._safe_extract_text(soup, selectors)
    
    def _extract_person_location(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai localização"""
        selectors = [
            '.text-body-small.inline.t-black--light.break-words',
            '.pv-text-details__left-panel .text-body-small',
            '.top-card-layout__first-subline',
            '.pv-top-card--list-bullet li'
        ]
        return self._safe_extract_text(soup, selectors)
    
    def _extract_current_company(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai empresa atual"""
        selectors = [
            '.pv-text-details__right-panel .hoverable-link-text',
            '.experience-item__title',
            '.pv-entity__company-summary-info h3',
            '.pv-top-card-v2-section__entity-name'
        ]
        return self._safe_extract_text(soup, selectors)
    
    def _extract_current_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai cargo atual"""
        selectors = [
            '.experience-item__subtitle',
            '.pv-entity__secondary-title',
            '.pv-top-card-v2-section__info h2'
        ]
        return self._safe_extract_text(soup, selectors)
    
    def _extract_profile_image(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai URL da foto de perfil"""
        try:
            img_selectors = [
                '.pv-top-card-profile-picture__image',
                '.profile-photo-edit__preview',
                '.presence-entity__image'
            ]
            
            for selector in img_selectors:
                img = soup.select_one(selector)
                if img:
                    src = img.get('src')
                    if src and 'http' in src:
                        return src
            return None
        except:
            return None
    
    def _extract_connections(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai número de conexões"""
        selectors = [
            '.pv-top-card--list-bullet li',
            '.t-black--light.t-normal',
            '.pv-top-card-v2-section__connections'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if 'conexões' in text.lower() or 'connections' in text.lower():
                    return text
        return None
    
    def _extract_skills(self, soup: BeautifulSoup) -> List[str]:
        """Extrai habilidades"""
        skills = []
        try:
            skill_selectors = [
                '.pv-skill-category-entity__name',
                '.skill-category-entity__name',
                '.pv-skill-entity__skill-name'
            ]
            
            for selector in skill_selectors:
                elements = soup.select(selector)
                for element in elements:
                    skill = element.get_text(strip=True)
                    if skill and skill not in skills:
                        skills.append(skill)
            
            return skills[:10]  # Limitar a 10 skills
        except:
            return []
    
    def _extract_experience(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extrai experiência profissional"""
        experience = []
        try:
            exp_sections = soup.select('.pv-profile-section__card-item-v2, .experience-item')
            
            for section in exp_sections[:5]:  # Limitar a 5 experiências
                company = self._safe_extract_text(section, ['.pv-entity__secondary-title', '.experience-item__subtitle'])
                title = self._safe_extract_text(section, ['.pv-entity__summary-info h3', '.experience-item__title'])
                duration = self._safe_extract_text(section, ['.pv-entity__date-range', '.experience-item__duration'])
                
                if company or title:
                    experience.append({
                        'company': company or 'Unknown',
                        'title': title or 'Unknown',
                        'duration': duration or 'Unknown'
                    })
            
            return experience
        except:
            return []
    
    def _extract_education(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extrai educação"""
        education = []
        try:
            edu_sections = soup.select('.pv-profile-section__card-item-v2, .education-item')
            
            for section in edu_sections[:3]:  # Limitar a 3 educações
                institution = self._safe_extract_text(section, ['.pv-entity__school-name', '.education-item__school'])
                degree = self._safe_extract_text(section, ['.pv-entity__degree-name', '.education-item__degree'])
                duration = self._safe_extract_text(section, ['.pv-entity__dates', '.education-item__duration'])
                
                if institution:
                    education.append({
                        'institution': institution,
                        'degree': degree or 'Unknown',
                        'duration': duration or 'Unknown'
                    })
            
            return education
        except:
            return []



    def _validate_person_match(self, person_data: Dict[str, Any], original_data: Dict[str, Any]) -> bool:
        """Valida se os dados extraídos correspondem à pessoa buscada"""
        if not person_data.get('name'):
            return False
        
        extracted_name = person_data.get('name', '').lower()
        
        # Verificar nome completo
        if original_data.get('full_name'):
            search_name = original_data['full_name'].lower()
            # Verificar se pelo menos 70% do nome bate
            name_parts = search_name.split()
            matches = sum(1 for part in name_parts if part in extracted_name)
            if matches / len(name_parts) < 0.7:
                return False
        
        # Verificar empresa se fornecida
        if original_data.get('company_name'):
            search_company = original_data['company_name'].lower()
            extracted_company = person_data.get('current_company', '').lower()
            if search_company not in extracted_company and extracted_company not in search_company:
                return False
        
        return True
    
    def _calculate_confidence_score(self, person_data: Dict[str, Any]) -> float:
        """Calcula score de confiança dos dados"""
        score = 0.0
        
        # Nome (peso 30%)
        if person_data.get('name') and person_data['name'] != 'Unknown':
            score += 0.3
        
        # Headline/título (peso 20%)
        if person_data.get('headline') and person_data['headline'] != 'Unknown':
            score += 0.2
        
        # Empresa atual (peso 20%)
        if person_data.get('current_company') and person_data['current_company'] != 'Unknown':
            score += 0.2
        
        # Localização (peso 10%)
        if person_data.get('location') and person_data['location'] != 'Unknown':
            score += 0.1
        
        # Experiência (peso 10%)
        if person_data.get('experience') and len(person_data['experience']) > 0:
            score += 0.1
        
        # Educação (peso 5%)
        if person_data.get('education') and len(person_data['education']) > 0:
            score += 0.05
        
        # Skills (peso 5%)
        if person_data.get('skills') and len(person_data['skills']) > 0:
            score += 0.05
        
        return min(score, 1.0)
    
    def _format_person_result(self, person_data: Dict[str, Any], source: str = 'unknown') -> Dict[str, Any]:
        """Formatar resultado final"""
        if not person_data:
            return self._create_empty_result()
        
        # Dividir nome em primeiro e último nome
        full_name = person_data.get('name', 'Unknown')
        name_parts = full_name.split() if full_name != 'Unknown' else []
        first_name = name_parts[0] if name_parts else 'Unknown'
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else 'Unknown'
        
        # Extrair localização
        location = person_data.get('location', 'Unknown')
        location_parts = location.split(',') if location != 'Unknown' else []
        city = location_parts[0].strip() if location_parts else 'Unknown'
        region = location_parts[1].strip() if len(location_parts) > 1 else 'Unknown'
        country = location_parts[-1].strip() if len(location_parts) > 2 else 'Unknown'
        
        result = {
            'full_name': full_name,
            'first_name': first_name,
            'last_name': last_name,
            'headline': person_data.get('headline', 'Unknown'),
            'current_company': person_data.get('current_company', 'Unknown'),
            'current_title': person_data.get('current_title', 'Unknown'),
            'location': location,
            'city': city,
            'region': region,
            'country': country,
            'linkedin_url': person_data.get('linkedin_url', ''),
            'profile_image': person_data.get('profile_image', ''),
            'connections': person_data.get('connections', 'Unknown'),
            'skills': person_data.get('skills', []),
            'experience': person_data.get('experience', []),
            'education': person_data.get('education', []),
            'social_media': [],  # Pode ser expandido futuramente
            'confidence_score': self._calculate_confidence_score(person_data),
            'data_source': source,
            'last_updated': datetime.now().isoformat()
        }
        
        return result
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """Cria resultado vazio quando nenhuma estratégia funciona"""
        return {
            'full_name': 'Unknown',
            'first_name': 'Unknown',
            'last_name': 'Unknown',
            'headline': 'Unknown',
            'current_company': 'Unknown',
            'current_title': 'Unknown',
            'location': 'Unknown',
            'city': 'Unknown',
            'region': 'Unknown',
            'country': 'Unknown',
            'linkedin_url': '',
            'profile_image': '',
            'connections': 'Unknown',
            'skills': [],
            'experience': [],
            'education': [],
            'social_media': [],
            'confidence_score': 0.0,
            'data_source': 'none',
            'last_updated': datetime.now().isoformat(),
            'error': 'Não foi possível encontrar dados para esta pessoa'
        }

    async def close(self):
        """Fecha recursos abertos"""
        try:
            if hasattr(self, 'session') and self.session:
                await self.session.close()
            if hasattr(self, 'browser') and self.browser:
                await self.browser.close()
            if hasattr(self, 'linkedin_browser') and self.linkedin_browser:
                await self.linkedin_browser.close()
        except Exception as e:
            self.log_service.log_debug("Error closing resources", {"error": str(e)})