from typing import Dict, Any, Optional, List, Union
import os
import re
import json
import logging
import asyncio

from api.log_service import LogService
from api.mcp_client import run_mcp

class PuppeteerInstagramScraperService:
    """Serviço especializado para scraping de perfis do Instagram usando Puppeteer"""
    
    def __init__(self, log_service: LogService = None):
        """Inicializa o serviço de scraping do Instagram com Puppeteer"""
        self.log_service = log_service or LogService()
    
    async def scrape_profile(self, instagram_url: str) -> Dict[str, Any]:
        """Faz scraping de um perfil do Instagram e extrai dados estruturados usando Puppeteer"""
        try:
            self.log_service.log_debug("Starting Instagram profile scraping with Puppeteer", {"url": instagram_url})
            
            # Validar e limpar URL
            username = self._extract_username_from_url(instagram_url)
            if not username:
                self.log_service.log_debug("Invalid Instagram URL format", {"url": instagram_url})
                return {"error": "Invalid Instagram URL format"}
            
            # Normalizar URL
            normalized_url = f"https://www.instagram.com/{username}/"
            
            # Usar Puppeteer para extrair dados
            extracted_data = await self._extract_with_puppeteer(normalized_url)
            
            if extracted_data and not extracted_data.get("error"):
                # Adicionar URL original
                extracted_data["url"] = normalized_url
                
                # Processar dados numéricos
                extracted_data["followers_count"] = self._convert_to_int(extracted_data.get("followers"))
                extracted_data["following_count"] = self._convert_to_int(extracted_data.get("following"))
                extracted_data["posts_count"] = self._convert_to_int(extracted_data.get("posts"))
                
                self.log_service.log_debug("Instagram profile data extracted successfully with Puppeteer", 
                                          {"username": extracted_data.get("username")})
                return {
                    "success": True,
                    "data": extracted_data
                }
            
            return {"error": "Failed to extract Instagram profile data"}
            
        except Exception as e:
            self.log_service.log_debug("Error scraping Instagram profile with Puppeteer", 
                                      {"url": instagram_url, "error": str(e)})
            return {"error": f"Failed to scrape Instagram profile: {str(e)}"}
    
    async def _extract_with_puppeteer(self, url: str) -> Dict[str, Any]:
        """Extrai dados estruturados usando Hyperbrowser diretamente"""
        try:
            # Definir o schema para extração de dados do Instagram
            instagram_schema = {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "Nome de usuário do perfil do Instagram"
                    },
                    "name": {
                        "type": "string",
                        "description": "Nome completo ou nome de exibição do perfil"
                    },
                    "bio": {
                        "type": "string",
                        "description": "Biografia ou descrição do perfil"
                    },
                    "followers": {
                        "type": "string",
                        "description": "Número de seguidores (formato texto)"
                    },
                    "following": {
                        "type": "string",
                        "description": "Número de pessoas que o perfil segue (formato texto)"
                    },
                    "posts": {
                        "type": "string",
                        "description": "Número de posts (formato texto)"
                    },
                    "website": {
                        "type": "string",
                        "description": "Website ou link externo do perfil"
                    },
                    "email": {
                        "type": "string",
                        "description": "Endereço de email encontrado na bio ou informações de contato"
                    },
                    "business_category": {
                        "type": "string",
                        "description": "Categoria de negócio do perfil (se for uma conta business)"
                    },
                    "location": {
                        "type": "string",
                        "description": "Localização do perfil ou negócio"
                    }
                }
            }
            
            # Tentar primeiro com a API Firecrawl v2
            try:
                from api.firecrawl_client import FirecrawlApp
                
                # Definir o schema para extração de dados do Instagram
                schema = {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string"},
                        "name": {"type": "string"},
                        "bio": {"type": "string"},
                        "posts": {"type": "string"},
                        "followers": {"type": "string"},
                        "following": {"type": "string"},
                        "website": {"type": "string"},
                        "email": {"type": "string"},
                        "businessCategory": {"type": "string"},
                        "location": {"type": "string"}
                    }
                }
                
                firecrawl = FirecrawlApp()
                result = firecrawl.extract_structured_data(
                    url=url,
                    schema=schema,
                    prompt="Extract all available information from this Instagram profile page including username, name, bio, followers count, following count, posts count, website, email, business category, and location. Pay special attention to contact information: extract ALL emails, phone numbers, and WhatsApp numbers found in the bio, contact section, or any visible text. Look for multiple contact methods as businesses often list several ways to reach them. Include website links, business addresses, and any social media handles mentioned."
                )
                
                if result and not result.get("error"):
                    self.log_service.log_debug("Instagram data extracted successfully with Firecrawl v2", {"url": url})
                    return result
                else:
                    self.log_service.log_debug("Firecrawl v2 extraction failed, falling back to Hyperbrowser", 
                                              {"url": url, "error": result.get("error")})
            except Exception as e:
                self.log_service.log_debug("Error with Firecrawl v2 extraction", {"error": str(e)})
            
            # Fallback para Hyperbrowser
            # Opções de sessão para o Hyperbrowser
            session_options = {
                "useProxy": False,
                "useStealth": True,
                "acceptCookies": True
            }
            
            # Extrair dados estruturados usando Hyperbrowser
            self.log_service.log_debug("Extracting Instagram profile data with Hyperbrowser", {"url": url})
            extract_result = await run_mcp(
                server_name="mcp.config.usrlocalmcp.Hyperbrowser",
                tool_name="extract_structured_data",
                args={
                    "urls": [url],
                    "prompt": "Extract all available information from this Instagram profile page including username, name, bio, followers count, following count, posts count, website, email, business category, and location. Pay special attention to contact information: extract ALL emails, phone numbers, and WhatsApp numbers found in the bio, contact section, or any visible text. Look for multiple contact methods as businesses often list several ways to reach them. Include website links, business addresses, and any social media handles mentioned.",
                    "schema": instagram_schema,
                    "sessionOptions": session_options
                }
            )
            
            # Processar o resultado
            if extract_result and isinstance(extract_result, list) and len(extract_result) > 0:
                profile_data = extract_result[0]
                
                # Processar dados numéricos
                if "followers" in profile_data:
                    profile_data["followers_count"] = self._convert_to_int(profile_data.get("followers"))
                if "following" in profile_data:
                    profile_data["following_count"] = self._convert_to_int(profile_data.get("following"))
                if "posts" in profile_data:
                    profile_data["posts_count"] = self._convert_to_int(profile_data.get("posts"))
                    
                return profile_data
            
            # Se falhar, tentar com Claude agent como fallback
            self.log_service.log_debug("Structured extraction failed, trying with Claude agent", {"url": url})
            return await self._fallback_with_claude_agent(url)
                
        except Exception as e:
            self.log_service.log_debug("Error in Hyperbrowser extraction", {"error": str(e)})
            # Tentar com Claude agent como fallback
            return await self._fallback_with_claude_agent(url)
            
    async def _fallback_with_claude_agent(self, url: str) -> Dict[str, Any]:
        """Usa Claude agent como fallback para extrair dados do Instagram"""
        try:
            self.log_service.log_debug("Trying fallback with Claude agent", {"url": url})
            
            # Preparar a tarefa para o Claude agent
            task = f"""Visit {url} and extract the following information from this Instagram profile:
            1. Username
            2. Full name
            3. Bio/description
            4. Number of posts
            5. Number of followers
            6. Number of following
            7. Website URL (if available)
            8. Email (if available)
            9. Business category (if available)
            10. Location (if available)
            
            Format the response as plain text with each piece of information on a new line.
            For example:
            Username: example_user
            Name: Example User
            Bio: This is my bio
            Posts: 100
            Followers: 1,500
            Following: 500
            Website: https://example.com
            Email: contact@example.com
            Business Category: Creator
            Location: New York, USA
            """
            
            # Usar Claude agent para extrair dados
            result = await run_mcp(
                server_name="mcp.config.usrlocalmcp.Hyperbrowser",
                tool_name="claude_computer_use_agent",
                args={
                    "task": task,
                    "sessionOptions": {
                        "useProxy": True,
                        "useStealth": True,
                        "acceptCookies": True
                    }
                }
            )
            
            # Processar o resultado do Claude agent
            if result and "content" in result:
                content = result["content"]
                self.log_service.log_debug("Instagram profile data extracted with Claude agent", {"content": content})
                
                # Extrair dados usando regex
                extracted_data = {}
                
                # Extrair username
                username_match = re.search(r"Username:\s*([^\n]+)", content)
                if username_match:
                    extracted_data["username"] = username_match.group(1).strip()
                
                # Extrair nome
                name_match = re.search(r"Name:\s*([^\n]+)", content)
                if name_match:
                    extracted_data["name"] = name_match.group(1).strip()
                
                # Extrair bio
                bio_match = re.search(r"Bio:\s*([^\n]+)", content)
                if bio_match:
                    extracted_data["bio"] = bio_match.group(1).strip()
                
                # Extrair posts
                posts_match = re.search(r"Posts:\s*([^\n]+)", content)
                if posts_match:
                    extracted_data["posts"] = posts_match.group(1).strip()
                
                # Extrair seguidores
                followers_match = re.search(r"Followers:\s*([^\n]+)", content)
                if followers_match:
                    extracted_data["followers"] = followers_match.group(1).strip()
                
                # Extrair seguindo
                following_match = re.search(r"Following:\s*([^\n]+)", content)
                if following_match:
                    extracted_data["following"] = following_match.group(1).strip()
                
                # Extrair website
                website_match = re.search(r"Website:\s*([^\n]+)", content)
                if website_match:
                    extracted_data["website"] = website_match.group(1).strip()
                
                # Extrair email
                email_match = re.search(r"Email:\s*([^\n]+)", content)
                if email_match:
                    extracted_data["email"] = email_match.group(1).strip()
                
                # Extrair categoria de negócio
                category_match = re.search(r"Business Category:\s*([^\n]+)", content)
                if category_match:
                    extracted_data["business_category"] = category_match.group(1).strip()
                
                # Extrair localização
                location_match = re.search(r"Location:\s*([^\n]+)", content)
                if location_match:
                    extracted_data["location"] = location_match.group(1).strip()
                
                return extracted_data
            else:
                return {"error": "No data extracted from Claude agent"}
                
        except Exception as e:
            self.log_service.log_debug("Error in Claude agent extraction", {"error": str(e)})
            return {"error": f"Claude agent extraction failed: {str(e)}"}
    
    def _convert_to_int(self, value: str) -> Optional[int]:
        """Converte strings de números (ex: '1.2k', '3,400') para inteiros"""
        if not value:
            return None
            
        try:
            # Remover caracteres não numéricos, exceto pontos e vírgulas
            clean_value = re.sub(r'[^0-9.,]', '', value)
            
            # Converter abreviações como 'k', 'm', etc.
            if 'k' in value.lower() or 'mil' in value.lower():
                # Converter para milhares
                multiplier = 1000
                clean_value = clean_value.replace(',', '.')
            elif 'm' in value.lower() or 'mi' in value.lower() or 'milhões' in value.lower():
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
    
    def _extract_username_from_url(self, url_or_username: str) -> str:
        """Extrai o nome de usuário de diferentes formatos de URL do Instagram"""
        if not url_or_username:
            return ""
            
        # Padrão para URLs completas do Instagram
        instagram_url_pattern = r'(?:https?://)?(?:www\.)?instagram\.com/([\w\.]+)/?.*'
        match = re.match(instagram_url_pattern, url_or_username)
        
        if match:
            return match.group(1)
        
        # Se for apenas o nome de usuário com @ no início
        if url_or_username.startswith('@'):
            return url_or_username[1:]
        
        # Se for apenas o nome de usuário sem @
        return url_or_username