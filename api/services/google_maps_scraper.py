import asyncio
import json
import re
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, parse_qs
from ..log_service import LogService

class GoogleMapsScraperService:
    """Serviço para scraping de dados de empresas do Google Maps"""
    
    def __init__(self, log_service: LogService):
        self.log_service = log_service
    
    def _normalize_google_maps_url(self, url: str) -> str:
        """Normaliza URLs do Google Maps para garantir formato consistente"""
        try:
            # Se for uma URL encurtada do Google Maps
            if 'maps.app.goo.gl' in url or 'goo.gl/maps' in url:
                return url
            
            # Se for uma URL completa do Google Maps
            if 'google.com/maps' in url or 'maps.google.com' in url:
                return url
            
            # Se for apenas o nome da empresa, criar uma URL de busca
            if not url.startswith('http'):
                return f"https://www.google.com/maps/search/{url.replace(' ', '+')}"
            
            return url
        except Exception as e:
            self.log_service.log_error(f"Erro ao normalizar URL do Google Maps: {e}")
            return url
    
    def _extract_place_id_from_url(self, url: str) -> Optional[str]:
        """Extrai o Place ID do Google Maps da URL"""
        try:
            # Padrões para extrair Place ID
            patterns = [
                r'place/[^/]+/data=.*?1s([^!]+)',
                r'data=.*?1s([^!]+)',
                r'place_id:([^&]+)',
                r'ftid=([^&]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            return None
        except Exception as e:
            self.log_service.log_error(f"Erro ao extrair Place ID: {e}")
            return None
    
    async def scrape_google_maps_business(self, url: str, use_hyperbrowser: bool = True) -> Dict[str, Any]:
        """Scraping principal de dados de empresas do Google Maps"""
        try:
            normalized_url = self._normalize_google_maps_url(url)
            self.log_service.log_debug(f"Iniciando scraping do Google Maps: {normalized_url}")
            
            if use_hyperbrowser:
                return await self._scrape_with_hyperbrowser(normalized_url)
            else:
                return await self._scrape_with_firecrawl(normalized_url)
                
        except Exception as e:
            self.log_service.log_error(f"Erro no scraping do Google Maps: {e}")
            return {
                "success": False,
                "error": f"Erro no scraping: {str(e)}",
                "url": url
            }
    
    async def _scrape_with_hyperbrowser(self, url: str) -> Dict[str, Any]:
        """Scraping usando Hyperbrowser para maior precisão"""
        try:
            from api.mcp_client import run_mcp
            
            # Schema para extração de dados do Google Maps
            extraction_schema = {
                "type": "object",
                "properties": {
                    "business_name": {"type": "string", "description": "Nome da empresa/negócio"},
                    "rating": {"type": "string", "description": "Avaliação/rating (ex: 4.5)"},
                    "total_reviews": {"type": "string", "description": "Número total de avaliações"},
                    "address": {"type": "string", "description": "Endereço completo"},
                    "phone": {"type": "string", "description": "Número de telefone"},
                    "website": {"type": "string", "description": "Website da empresa"},
                    "business_hours": {"type": "string", "description": "Horário de funcionamento"},
                    "business_type": {"type": "string", "description": "Tipo de negócio/categoria"},
                    "price_range": {"type": "string", "description": "Faixa de preço ($ $$ $$$ $$$$)"},
                    "description": {"type": "string", "description": "Descrição do negócio"},
                    "amenities": {"type": "array", "items": {"type": "string"}, "description": "Comodidades/serviços oferecidos"},
                    "popular_times": {"type": "string", "description": "Horários de maior movimento"},
                    "coordinates": {"type": "string", "description": "Coordenadas GPS (latitude, longitude)"},
                    "place_id": {"type": "string", "description": "Google Place ID"},
                    "photos_count": {"type": "string", "description": "Número de fotos disponíveis"}
                }
            }
            
            # Usar Hyperbrowser para extrair dados estruturados
            self.log_service.log_debug("Extraindo dados do Google Maps com Hyperbrowser", {"url": url})
            
            extract_result = await run_mcp(
                server_name="mcp.config.usrlocalmcp.Hyperbrowser",
                tool_name="extract_structured_data",
                args={
                    "urls": [url],
                    "prompt": "Extraia todas as informações disponíveis sobre esta empresa no Google Maps, incluindo nome, avaliações, endereço, telefone, website, horários, tipo de negócio, faixa de preço, descrição, comodidades e coordenadas GPS.",
                    "schema": extraction_schema
                }
            )
            
            if extract_result and not extract_result.get("error"):
                extracted_data = extract_result.get("data", {})
                if isinstance(extracted_data, list) and len(extracted_data) > 0:
                    business_data = extracted_data[0]
                    
                    # Processar e limpar dados
                    processed_data = self._process_business_data(business_data)
                    
                    return {
                        "success": True,
                        "url": url,
                        "data": processed_data,
                        "extraction_method": "hyperbrowser"
                    }
            
            # Fallback: tentar scraping básico
            return await self._scrape_basic_data(url)
            
        except Exception as e:
            self.log_service.log_error(f"Erro no Hyperbrowser: {e}")
            return await self._scrape_basic_data(url)
    
    async def _scrape_with_firecrawl(self, url: str) -> Dict[str, Any]:
        """Scraping usando Firecrawl como alternativa"""
        try:
            from api.firecrawl_client import FirecrawlApp
            
            firecrawl = FirecrawlApp()
            
            # Schema para Firecrawl
            schema = {
                "type": "object",
                "properties": {
                    "businessName": {"type": "string"},
                    "rating": {"type": "string"},
                    "totalReviews": {"type": "string"},
                    "address": {"type": "string"},
                    "phone": {"type": "string"},
                    "website": {"type": "string"},
                    "businessHours": {"type": "string"},
                    "businessType": {"type": "string"},
                    "priceRange": {"type": "string"},
                    "description": {"type": "string"}
                }
            }
            
            result = firecrawl.extract_structured_data(
                url=url,
                schema=schema,
                prompt="Extraia informações detalhadas sobre esta empresa do Google Maps incluindo nome, avaliações, endereço, telefone, website, horários e tipo de negócio."
            )
            
            if result and not result.get("error"):
                return {
                    "success": True,
                    "url": url,
                    "data": result,
                    "extraction_method": "firecrawl"
                }
            
            return await self._scrape_basic_data(url)
            
        except Exception as e:
            self.log_service.log_error(f"Erro no Firecrawl: {e}")
            return await self._scrape_basic_data(url)
    
    async def _scrape_basic_data(self, url: str) -> Dict[str, Any]:
        """Scraping básico usando Hyperbrowser sem schema estruturado"""
        try:
            from api.mcp_client import run_mcp
            
            # Scraping básico da página
            scrape_result = await run_mcp(
                server_name="mcp.config.usrlocalmcp.Hyperbrowser",
                tool_name="scrape_webpage",
                args={
                    "url": url,
                    "outputFormat": ["markdown", "html"]
                }
            )
            
            if scrape_result and not scrape_result.get("error"):
                content = scrape_result.get("markdown", "")
                html = scrape_result.get("html", "")
                
                # Extrair dados básicos usando regex
                basic_data = self._extract_basic_info_from_content(content, html)
                
                return {
                    "success": True,
                    "url": url,
                    "data": basic_data,
                    "extraction_method": "basic_scraping",
                    "raw_content": content[:1000]  # Primeiros 1000 caracteres para debug
                }
            
            return {
                "success": False,
                "error": "Falha ao extrair dados básicos",
                "url": url
            }
            
        except Exception as e:
            self.log_service.log_error(f"Erro no scraping básico: {e}")
            return {
                "success": False,
                "error": f"Erro no scraping básico: {str(e)}",
                "url": url
            }
    
    def _process_business_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa e limpa os dados extraídos da empresa"""
        processed = {}
        
        # Mapeamento de campos
        field_mapping = {
            'business_name': 'name',
            'rating': 'rating',
            'total_reviews': 'reviews_count',
            'address': 'address',
            'phone': 'phone',
            'website': 'website',
            'business_hours': 'hours',
            'business_type': 'category',
            'price_range': 'price_level',
            'description': 'description',
            'amenities': 'amenities',
            'popular_times': 'popular_times',
            'coordinates': 'coordinates',
            'place_id': 'place_id',
            'photos_count': 'photos_count'
        }
        
        for original_key, new_key in field_mapping.items():
            if original_key in data and data[original_key]:
                value = data[original_key]
                
                # Limpeza específica por tipo de campo
                if original_key == 'rating':
                    processed[new_key] = self._extract_rating(str(value))
                elif original_key == 'total_reviews':
                    processed[new_key] = self._extract_number(str(value))
                elif original_key == 'phone':
                    processed[new_key] = self._clean_phone(str(value))
                elif original_key == 'website':
                    processed[new_key] = self._clean_url(str(value))
                else:
                    processed[new_key] = str(value).strip()
        
        return processed
    
    def _extract_basic_info_from_content(self, content: str, html: str) -> Dict[str, Any]:
        """Extrai informações básicas usando regex do conteúdo"""
        data = {}
        
        # Padrões regex para extração
        patterns = {
            'name': r'<h1[^>]*>([^<]+)</h1>',
            'rating': r'(\d+[.,]\d+)\s*(?:stars?|estrelas?)',
            'reviews': r'(\d+(?:[.,]\d+)?)\s*(?:reviews?|avaliações?)',
            'phone': r'(?:tel:|phone:|telefone:)?\s*([+]?[\d\s\(\)\-\.]{10,})',
            'address': r'(?:address:|endereço:)?\s*([^\n]{20,100})',
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                data[field] = match.group(1).strip()
        
        return data
    
    def _extract_rating(self, text: str) -> Optional[float]:
        """Extrai rating numérico do texto"""
        try:
            match = re.search(r'(\d+[.,]\d+)', text)
            if match:
                return float(match.group(1).replace(',', '.'))
            return None
        except:
            return None
    
    def _extract_number(self, text: str) -> Optional[int]:
        """Extrai número inteiro do texto"""
        try:
            # Remove caracteres não numéricos exceto vírgulas e pontos
            clean_text = re.sub(r'[^\d.,]', '', text)
            # Remove pontos que são separadores de milhares
            clean_text = clean_text.replace('.', '').replace(',', '')
            return int(clean_text) if clean_text else None
        except:
            return None
    
    def _clean_phone(self, phone: str) -> str:
        """Limpa e formata número de telefone"""
        # Remove caracteres especiais exceto números, +, (, ), -, espaços
        cleaned = re.sub(r'[^\d+\(\)\-\s]', '', phone)
        return cleaned.strip()
    
    def _clean_url(self, url: str) -> str:
        """Limpa e valida URL"""
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
    
    async def search_business_by_name(self, business_name: str, location: str = "") -> Dict[str, Any]:
        """Busca empresa por nome no Google Maps"""
        try:
            # Construir URL de busca
            query = business_name
            if location:
                query += f" {location}"
            
            search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
            
            return await self.scrape_google_maps_business(search_url)
            
        except Exception as e:
            self.log_service.log_error(f"Erro na busca por nome: {e}")
            return {
                "success": False,
                "error": f"Erro na busca: {str(e)}",
                "query": business_name
            }