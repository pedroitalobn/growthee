from typing import Dict, Any, Optional, List, Union
import os
import re
import json
import logging
from bs4 import BeautifulSoup

from api.firecrawl_client import FirecrawlApp
from api.log_service import LogService

class InstagramScraperService:
    """Serviço especializado para scraping de perfis do Instagram"""
    
    def __init__(self, log_service: LogService = None, firecrawl_api_key: str = None):
        """Inicializa o serviço de scraping do Instagram"""
        self.log_service = log_service or LogService()
        self.firecrawl_api_key = firecrawl_api_key or os.getenv("FIRECRAWL_API_KEY")
    
    async def scrape_profile(self, instagram_url: str) -> Dict[str, Any]:
        """Faz scraping de um perfil do Instagram e extrai dados estruturados"""
        try:
            self.log_service.log_debug("Starting Instagram profile scraping", {"url": instagram_url})
            
            # Validar e limpar URL
            username = self._extract_username_from_url(instagram_url)
            if not username:
                self.log_service.log_debug("Invalid Instagram URL format", {"url": instagram_url})
                return {"error": "Invalid Instagram URL format"}
            
            # Normalizar URL
            normalized_url = f"https://www.instagram.com/{username}/"
            
            # Usar Firecrawl para fazer scraping do Instagram
            firecrawl = FirecrawlApp(api_key=self.firecrawl_api_key)
            
            # Schema para extração estruturada
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
            
            # Usar extração estruturada direta com DeepSeek como LLM
            result = firecrawl.extract_structured_data(normalized_url, instagram_schema, use_deepseek=True)
            
            if result and not result.get("error"):
                # Verificar se os dados estão no formato esperado (dentro de 'data')
                extracted_data = result.get("data", {})
                if not extracted_data and isinstance(result, dict):
                    # Se não houver 'data', usar o próprio resultado
                    extracted_data = result
                
                # Adicionar URL original
                extracted_data["url"] = normalized_url
                
                # Processar dados numéricos
                extracted_data["followers_count"] = self._convert_to_int(extracted_data.get("followers"))
                extracted_data["following_count"] = self._convert_to_int(extracted_data.get("following"))
                extracted_data["posts_count"] = self._convert_to_int(extracted_data.get("posts"))
                
                self.log_service.log_debug("Instagram profile data extracted successfully", 
                                          {"username": extracted_data.get("username")})
                return {
                    "success": True,
                    "data": extracted_data
                }
            
            # Se falhar com extração estruturada, tentar com scrape + LLM
            self.log_service.log_debug("Structured extraction failed, trying with scrape + LLM", 
                                      {"url": normalized_url})
            return await self._fallback_scrape_with_llm(normalized_url)
            
        except Exception as e:
            self.log_service.log_debug("Error scraping Instagram profile", 
                                      {"url": instagram_url, "error": str(e)})
            return {"error": f"Failed to scrape Instagram profile: {str(e)}"}
    
    async def _fallback_scrape_with_llm(self, instagram_url: str) -> Dict[str, Any]:
        """Método de fallback usando scrape + LLM para extração"""
        try:
            firecrawl = FirecrawlApp(api_key=self.firecrawl_api_key)
            
            # Fazer scrape da página
            scrape_result = firecrawl.scrape_url(
                instagram_url,
                params={
                    'formats': ['markdown', 'html'],
                    'includeTags': ['div', 'span', 'a', 'meta', 'script'],
                    'onlyMainContent': False,
                    'waitFor': 3000
                }
            )
            
            # Verificar se temos conteúdo markdown
            markdown_content = None
            
            # Verificar se scrape_result é uma lista (formato atual da resposta)
            if isinstance(scrape_result, list) and len(scrape_result) > 0:
                # Assumir que o primeiro item contém markdown
                if len(scrape_result) >= 1 and isinstance(scrape_result[0], str):
                    markdown_content = scrape_result[0]
            # Verificar se é um objeto com atributos
            elif hasattr(scrape_result, 'markdown'):
                markdown_content = scrape_result.markdown
            # Verificar se é um dicionário
            elif isinstance(scrape_result, dict):
                markdown_content = scrape_result.get('markdown')
            
            if not markdown_content:
                return {"error": "No content extracted from Instagram profile"}
            
            # Schema para extração via LLM
            instagram_schema = {
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
            
            # Usar o serviço de extração com LLM
            from api.services import CompanyEnrichmentService
            company_service = CompanyEnrichmentService()
            extracted_data = await company_service._extract_json_from_markdown(markdown_content, instagram_schema)
            
            if extracted_data:
                # Adicionar URL original
                extracted_data["url"] = instagram_url
                
                # Processar dados numéricos
                extracted_data["followers_count"] = self._convert_to_int(extracted_data.get("followers"))
                extracted_data["following_count"] = self._convert_to_int(extracted_data.get("following"))
                extracted_data["posts_count"] = self._convert_to_int(extracted_data.get("posts"))
                
                self.log_service.log_debug("Instagram profile data extracted with LLM", 
                                          {"username": extracted_data.get("username")})
                return {
                    "success": True,
                    "data": extracted_data
                }
            
            return {"error": "Failed to extract data from Instagram profile"}
            
        except Exception as e:
            self.log_service.log_debug("Error in fallback Instagram scraping", 
                                      {"url": instagram_url, "error": str(e)})
            return {"error": f"Fallback Instagram scraping failed: {str(e)}"}
    
    def _extract_username_from_url(self, instagram_url: str) -> Optional[str]:
        """Extrai o nome de usuário de uma URL do Instagram ou username direto"""
        if not instagram_url:
            return None
            
        # Limpar a URL
        cleaned_url = instagram_url.strip().lower()
        
        # Se a entrada é apenas um nome de usuário sem URL ou símbolo @
        if re.match(r'^[a-zA-Z0-9_.]+$', cleaned_url):
            return cleaned_url
        
        # Padrões de URL do Instagram
        patterns = [
            r'instagram\.com/([a-zA-Z0-9_.]+)/?',  # instagram.com/username
            r'instagram\.com/([a-zA-Z0-9_.]+)\?',  # instagram.com/username?igshid=...
            r'@([a-zA-Z0-9_.]+)'  # @username
        ]
        
        for pattern in patterns:
            match = re.search(pattern, cleaned_url)
            if match:
                username = match.group(1)
                # Remover parâmetros ou caracteres inválidos
                username = re.sub(r'[^a-zA-Z0-9_.]', '', username)
                return username
                
        return None
    
    def _convert_to_int(self, value: Optional[str]) -> Optional[int]:
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