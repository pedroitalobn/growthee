from typing import Dict, Any, Optional, List, Union
import os
import re
import json
import logging
from bs4 import BeautifulSoup

from api.log_service import LogService

class HyperbrowserInstagramScraperService:
    """Serviço especializado para scraping de perfis do Instagram usando Hyperbrowser"""
    
    def __init__(self, log_service: LogService = None):
        """Inicializa o serviço de scraping do Instagram com Hyperbrowser"""
        self.log_service = log_service or LogService()
    
    async def scrape_profile(self, instagram_url: str) -> Dict[str, Any]:
        """Faz scraping de um perfil do Instagram e extrai dados estruturados usando Hyperbrowser"""
        try:
            self.log_service.log_debug("Starting Instagram profile scraping with Hyperbrowser", {"url": instagram_url})
            
            # Validar e limpar URL
            username = self._extract_username_from_url(instagram_url)
            if not username:
                self.log_service.log_debug("Invalid Instagram URL format", {"url": instagram_url})
                return {"error": "Invalid Instagram URL format"}
            
            # Normalizar URL
            normalized_url = f"https://www.instagram.com/{username}/"
            
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
            
            # Usar Hyperbrowser para extrair dados estruturados
            extracted_data = await self._extract_with_hyperbrowser(normalized_url, instagram_schema)
            
            if extracted_data and not extracted_data.get("error"):
                # Adicionar URL original
                extracted_data["url"] = normalized_url
                
                # Processar dados numéricos
                extracted_data["followers_count"] = self._convert_to_int(extracted_data.get("followers"))
                extracted_data["following_count"] = self._convert_to_int(extracted_data.get("following"))
                extracted_data["posts_count"] = self._convert_to_int(extracted_data.get("posts"))
                
                self.log_service.log_debug("Instagram profile data extracted successfully with Hyperbrowser", 
                                          {"username": extracted_data.get("username")})
                return {
                    "success": True,
                    "data": extracted_data
                }
            
            # Se falhar, tentar com o agente Claude
            self.log_service.log_debug("Structured extraction failed, trying with Claude agent", 
                                      {"url": normalized_url})
            return await self._fallback_with_claude_agent(normalized_url)
            
        except Exception as e:
            self.log_service.log_debug("Error scraping Instagram profile with Hyperbrowser", 
                                      {"url": instagram_url, "error": str(e)})
            return {"error": f"Failed to scrape Instagram profile: {str(e)}"}
    
    async def _extract_with_hyperbrowser(self, url: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extrai dados estruturados usando Hyperbrowser"""
        try:
            # Importar o módulo MCP para usar o Hyperbrowser
            import json
            from api.mcp_client import run_mcp
            from api.firecrawl_client import FirecrawlApp
            
            # Tentar primeiro com a API Firecrawl v2
            try:
                firecrawl = FirecrawlApp()
                result = firecrawl.extract_structured_data(
                    url=url,
                    schema=schema,
                    prompt="Extract all available information from this Instagram profile. Pay special attention to contact information: extract ALL emails, phone numbers, and WhatsApp numbers found in the bio, contact section, or any visible text. Look for multiple contact methods as businesses often list several ways to reach them. Include website links, business addresses, and any social media handles mentioned."
                )
                
                if result and not result.get("error"):
                    self.log_service.log_debug("Instagram data extracted successfully with Firecrawl v2", {"url": url})
                    return result
                else:
                    self.log_service.log_debug("Firecrawl v2 extraction failed, falling back to Hyperbrowser", 
                                              {"url": url, "error": result.get("error")})
            except Exception as e:
                self.log_service.log_debug("Error with Firecrawl v2 extraction", {"error": str(e)})
            
            # Fallback para Hyperbrowser MCP
            self.log_service.log_debug("Using Hyperbrowser MCP for extraction", {"url": url})
            
            # Configurar a extração estruturada
            result = await run_mcp(
                server_name="mcp.config.usrlocalmcp.Hyperbrowser",
                tool_name="extract_structured_data",
                args={
                    "urls": [url],
                    "prompt": "Extract all available information from this Instagram profile. Pay special attention to contact information: extract ALL emails, phone numbers, and WhatsApp numbers found in the bio, contact section, or any visible text. Look for multiple contact methods as businesses often list several ways to reach them. Include website links, business addresses, and any social media handles mentioned.",
                    "schema": schema,
                    "sessionOptions": {
                        "useProxy": True,
                        "useStealth": True,
                        "acceptCookies": True
                    }
                }
            )
            
            # Processar o resultado
            if result and isinstance(result, list) and len(result) > 0:
                return result[0]
            elif result and isinstance(result, dict):
                return result
            else:
                return {"error": "No data extracted"}
                
        except Exception as e:
            self.log_service.log_debug("Error in Hyperbrowser extraction", {"error": str(e)})
            return {"error": f"Hyperbrowser extraction failed: {str(e)}"}
    
    async def _fallback_with_claude_agent(self, url: str) -> Dict[str, Any]:
        """Método de fallback usando o agente Claude do Hyperbrowser"""
        try:
            # Importar o módulo MCP para usar o Hyperbrowser
            from api.mcp_client import run_mcp
            
            # Usar o agente Claude para extrair informações
            result = await run_mcp(
                server_name="mcp.config.usrlocalmcp.Hyperbrowser",
                tool_name="claude_computer_use_agent",
                args={
                    "task": f"Visit {url} and extract the following information from this Instagram profile: \n"
                           f"1. Username\n"
                           f"2. Full name\n"
                           f"3. Bio/description\n"
                           f"4. Number of followers\n"
                           f"5. Number of following\n"
                           f"6. Number of posts\n"
                           f"7. Email (if available)\n"
                           f"8. Website (if available)\n"
                           f"9. Business category (if available)\n"
                           f"10. Location (if available)\n"
                           f"Return the data in a structured format.",
                    "sessionOptions": {
                        "useProxy": True,
                        "useStealth": True,
                        "acceptCookies": True
                    },
                    "maxSteps": 25
                }
            )
            
            # Processar o resultado
            if not result or not isinstance(result, dict):
                return {"error": "No data extracted by Claude agent"}
                
            # Extrair informações do resultado
            extracted_data = {}
            content = result.get("content", "")
            
            # Usar regex para extrair informações
            username_match = re.search(r'Username[:\s]+([@\w\.]+)', content, re.IGNORECASE)
            if username_match:
                extracted_data["username"] = username_match.group(1).strip().replace("@", "")
                
            name_match = re.search(r'Full name[:\s]+([^\n]+)', content, re.IGNORECASE)
            if name_match:
                extracted_data["name"] = name_match.group(1).strip()
                
            bio_match = re.search(r'Bio/description[:\s]+([^\n]+(?:\n[^\d\n][^\n]*)*)', content, re.IGNORECASE)
            if bio_match:
                extracted_data["bio"] = bio_match.group(1).strip()
                
            followers_match = re.search(r'followers[:\s]+([\d,.km]+)', content, re.IGNORECASE)
            if followers_match:
                extracted_data["followers"] = followers_match.group(1).strip()
                
            following_match = re.search(r'following[:\s]+([\d,.km]+)', content, re.IGNORECASE)
            if following_match:
                extracted_data["following"] = following_match.group(1).strip()
                
            posts_match = re.search(r'posts[:\s]+([\d,.km]+)', content, re.IGNORECASE)
            if posts_match:
                extracted_data["posts"] = posts_match.group(1).strip()
                
            email_match = re.search(r'Email[:\s]+([^\n]+)', content, re.IGNORECASE)
            if email_match and "not available" not in email_match.group(1).lower():
                extracted_data["email"] = email_match.group(1).strip()
                
            website_match = re.search(r'Website[:\s]+([^\n]+)', content, re.IGNORECASE)
            if website_match and "not available" not in website_match.group(1).lower():
                extracted_data["website"] = website_match.group(1).strip()
                
            category_match = re.search(r'Business category[:\s]+([^\n]+)', content, re.IGNORECASE)
            if category_match and "not available" not in category_match.group(1).lower():
                extracted_data["business_category"] = category_match.group(1).strip()
                
            location_match = re.search(r'Location[:\s]+([^\n]+)', content, re.IGNORECASE)
            if location_match and "not available" not in location_match.group(1).lower():
                extracted_data["location"] = location_match.group(1).strip()
            
            # Adicionar URL original
            extracted_data["url"] = url
            
            # Processar dados numéricos
            extracted_data["followers_count"] = self._convert_to_int(extracted_data.get("followers"))
            extracted_data["following_count"] = self._convert_to_int(extracted_data.get("following"))
            extracted_data["posts_count"] = self._convert_to_int(extracted_data.get("posts"))
            
            self.log_service.log_debug("Instagram profile data extracted with Claude agent", 
                                      {"username": extracted_data.get("username")})
            return {
                "success": True,
                "data": extracted_data
            }
            
        except Exception as e:
            self.log_service.log_debug("Error in Claude agent extraction", {"error": str(e)})
            return {"error": f"Claude agent extraction failed: {str(e)}"}
    
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