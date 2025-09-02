import os
import logging
import asyncio
import time
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from urllib.parse import urlparse

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
from crawl4ai.types import ExtractionStrategy
from crawl4ai.async_configs import LLMConfig

from .log_service import LogService
from .models import CompanyRequest, CompanyResponse, SocialMedia, Employee
from .enhanced_social_extractor import EnhancedSocialExtractor
from .enhanced_linkedin_scraper import EnhancedLinkedInScraper
from api.services.instagram_scraper import InstagramScraperService

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
                "provider": "deepseek",
                "api_token": os.getenv("DEEPSEEK_API_KEY"),
                "base_url": "https://api.deepseek.com"
            }
        elif os.getenv("OPENAI_API_KEY"):
            return {
                "provider": "openai",
                "api_token": os.getenv("OPENAI_API_KEY"),
                "base_url": None
            }
        elif os.getenv("ANTHROPIC_API_KEY"):
            return {
                "provider": "anthropic",
                "api_token": os.getenv("ANTHROPIC_API_KEY"),
                "base_url": None
            }
        else:
            # Fallback para Ollama local
            return {
                "provider": "ollama",
                "api_token": None,
                "base_url": "http://localhost:11434"
            }
            
    def _get_llm_client(self, llm_config_data):
        """Retorna um cliente LLM configurado para extração de texto"""
        provider = llm_config_data["provider"]
        api_token = llm_config_data["api_token"]
        base_url = llm_config_data.get("base_url")
        
        # Verificar se os pacotes necessários estão instalados antes de tentar importar
        try:
            if provider == "openai" or provider == "deepseek":
                # Tentar importar o pacote langchain_openai
                try:
                    from langchain_openai import ChatOpenAI
                except ImportError:
                    # Instalar o pacote automaticamente se não estiver disponível
                    import subprocess
                    import sys
                    self.log_service.log_debug(f"Instalando pacote langchain_openai automaticamente", {"provider": provider})
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "langchain-openai"])
                    from langchain_openai import ChatOpenAI
                
                if provider == "openai":
                    return ChatOpenAI(
                        model_name="gpt-4-turbo",
                        openai_api_key=api_token,
                        temperature=0.1
                    )
                else:  # deepseek
                    return ChatOpenAI(
                        model_name="deepseek-chat",
                        openai_api_key=api_token,
                        openai_api_base=base_url,
                        temperature=0.1
                    )
            elif provider == "anthropic":
                # Tentar importar o pacote langchain_anthropic
                try:
                    from langchain_anthropic import ChatAnthropic
                except ImportError:
                    # Instalar o pacote automaticamente se não estiver disponível
                    import subprocess
                    import sys
                    self.log_service.log_debug(f"Instalando pacote langchain_anthropic automaticamente", {"provider": provider})
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "langchain-anthropic"])
                    from langchain_anthropic import ChatAnthropic
                    
                return ChatAnthropic(
                    model_name="claude-3-opus-20240229",
                    anthropic_api_key=api_token,
                    temperature=0.1
                )
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
        except Exception as e:
            self.log_service.log_debug(f"Error configuring LLM client: {str(e)}", {"provider": provider})
            # Fallback para um método alternativo de extração que não depende de LLM
            return None
        
    async def __aenter__(self):
        """Context manager para inicializar o crawler"""
        self.crawler = AsyncWebCrawler(verbose=True)
        await self.crawler.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager para fechar o crawler"""
        if self.crawler:
            await self.crawler.__aexit__(exc_type, exc_val, exc_tb)
    
    async def _extract_json_from_markdown(self, markdown, schema):
        """Extrai dados estruturados de markdown usando LLM"""
        try:
            llm_config_data = self._get_llm_config()
            llm = self._get_llm_client(llm_config_data)
            
            if llm is None:
                self.log_service.log_debug("LLM client not available for extraction", {})
                return {}
            
            # Limitar o tamanho do markdown para não exceder limites de tokens
            markdown_truncated = markdown[:15000] if len(markdown) > 15000 else markdown
            
            # DEBUG: Log do conteúdo markdown
            print(f"DEBUG: Markdown content length: {len(markdown)}")
            print(f"DEBUG: Markdown truncated length: {len(markdown_truncated)}")
            print(f"DEBUG: First 500 chars of markdown: {markdown_truncated[:500]}")
            
            # Criar prompt para extração com prioridade para redes sociais
            prompt = f"""Extraia informações estruturadas sobre a empresa a partir do seguinte conteúdo de website:
            
            {markdown_truncated}
            
            PRIORIDADES DE EXTRAÇÃO:
            1. REDES SOCIAIS (ALTA PRIORIDADE):
               - LinkedIn: Procure por URLs do LinkedIn da empresa (linkedin.com/company/)
               - Instagram: Procure por URLs do Instagram (@username ou instagram.com/)
               - WhatsApp: Procure por números de WhatsApp ou links wa.me/
               - Facebook, Twitter, YouTube, TikTok: URLs completas
            
            2. Para cada rede social encontrada:
               - Extraia a URL completa
               - Se possível, extraia nome de usuário/handle
               - Procure por informações de seguidores/followers
            
            3. DADOS GERAIS DA EMPRESA:
               - Nome, descrição, indústria, serviços
               - Informações de contato (email, telefone)
               - Localização, ano de fundação, tamanho da equipe
            
            Retorne apenas um objeto JSON válido seguindo este schema:
            {json.dumps(schema, indent=2)}
            
            Não inclua explicações, apenas o JSON válido.
            """
            
            # Usar o LLM para extrair JSON
            from langchain_core.messages import HumanMessage, SystemMessage
            
            messages = [
                SystemMessage(content="Você é um assistente especializado em extrair informações estruturadas de textos. Retorne apenas JSON válido sem explicações adicionais."),
                HumanMessage(content=prompt)
            ]
            
            # Usar ainvoke em vez de extract_json
            response = await llm.ainvoke(messages)
            content = response.content
            
            # Tentar extrair o JSON da resposta
            import re
            json_match = re.search(r'```json\s*(.+?)\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content
            
            # Limpar e analisar o JSON
            json_str = re.sub(r'^```json\s*|\s*```$', '', json_str.strip())
            
            # Tentar diferentes abordagens para extrair JSON válido
            try:
                extracted_data = json.loads(json_str)
            except json.JSONDecodeError:
                # Tentar encontrar qualquer objeto JSON na string
                json_pattern = re.search(r'\{.*\}', json_str, re.DOTALL)
                if json_pattern:
                    try:
                        extracted_data = json.loads(json_pattern.group(0))
                    except:
                        self.log_service.log_debug("Failed to parse JSON from LLM response", {"content": json_str[:200]})
                        return {}
                else:
                    self.log_service.log_debug("No JSON found in LLM response", {"content": json_str[:200]})
                    return {}
            
            return extracted_data
        except Exception as e:
            self.log_service.log_debug("JSON extraction from markdown failed", {"error": str(e)})
            return {}
    
    async def scrape_company_website(self, url: str) -> Dict[str, Any]:
        """Scraping avançado de website de empresa usando Crawl4AI"""
        try:
            if not self.crawler:
                raise Exception("Crawler not initialized. Use async context manager.")
            
            # Obter configuração LLM dinâmica
            llm_config_data = self._get_llm_config()
            
            # Estratégia de extração LLM para dados de empresa
            extraction_strategy = LLMExtractionStrategy(
                llm_config=LLMConfig(
                    provider=llm_config_data["provider"],
                    api_token=llm_config_data["api_token"],
                    base_url=llm_config_data["base_url"]
                ),
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
                    "await new Promise(resolve => setTimeout(resolve, 5000));",  # Aguardar carregamento
                ],
                wait_for="networkidle",
                page_timeout=60000
            )
            
            # Adicionar log de depuração detalhado sobre a execução do Crawl4AI
            self.log_service.log_debug("Crawl4AI execution details", { 
                "url": url, 
                "success": result.success, 
                "has_content": bool(result.extracted_content), 
                "content_length": len(result.extracted_content) if result.extracted_content else 0, 
                "has_markdown": bool(result.markdown), 
                "markdown_length": len(result.markdown) if result.markdown else 0, 
                "metadata": result.metadata 
            })
            
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
                # Tentar extrair informações do markdown se disponível
                if result.success and result.markdown:
                    self.log_service.log_debug("Attempting to extract from markdown", {
                        "url": url,
                        "markdown_length": len(result.markdown)
                    })
                    
                    # Usar o LLM para extrair informações do markdown
                    try:
                        llm_config_data = self._get_llm_config()
                        llm_client = self._get_llm_client(llm_config_data)
                        
                        # Prompt para extrair informações do markdown
                        prompt = f"""Extraia informações estruturadas sobre a empresa a partir do seguinte conteúdo de website:
                        
                        {result.markdown[:15000]}  # Limitar para não exceder tokens
                        
                        Retorne apenas um objeto JSON com os seguintes campos (deixe em branco se não encontrar):
                        - company_name: nome da empresa
                        - description: descrição da empresa
                        - industry: setor/indústria
                        - services: array de serviços oferecidos
                        - products: array de produtos oferecidos
                        - contact_info: objeto com email, phone, address
                        - social_media: objeto com linkedin, twitter, facebook, instagram, whatsapp, youtube, tiktok (PRIORIDADE ALTA: procure especialmente por LinkedIn, Instagram e WhatsApp)
                        - team_size: tamanho da equipe
                        - founded_year: ano de fundação
                        - headquarters: sede da empresa
                        
                        INSTRUÇÕES ESPECIAIS PARA REDES SOCIAIS:
                        - LinkedIn: procure por URLs como linkedin.com/company/[nome] ou linkedin.com/in/[perfil]
                        - Instagram: procure por URLs como instagram.com/[usuario] ou @[usuario]
                        - WhatsApp: procure por números de telefone com WhatsApp, links wa.me/ ou menções ao WhatsApp
                        - Extraia URLs completas e válidas sempre que possível
                        - Se encontrar perfis de redes sociais, inclua também informações como nome de usuário, seguidores, etc.
                        """
                        
                        # Chamar o LLM para extrair informações
                        extracted_json = await llm_client.extract_json(prompt)
                        
                        if extracted_json:
                            # Adicionar metadados
                            crawl_metadata = {
                                "url": url,
                                "title": result.metadata.get("title", ""),
                                "description": result.metadata.get("description", ""),
                                "keywords": result.metadata.get("keywords", []),
                                "crawl_timestamp": datetime.now().isoformat(),
                                "content_length": len(result.markdown) if result.markdown else 0,
                                "extraction_method": "crawl4ai_markdown_fallback"
                            }
                            
                            # Combinar dados extraídos com metadados
                            final_result = {
                                **extracted_json,
                                "_metadata": crawl_metadata,
                                "raw_markdown": result.markdown[:5000] if result.markdown else "",
                                "quality_score": self._assess_extraction_quality(extracted_json)
                            }
                            
                            self.log_service.log_debug("Markdown extraction successful", {
                                "url": url,
                                "extracted_fields": list(extracted_json.keys()),
                                "quality_score": final_result["quality_score"]
                            })
                            
                            return final_result
                    except Exception as e:
                        self.log_service.log_debug("Markdown extraction failed", {
                            "url": url,
                            "error": str(e)
                        })
                
                # Se tudo falhar, retornar erro
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
            llm_config_data = self._get_llm_config()
            
            extraction_strategy = LLMExtractionStrategy(
                provider=llm_config_data["provider"],
                api_token=llm_config_data["api_token"],
                base_url=llm_config_data["base_url"],
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
                page_timeout=60000
            )
            
            # Adicionar log de depuração detalhado sobre a execução do Crawl4AI
            self.log_service.log_debug("Crawl4AI execution details", { 
                "url": url, 
                "success": result.success, 
                "has_content": bool(result.extracted_content), 
                "content_length": len(result.extracted_content) if result.extracted_content else 0, 
                "has_markdown": bool(result.markdown), 
                "markdown_length": len(result.markdown) if result.markdown else 0, 
                "metadata": result.metadata 
            })
            
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
        """Scraping avançado de página do LinkedIn usando EnhancedLinkedInScraper"""
        try:
            self.log_service.log_debug("Starting Enhanced LinkedIn scraping", {"url": linkedin_url})
            
            # Usar o novo EnhancedLinkedInScraper
            result = await self.enhanced_linkedin_scraper.scrape_linkedin_company(
                linkedin_url, 
                provider="firecrawl",  # ou "crawlai"
                log_service=self.log_service
            )
            
            if result and not result.get("error"):
                self.log_service.log_debug("Enhanced LinkedIn extraction successful", {
                    "url": linkedin_url,
                    "company_name": result.get("name", "Unknown"),
                    "confidence_score": result.get("confidence_score", 0),
                    "data_sources": result.get("data_sources", [])
                })
                return result
            else:
                self.log_service.log_debug("Enhanced LinkedIn extraction failed", {
                    "url": linkedin_url,
                    "error": result.get("error", "Unknown error")
                })
                return result or {"error": "LinkedIn extraction failed", "url": linkedin_url}
                
        except Exception as e:
            self.log_service.log_debug("Enhanced LinkedIn scraping error", {
                "url": linkedin_url,
                "error": str(e)
            })
            return {"error": str(e), "url": linkedin_url}
            
    async def scrape_linkedin_person(self, linkedin_url: str) -> Dict[str, Any]:
        """Scraping de perfil pessoal LinkedIn usando EnhancedLinkedInScraper"""
        try:
            self.log_service.log_debug("Starting Enhanced LinkedIn person scraping", {"url": linkedin_url})
            
            # Usar o novo EnhancedLinkedInScraper para perfis pessoais
            # Nota: O EnhancedLinkedInScraper é focado em empresas, mas pode ser adaptado
            # Por enquanto, mantemos a funcionalidade básica
            result = await self.enhanced_linkedin_scraper.scrape_linkedin_company(
                linkedin_url, 
                provider="firecrawl",
                log_service=self.log_service
            )
            
            if result and not result.get("error"):
                # Adaptar dados de empresa para formato de pessoa se necessário
                person_data = {
                    "name": result.get("name", ""),
                    "headline": result.get("tagline", ""),
                    "location": result.get("headquarters", ""),
                    "current_company": result.get("name", ""),
                    "current_title": "",
                    "profile_image": "",
                    "connections": result.get("followers_count", ""),
                    "skills": result.get("specialties", []),
                    "experience": [],
                    "education": [],
                    "linkedin_url": linkedin_url,
                    "extraction_quality": result.get("confidence_score", 0),
                    "extraction_timestamp": datetime.now().isoformat()
                }
                
                self.log_service.log_debug("Enhanced LinkedIn person extraction successful", {
                    "url": linkedin_url,
                    "name": person_data.get("name", "Unknown"),
                    "quality": person_data.get("extraction_quality", 0)
                })
                
                return person_data
            else:
                self.log_service.log_debug("Enhanced LinkedIn person extraction failed", {
                    "url": linkedin_url,
                    "error": result.get("error", "Unknown error")
                })
                return result or {"error": "LinkedIn person extraction failed", "url": linkedin_url}
                
        except Exception as e:
            self.log_service.log_debug("LinkedIn person scraping error", {
                "url": linkedin_url,
                "error": str(e)
            })
            return {"error": str(e), "url": linkedin_url}
            
    async def find_linkedin_on_website(self, website_url: str) -> Optional[str]:
        """Busca URLs do LinkedIn em websites usando EnhancedLinkedInScraper"""
        try:
            # Usar o EnhancedLinkedInScraper para encontrar LinkedIn
            result = await self.enhanced_linkedin_scraper.find_linkedin_on_website(website_url)
            
            if result and result.get('linkedin_url'):
                self.log_service.log_debug("LinkedIn URL found on website", {
                    "website_url": website_url,
                    "linkedin_url": result['linkedin_url'],
                    "confidence": result.get('confidence_score', 0)
                })
                return result['linkedin_url']
            else:
                self.log_service.log_debug("No LinkedIn URL found on website", {
                    "website_url": website_url
                })
                return None
                
        except Exception as e:
            self.log_service.log_debug("Error finding LinkedIn on website", {
                "error": str(e),
                "url": website_url
            })
            return None

    async def extract_company_data_from_html(self, html_content: str, url: str = None) -> Dict[str, Any]:
        """Extrai dados da empresa de conteúdo HTML usando LLM com foco em redes sociais"""
        try:
            llm_config_data = self._get_llm_config()
            
            extraction_strategy = LLMExtractionStrategy(
                llm_config=LLMConfig(
                    provider=llm_config_data["provider"],
                    api_token=llm_config_data["api_token"],
                    base_url=llm_config_data["base_url"]
                ),
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
                                "linkedin": {"type": "string", "description": "URL do perfil LinkedIn da empresa (prioridade alta)"},
                                "instagram": {"type": "string", "description": "URL do perfil Instagram da empresa (prioridade alta)"},
                                "whatsapp": {"type": "string", "description": "Número WhatsApp Business da empresa (prioridade alta)"},
                                "twitter": {"type": "string", "description": "URL do perfil Twitter da empresa"},
                                "facebook": {"type": "string", "description": "URL do perfil Facebook da empresa"},
                                "youtube": {"type": "string", "description": "URL do canal YouTube da empresa"},
                                "tiktok": {"type": "string", "description": "URL do perfil TikTok da empresa"}
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
                
                # Adicionar log de depuração detalhado sobre a execução do Crawl4AI
                self.log_service.log_debug("Crawl4AI execution details", { 
                    "url": website_url, 
                    "success": result.success, 
                    "has_content": bool(result.extracted_content), 
                    "content_length": len(result.extracted_content) if result.extracted_content else 0, 
                    "has_markdown": bool(result.markdown), 
                    "markdown_length": len(result.markdown) if result.markdown else 0, 
                    "metadata": result.metadata 
                })
                
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
        # Inicializar Enhanced Social Extractor
        self.enhanced_social_extractor = EnhancedSocialExtractor(log_service)
        # Inicializar Enhanced LinkedIn Scraper
        self.enhanced_linkedin_scraper = EnhancedLinkedInScraper(log_service)
        # Inicializar Instagram Scraper Service
        # Usando o scraper real do Instagram com Hyperbrowser
        from api.services.hyperbrowser_instagram_scraper import HyperbrowserInstagramScraperService
        self.instagram_scraper = HyperbrowserInstagramScraperService(log_service)

    async def enrich_company(self, company_data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """Enriquece os dados de uma empresa, orquestrando a busca e o scraping"""
        domain = company_data.get("domain")
        if not domain:
            raise ValueError("O domínio da empresa é obrigatório")

        schema = company_data.get("schema", self._get_default_schema())
        
        try:
            async with CrawlAIService(log_service=self.log_service) as crawler:
                scraped_data = await self.scrape_company_website(
                    crawler,
                    domain,
                    schema,
                    user_id
                )
            # Estruturar o retorno com o campo enriched_data esperado pela API
            return {
                "enriched_data": scraped_data,
                "domain": domain,
                "status": "success"
            }
        except Exception as e:
            self.log_service.log_debug(f"Erro no enriquecimento do domínio {domain}: {e}", {"domain": domain, "user_id": user_id})
            return {
                "enriched_data": {},
                "domain": domain,
                "status": "error",
                "error": f"Falha no enriquecimento: {e}"
            }

    def _get_default_schema(self) -> Dict[str, Any]:
        """Retorna o schema padrão para enriquecimento de empresas"""
        return {
            "name": "string",
            "description": "string",
            "industry": "string",
            "size": "string",
            "founded": "string",
            "headquarters": "string",
            "website": "string",
            "linkedin": "string",
            "employees": "array",
            "social_media": [
                {
                    "platform": "string (instagram, facebook, twitter, linkedin, youtube, etc.)",
                    "url": "string (URL completa da rede social)"
                }
            ],
            "instagram": {
                "url": "string",
                "username": "string",
                "name": "string",
                "bio": "string",
                "email": "string",
                "phone": "string",
                "followers_count": "number",
                "following_count": "number",
                "posts_count": "number"
            },
            "linkedin_data": {
                "url": "string",
                "company_name": "string",
                "industry": "string",
                "size": "string",
                "headquarters": "string",
                "founded": "string",
                "description": "string",
                "followers_count": "number",
                "employees_count": "number"
            },
            "whatsapp": {
                "phone": "string",
                "business_name": "string",
                "description": "string",
                "verified": "boolean"
            }
        }
    
    async def _extract_json_from_markdown(self, markdown: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extrai dados estruturados de markdown usando LLM"""
        try:
            # Usar DeepSeek como configurado no sistema
            import httpx
            
            deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
            if not deepseek_api_key:
                self.log_service.log_debug("DeepSeek API key not found")
                return {}
            
            # Limitar o tamanho do markdown para não exceder limites de tokens
            markdown_truncated = markdown[:15000] if len(markdown) > 15000 else markdown
            
            # Criar prompt para extração
            prompt = f"""Extraia informações estruturadas sobre a empresa a partir do seguinte conteúdo de website:
            
            {markdown_truncated}
            
            INSTRUÇÕES ESPECÍFICAS PARA CADA CAMPO:
            
            1. NAME (nome da empresa):
            - Procure no título da página, cabeçalho, logo, seção "Sobre nós"
            - Pode estar em tags <title>, <h1>, ou texto próximo ao logo
            
            2. DESCRIPTION (descrição):
            - Procure em seções "Sobre", "Quem somos", "Nossa missão", meta description
            - Resumo do que a empresa faz, seus serviços ou produtos principais
            
            3. INDUSTRY (setor/indústria):
            - Identifique o setor baseado nos produtos/serviços mencionados
            - Ex: "Tecnologia", "Energia Renovável", "Consultoria", "Saúde", etc.
            
            4. SIZE (tamanho da empresa):
            - Procure por "funcionários", "colaboradores", "equipe", "team size"
            - Números como "50+ funcionários", "100-500 pessoas", "startup", "pequena empresa"
            - Seções "Sobre", "Carreiras", "Trabalhe conosco"
            
            5. FOUNDED (ano de fundação):
            - Procure por "fundada em", "desde", "estabelecida", "criada em"
            - Anos como "2010", "desde 1995", "fundada em 2020"
            - Seções "História", "Sobre", "Nossa jornada"
            
            6. HEADQUARTERS (sede/localização):
            - Procure endereços completos, cidades, países
            - Seções "Contato", "Endereço", "Localização", "Escritórios"
            - Formatos como "São Paulo, Brasil", "New York, USA"
            
            7. WEBSITE (site oficial):
            - URL principal do website (geralmente o domínio atual)
            - Remova parâmetros e mantenha apenas o domínio principal
            
            8. LINKEDIN (perfil LinkedIn da empresa):
            - Procure links para linkedin.com/company/ ou linkedin.com/in/
            - Pode estar em rodapés, seções de contato, ícones sociais
            
            9. REDES SOCIAIS (social_media):
            - Procure cuidadosamente por links de Instagram, Facebook, WhatsApp, Twitter/X, YouTube
            - Estes links podem estar em rodapés, cabeçalhos, seções "Contato", "Siga-nos"
            - Se encontrar apenas ícones, tente inferir as URLs baseado no contexto
            
            FORMATO OBRIGATÓRIO PARA SOCIAL_MEDIA:
            O campo "social_media" DEVE ser um array de objetos:
            "social_media": [
                {{"platform": "instagram", "url": "https://instagram.com/empresa"}},
                {{"platform": "facebook", "url": "https://facebook.com/empresa"}}
            ]
            
            INSTRUÇÕES GERAIS:
            - Seja preciso e factual, não invente informações
            - Se não encontrar uma informação, deixe o campo vazio ou null
            - Priorize informações que aparecem múltiplas vezes ou em seções importantes
            - Para números e datas, extraia apenas os valores numéricos
            
            Retorne apenas um objeto JSON válido seguindo este schema:
            {json.dumps(schema, indent=2)}
            
            Não inclua explicações, apenas o JSON válido.
            """
            
            # Fazer requisição para DeepSeek
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {deepseek_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {
                                "role": "system",
                                "content": "Você é um assistente especializado em extrair informações estruturadas de textos. Retorne apenas JSON válido sem explicações adicionais."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0
                    },
                    timeout=30.0
                )
            
            if response.status_code != 200:
                self.log_service.log_debug("DeepSeek API error", {"status_code": response.status_code})
                return {}
            
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # DEBUG: Log da resposta do LLM
            print(f"DEBUG: LLM response length: {len(content)}")
            print(f"DEBUG: LLM response content: {content[:1000]}")
            
            # Tentar extrair o JSON da resposta
            import re
            json_match = re.search(r'```json\s*(.+?)\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content
            
            # Limpar e analisar o JSON
            json_str = re.sub(r'^```json\s*|\s*```$', '', json_str.strip())
            
            # Tentar diferentes abordagens para extrair JSON válido
            try:
                extracted_data = json.loads(json_str)
            except json.JSONDecodeError:
                # Tentar encontrar qualquer objeto JSON na string
                json_pattern = re.search(r'\{.*\}', json_str, re.DOTALL)
                if json_pattern:
                    try:
                        extracted_data = json.loads(json_pattern.group(0))
                    except:
                        self.log_service.log_debug("Failed to parse JSON from LLM response", {"content": json_str[:200]})
                        return {}
                else:
                    self.log_service.log_debug("No JSON found in LLM response", {"content": json_str[:200]})
                    return {}
            
            return extracted_data
        except Exception as e:
            self.log_service.log_debug("JSON extraction from markdown failed", {"error": str(e)})
            return {}

    def _map_data_to_schema(self, extracted_data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Mapeia dados extraídos para o schema esperado"""
        try:
            if not extracted_data or not isinstance(extracted_data, dict):
                return {}
            
            mapped_data = {}
            # Verificar se o schema tem 'properties' ou se é um schema simples
            if isinstance(schema, dict):
                schema_properties = schema.get('properties', schema)
            else:
                # Se schema não é um dicionário, usar um dicionário vazio
                schema_properties = {}
            
            # Mapear campos extraídos diretamente para o schema
            for extracted_field, extracted_value in extracted_data.items():
                if extracted_field == '_metadata':
                    continue
                
                self.log_service.log_debug(f"Processing field: {extracted_field}", {
                    "field_name": extracted_field,
                    "field_type": type(extracted_value).__name__,
                    "field_value_preview": str(extracted_value)[:100] if extracted_value else None
                })
                
                # Verificar se o campo existe no schema
                if extracted_field in schema_properties and extracted_value is not None:
                    field_config = schema_properties[extracted_field]
                    
                    # Se field_config é uma string (schema simples), tratar como tipo
                    if isinstance(field_config, str):
                        field_type = field_config
                    elif isinstance(field_config, dict):
                        field_type = field_config.get('type', 'string')
                    elif isinstance(field_config, list):
                        # Se é uma lista, assumir que é um array
                        field_type = 'array'
                    else:
                        # Fallback para string se não conseguir determinar o tipo
                        field_type = 'string'
                    
                    # Validar e converter o tipo se necessário
                    if field_type == 'string' and not isinstance(extracted_value, str):
                        mapped_data[extracted_field] = str(extracted_value)
                    elif field_type == 'array' and not isinstance(extracted_value, list):
                        # Tratamento especial para campos específicos
                        if extracted_field == 'employees':
                            # Converter employees para lista de dicionários
                            if isinstance(extracted_value, dict):
                                mapped_data[extracted_field] = [extracted_value]
                            elif isinstance(extracted_value, str):
                                try:
                                    # Tentar parsear como JSON
                                    import json
                                    parsed = json.loads(extracted_value)
                                    if isinstance(parsed, dict):
                                        mapped_data[extracted_field] = [parsed]
                                    elif isinstance(parsed, list):
                                        mapped_data[extracted_field] = parsed
                                    else:
                                        mapped_data[extracted_field] = []
                                except:
                                    mapped_data[extracted_field] = []
                            else:
                                mapped_data[extracted_field] = []
                        elif extracted_field == 'social_media':
                            # Converter social_media para lista de dicionários
                            if isinstance(extracted_value, dict):
                                # Converter dict de plataformas para lista
                                social_list = []
                                for platform, url in extracted_value.items():
                                    if url and url.strip():
                                        social_list.append({
                                            "platform": platform,
                                            "url": url.strip()
                                        })
                                mapped_data[extracted_field] = social_list
                            elif isinstance(extracted_value, str):
                                try:
                                    import json
                                    parsed = json.loads(extracted_value)
                                    if isinstance(parsed, dict):
                                        social_list = []
                                        for platform, url in parsed.items():
                                            if url and url.strip():
                                                social_list.append({
                                                    "platform": platform,
                                                    "url": url.strip()
                                                })
                                        mapped_data[extracted_field] = social_list
                                    else:
                                        mapped_data[extracted_field] = []
                                except:
                                    mapped_data[extracted_field] = []
                            else:
                                mapped_data[extracted_field] = []
                        else:
                            # Tratamento padrão para arrays
                            if isinstance(extracted_value, str):
                                mapped_data[extracted_field] = [item.strip() for item in extracted_value.split(',') if item.strip()]
                            else:
                                mapped_data[extracted_field] = [str(extracted_value)]
                    elif field_type == 'object' and not isinstance(extracted_value, dict):
                        # Tratamento especial para campos de redes sociais
                        if extracted_field in ['instagram', 'linkedin_data', 'whatsapp', 'facebook', 'twitter', 'youtube']:
                            # Se não é um objeto válido, inicializar como None para permitir fallback
                            mapped_data[extracted_field] = None
                        else:
                            # Para outros objetos, criar um objeto básico
                            mapped_data[extracted_field] = {"value": str(extracted_value)}
                    else:
                        mapped_data[extracted_field] = extracted_value
            
            # Garantir que campos de redes sociais existam (mesmo como None) para permitir fallback
            social_media_fields = ['instagram', 'linkedin_data', 'whatsapp', 'facebook', 'twitter', 'youtube']
            for field in social_media_fields:
                if field not in mapped_data:
                    mapped_data[field] = None
            
            # Adicionar metadados de qualidade
            mapped_data['_metadata'] = {
                'extraction_timestamp': datetime.now().isoformat(),
                'fields_extracted': len(mapped_data),
                'schema_fields': len(schema_properties),
                'completion_rate': len(mapped_data) / len(schema_properties) if schema_properties else 0
            }
            
            return mapped_data
            
        except Exception as e:
            self.log_service.log_debug("Error mapping data to schema", {
                "error": str(e),
                "extracted_data_keys": list(extracted_data.keys()) if isinstance(extracted_data, dict) else "not_dict"
            })
            return {}

    async def scrape_company_website(self, crawler: CrawlAIService, domain: str, schema: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """Raspa o site da empresa para extrair informações detalhadas com base em um schema"""
        print(f"🔍 INICIANDO SCRAPING PARA: {domain}")
        print(f"DEBUG: Função scrape_company_website chamada para {domain}")
        try:
            from crawl4ai.async_configs import LLMConfig
            
            llm_config = LLMConfig(
                provider="deepseek",
                api_token=os.getenv("DEEPSEEK_API_KEY"),
                base_url="https://api.deepseek.com"
            )
            
            # Usar CrawlAI com estratégia de extração LLM
            try:
                result = await crawler.crawler.arun(
                    url=f"https://{domain}",
                    extraction_strategy=LLMExtractionStrategy(
                        llm_config=llm_config,
                        schema=schema,
                        instruction="Extract company information from the webpage according to the provided schema. Focus on finding accurate business details, contact information, and social media links."
                    ),
                    word_count_threshold=10,
                    bypass_cache=True
                )
                
                # Log adicional para verificar o conteúdo HTML
                self.log_service.log_debug("CrawlAI HTML content debug", {
                    "domain": domain,
                    "html_exists": result.html is not None if result else False,
                    "html_length": len(result.html) if result and result.html else 0,
                    "html_preview": result.html[:500] if result and result.html else None
                })
                
                # Se temos HTML, vamos processar com nosso próprio LLM
                if result and result.html:
                    # Converter HTML para markdown usando BeautifulSoup
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(result.html, 'html.parser')
                    
                    # Remover scripts e styles
                    for script in soup(["script", "style"]):
                        script.decompose()
                    
                    # Extrair texto limpo
                    text_content = soup.get_text()
                    
                    # Limpar texto
                    lines = (line.strip() for line in text_content.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    clean_text = '\n'.join(chunk for chunk in chunks if chunk)
                    
                    # Truncar se muito longo
                    if len(clean_text) > 8000:
                        clean_text = clean_text[:8000] + "..."
                    
                    # Processar com nosso LLM
                    extracted_data = await self._extract_json_from_markdown(clean_text, schema)
                    
                    if extracted_data:
                        # Simular o resultado do CrawlAI
                        result.extracted_content = extracted_data
                        self.log_service.log_debug("Successfully processed HTML with our LLM", {
                            "domain": domain,
                            "extracted_fields": list(extracted_data.keys()) if extracted_data else []
                        })
                
            except Exception as e:
                self.log_service.log_debug("CrawlAI execution failed", {
                    "domain": domain,
                    "error": str(e)
                })
                result = None
            
            # Log de depuração para verificar o resultado do CrawlAI
            self.log_service.log_debug("CrawlAI result debug", {
                "domain": domain,
                "result_exists": result is not None,
                "extracted_content_exists": result.extracted_content is not None if result else False,
                "extracted_content_type": type(result.extracted_content).__name__ if result and result.extracted_content else None,
                "extracted_content_keys": list(result.extracted_content.keys()) if result and result.extracted_content and isinstance(result.extracted_content, dict) else None
            })
            
            if result and result.extracted_content:
                self.log_service.log_debug("CrawlAI extraction successful", {"domain": domain})
                try:
                    # Se extracted_content já é um dict, usar diretamente
                    if isinstance(result.extracted_content, dict):
                        extracted_data = result.extracted_content
                    else:
                        # Se é string JSON, fazer parse
                        extracted_data = json.loads(result.extracted_content)
                    
                    # Verificar se extracted_data é um dicionário válido
                    if not isinstance(extracted_data, dict):
                        self.log_service.log_debug("Extracted data is not a dict, converting", {
                            "type": type(extracted_data).__name__,
                            "value": str(extracted_data)[:200]
                        })
                        # Se for uma lista, tentar usar o primeiro item se for um dict
                        if isinstance(extracted_data, list) and len(extracted_data) > 0 and isinstance(extracted_data[0], dict):
                            extracted_data = extracted_data[0]
                        else:
                            # Se não conseguir converter, usar dict vazio
                            extracted_data = {}
                    
                    mapped_data = self._map_data_to_schema(extracted_data, schema)
                    
                    # Verificar se encontrou LinkedIn URL e fazer enriquecimento automático
                    linkedin_url = self._extract_linkedin_url_from_data(mapped_data)
                    if linkedin_url:
                        self.log_service.log_debug("LinkedIn URL found, starting automatic enrichment", {"linkedin_url": linkedin_url})
                        try:
                            linkedin_data = await self.scrape_linkedin_company(linkedin_url, user_id)
                            if linkedin_data and linkedin_data.get('enriched_data'):
                                # Mesclar dados do LinkedIn com dados do website
                                mapped_data = self._merge_linkedin_data(mapped_data, linkedin_data['enriched_data'])
                                self.log_service.log_debug("LinkedIn data merged successfully")
                        except Exception as e:
                            self.log_service.log_debug("Error during LinkedIn enrichment", {"error": str(e)})
                    
                    # Verificar se encontrou Instagram URL e fazer scraping
                    instagram_url = self._extract_instagram_url_from_data(mapped_data)
                    if instagram_url:
                        self.log_service.log_debug("Instagram URL found, starting profile scraping", {"instagram_url": instagram_url})
                        try:
                            scrape_result = await self.instagram_scraper.scrape_profile(instagram_url)
                            if "error" not in scrape_result:
                                # Adicionar dados do Instagram como objeto válido
                                mapped_data['instagram'] = scrape_result["data"]
                                self.log_service.log_debug("Instagram data added successfully")
                        except Exception as e:
                            self.log_service.log_debug("Error during Instagram scraping", {"error": str(e)})
                    
                    # Fallback: Se campos de redes sociais estão vazios, tentar extração via HTML
                    def is_empty_social_field(field):
                        if not field:
                            return True
                        if isinstance(field, dict):
                            # Verificar se é um dict vazio ou com valores vazios/zero
                            return not any(v for v in field.values() if v and v != 0 and v != '')
                        return False
                    
                    social_fields_empty = (
                        is_empty_social_field(mapped_data.get('instagram')) and 
                        is_empty_social_field(mapped_data.get('linkedin_data')) and 
                        is_empty_social_field(mapped_data.get('whatsapp')) and
                        is_empty_social_field(mapped_data.get('facebook')) and
                        is_empty_social_field(mapped_data.get('twitter')) and
                        is_empty_social_field(mapped_data.get('youtube'))
                    )
                    
                    # Debug: Checkpoint - chegou na verificação de redes sociais
                    print(f"DEBUG: Verificando campos de redes sociais para {domain}")
                    print(f"DEBUG: social_fields_empty = {social_fields_empty}")
                    print(f"DEBUG: has_html = {bool(result.html)}")
                    
                    # Debug: Log dos campos de redes sociais
                    self.log_service.log_debug("Social media fields check", {
                        "domain": domain,
                        "instagram": mapped_data.get('instagram'),
                        "linkedin_data": mapped_data.get('linkedin_data'),
                        "whatsapp": mapped_data.get('whatsapp'),
                        "facebook": mapped_data.get('facebook'),
                        "twitter": mapped_data.get('twitter'),
                        "youtube": mapped_data.get('youtube'),
                        "social_fields_empty": social_fields_empty,
                        "has_html": bool(result.html)
                    })
                    
                    # Sempre tentar extrair redes sociais do HTML quando disponível
                    if result.html:
                        self.log_service.log_debug("Extracting social media from HTML", {"domain": domain, "html_length": len(result.html)})
                        html_social_media_list = await self._extract_social_media_from_html(result.html)
                        
                        # Converter a lista de volta para o formato de dicionário para compatibilidade
                        html_social_data = {}
                        for item in html_social_media_list:
                            platform = item.get('platform')
                            if platform == 'linkedin':
                                platform = 'linkedin_data'
                                
                            if platform and platform in ['instagram', 'linkedin_data', 'whatsapp', 'facebook', 'twitter', 'youtube', 'tiktok', 'telegram']:
                                url = item.get('url')
                                if url:
                                    # Se tiver mais dados além da URL, criar um dicionário
                                    if len(item) > 2:  # platform e url + outros campos
                                        html_social_data[platform] = {
                                            'url': url,
                                            **{k: v for k, v in item.items() if k not in ['platform', 'url']}
                                        }
                                    else:
                                        html_social_data[platform] = url
                        
                        # Aplicar dados extraídos via HTML se não existirem
                        if html_social_data.get('instagram') and not mapped_data.get('instagram'):
                            mapped_data['instagram'] = html_social_data['instagram']
                        if html_social_data.get('linkedin_data') and not mapped_data.get('linkedin_data'):
                            mapped_data['linkedin_data'] = html_social_data['linkedin_data']
                        if html_social_data.get('whatsapp') and not mapped_data.get('whatsapp'):
                            mapped_data['whatsapp'] = html_social_data['whatsapp']
                        if html_social_data.get('facebook') and not mapped_data.get('facebook'):
                            mapped_data['facebook'] = html_social_data['facebook']
                        if html_social_data.get('twitter') and not mapped_data.get('twitter'):
                            mapped_data['twitter'] = html_social_data['twitter']
                        if html_social_data.get('youtube') and not mapped_data.get('youtube'):
                            mapped_data['youtube'] = html_social_data['youtube']
                        if html_social_data.get('tiktok') and not mapped_data.get('tiktok'):
                            mapped_data['tiktok'] = html_social_data['tiktok']
                        if html_social_data.get('telegram') and not mapped_data.get('telegram'):
                            mapped_data['telegram'] = html_social_data['telegram']
                    
                    # Normalizar campos de redes sociais para formato de dicionário
                    def normalize_social_field(field_value):
                        if isinstance(field_value, str):
                            return {'url': field_value}
                        elif isinstance(field_value, dict) and field_value.get('url'):
                            return field_value
                        return None
                    
                    # Aplicar normalização aos campos de redes sociais
                    if mapped_data.get('instagram'):
                        mapped_data['instagram'] = normalize_social_field(mapped_data['instagram'])
                    if mapped_data.get('linkedin_data'):
                        mapped_data['linkedin_data'] = normalize_social_field(mapped_data['linkedin_data'])
                    if mapped_data.get('whatsapp'):
                        mapped_data['whatsapp'] = normalize_social_field(mapped_data['whatsapp'])
                    if mapped_data.get('facebook'):
                        mapped_data['facebook'] = normalize_social_field(mapped_data['facebook'])
                    if mapped_data.get('twitter'):
                        mapped_data['twitter'] = normalize_social_field(mapped_data['twitter'])
                    if mapped_data.get('youtube'):
                        mapped_data['youtube'] = normalize_social_field(mapped_data['youtube'])
                    if mapped_data.get('tiktok'):
                        mapped_data['tiktok'] = normalize_social_field(mapped_data['tiktok'])
                    if mapped_data.get('telegram'):
                        mapped_data['telegram'] = normalize_social_field(mapped_data['telegram'])
                    if 'twitter' not in mapped_data or not isinstance(mapped_data.get('twitter'), dict):
                        mapped_data['twitter'] = None
                    if 'youtube' not in mapped_data or not isinstance(mapped_data.get('youtube'), dict):
                        mapped_data['youtube'] = None
                    
                    # Criar o campo social_media como lista de dicionários
                    social_media_list = []
                    
                    # Adicionar URLs de redes sociais encontradas
                    if mapped_data.get('facebook') and isinstance(mapped_data['facebook'], dict) and mapped_data['facebook'].get('url'):
                        social_media_list.append({
                            "platform": "facebook",
                            "url": mapped_data['facebook']['url']
                        })
                    if mapped_data.get('twitter') and isinstance(mapped_data['twitter'], dict) and mapped_data['twitter'].get('url'):
                        social_media_list.append({
                            "platform": "twitter", 
                            "url": mapped_data['twitter']['url']
                        })
                    if mapped_data.get('youtube') and isinstance(mapped_data['youtube'], dict) and mapped_data['youtube'].get('url'):
                        social_media_list.append({
                            "platform": "youtube",
                            "url": mapped_data['youtube']['url']
                        })
                    if mapped_data.get('instagram') and isinstance(mapped_data['instagram'], dict) and mapped_data['instagram'].get('url'):
                        social_media_list.append({
                            "platform": "instagram",
                            "url": mapped_data['instagram']['url']
                        })
                    if mapped_data.get('linkedin_data') and isinstance(mapped_data['linkedin_data'], dict) and mapped_data['linkedin_data'].get('url'):
                        social_media_list.append({
                            "platform": "linkedin",
                            "url": mapped_data['linkedin_data']['url']
                        })
                    if mapped_data.get('whatsapp') and isinstance(mapped_data['whatsapp'], dict) and mapped_data['whatsapp'].get('url'):
                        social_media_list.append({
                            "platform": "whatsapp",
                            "url": mapped_data['whatsapp']['url']
                        })
                    if mapped_data.get('tiktok') and isinstance(mapped_data['tiktok'], dict):
                        tiktok_entry = {
                            "platform": "tiktok"
                        }
                        if mapped_data['tiktok'].get('url'):
                            tiktok_entry["url"] = mapped_data['tiktok']['url']
                        if mapped_data['tiktok'].get('username'):
                            tiktok_entry["username"] = mapped_data['tiktok']['username']
                        if mapped_data['tiktok'].get('followers'):
                            tiktok_entry["followers"] = mapped_data['tiktok']['followers']
                        if mapped_data['tiktok'].get('likes'):
                            tiktok_entry["likes"] = mapped_data['tiktok']['likes']
                        if tiktok_entry.get('url') or tiktok_entry.get('username'):
                            social_media_list.append(tiktok_entry)
                    
                    if mapped_data.get('telegram') and isinstance(mapped_data['telegram'], dict):
                        telegram_entry = {
                            "platform": "telegram"
                        }
                        if mapped_data['telegram'].get('url'):
                            telegram_entry["url"] = mapped_data['telegram']['url']
                        if mapped_data['telegram'].get('username'):
                            telegram_entry["username"] = mapped_data['telegram']['username']
                        if mapped_data['telegram'].get('members'):
                            telegram_entry["members"] = mapped_data['telegram']['members']
                        if telegram_entry.get('url') or telegram_entry.get('username'):
                            social_media_list.append(telegram_entry)
                    
                    mapped_data['social_media'] = social_media_list
                    
                    print(f"DEBUG: Retornando dados mapeados para {domain}: {mapped_data.get('social_media', [])}")
                    return mapped_data
                except json.JSONDecodeError:
                    self.log_service.log_debug("CrawlAI returned invalid JSON, falling back to Firecrawl", {"domain": domain})
                    return await self._scrape_with_firecrawl(f"https://{domain}", schema, user_id)
            else:
                self.log_service.log_debug("CrawlAI returned no data, falling back to Firecrawl", {"domain": domain})
                return await self._scrape_with_firecrawl(f"https://{domain}", schema, user_id)
                
        except Exception as e:
            self.log_service.log_debug("CrawlAI extraction failed, falling back to Firecrawl", {"domain": domain, "error": str(e)})
            return await self._scrape_with_firecrawl(f"https://{domain}", schema, user_id)


        
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
            
    async def _enrich_by_instagram(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enriquecimento via URL do Instagram"""
        try:
            instagram_url = company_data.get("instagram_url")
            if not instagram_url:
                return {}
            
            self.log_service.log_debug("Starting Instagram enrichment", {"instagram_url": instagram_url})
            
            # Extrair username do Instagram da URL
            username = self._extract_instagram_username(instagram_url)
            if not username:
                self.log_service.log_debug("Invalid Instagram URL format", {"instagram_url": instagram_url})
                return {}
                
            # Fazer scraping do perfil do Instagram usando o serviço dedicado
            scrape_result = await self.instagram_scraper.scrape_profile(instagram_url)
            if "error" in scrape_result:
                self.log_service.log_debug("Failed to scrape Instagram profile", {"instagram_url": instagram_url, "error": scrape_result["error"]})
                return {}
                
            instagram_data = scrape_result["data"]
                
            # Normalizar dados do Instagram para o formato esperado pela API
            normalized_data = self._normalize_instagram_data(instagram_data)
            normalized_data["_source"] = "instagram_scraping"
            return normalized_data
            
        except Exception as e:
            self.log_service.log_debug("Instagram enrichment error", {
                "instagram_url": company_data.get("instagram_url"),
                "error": str(e)
            })
            return {}
            
    def _extract_instagram_username(self, instagram_url: str) -> Optional[str]:
        """Extrai o nome de usuário do Instagram a partir da URL"""
        try:
            import re
            match = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)', instagram_url, re.IGNORECASE)
            if match:
                return match.group(1)
            return None
        except Exception as e:
            self.log_service.log_debug("Error extracting Instagram username", {"error": str(e)})
            return None
            
    def _normalize_instagram_data(self, instagram_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza os dados do Instagram para o formato esperado pela API"""
        try:
            # Converter followers/following/posts para inteiros quando possível
            followers = instagram_data.get("followers", "0")
            following = instagram_data.get("following", "0")
            posts = instagram_data.get("posts", "0")
            
            # Remover texto não numérico e converter para int
            followers_count = self._extract_number(followers) if followers else 0
            following_count = self._extract_number(following) if following else 0
            posts_count = self._extract_number(posts) if posts else 0
            
            # Criar objeto Instagram no formato esperado
            instagram_obj = {
                "url": instagram_data.get("url", ""),
                "name": instagram_data.get("name", ""),
                "user": instagram_data.get("username", ""),
                "bio": instagram_data.get("bio", ""),
                "email": instagram_data.get("email", ""),
                "phone": instagram_data.get("phone", ""),
                "followers": followers_count,
                "following": following_count,
                "posts": posts_count
            }
            
            # Criar estrutura de resposta
            normalized_data = {
                "name": instagram_data.get("name", ""),
                "description": instagram_data.get("bio", ""),
                "website": instagram_data.get("website", ""),
                "instagram": instagram_obj,
                "social_media": [
                    {
                        "platform": "instagram",
                        "url": instagram_data.get("url", ""),
                        "followers": followers_count
                    }
                ]
            }
            
            # Adicionar email e telefone se disponíveis
            if instagram_data.get("email"):
                normalized_data["contact_info"] = {"email": instagram_data.get("email")}
            
            if instagram_data.get("phone"):
                if not normalized_data.get("contact_info"):
                    normalized_data["contact_info"] = {}
                normalized_data["contact_info"]["phone"] = instagram_data.get("phone")
                
            return normalized_data
            
        except Exception as e:
            self.log_service.log_debug("Error normalizing Instagram data", {"error": str(e)})
            return {}
            
    def _extract_number(self, text: str) -> int:
        """Extrai número de uma string (ex: '1.5K followers' -> 1500)"""
        try:
            import re
            if not text or not isinstance(text, str):
                return 0
                
            # Remover texto não numérico
            num_str = re.sub(r'[^0-9.,]', '', text)
            
            # Converter K, M, B para valores numéricos
            if 'K' in text or 'k' in text:
                multiplier = 1000
            elif 'M' in text or 'm' in text:
                multiplier = 1000000
            elif 'B' in text or 'b' in text:
                multiplier = 1000000000
            else:
                multiplier = 1
                
            # Converter para float e depois para int
            try:
                # Substituir vírgula por ponto para conversão correta
                num_str = num_str.replace(',', '.')
                return int(float(num_str) * multiplier)
            except ValueError:
                return 0
        except Exception:
            return 0
            
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
            
    async def _find_linkedin_url_on_page(self, markdown_content: str) -> Optional[str]:
        """Encontra uma URL do LinkedIn no conteúdo markdown de uma página."""
        # Regex para encontrar URLs do LinkedIn de forma mais robusta
        linkedin_pattern = re.compile(r'https?://(?:www\.)?linkedin\.com/company/[a-zA-Z0-9_-]+')
        match = linkedin_pattern.search(markdown_content)
        
        if match:
            linkedin_url = match.group(0)
            self.log_service.log_debug("LinkedIn URL found on page", {"url": linkedin_url})
            return linkedin_url
        
        return None

    async def _find_linkedin_on_website_firecrawl(self, url: str) -> Optional[str]:
        """Usa o Firecrawl para encontrar um link do LinkedIn em um site, com extração estruturada."""
        try:
            # Schema para extrair apenas a URL do LinkedIn
            linkedin_schema = {
                "type": "object",
                "properties": {
                    "linkedin_url": {"type": "string", "description": "URL do perfil da empresa no LinkedIn, geralmente encontrada em links de redes sociais ou no rodapé do site"}
                },
                "required": ["linkedin_url"]
            }
            
            # Chamar o _scrape_with_firecrawl com o schema para usar extract_structured_data
            scraped_data = await self._scrape_with_firecrawl(url, linkedin_schema)

            if scraped_data and "linkedin_url" in scraped_data:
                return scraped_data["linkedin_url"]
            
            return None
        except Exception as e:
            self.log_service.log_debug("Error finding LinkedIn with Firecrawl", {"url": url, "error": str(e)})
            return None

    async def _add_website_enrichment(self, result: Dict[str, Any], company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Adiciona enriquecimento de dados do website da empresa"""
        try:
            website_url = result.get('website') or company_data.get('domain')
            if website_url:
                if not website_url.startswith(('http://', 'https://')):
                    website_url = f'https://{website_url}'
                
                # Enriquecer com o novo método que usa extract_structured_data
                enriched_data = await self._enrich_company_with_website({
                    "website": website_url,
                    "name": result.get("name") or company_data.get("name"),
                    "domain": company_data.get("domain")
                })
                
                if enriched_data:
                    # Mesclar dados do website com dados existentes
                    result = self._merge_website_data(result, enriched_data)
                else:
                    # Fallback para o método antigo
                    website_data = await self._scrape_company_website(website_url)
                    if website_data:
                        result = self._merge_website_data(result, website_data)
            
            return result
        except Exception as e:
            self.log_service.log_debug("Website enrichment failed", {"error": str(e)})
            return result
            
    async def _enrich_company_with_website(self, company: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """Enriquece dados da empresa usando o site da empresa com extração estruturada"""
        if not company.get("website"):
            return company
        
        website = company["website"]
        
        # Schema completo para extração de dados da empresa
        company_schema = {
            "type": "object",
            "properties": {
                "linkedin_url": {"type": "string", "description": "URL do perfil da empresa no LinkedIn"},
                "instagram_url": {"type": "string", "description": "URL do perfil da empresa no Instagram"},
                "twitter_url": {"type": "string", "description": "URL do perfil da empresa no Twitter/X"},
                "facebook_url": {"type": "string", "description": "URL do perfil da empresa no Facebook"},
                "company_name": {"type": "string", "description": "Nome oficial da empresa"},
                "description": {"type": "string", "description": "Descrição ou sobre a empresa"},
                "industry": {"type": "string", "description": "Indústria ou setor da empresa"},
                "founded_year": {"type": "string", "description": "Ano de fundação da empresa"},
                "employee_count": {"type": "string", "description": "Número aproximado de funcionários"},
                "headquarters": {"type": "string", "description": "Localização da sede da empresa"},
                "phone": {"type": "string", "description": "Número de telefone principal"},
                "email": {"type": "string", "description": "Email de contato principal"}
            }
        }
        
        # Extrair dados estruturados do site
        self.log_service.log_debug("Extracting structured data from website", {"website": website})
        structured_data = await self._scrape_with_firecrawl(website, company_schema, user_id)
        
        if structured_data and not structured_data.get("error"):
            # Mapear campos extraídos para o formato da empresa
            if structured_data.get("linkedin_url"):
                company["linkedin"] = structured_data["linkedin_url"]
            if structured_data.get("instagram_url"):
                company["instagram"] = structured_data["instagram_url"]
            if structured_data.get("twitter_url"):
                company["twitter"] = structured_data["twitter_url"]
            if structured_data.get("facebook_url"):
                company["facebook"] = structured_data["facebook_url"]
            if structured_data.get("company_name") and not company.get("name"):
                company["name"] = structured_data["company_name"]
            if structured_data.get("description") and not company.get("description"):
                company["description"] = structured_data["description"]
            if structured_data.get("industry") and not company.get("industry"):
                company["industry"] = structured_data["industry"]
            if structured_data.get("founded_year") and not company.get("founded"):
                company["founded"] = structured_data["founded_year"]
            if structured_data.get("employee_count") and not company.get("size"):
                company["size"] = structured_data["employee_count"]
            if structured_data.get("headquarters") and not company.get("headquarters"):
                company["headquarters"] = structured_data["headquarters"]
            if structured_data.get("phone") and not company.get("phone"):
                company["phone"] = structured_data["phone"]
            if structured_data.get("email") and not company.get("email"):
                company["email"] = structured_data["email"]
        
        # Se encontrou LinkedIn, tentar enriquecer com ele
        if company.get("linkedin") and not company.get("linkedin_enriched"):
            self.log_service.log_debug("Enriching with LinkedIn", {"linkedin": company["linkedin"]})
            enriched_data = await self._enrich_company_with_linkedin(company, user_id)
            if enriched_data:
                company.update(enriched_data)
                company["linkedin_enriched"] = True
                
        return company

    def _parse_linkedin_markdown(self, markdown_content: str) -> Dict[str, Any]:
        """Analisa o conteúdo markdown de uma página de empresa do LinkedIn."""
        try:
            lines = markdown_content.strip().split('\n')
            mapped_data = {}

            for line in lines:
                if ":" in line:
                    key, *value_parts = line.split(":", 1)
                    key = key.strip().lower().replace(" ", "_")
                    value = ":".join(value_parts).strip()

                    if key in mapped_data:
                        if isinstance(mapped_data[key], list):
                            mapped_data[key].append(value)
                        else:
                            mapped_data[key] = [mapped_data[key], value]
                    else:
                        mapped_data[key] = value
            
            self.log_service.log_debug("Markdown parsing completed", {
                "extracted_fields": list(mapped_data.keys()),
                "quality": self._assess_data_quality(mapped_data)
            })
            
            return mapped_data
            
        except Exception as e:
            self.log_service.log_debug("Markdown parsing failed", {"error": str(e)})
            return {}

    async def _scrape_with_firecrawl(self, url: str, schema: Dict[str, Any] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Fallback para scraping com Firecrawl e extração com LLM"""
        if not self.firecrawl_api_key:
            self.log_service.log_debug("Firecrawl API key not configured.", {})
            return {"error": "Firecrawl not configured"}

        try:
            from api.firecrawl_client import FirecrawlApp
            app = FirecrawlApp(api_key=self.firecrawl_api_key)
            
            self.log_service.log_debug("Starting Firecrawl scraping with enhanced config", {"url": url})
            
            # Se um schema foi fornecido, usar extract_structured_data
            if schema:
                self.log_service.log_debug("Using structured data extraction with schema", {"url": url})
                return app.extract_structured_data(url, schema)
            
            # Caso contrário, usar scrape_url normal
            # Configurar parâmetros para garantir captura de HTML e markdown
            scraped_data = app.scrape_url(
                url,
                params={
                    'formats': ['markdown', 'html'],
                    'includeTags': ['a', 'script', 'meta', 'link', 'div', 'span', 'footer', 'header', 'nav'],
                    'onlyMainContent': False,
                    'waitFor': 3000,
                    'screenshot': False,
                    'fullPageScreenshot': False
                }
            )
            
            # Acessar markdown e HTML corretamente do objeto ScrapeResponse
            markdown_content = None
            html_content = None
            
            # Verificar se scraped_data é uma lista (formato atual da resposta)
            if isinstance(scraped_data, list) and len(scraped_data) > 0:
                # Assumir que o primeiro item contém markdown e o segundo contém HTML
                if len(scraped_data) >= 1 and isinstance(scraped_data[0], str):
                    markdown_content = scraped_data[0]
                if len(scraped_data) >= 2 and isinstance(scraped_data[1], str):
                    html_content = scraped_data[1]
            # Verificar se é um objeto com atributos
            elif hasattr(scraped_data, 'markdown'):
                markdown_content = scraped_data.markdown
            # Verificar se é um dicionário
            elif isinstance(scraped_data, dict):
                markdown_content = scraped_data.get('markdown')
                
            # Verificar HTML da mesma forma
            if html_content is None:
                if hasattr(scraped_data, 'html'):
                    html_content = scraped_data.html
                elif isinstance(scraped_data, dict):
                    html_content = scraped_data.get('html')

            self.log_service.log_debug("Firecrawl response details", {
                "url": url,
                "response_type": str(type(scraped_data)),
                "has_markdown_attr": hasattr(scraped_data, 'markdown'),
                "has_html_attr": hasattr(scraped_data, 'html'),
                "scraped_data_keys": list(scraped_data.__dict__.keys()) if hasattr(scraped_data, '__dict__') else "No __dict__",
                "scraped_data_dir": [attr for attr in dir(scraped_data) if not attr.startswith('_')],
                "markdown_length": len(markdown_content) if markdown_content else 0,
                "html_length": len(html_content) if html_content else 0
            })
            
            if not markdown_content:
                self.log_service.log_debug("Firecrawl response has no markdown content", {
                    "url": url,
                    "response_type": str(type(scraped_data)),
                    "has_markdown_attr": hasattr(scraped_data, 'markdown'),
                    "has_html_attr": hasattr(scraped_data, 'html'),
                    "markdown_length": len(markdown_content) if markdown_content else 0,
                    "html_length": len(html_content) if html_content else 0
                })
                return {"error": "No markdown content from Firecrawl"}
            
            extracted = await self._extract_json_from_markdown(markdown_content, schema)
            
            if not extracted:
                self.log_service.log_debug("Markdown extraction with LLM returned no data", {"url": url})
                return {"error": "Failed to extract data from markdown"}

            mapped_data = self._map_data_to_schema(extracted, schema)
            
            # Garantir que instagram, linkedin_data e whatsapp sejam objetos válidos ou None
            if 'instagram' in mapped_data and not isinstance(mapped_data['instagram'], dict):
                mapped_data['instagram'] = None
            if 'linkedin_data' in mapped_data and not isinstance(mapped_data['linkedin_data'], dict):
                mapped_data['linkedin_data'] = None
            if 'whatsapp' in mapped_data and not isinstance(mapped_data['whatsapp'], dict):
                mapped_data['whatsapp'] = None
            
            self.log_service.log_debug("Firecrawl markdown extraction successful", {
                "url": url, 
                "extracted_keys": list(mapped_data.keys()) if mapped_data else [],
                "data_quality": self._assess_data_quality(mapped_data) if mapped_data else 0,
                "has_html_for_fallback": bool(html_content)
            })
            
            # Verificar se redes sociais foram extraídas
            social_media = mapped_data.get('social_media', []) if isinstance(mapped_data, dict) else []
            
            # Verificar se social_media é uma lista antes de acessar seus atributos
            if isinstance(social_media, list):
                has_social_media = len(social_media) > 0 and any(
                    item.get('platform') in ['instagram', 'linkedin', 'facebook', 'twitter', 'youtube', 'whatsapp']
                    for item in social_media if isinstance(item, dict)
                )
            else:
                has_social_media = False
                # Corrigir o tipo de social_media se não for uma lista
                social_media = []
                if isinstance(mapped_data, dict):
                    mapped_data['social_media'] = social_media
            
            # Se não encontrou redes sociais no Firecrawl, tentar fallback com requests
            if not has_social_media:
                self.log_service.log_debug("No social media found in Firecrawl, trying requests fallback", {"url": url})
                try:
                    import requests
                    from bs4 import BeautifulSoup
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    response = requests.get(url, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    # Extrair redes sociais do HTML completo
                    fallback_social_list = await self._extract_social_media_from_html(response.text)
                    
                    # Usar a lista diretamente sem conversão para dict
                    if fallback_social_list and len(fallback_social_list) > 0:
                        self.log_service.log_debug("Found social media with requests fallback", {
                            "url": url,
                            "social_media": fallback_social_list
                        })
                        # Mesclar com dados existentes
                        if 'social_media' not in mapped_data:
                            mapped_data['social_media'] = []
                        # Adicionar novos itens da lista de fallback
                        if isinstance(mapped_data['social_media'], list):
                            mapped_data['social_media'].extend(fallback_social_list)
                        else:
                            mapped_data['social_media'] = fallback_social_list
                    
                except Exception as e:
                    self.log_service.log_debug("Requests fallback failed", {
                        "url": url,
                        "error": str(e)
                    })
            
            # Incluir HTML no resultado para permitir fallback
            result = mapped_data.copy() if mapped_data else {}
            if html_content:
                result['html'] = html_content
            
            return result
            
        except Exception as e:
            self.log_service.log_debug("Firecrawl scraping failed", {"url": url, "error": str(e)})
            return {"error": f"Failed to scrape with Firecrawl: {e}"}

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
        
    async def _scrape_linkedin_company_with_retry(self, linkedin_url: str, max_retries: int = 3) -> Dict[str, Any]:
        """Tenta fazer o scraping de uma página do LinkedIn com várias tentativas e timeouts."""
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
        """Resolve redirecionamentos do LinkedIn usando requests"""
        try:
            # Se já é uma URL completa do LinkedIn, retorna como está
            if 'linkedin.com/company/' in linkedin_url:
                return linkedin_url
            
            # Se é um redirecionamento, tenta resolver usando requests
            if 'linkedin.com' in linkedin_url and '/redir/' in linkedin_url:
                try:
                    response = requests.get(
                        linkedin_url, 
                        allow_redirects=True, 
                        timeout=10,
                        headers={
                            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                        }
                    )
                    return response.url
                except Exception as e:
                    self.log_service.log_debug("Error resolving LinkedIn redirect with requests", {"error": str(e)})
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





    async def _enrich_by_name_region_country(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enriquecimento por nome, região e país"""
        try:
            name = company_data.get("name")
            region = company_data.get("region")
            country = company_data.get("country")
            
            if not name:
                return {}
                
            self.log_service.log_debug("Starting enrichment by name, region, country", {
                "name": name,
                "region": region,
                "country": country
            })
            
            # Buscar LinkedIn URL usando Brave Search
            linkedin_url = await self._find_linkedin_by_name_region_country(name, region, country)
            
            if not linkedin_url:
                self.log_service.log_debug("No LinkedIn URL found for company", {"name": name})
                return {}
                
            # Enriquecer com dados do LinkedIn
            async with CrawlAIService(self.log_service) as crawl_service:
                linkedin_data = await crawl_service.scrape_linkedin_company_advanced(linkedin_url)
                
                if linkedin_data and not linkedin_data.get("error"):
                    # Normalizar dados do LinkedIn
                    normalized_data = crawl_service._normalize_linkedin_data(linkedin_data)
                    normalized_data["_source"] = "crawl4ai_linkedin_by_name"
                    normalized_data["linkedin_url"] = linkedin_url
                    return normalized_data
            
            return {}
            
        except Exception as e:
            self.log_service.log_debug("Name/Region/Country enrichment error", {
                "name": company_data.get("name"),
                "error": str(e)
            })
            return {}
            
    async def _find_linkedin_by_name_region_country(self, name: str, region: Optional[str] = None, country: Optional[str] = None) -> Optional[str]:
        """Encontra URL do LinkedIn usando nome, região e país"""
        try:
            # Aguardar rate limiting se necessário
            can_proceed = await self.rate_limiter.wait_if_needed()
            if not can_proceed:
                self.log_service.log_debug("Rate limit exceeded for Brave Search", {})
                return None
                
            # Estratégias de busca otimizadas
            search_strategies = [
                f'"{name}" official linkedin company profile',
                f'site:linkedin.com/company "{name}"'
            ]

            if region:
                search_strategies.append(f'site:linkedin.com/company "{name}" "{region}"')
            if country:
                search_strategies.append(f'site:linkedin.com/company "{name}" "{country}"')
                
            for strategy in search_strategies:
                try:
                    linkedin_url = await self._search_linkedin_url_with_brave(strategy, region, country)
                    if linkedin_url:
                        return linkedin_url
                except Exception as e:
                    self.log_service.log_debug(f"Search strategy failed: {strategy}", {"error": str(e)})
                    continue
                    
            return None
            
        except Exception as e:
            self.log_service.log_debug("Error finding LinkedIn URL", {"error": str(e)})
            return None
            
    async def _search_linkedin_url_with_brave(self, search_query: str, region: Optional[str] = None, country: Optional[str] = None) -> Optional[str]:
        """Busca URL do LinkedIn usando Brave Search"""
        try:
            self.log_service.log_debug("Searching LinkedIn URL with Brave", {"query": search_query})
            
            # Parâmetros da API Brave Search
            params = {
                'q': search_query,
                'count': 10
            }
            
            # Adicionar país se fornecido (formato correto: código de 2 letras)
            if country:
                country_code = self._get_country_code(country)
                if country_code:
                    params['country'] = country_code
                    
            response = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={
                    'x-subscription-token': self.brave_api_key,
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip',
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                },
                params=params,
                timeout=15
            )
            
            if response.status_code != 200:
                self.log_service.log_debug("Brave Search API error", {"status": response.status_code})
                return None
                
            data = response.json()
            
            # Extrair URLs do LinkedIn dos resultados
            for result in data.get('web', {}).get('results', []):
                url = result.get('url', '')
                if 'linkedin.com/company/' in url:
                    return url
                    
            return None
            
        except Exception as e:
            self.log_service.log_debug("Error searching LinkedIn URL with Brave", {"error": str(e)})
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
            # Primeiro tenta com CrawlAI usando context manager
            async with self.crawl4ai_service as crawler:
                result = await crawler.scrape_company_website_complete(website_url)
            
            if result.get('success') and result.get('confidence_score', 0) > 0.6:
                # Verificar se encontrou redes sociais
                social_media_found = self._check_social_media_found(result)
                
                # Se não encontrou redes sociais, tentar buscar em páginas de contato
                if not social_media_found:
                    self.log_service.log_debug("No social media found in main page, searching contact pages", {
                        "url": website_url
                    })
                    contact_social_media = await self._scrape_contact_pages_for_social_media(website_url)
                    
                    # Merge das redes sociais encontradas nas páginas de contato
                    if any(contact_social_media.values()):
                        result = self._merge_contact_social_media(result, contact_social_media)
                        self.log_service.log_debug("Merged social media from contact pages", {
                            "contact_social_media": {k: v for k, v in contact_social_media.items() if v}
                        })
                
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
            
            # Usar schema padrão para Firecrawl
            schema = self._get_default_schema()
            firecrawl_result = await self._scrape_with_firecrawl(website_url, schema)
            
            if firecrawl_result.get('success'):
                # Verificar se encontrou redes sociais no Firecrawl
                social_media_found = self._check_social_media_found(firecrawl_result.get('data', {}))
                
                # Se não encontrou redes sociais, tentar buscar em páginas de contato
                if not social_media_found:
                    self.log_service.log_debug("No social media found in Firecrawl result, searching contact pages", {
                        "url": website_url
                    })
                    contact_social_media = await self._scrape_contact_pages_for_social_media(website_url)
                    
                    # Merge das redes sociais encontradas nas páginas de contato
                    if any(contact_social_media.values()):
                        firecrawl_data = firecrawl_result.get('data', {})
                        firecrawl_data = self._merge_contact_social_media(firecrawl_data, contact_social_media)
                        firecrawl_result['data'] = firecrawl_data
                        self.log_service.log_debug("Merged social media from contact pages to Firecrawl", {
                            "contact_social_media": {k: v for k, v in contact_social_media.items() if v}
                        })
                
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

    def _check_social_media_found(self, data: Dict[str, Any]) -> bool:
        """Verifica se foram encontradas redes sociais nos dados"""
        if not data:
            return False
            
        social_platforms = ['instagram', 'linkedin', 'facebook', 'youtube', 'whatsapp', 'twitter']
        
        # Verificar se há redes sociais no nível raiz
        for platform in social_platforms:
            if data.get(platform):
                return True
        
        # Verificar se há redes sociais em social_media
        social_media = data.get('social_media', {})
        if isinstance(social_media, dict):
            for platform in social_platforms:
                if social_media.get(platform):
                    return True
        
        return False
    
    def _merge_contact_social_media(self, main_data: Dict[str, Any], contact_social: Dict[str, str]) -> Dict[str, Any]:
        """Merge das redes sociais encontradas em páginas de contato com os dados principais"""
        if not contact_social or not any(contact_social.values()):
            return main_data
        
        # Garantir que existe a estrutura social_media
        if 'social_media' not in main_data:
            main_data['social_media'] = []
        
        # Merge das redes sociais, priorizando as já existentes
        for platform, url in contact_social.items():
            if url:
                # Adicionar no nível raiz se não existir
                if not main_data.get(platform):
                    main_data[platform] = url
                
                # Adicionar em social_media se não existir
                if not main_data['social_media'].get(platform):
                    main_data['social_media'][platform] = url
        
        return main_data
    
    async def _scrape_contact_pages_for_social_media(self, base_url: str) -> Dict[str, Any]:
        """Busca redes sociais em páginas de contato quando não encontradas na página principal"""
        social_media = {
            "instagram": None,
            "linkedin_data": None,
            "whatsapp": None,
            "facebook": None,
            "twitter": None,
            "youtube": None,
            "tiktok": None,
            "telegram": None
        }
        
        try:
            from urllib.parse import urljoin, urlparse
            
            # Lista de possíveis URLs de contato
            contact_urls = [
                urljoin(base_url, '/contato'),
                urljoin(base_url, '/contact'),
                urljoin(base_url, '/contact-us'),
                urljoin(base_url, '/fale-conosco'),
                urljoin(base_url, '/sobre'),
                urljoin(base_url, '/about'),
                urljoin(base_url, '/about-us'),
                urljoin(base_url, '/empresa'),
                urljoin(base_url, '/company'),
                urljoin(base_url, '/footer'),
                urljoin(base_url, '/rodape')
            ]
            
            # Adicionar variações com subdomínios
            parsed_url = urlparse(base_url)
            if not parsed_url.netloc.startswith('www.'):
                www_base = f"{parsed_url.scheme}://www.{parsed_url.netloc}"
                contact_urls.extend([
                    urljoin(www_base, '/contato'),
                    urljoin(www_base, '/contact'),
                    urljoin(www_base, '/contact-us')
                ])
            
            # Adicionar subdomínios comuns
            subdomain_bases = [
                f"{parsed_url.scheme}://materiais.{parsed_url.netloc.replace('www.', '')}",
                f"{parsed_url.scheme}://site.{parsed_url.netloc.replace('www.', '')}",
                f"{parsed_url.scheme}://portal.{parsed_url.netloc.replace('www.', '')}"
            ]
            
            for subdomain_base in subdomain_bases:
                contact_urls.extend([
                    urljoin(subdomain_base, '/contato'),
                    urljoin(subdomain_base, '/contact')
                ])
            
            self.log_service.log_debug("Searching for social media in contact pages", {
                "base_url": base_url,
                "contact_urls_count": len(contact_urls)
            })
            
            # Tentar cada URL de contato
            for contact_url in contact_urls:
                try:
                    self.log_service.log_debug("Trying contact URL", {"url": contact_url})
                    
                    # Usar Firecrawl para scraping da página de contato
                    try:
                        firecrawl_app = FirecrawlApp(api_key=os.getenv('FIRECRAWL_API_KEY'))
                        
                        # Usar sintaxe correta do Firecrawl v2
                        scraped_data = firecrawl_app.scrape_url(
                            contact_url,
                            formats=['markdown', 'html']
                        )
                        
                        # scraped_data é um objeto ScrapeResponse com atributo data
                        firecrawl_result = {
                            'success': True,
                            'data': scraped_data.data if hasattr(scraped_data, 'data') else {}
                        }
                        
                    except Exception as e:
                        self.log_service.log_error("Error scraping contact page with Firecrawl", {
                            "url": contact_url,
                            "error": str(e)
                        })
                        firecrawl_result = {'success': False}
                    
                    if firecrawl_result.get('success'):
                        html_content = firecrawl_result.get('data', {}).get('html', '')
                        markdown_content = firecrawl_result.get('data', {}).get('markdown', '')
                        
                        if html_content:
                            # Extrair redes sociais do HTML
                            page_social_media_list = await self._extract_social_media_from_html(html_content)
                            
                            # Converter a lista para o formato de dicionário para compatibilidade
                            page_social_media = {}
                            for item in page_social_media_list:
                                platform = item.get('platform')
                                if platform == 'linkedin':
                                    platform = 'linkedin_data'
                                    
                                if platform and platform in ['instagram', 'linkedin_data', 'whatsapp', 'facebook', 'twitter', 'youtube', 'tiktok', 'telegram']:
                                    url = item.get('url')
                                    if url:
                                        # Se tiver mais dados além da URL, criar um dicionário
                                        if len(item) > 2:  # platform e url + outros campos
                                            page_social_media[platform] = {
                                                'url': url,
                                                **{k: v for k, v in item.items() if k not in ['platform', 'url']}
                                            }
                                        else:
                                            page_social_media[platform] = url
                            
                            # Também buscar no markdown
                            if markdown_content:
                                markdown_social_media_list = self._extract_social_media_from_markdown(markdown_content)
                                
                                # Converter a lista para o formato de dicionário para compatibilidade
                                markdown_social_media = {}
                                for item in markdown_social_media_list:
                                    platform = item.get('platform')
                                    if platform == 'linkedin':
                                        platform = 'linkedin_data'
                                        
                                    if platform and platform in ['instagram', 'linkedin_data', 'whatsapp', 'facebook', 'twitter', 'youtube', 'tiktok', 'telegram']:
                                        url = item.get('url')
                                        if url:
                                            # Se tiver mais dados além da URL, criar um dicionário
                                            if len(item) > 2:  # platform e url + outros campos
                                                markdown_social_media[platform] = {
                                                    'url': url,
                                                    **{k: v for k, v in item.items() if k not in ['platform', 'url']}
                                                }
                                            else:
                                                markdown_social_media[platform] = url
                                
                                # Merge dos resultados
                                for platform, url in markdown_social_media.items():
                                    if url and not page_social_media.get(platform):
                                        page_social_media[platform] = url
                            
                            # Verificar se encontrou alguma rede social
                            found_any = any(page_social_media.values())
                            if found_any:
                                self.log_service.log_debug("Found social media in contact page", {
                                    "url": contact_url,
                                    "social_media": {k: v for k, v in page_social_media.items() if v}
                                })
                                
                                # Merge com os resultados existentes
                                for platform, url in page_social_media.items():
                                    if url and not social_media.get(platform):
                                        social_media[platform] = url
                                
                                # Se encontrou redes sociais suficientes, pode parar
                                filled_count = sum(1 for v in social_media.values() if v)
                                if filled_count >= 3:  # Se encontrou 3 ou mais redes sociais
                                    break
                    
                except Exception as e:
                    self.log_service.log_debug("Error scraping contact URL", {
                        "url": contact_url,
                        "error": str(e)
                    })
                    continue
            
            return social_media
            
        except Exception as e:
            self.log_service.log_debug("Error in contact pages social media search", {
                "error": str(e),
                "base_url": base_url
            })
            return social_media
    
    def _extract_social_media_from_markdown(self, markdown_content: str) -> List[Dict[str, Any]]:
        """Extrai URLs de redes sociais do conteúdo markdown"""
        social_media = {
            "instagram": None,
            "linkedin_data": None,
            "whatsapp": None,
            "facebook": None,
            "twitter": None,
            "youtube": None,
            "tiktok": None,
            "telegram": None
        }
        
        try:
            import re
            
            # Patterns para buscar no markdown
            patterns = {
                "instagram": [
                    r'https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)/?',
                    r'\[.*?\]\(https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)/?\)',
                    r'@([a-zA-Z0-9_.]+).*instagram'
                ],
                "linkedin": [
                    r'https?://(?:www\.)?linkedin\.com/company/([a-zA-Z0-9-]+)/?',
                    r'\[.*?\]\(https?://(?:www\.)?linkedin\.com/company/([a-zA-Z0-9-]+)/?\)',
                    r'https?://(?:www\.)?linkedin\.com/in/([a-zA-Z0-9-]+)/?'
                ],
                "facebook": [
                    r'https?://(?:www\.)?facebook\.com/([a-zA-Z0-9.]+)/?',
                    r'\[.*?\]\(https?://(?:www\.)?facebook\.com/([a-zA-Z0-9.]+)/?\)'
                ],
                "youtube": [
                    r'https?://(?:www\.)?youtube\.com/(?:channel/|c/|user/)?([a-zA-Z0-9_-]+)/?',
                    r'\[.*?\]\(https?://(?:www\.)?youtube\.com/(?:channel/|c/|user/)?([a-zA-Z0-9_-]+)/?\)'
                ],
                "whatsapp": [
                    r'https?://(?:wa\.me|api\.whatsapp\.com)/([0-9]+)',
                    r'\[.*?\]\(https?://(?:wa\.me|api\.whatsapp\.com)/([0-9]+)\)',
                    r'\+?([0-9]{10,15}).*whatsapp'
                ],
                "twitter": [
                    r'https?://(?:www\.)?(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)/?',
                    r'\[.*?\]\(https?://(?:www\.)?(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)/?\)'
                ]
            }
            
            for platform, platform_patterns in patterns.items():
                for pattern in platform_patterns:
                    matches = re.findall(pattern, markdown_content, re.IGNORECASE)
                    if matches:
                        if platform == 'linkedin':
                            social_media['linkedin_data'] = f"https://linkedin.com/company/{matches[0]}"
                        elif platform == 'whatsapp':
                            social_media['whatsapp'] = f"https://wa.me/{matches[0]}"
                        else:
                            base_urls = {
                                'instagram': 'https://instagram.com/',
                                'facebook': 'https://facebook.com/',
                                'youtube': 'https://youtube.com/c/',
                                'twitter': 'https://twitter.com/'
                            }
                            if platform in base_urls:
                                social_media[platform] = f"{base_urls[platform]}{matches[0]}"
                        break
            
            # Converter o dicionário em uma lista de dicionários no formato esperado
            social_media_list = []
            for platform, data in social_media.items():
                if data is not None:
                    if platform == "linkedin_data":
                        platform_name = "linkedin"
                    else:
                        platform_name = platform
                    
                    if isinstance(data, dict):
                        social_media_list.append({
                            "platform": platform_name,
                            "url": data.get("url"),
                            **{k: v for k, v in data.items() if k != "url"}
                        })
                    else:
                        social_media_list.append({
                            "platform": platform_name,
                            "url": data
                        })
            
            return social_media_list
            
        except Exception as e:
            self.log_service.log_debug("Error extracting social media from markdown", {
                "error": str(e)
            })
            return []

    def _extract_json_ld_social_media(self, html_content: str) -> List[Dict[str, Any]]:
        """Extrai dados de redes sociais de estruturas JSON-LD"""
        social_data = {}
        
        try:
            from bs4 import BeautifulSoup
            import json
            
            soup = BeautifulSoup(html_content, 'html.parser')
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    
                    # Processar diferentes estruturas JSON-LD
                    if isinstance(data, list):
                        for item in data:
                            self._process_json_ld_item(item, social_data)
                    elif isinstance(data, dict):
                        self._process_json_ld_item(data, social_data)
                        
                        # Verificar se há @graph
                        if '@graph' in data:
                            for item in data['@graph']:
                                self._process_json_ld_item(item, social_data)
                                
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            self.log_service.log_debug("Error extracting JSON-LD social media", {"error": str(e)})
            
        # Converter o dicionário em uma lista de dicionários no formato esperado
        social_media_list = []
        for platform, data in social_data.items():
            if data is not None:
                if platform == "linkedin_data":
                    platform_name = "linkedin"
                else:
                    platform_name = platform
                
                if isinstance(data, dict):
                    social_media_list.append({
                        "platform": platform_name,
                        "url": data.get("url"),
                        **{k: v for k, v in data.items() if k != "url"}
                    })
                else:
                    social_media_list.append({
                        "platform": platform_name,
                        "url": data
                    })
        
        return social_media_list
    
    def _process_json_ld_item(self, item: Dict[str, Any], social_data: Dict[str, Any]) -> None:
        """Processa um item JSON-LD para extrair URLs de redes sociais"""
        if not isinstance(item, dict):
            return
            
        # Verificar campo sameAs
        if 'sameAs' in item:
            same_as = item['sameAs']
            if isinstance(same_as, list):
                for url in same_as:
                    self._categorize_social_url(url, social_data)
            elif isinstance(same_as, str):
                self._categorize_social_url(same_as, social_data)
        
        # Verificar outros campos comuns
        social_fields = ['url', 'mainEntityOfPage', 'potentialAction']
        for field in social_fields:
            if field in item:
                value = item[field]
                if isinstance(value, str):
                    self._categorize_social_url(value, social_data)
                elif isinstance(value, list):
                    for url in value:
                        if isinstance(url, str):
                            self._categorize_social_url(url, social_data)
    
    def _categorize_social_url(self, url: str, social_data: Dict[str, Any]) -> None:
        """Categoriza uma URL em uma plataforma de rede social"""
        if not url or not isinstance(url, str):
            return
            
        url_lower = url.lower()
        
        if 'instagram.com' in url_lower:
            social_data['instagram'] = url
        elif 'linkedin.com' in url_lower:
            social_data['linkedin'] = url
        elif 'facebook.com' in url_lower or 'fb.com' in url_lower:
            social_data['facebook'] = url
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            social_data['twitter'] = url
        elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            social_data['youtube'] = url
        elif 'tiktok.com' in url_lower:
            social_data['tiktok'] = url
        elif 'telegram.org' in url_lower or 't.me' in url_lower:
            social_data['telegram'] = url
        elif 'wa.me' in url_lower or 'whatsapp.com' in url_lower:
            social_data['whatsapp'] = url

    async def _extract_social_media_from_html(self, html_content: str) -> List[Dict[str, Any]]:
        """Extrai URLs de redes sociais usando o EnhancedSocialExtractor"""
        try:
            # Debug: Log HTML content length and sample
            self.log_service.log_debug("Extracting social media from HTML with EnhancedSocialExtractor", {
                "html_length": len(html_content) if html_content else 0,
                "html_sample": html_content[:500] if html_content else "No HTML content"
            })
            
            # Usar o novo extrator aprimorado
            async with self.enhanced_social_extractor as extractor:
                # Definir domínio genérico sem especificidade
                domain = ""
                try:
                    # Extrair domínio do conteúdo HTML (sem especificidade de domínios)
                    soup = BeautifulSoup(html_content, 'html.parser')
                    # Tentar extrair do canonical link
                    canonical = soup.find('link', {'rel': 'canonical'})
                    if canonical and canonical.get('href'):
                        parsed_url = urlparse(canonical.get('href'))
                        domain = parsed_url.netloc
                    # Se não encontrou, tentar extrair do og:url
                    if not domain:
                        og_url = soup.find('meta', {'property': 'og:url'}) or soup.find('meta', {'name': 'og:url'})
                        if og_url and og_url.get('content'):
                            parsed_url = urlparse(og_url.get('content'))
                            domain = parsed_url.netloc
                except Exception as e:
                    self.log_service.log_debug(f"Error extracting domain: {e}", {"error": str(e)})
                
                result = await extractor.extract_comprehensive_social_media(html_content, domain)
            
            # Debug: Log the raw result from extractor
            self.log_service.log_debug("Raw result from EnhancedSocialExtractor", {
                "result_type": type(result).__name__,
                "result_keys": list(result.keys()) if isinstance(result, dict) else "Not a dict",
                "social_media_keys": list(result.get('social_media', {}).keys()) if isinstance(result, dict) else "No social_media"
            })
            
            # Adicionar redes sociais específicas para domínios conhecidos
            domain = result.get('domain', '')
            # Processamento agnóstico de redes sociais para qualquer domínio
            # Os dados de redes sociais devem ser extraídos dinamicamente do conteúdo HTML
            # sem hardcoding para domínios específicos
            
            # Converter o resultado para o formato esperado
            social_media_list = []
            
            # Processar social media encontradas
            social_media_data = result.get('social_media', {})
            for platform, data in social_media_data.items():
                if data and isinstance(data, dict):
                    primary_url = data.get('primary_url')
                    if primary_url and isinstance(primary_url, str):
                        social_item = {
                            "platform": platform,
                            "url": primary_url
                        }
                        
                        # Adicionar campos extras se disponíveis
                        all_data = data.get('all_data', [])
                        if all_data and isinstance(all_data, list) and len(all_data) > 0:
                            first_item = all_data[0]
                            if isinstance(first_item, dict):
                                if first_item.get('username'):
                                    social_item["username"] = first_item['username']
                                if first_item.get('confidence_score'):
                                    social_item["confidence"] = first_item['confidence_score']
                        
                        social_media_list.append(social_item)
            
            # Processar informações de contato (WhatsApp)
            contact_info = result.get('contact_info', {})
            if contact_info and isinstance(contact_info, dict):
                whatsapp_data = contact_info.get('whatsapp', [])
                if isinstance(whatsapp_data, list):
                    for whatsapp in whatsapp_data:
                        if isinstance(whatsapp, str):
                            clean_phone = re.sub(r'[^0-9]', '', whatsapp)
                            if len(clean_phone) >= 10:
                                social_media_list.append({
                                    "platform": "whatsapp",
                                    "url": f"https://wa.me/{clean_phone}",
                                    "phone": whatsapp,
                                    "username": clean_phone
                                })
            
            # Tentar extrair redes sociais adicionais do HTML usando regex
            try:
                # Instagram
                instagram_patterns = [
                    r'instagram\.com/([\w\._]+)',
                    r'\binstagram\b[^<>]*?[\s:]+@?([\w\._]+)',
                    r'\binstagram\b[^<>]*?[\s:]+([\w\._]+)',
                    r'@([\w\._]+)\s+(?:no\s+)?instagram'
                ]
                
                for pattern in instagram_patterns:
                    matches = re.finditer(pattern, html_content, re.IGNORECASE)
                    for match in matches:
                        username = match.group(1).strip('/@.')
                        if username and len(username) > 2 and not any(item.get('platform') == 'instagram' for item in social_media_list):
                            social_media_list.append({
                                "platform": "instagram",
                                "url": f"https://www.instagram.com/{username}",
                                "username": username
                            })
                            break
                
                # LinkedIn
                linkedin_patterns = [
                    r'linkedin\.com/(?:in|company)/([\w\-\.]+)',
                    r'\blinkedin\b[^<>]*?[\s:]+([\w\-\.]+)',
                    r'\blinkedin\b[^<>]*?[\s:]+@?([\w\-\.]+)'
                ]
                
                for pattern in linkedin_patterns:
                    matches = re.finditer(pattern, html_content, re.IGNORECASE)
                    for match in matches:
                        username = match.group(1).strip('/@.')
                        if username and len(username) > 2 and not any(item.get('platform') == 'linkedin' for item in social_media_list):
                            social_media_list.append({
                                "platform": "linkedin",
                                "url": f"https://www.linkedin.com/in/{username}",
                                "username": username
                            })
                            break
                
                # Facebook
                facebook_patterns = [
                    r'facebook\.com/([\w\.\-]+)',
                    r'fb\.com/([\w\.\-]+)',
                    r'\bfacebook\b[^<>]*?[\s:]+@?([\w\.\-]+)',
                    r'@([\w\.\-]+)\s+(?:no\s+)?facebook'
                ]
                
                for pattern in facebook_patterns:
                    matches = re.finditer(pattern, html_content, re.IGNORECASE)
                    for match in matches:
                        username = match.group(1).strip('/@.')
                        if username and len(username) > 2 and not any(item.get('platform') == 'facebook' for item in social_media_list):
                            social_media_list.append({
                                "platform": "facebook",
                                "url": f"https://www.facebook.com/{username}",
                                "username": username
                            })
                            break
            except Exception as e:
                self.log_service.log_debug(f"Error in additional social media extraction: {e}", {
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                })
            
            # Debug: Log final results
            self.log_service.log_debug("Final social media extraction results", {
                "total_found": len(social_media_list),
                "platforms": [item.get('platform') for item in social_media_list],
                "urls": [item.get('url') for item in social_media_list]
            })
            
            return social_media_list
            
        except Exception as e:
            self.log_service.log_debug(f"Error in social media extraction: {e}", {
                "error_type": type(e).__name__,
                "error_message": str(e)
            })
            return []
    
    def _process_social_url(self, url: str, social_media: Dict[str, Any]) -> None:
        """Processa uma URL e extrai informações de redes sociais"""
        try:
            import re
            
            if not url or not isinstance(url, str):
                return
            
            url = url.strip()
            url_lower = url.lower()
            
            # Verificar se a URL é relativa e tentar completá-la
            if not url_lower.startswith(('http://', 'https://', 'www.')) and not url_lower.startswith(('tel:', 'mailto:')):
                # Se for um handle de rede social (começando com @)
                if url_lower.startswith('@'):
                    handle = url_lower[1:]
                    # Tentar identificar a plataforma pelo contexto
                    if not social_media.get('instagram'):
                        social_media['instagram'] = {
                            'url': f"https://instagram.com/{handle}",
                            'username': handle
                        }
                        self.log_service.log_debug(f"Found Instagram handle", {"handle": handle})
                        return
                # Se for um caminho relativo, ignorar
                elif url_lower.startswith('/'):
                    return
            
            # Instagram
            if any(domain in url_lower for domain in ['instagram.com', 'instagr.am', 'insta.gram']):
                match = re.search(r'(?:instagram\.com|instagr\.am)/([a-zA-Z0-9_.]+)', url_lower, re.IGNORECASE)
                if match and not social_media.get('instagram'):
                    username = match.group(1)
                    cleaned_url = self._clean_social_url(url)
                    if cleaned_url:
                        social_media['instagram'] = {
                            'url': cleaned_url,
                            'username': username
                        }
                        self.log_service.log_debug(f"Found Instagram URL", {"url": cleaned_url, "username": username})
            
            # LinkedIn
            elif any(domain in url_lower for domain in ['linkedin.com', 'lnkd.in']):
                match = re.search(r'(?:linkedin\.com|lnkd\.in)/(?:company|in|school)/([a-zA-Z0-9_-]+)', url_lower, re.IGNORECASE)
                if not social_media.get('linkedin_data'):
                    cleaned_url = self._clean_social_url(url)
                    if cleaned_url:
                        linkedin_data = {
                            'url': cleaned_url
                        }
                        if match:
                            linkedin_data['handle'] = match.group(1)
                        social_media['linkedin_data'] = linkedin_data
                        self.log_service.log_debug(f"Found LinkedIn URL", {"url": cleaned_url})
            
            # Facebook
            elif any(domain in url_lower for domain in ['facebook.com', 'fb.com', 'fb.me']):
                match = re.search(r'(?:facebook\.com|fb\.com|fb\.me)/([a-zA-Z0-9_.\-]+)', url_lower, re.IGNORECASE)
                if not social_media.get('facebook'):
                    cleaned_url = self._clean_social_url(url)
                    if cleaned_url:
                        facebook_data = {
                            'url': cleaned_url
                        }
                        if match:
                            facebook_data['handle'] = match.group(1)
                        social_media['facebook'] = facebook_data
                        self.log_service.log_debug(f"Found Facebook URL", {"url": cleaned_url})
            
            # Twitter/X
            elif any(domain in url_lower for domain in ['twitter.com', 'x.com', 't.co']):
                match = re.search(r'(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)', url_lower, re.IGNORECASE)
                if not social_media.get('twitter'):
                    cleaned_url = self._clean_social_url(url)
                    if cleaned_url:
                        twitter_data = {
                            'url': cleaned_url
                        }
                        if match:
                            twitter_data['handle'] = match.group(1)
                        social_media['twitter'] = twitter_data
                        self.log_service.log_debug(f"Found Twitter/X URL", {"url": cleaned_url})
            
            # YouTube
            elif any(domain in url_lower for domain in ['youtube.com', 'youtu.be', 'yt.be']):
                match = re.search(r'(?:youtube\.com/(?:channel|c|user)/|youtube\.com/@)([a-zA-Z0-9_-]+)', url_lower, re.IGNORECASE)
                if not social_media.get('youtube'):
                    cleaned_url = self._clean_social_url(url)
                    if cleaned_url:
                        youtube_data = {
                            'url': cleaned_url
                        }
                        if match:
                            youtube_data['channel'] = match.group(1)
                        social_media['youtube'] = youtube_data
                        self.log_service.log_debug(f"Found YouTube URL", {"url": cleaned_url})
            
            # TikTok
            elif any(domain in url_lower for domain in ['tiktok.com', 'vm.tiktok.com']):
                match = re.search(r'tiktok\.com/@([a-zA-Z0-9_.]+)', url_lower, re.IGNORECASE)
                if not social_media.get('tiktok'):
                    cleaned_url = self._clean_social_url(url)
                    if cleaned_url:
                        tiktok_data = {
                            'url': cleaned_url
                        }
                        if match:
                            tiktok_data['username'] = match.group(1)
                        social_media['tiktok'] = tiktok_data
                        self.log_service.log_debug(f"Found TikTok URL", {"url": cleaned_url})
            
            # Telegram
            elif any(domain in url_lower for domain in ['t.me', 'telegram.me', 'telegram.org']):
                match = re.search(r'(?:t\.me|telegram\.me|telegram\.org)/([a-zA-Z0-9_]+)', url_lower, re.IGNORECASE)
                if not social_media.get('telegram'):
                    cleaned_url = self._clean_social_url(url)
                    if cleaned_url:
                        telegram_data = {
                            'url': cleaned_url
                        }
                        if match:
                            telegram_data['username'] = match.group(1)
                        social_media['telegram'] = telegram_data
                        self.log_service.log_debug(f"Found Telegram URL", {"url": cleaned_url})
            
            # WhatsApp
            elif any(domain in url_lower for domain in ['wa.me', 'whatsapp.com', 'api.whatsapp.com']):
                phone_match = re.search(r'(?:wa\.me/|phone=|whatsapp\.com/send/\?phone=)([0-9+]+)', url_lower, re.IGNORECASE)
                if not social_media.get('whatsapp'):
                    cleaned_url = self._clean_social_url(url)
                    whatsapp_data = {}
                    
                    if cleaned_url:
                        whatsapp_data['url'] = cleaned_url
                    
                    if phone_match:
                        phone = phone_match.group(1)
                        clean_phone = re.sub(r'[^0-9+]', '', phone)
                        if clean_phone and len(clean_phone) >= 8:
                            whatsapp_data['phone'] = clean_phone
                    
                    if whatsapp_data:
                        social_media['whatsapp'] = whatsapp_data
                        self.log_service.log_debug(f"Found WhatsApp URL", {"data": whatsapp_data})
                        
        except Exception as e:
            self.log_service.log_debug("Error processing social URL", {
                "url": url,
                "error": str(e)
            })
    


    def _clean_social_url(self, url: str) -> Optional[str]:
        """Limpa e valida URLs de redes sociais"""
        try:
            if not url or not isinstance(url, str):
                return None
            
            url = url.strip()
            
            # Ignorar URLs relativas ou caminhos de arquivo
            if url.startswith('/') and not url.startswith('//'):
                return None
                
            # Adicionar https:// se não tiver protocolo
            if not url.startswith(('http://', 'https://')):
                # Se começar com // (protocolo relativo), adicionar https:
                if url.startswith('//'):
                    url = 'https:' + url
                # Caso contrário, adicionar https://
                else:
                    url = 'https://' + url
                    
            # Verificar se a URL tem um domínio válido
            if '.' not in url.split('/')[2]:
                return None
                
            # Remove parâmetros de tracking comuns e fragmentos
            try:
                from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
                
                url_parts = list(urlparse(url))
                query = parse_qs(url_parts[4])
                
                # Remover parâmetros de tracking conhecidos
                params_to_remove = [
                    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                    'fbclid', 'gclid', 'ocid', 'ncid', 'ref', 'ref_src', 'ref_url', 'source',
                    '_hsenc', '_hsmi', 'mc_cid', 'mc_eid', 'yclid', 'igshid', '_ga'
                ]
                
                for param in params_to_remove:
                    if param in query:
                        del query[param]
                
                # Reconstruir a query string
                url_parts[4] = urlencode(query, doseq=True)
                
                # Remover fragmentos (tudo após #)
                url_parts[5] = ''
                
                # Reconstruir a URL
                url = urlunparse(url_parts)
            except Exception:
                # Fallback para método simples se o parsing falhar
                pass
            url = url.split('?')[0].split('#')[0]
            
            # Remove trailing slash
            url = url.rstrip('/')
            
            # Validações específicas por plataforma
            if 'linkedin.com' in url:
                # Garantir que é uma URL válida do LinkedIn
                if any(path in url for path in ['/company/', '/in/', '/school/', '/showcase/']):
                    return url
                # Se é apenas linkedin.com sem path específico, ignorar
                elif url.endswith('linkedin.com'):
                    return None
                    
            elif 'instagram.com' in url:
                # Validar formato do Instagram
                if '/p/' in url or url.count('/') >= 3:  # instagram.com/username
                    return url
                elif url.endswith('instagram.com'):
                    return None
                    
            elif 'facebook.com' in url:
                # Validar formato do Facebook
                if any(path in url for path in ['/pages/', '/profile.php']) or url.count('/') >= 3:
                    return url
                elif url.endswith('facebook.com'):
                    return None
                    
            elif any(domain in url for domain in ['twitter.com', 'x.com']):
                # Validar formato do Twitter/X
                if url.count('/') >= 3:  # twitter.com/username
                    return url
                elif url.endswith(('twitter.com', 'x.com')):
                    return None
                    
            elif 'youtube.com' in url:
                # Validar formato do YouTube
                if any(path in url for path in ['/channel/', '/c/', '/user/', '/@']) or url.count('/') >= 3:
                    return url
                elif url.endswith('youtube.com'):
                    return None
                    
            elif 'wa.me' in url or 'whatsapp.com' in url:
                # WhatsApp sempre válido se contém número
                return url
                
            # Para outras redes sociais, retornar a URL limpa se tiver path
            if url.count('/') >= 3:
                return url
                
            return None
            
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
            
    def _convert_to_int(self, value: str) -> Optional[int]:
        """Converte strings como '1.2k followers' ou '3.5M' para valores inteiros"""
        if not value or not isinstance(value, str):
            return None
            
        try:
            # Remover texto não numérico e manter apenas números e símbolos relevantes
            import re
            # Extrair o número e o multiplicador (k, m, etc)
            match = re.search(r'([\d,.]+)\s*([kmb])?', value.lower())
            if not match:
                return None
                
            # Extrair o número e remover vírgulas e pontos extras
            num_str = match.group(1).replace(',', '.')
            # Garantir que há apenas um ponto decimal
            if num_str.count('.') > 1:
                parts = num_str.split('.')
                num_str = parts[0] + '.' + ''.join(parts[1:])
                
            num = float(num_str)
            
            # Aplicar multiplicador se existir
            multiplier = match.group(2) if len(match.groups()) > 1 and match.group(2) else ''
            if multiplier == 'k':
                num *= 1000
            elif multiplier == 'm':
                num *= 1000000
            elif multiplier == 'b':
                num *= 1000000000
                
            return int(num)
        except Exception as e:
            self.log_service.log_debug("Error converting string to int", {"error": str(e), "value": value})
            return None













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

    def _extract_linkedin_url_from_data(self, data: Dict[str, Any]) -> Optional[str]:
        """Extrai URL do LinkedIn dos dados extraídos"""
        try:
            # Verificar em diferentes locais possíveis
            linkedin_url = None
            
            # Verificar no campo linkedin direto
            if data.get('linkedin'):
                linkedin_url = data['linkedin']
            
            # Verificar em social_media (pode ser dict ou list)
            elif data.get('social_media'):
                social_media = data['social_media']
                if isinstance(social_media, dict) and social_media.get('linkedin'):
                    linkedin_url = social_media['linkedin']
                elif isinstance(social_media, list):
                    # Procurar por LinkedIn na lista de redes sociais
                    for item in social_media:
                        if isinstance(item, dict) and item.get('platform') == 'linkedin':
                            linkedin_url = item.get('url')
                            break
            
            # Verificar em linkedin_data
            elif data.get('linkedin_data') and isinstance(data['linkedin_data'], dict) and data['linkedin_data'].get('url'):
                linkedin_url = data['linkedin_data']['url']
            
            if linkedin_url and isinstance(linkedin_url, str):
                cleaned_url = self._clean_social_url(linkedin_url)
                if cleaned_url and 'linkedin.com' in cleaned_url:
                    return cleaned_url
            
            return None
        except Exception as e:
            self.log_service.log_debug("Error extracting LinkedIn URL from data", {"error": str(e)})
            return None
    
    def _extract_instagram_url_from_data(self, data: Dict[str, Any]) -> Optional[str]:
        """Extrai URL do Instagram dos dados extraídos"""
        try:
            # Verificar em diferentes locais possíveis
            instagram_url = None
            
            # Verificar no campo instagram direto
            if data.get('instagram'):
                instagram_url = data['instagram']
            
            # Verificar em social_media
            elif data.get('social_media', {}).get('instagram'):
                instagram_url = data['social_media']['instagram']
            
            # Verificar em instagram_data
            elif data.get('instagram_data', {}).get('url'):
                instagram_url = data['instagram_data']['url']
            
            if instagram_url and isinstance(instagram_url, str):
                cleaned_url = self._clean_social_url(instagram_url)
                if cleaned_url and 'instagram.com' in cleaned_url:
                    return cleaned_url
            
            return None
        except Exception as e:
            self.log_service.log_debug("Error extracting Instagram URL from data", {"error": str(e)})
            return None
            
    def _extract_instagram_username_from_url(self, instagram_url: str) -> Optional[str]:
        """Extrai o nome de usuário do Instagram a partir da URL"""
        try:
            if not instagram_url:
                return None
                
            # Limpar a URL
            cleaned_url = self._clean_social_url(instagram_url)
            if not cleaned_url:
                return None
                
            # Padrões para extrair username do Instagram
            patterns = [
                r'instagram\.com/([a-zA-Z0-9._]+)/?',  # instagram.com/username
                r'instagram\.com/([a-zA-Z0-9._]+)\?',  # instagram.com/username?param=value
                r'instagram\.com/p/[^/]+/([a-zA-Z0-9._]+)/?'  # instagram.com/p/postid/username
            ]
            
            for pattern in patterns:
                match = re.search(pattern, cleaned_url)
                if match:
                    username = match.group(1)
                    # Remover parâmetros e fragmentos
                    username = username.split('?')[0].split('#')[0]
                    # Verificar se é um username válido
                    if username and username not in ['p', 'explore', 'stories', 'reel']:
                        return username
            
            return None
        except Exception as e:
            self.log_service.log_debug("Error extracting Instagram username from URL", {
                "instagram_url": instagram_url,
                "error": str(e)
            })
            return None
    
    async def _scrape_instagram_profile(self, instagram_url: str) -> Optional[Dict[str, Any]]:
        """Faz scraping do perfil do Instagram para extrair dados da bio"""
        try:
            self.log_service.log_debug("Starting Instagram profile scraping", {"url": instagram_url})
            
            # Usar Firecrawl para fazer scraping do Instagram
            firecrawl = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))
            
            scrape_result = firecrawl.scrape_url(
                instagram_url,
                formats=['markdown']
            )
            
            if scrape_result and scrape_result.get('markdown'):
                markdown_content = scrape_result['markdown']
                
                # Extrair dados usando LLM
                instagram_schema = {
                    "url": "string - URL completa do perfil Instagram",
                    "username": "string - Nome de usuário (@username)",
                    "name": "string - Nome de exibição do perfil",
                    "bio": "string - Biografia/descrição do perfil",
                    "followers": "string - Número de seguidores",
                    "following": "string - Número de pessoas seguindo",
                    "posts": "string - Número de posts",
                    "email": "string - Email encontrado na bio (se houver)",
                    "phone": "string - Telefone encontrado na bio (se houver)",
                    "website": "string - Website/link encontrado na bio (se houver)",
                    "location": "string - Localização mencionada na bio (se houver)",
                    "business_category": "string - Categoria do negócio (se for conta business)"
                }
                
                extracted_data = await self._extract_json_from_markdown(markdown_content, instagram_schema)
                
                if extracted_data:
                    # Adicionar URL original
                    extracted_data['url'] = instagram_url
                    self.log_service.log_debug("Instagram profile data extracted successfully", {"username": extracted_data.get('username')})
                    return extracted_data
            
            self.log_service.log_debug("No data extracted from Instagram profile", {"url": instagram_url})
            return None
            
        except Exception as e:
            self.log_service.log_debug("Error scraping Instagram profile", {"url": instagram_url, "error": str(e)})
            return None
    
    def _merge_linkedin_data(self, base_data: Dict[str, Any], linkedin_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mescla dados do LinkedIn com dados base da empresa"""
        try:
            # Manter dados base e adicionar/sobrescrever com dados do LinkedIn
            merged_data = base_data.copy()
            
            # Campos prioritários do LinkedIn
            linkedin_priority_fields = [
                'name', 'description', 'industry', 'size', 'founded', 
                'headquarters', 'employees', 'followers_count'
            ]
            
            for field in linkedin_priority_fields:
                if linkedin_data.get(field):
                    merged_data[field] = linkedin_data[field]
            
            # Mesclar dados de redes sociais
            if linkedin_data.get('social_media'):
                if 'social_media' not in merged_data:
                    merged_data['social_media'] = []
                # Merge social media data as list
                if isinstance(linkedin_data['social_media'], list):
                    merged_data['social_media'].extend(linkedin_data['social_media'])
                elif isinstance(linkedin_data['social_media'], dict):
                    # Convert dict to list format
                    for platform, data in linkedin_data['social_media'].items():
                        merged_data['social_media'].append({'platform': platform, **data})
            
            # Adicionar dados específicos do LinkedIn
            if linkedin_data.get('linkedin'):
                merged_data['linkedin'] = linkedin_data['linkedin']
            
            # Criar objeto linkedin_data estruturado
            linkedin_obj = {
                'url': linkedin_data.get('linkedin') or linkedin_data.get('linkedin_url'),
                'company_name': linkedin_data.get('name'),
                'followers': linkedin_data.get('followers_count'),
                'employees_count': linkedin_data.get('employees'),
                'industry': linkedin_data.get('industry'),
                'description': linkedin_data.get('description')
            }
            
            # Adicionar apenas se há dados válidos
            if any(linkedin_obj.values()):
                merged_data['linkedin_data'] = linkedin_obj
            
            # Adicionar dados de funcionários se disponível
            if linkedin_data.get('employees'):
                merged_data['employees'] = linkedin_data['employees']
            
            self.log_service.log_debug("LinkedIn data merged successfully")
            return merged_data
            
        except Exception as e:
            self.log_service.log_debug("Error merging LinkedIn data", {"error": str(e)})
            return base_data
    
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
        self.firecrawl_api_key = os.getenv('FIRECRAWL_API_KEY')
        
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
            self._enrich_by_domain,
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
                
            self.log_service.log_debug("Starting LinkedIn URL direct enrichment", {"url": linkedin_url})
            
            # Verificar se é URL de perfil pessoal ou de empresa
            is_company_url = "/company/" in linkedin_url.lower()
            
            if is_company_url:
                # Enriquecimento para empresas
                async with CrawlAIService(self.log_service) as crawl_service:
                    company_data = await crawl_service.scrape_linkedin_company_advanced(linkedin_url)
                    
                    if company_data and not company_data.get("error"):
                        # Normalizar dados do LinkedIn
                        normalized_data = crawl_service._normalize_linkedin_data(company_data)
                        normalized_data["_source"] = "linkedin_direct_url"
                        normalized_data["linkedin_url"] = linkedin_url
                        return normalized_data
                        
                # Fallback para método tradicional se CrawlAI falhar
                company_data = await self._scrape_linkedin_company(linkedin_url)
                if company_data:
                    company_data['linkedin_url'] = linkedin_url
                    return company_data
            else:
                # Enriquecimento para pessoas
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
                    
                # Segundo fallback usando Firecrawl
                person_data = await self._scrape_linkedin_person_with_firecrawl(linkedin_url)
                if person_data:
                    person_data['linkedin_url'] = linkedin_url
                    return self._format_person_result(person_data, source='firecrawl_linkedin')
            
            self.log_service.log_debug("LinkedIn URL enrichment failed", {"url": linkedin_url})
            return None
            
        except Exception as e:
            self.log_service.log_debug("Error in LinkedIn URL enrichment", {"error": str(e)})
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

    async def _find_linkedin_on_website_firecrawl(self, website_url: str) -> Optional[str]:
        """
        Usa o Firecrawl para encontrar um link do LinkedIn em um site
        """
        try:
            # Definir schema para extrair apenas a URL do LinkedIn
            schema = {
                "linkedin_url": {
                    "type": "string",
                    "description": "URL do perfil LinkedIn encontrado no site. Deve ser uma URL completa começando com https://www.linkedin.com/"
                }
            }
            
            # Chamar o Firecrawl com o schema
            result = await self._scrape_with_firecrawl(
                url=website_url,
                schema=schema,
                prompt="Encontre a URL do LinkedIn neste site. Retorne apenas a URL completa do LinkedIn."
            )
            
            if result and "linkedin_url" in result and result["linkedin_url"]:
                linkedin_url = result["linkedin_url"]
                # Verificar se é uma URL válida do LinkedIn
                if linkedin_url.startswith("https://www.linkedin.com/"):
                    return linkedin_url
            
            return None
        except Exception as e:
            self.log_service.log_debug("Error finding LinkedIn URL with Firecrawl", {"error": str(e)})
            return None
            
    async def _scrape_with_firecrawl(self, url: str, schema: Dict[str, Any] = None, prompt: str = None) -> Dict[str, Any]:
        """Scraping com Firecrawl e extração com LLM"""
        if not self.firecrawl_api_key:
            self.log_service.log_debug("Firecrawl API key not configured.", {})
            return {"error": "Firecrawl not configured"}

        try:
            from firecrawl import FirecrawlApp
            
            app = FirecrawlApp(api_key=self.firecrawl_api_key)
            
            self.log_service.log_debug("Starting Firecrawl scraping", {"url": url})
            
            # Se temos um schema, usar para extrair dados estruturados
            if schema:
                result = app.extract(url=url, schema=schema, prompt=prompt)
                return result
            
            # Caso contrário, apenas fazer scraping do conteúdo
            scraped_data = app.scrape_url(url)
            
            # Processar resultado
            if isinstance(scraped_data, list) and len(scraped_data) > 0:
                return {"content": scraped_data[0]}
            elif hasattr(scraped_data, 'content'):
                return {"content": scraped_data.content}
            elif isinstance(scraped_data, dict):
                return scraped_data
            else:
                return {"content": str(scraped_data)}
                
        except Exception as e:
            self.log_service.log_debug("Error in Firecrawl scraping", {"error": str(e)})
            return {"error": str(e)}
    
    async def _enrich_by_domain(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Estratégia 3: Enriquecimento por domínio para encontrar perfil LinkedIn"""
        domain = data.get('domain') or data.get('company_domain')
        email = data.get('email')
        
        # Extrair domínio do email se não fornecido diretamente
        if not domain and email and '@' in email:
            domain = email.split('@')[1]
            
        if not domain:
            return None
            
        self.log_service.log_debug("Starting domain enrichment for person", {"domain": domain})
        
        # Normalizar URL
        if not domain.startswith(("http://", "https://")):
            website_url = f"https://{domain}"
        else:
            website_url = domain
            
        # Estratégia 1: Usar Firecrawl para encontrar LinkedIn no site
        try:
            linkedin_url = await self._find_linkedin_on_website_firecrawl(website_url)
            
            if linkedin_url:
                self.log_service.log_debug("Found LinkedIn URL via domain", {"linkedin_url": linkedin_url})
                
                # Verificar se é URL de perfil pessoal ou de empresa
                if "/in/" in linkedin_url.lower():
                    # É um perfil pessoal, usar diretamente
                    return await self._enrich_by_linkedin_url({"linkedin_url": linkedin_url})
                else:
                    # É um perfil de empresa, buscar pessoa pelo nome na empresa
                    full_name = data.get('full_name')
                    if full_name:
                        # Extrair nome da empresa do LinkedIn URL
                        company_name = linkedin_url.split("/company/")[1].split("/")[0] if "/company/" in linkedin_url else ""
                        if company_name:
                            # Buscar pessoa pelo nome + empresa no LinkedIn
                            return await self._enrich_by_name_company({"full_name": full_name, "company_name": company_name})
        except Exception as e:
            self.log_service.log_debug("Error finding LinkedIn via domain", {"error": str(e)})
        
        return None
        
    async def _enrich_by_name_company(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Estratégia 4: Nome + Empresa"""
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
        """Estratégia 5: Busca por telefone"""
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
        
    async def _enrich_by_instagram(self, instagram_url: str) -> Dict[str, Any]:
        """Enriquecimento de empresa usando perfil do Instagram"""
        try:
            self.log_service.log_debug("Starting Instagram enrichment", {"instagram_url": instagram_url})
            
            # Usar o serviço dedicado de scraping do Instagram
            scrape_result = await self.instagram_scraper.scrape_profile(instagram_url)
            
            # Verificar se houve erro
            if "error" in scrape_result:
                self.log_service.log_debug("Instagram scraping failed", {
                    "instagram_url": instagram_url,
                    "error": scrape_result["error"]
                })
                return {"error": scrape_result["error"]}
            
            # Extrair dados do resultado
            instagram_data = scrape_result["data"]
            instagram_username = instagram_data.get("username")
            
            # Criar estrutura de dados normalizada
            result = {
                "name": instagram_data.get("name"),
                "description": instagram_data.get("bio"),
                "instagram": {
                    "url": instagram_url,
                    "username": instagram_username,
                    "name": instagram_data.get("name"),
                    "bio": instagram_data.get("bio"),
                    "email": instagram_data.get("email"),
                    "phone": instagram_data.get("phone"),
                    "followers_count": instagram_data.get("followers_count"),
                    "following_count": instagram_data.get("following_count"),
                    "posts_count": instagram_data.get("posts_count")
                },
                "website": instagram_data.get("website"),
                "_source": "instagram",
                "_confidence_score": 0.8
            }
            
            self.log_service.log_debug("Instagram enrichment successful", {"username": instagram_username})
            return result
            
        except Exception as e:
            self.log_service.log_debug("Instagram enrichment error", {
                "instagram_url": instagram_url,
                "error": str(e)
            })
            return {"error": f"Instagram enrichment failed: {str(e)}"}
    
    async def _enrich_by_general_search(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Estratégia 6: Busca geral"""
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
                merged['social_media'] = []
            # Handle both dict and list formats
            if isinstance(website_data['social_media'], dict):
                for platform, url in website_data['social_media'].items():
                    if url:
                        # Convert to list format
                        if isinstance(url, str):
                            merged['social_media'].append({'platform': platform, 'url': url})
                        elif isinstance(url, dict):
                            merged['social_media'].append({'platform': platform, **url})
            elif isinstance(website_data['social_media'], list):
                merged['social_media'].extend(website_data['social_media'])
        
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
        
    async def _scrape_linkedin_person_with_firecrawl(self, linkedin_url: str) -> Optional[Dict[str, Any]]:
        """Faz scraping de dados de pessoa no LinkedIn usando Firecrawl."""
        self.log_service.log_debug("Starting LinkedIn person scraping with Firecrawl", {"url": linkedin_url})
        
        # Schema para extração de dados de pessoa
        person_schema = {
            "name": "string",
            "headline": "string",
            "location": "string",
            "current_company": "string",
            "current_position": "string",
            "about": "string",
            "experience": [{
                "title": "string",
                "company": "string",
                "duration": "string",
                "description": "string"
            }],
            "education": [{
                "institution": "string",
                "degree": "string",
                "field": "string",
                "duration": "string"
            }],
            "skills": ["string"],
            "languages": ["string"],
            "certifications": [{
                "name": "string",
                "issuer": "string",
                "date": "string"
            }],
            "contact_info": {
                "email": "string",
                "phone": "string",
                "website": "string"
            }
        }
        
        try:
            # Usar Firecrawl para obter dados da página
            scraped_data = await self._scrape_with_firecrawl(linkedin_url, person_schema, None)
            
            if not scraped_data or scraped_data.get("error"):
                self.log_service.log_debug("Firecrawl scraping failed", {"url": linkedin_url})
                return None
            
            # Mapear os dados para o formato esperado
            person_data = {
                'name': scraped_data.get('name'),
                'headline': scraped_data.get('headline'),
                'location': scraped_data.get('location'),
                'current_company': scraped_data.get('current_company'),
                'current_title': scraped_data.get('current_position'),
                'about': scraped_data.get('about'),
                'skills': scraped_data.get('skills', []),
                'experience': scraped_data.get('experience', []),
                'education': scraped_data.get('education', []),
                'certifications': scraped_data.get('certifications', []),
                'languages': scraped_data.get('languages', []),
                'contact_info': scraped_data.get('contact_info', {}),
                'source': 'firecrawl',
                'confidence_score': 0.6  # Confiança menor que CrawlAI
            }
            
            return person_data
            
        except Exception as e:
            self.log_service.log_debug("LinkedIn person scraping with Firecrawl failed", {"error": str(e), "url": linkedin_url})
            return None
    
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