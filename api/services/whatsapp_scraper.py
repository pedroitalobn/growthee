from typing import Dict, Any, Optional, List, Union
import os
import re
import json
import logging
import asyncio
from urllib.parse import urlparse, parse_qs

from api.log_service import LogService
from api.mcp_client import run_mcp

class WhatsAppScraperService:
    """Serviço especializado para scraping de perfis do WhatsApp Business e links do WhatsApp"""
    
    def __init__(self, log_service: LogService = None):
        """Inicializa o serviço de scraping do WhatsApp"""
        self.log_service = log_service or LogService()
        self.base_patterns = {
            'wa_me': r'wa\.me/([0-9]+)',
            'whatsapp_api': r'api\.whatsapp\.com/send\?phone=([0-9]+)',
            'whatsapp_chat': r'chat\.whatsapp\.com/([a-zA-Z0-9]+)',
            'whatsapp_business': r'business\.whatsapp\.com/catalog/([0-9]+)'
        }
    
    def _normalize_whatsapp_url(self, url: str) -> str:
        """Normaliza URLs do WhatsApp para formato padrão"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Extrair número de telefone de diferentes formatos
        phone_number = None
        
        # wa.me/number
        wa_me_match = re.search(r'wa\.me/([0-9]+)', url)
        if wa_me_match:
            phone_number = wa_me_match.group(1)
        
        # api.whatsapp.com/send?phone=number
        api_match = re.search(r'phone=([0-9]+)', url)
        if api_match:
            phone_number = api_match.group(1)
        
        # Se encontrou número, normalizar para wa.me
        if phone_number:
            return f"https://wa.me/{phone_number}"
        
        return url
    
    def _extract_phone_from_url(self, url: str) -> Optional[str]:
        """Extrai número de telefone da URL do WhatsApp"""
        patterns = [
            r'wa\.me/([0-9]+)',
            r'phone=([0-9]+)',
            r'whatsapp://send\?phone=([0-9]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _is_business_number(self, phone: str) -> bool:
        """Verifica se o número parece ser de um WhatsApp Business"""
        # Números business geralmente têm certas características
        # Esta é uma heurística básica que pode ser melhorada
        return len(phone) >= 10 and not phone.startswith('1')
    
    async def _extract_with_hyperbrowser(self, url: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extrai dados usando Hyperbrowser com schema estruturado"""
        try:
            result = await run_mcp(
                server_name="mcp.config.usrlocalmcp.Hyperbrowser",
                tool_name="extract_structured_data",
                args={
                    "urls": [url],
                    "prompt": "Extract WhatsApp Business profile information including business name, phone number, description, category, and verification status",
                    "schema": schema
                }
            )
            
            if result and isinstance(result, dict) and 'data' in result:
                extracted_data = result['data']
                if isinstance(extracted_data, list) and len(extracted_data) > 0:
                    return extracted_data[0]
                elif isinstance(extracted_data, dict):
                    return extracted_data
            
            return {}
            
        except Exception as e:
            self.log_service.log_error(f"Erro no Hyperbrowser: {e}")
            return {}
    
    async def _scrape_with_firecrawl(self, url: str) -> Dict[str, Any]:
        """Scraping usando Firecrawl como fallback"""
        try:
            from api.firecrawl_client import FirecrawlApp
            
            firecrawl = FirecrawlApp()
            
            # Schema para extração de dados do WhatsApp Business
            schema = {
                "type": "object",
                "properties": {
                    "business_name": {"type": "string", "description": "Nome do negócio no WhatsApp Business"},
                    "phone": {"type": "string", "description": "Número de telefone do WhatsApp"},
                    "description": {"type": "string", "description": "Descrição do negócio"},
                    "category": {"type": "string", "description": "Categoria do negócio"},
                    "verified": {"type": "boolean", "description": "Se o perfil é verificado"},
                    "address": {"type": "string", "description": "Endereço do negócio"},
                    "website": {"type": "string", "description": "Website do negócio"},
                    "hours": {"type": "string", "description": "Horário de funcionamento"}
                }
            }
            
            result = firecrawl.scrape_url(
                url=url,
                params={
                    'formats': ['extract'],
                    'extract': {
                        'schema': schema,
                        'systemPrompt': 'Extract WhatsApp Business profile information accurately'
                    },
                    'onlyMainContent': True
                }
            )
            
            if result and 'extract' in result:
                return result['extract']
            
            return {}
            
        except Exception as e:
            self.log_service.log_error(f"Erro no Firecrawl: {e}")
            return {}
    
    async def _scrape_basic_data(self, url: str) -> Dict[str, Any]:
        """Scraping básico extraindo informações da URL"""
        try:
            phone = self._extract_phone_from_url(url)
            
            if phone:
                return {
                    "success": True,
                    "url": url,
                    "data": {
                        "phone": phone,
                        "is_business": self._is_business_number(phone),
                        "whatsapp_url": f"https://wa.me/{phone}"
                    },
                    "extraction_method": "basic_url_parsing"
                }
            
            return {
                "success": False,
                "error": "Não foi possível extrair número de telefone da URL",
                "url": url
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Erro no scraping básico: {str(e)}",
                "url": url
            }
    
    def _process_whatsapp_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa e normaliza dados extraídos do WhatsApp"""
        processed = {}
        
        # Mapear campos comuns
        field_mapping = {
            'business_name': ['business_name', 'name', 'title', 'businessName'],
            'phone': ['phone', 'phoneNumber', 'number', 'whatsapp'],
            'description': ['description', 'bio', 'about', 'desc'],
            'category': ['category', 'businessCategory', 'type'],
            'verified': ['verified', 'isVerified', 'business_verified'],
            'address': ['address', 'location', 'addr'],
            'website': ['website', 'url', 'link'],
            'hours': ['hours', 'businessHours', 'opening_hours']
        }
        
        for target_field, source_fields in field_mapping.items():
            for source_field in source_fields:
                if source_field in raw_data and raw_data[source_field]:
                    processed[target_field] = raw_data[source_field]
                    break
        
        # Normalizar telefone
        if 'phone' in processed:
            phone = re.sub(r'[^0-9]', '', str(processed['phone']))
            processed['phone'] = phone
            processed['whatsapp_url'] = f"https://wa.me/{phone}"
        
        # Determinar se é business
        if 'phone' in processed:
            processed['is_business'] = self._is_business_number(processed['phone'])
        
        return processed
    
    async def scrape_whatsapp_profile(self, url: str, use_hyperbrowser: bool = True) -> Dict[str, Any]:
        """Scraping completo de um perfil do WhatsApp/WhatsApp Business"""
        try:
            normalized_url = self._normalize_whatsapp_url(url)
            self.log_service.log_debug(f"Iniciando scraping do WhatsApp: {normalized_url}")
            
            if use_hyperbrowser:
                # Schema para extração estruturada
                whatsapp_schema = {
                    "type": "object",
                    "properties": {
                        "business_name": {"type": "string", "description": "Nome do negócio"},
                        "phone": {"type": "string", "description": "Número de telefone"},
                        "description": {"type": "string", "description": "Descrição do negócio"},
                        "category": {"type": "string", "description": "Categoria do negócio"},
                        "verified": {"type": "boolean", "description": "Status de verificação"},
                        "address": {"type": "string", "description": "Endereço"},
                        "website": {"type": "string", "description": "Website"},
                        "hours": {"type": "string", "description": "Horário de funcionamento"}
                    }
                }
                
                # Tentar com Hyperbrowser primeiro
                business_data = await self._extract_with_hyperbrowser(normalized_url, whatsapp_schema)
                
                if business_data and not business_data.get("error"):
                    processed_data = self._process_whatsapp_data(business_data)
                    
                    return {
                        "success": True,
                        "url": normalized_url,
                        "data": processed_data,
                        "extraction_method": "hyperbrowser"
                    }
            
            # Fallback: tentar com Firecrawl
            firecrawl_data = await self._scrape_with_firecrawl(normalized_url)
            if firecrawl_data:
                processed_data = self._process_whatsapp_data(firecrawl_data)
                
                return {
                    "success": True,
                    "url": normalized_url,
                    "data": processed_data,
                    "extraction_method": "firecrawl"
                }
            
            # Último recurso: scraping básico
            return await self._scrape_basic_data(normalized_url)
            
        except Exception as e:
            self.log_service.log_error(f"Erro no scraping do WhatsApp: {e}")
            return {
                "success": False,
                "error": f"Erro no scraping: {str(e)}",
                "url": url
            }
    
    async def search_whatsapp_business(self, business_name: str, location: str = None, use_hyperbrowser: bool = True) -> Dict[str, Any]:
        """Busca por WhatsApp Business usando nome do negócio"""
        try:
            # Construir query de busca
            query = f"{business_name} WhatsApp Business"
            if location:
                query += f" {location}"
            
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            
            self.log_service.log_debug(f"Buscando WhatsApp Business: {query}")
            
            if use_hyperbrowser:
                # Schema para busca
                search_schema = {
                    "type": "object",
                    "properties": {
                        "whatsapp_links": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Links do WhatsApp encontrados"
                        },
                        "business_info": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "phone": {"type": "string"},
                                "address": {"type": "string"}
                            }
                        }
                    }
                }
                
                search_data = await self._extract_with_hyperbrowser(search_url, search_schema)
                
                if search_data and search_data.get("whatsapp_links"):
                    # Pegar o primeiro link válido
                    for link in search_data["whatsapp_links"]:
                        if 'wa.me' in link or 'whatsapp.com' in link:
                            # Fazer scraping do perfil encontrado
                            profile_data = await self.scrape_whatsapp_profile(link, use_hyperbrowser)
                            if profile_data.get("success"):
                                return profile_data
            
            return {
                "success": False,
                "error": "Nenhum WhatsApp Business encontrado para esta busca",
                "query": query
            }
            
        except Exception as e:
            self.log_service.log_error(f"Erro na busca do WhatsApp Business: {e}")
            return {
                "success": False,
                "error": f"Erro na busca: {str(e)}",
                "query": business_name
            }
    
    def validate_whatsapp_url(self, url: str) -> bool:
        """Valida se a URL é um link válido do WhatsApp"""
        whatsapp_patterns = [
            r'wa\.me/[0-9]+',
            r'api\.whatsapp\.com/send\?phone=[0-9]+',
            r'chat\.whatsapp\.com/[a-zA-Z0-9]+',
            r'whatsapp://send\?phone=[0-9]+'
        ]
        
        for pattern in whatsapp_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        return False