import os
import httpx
import asyncio
from typing import Dict, List, Optional, Any
import re
from urllib.parse import urlparse
from ..log_service import LogService

class BraveSearchService:
    """Serviço para buscar informações de empresas usando Brave Search API"""
    
    def __init__(self, log_service: LogService):
        self.log_service = log_service
        self.api_key = os.getenv('BRAVE_SEARCH_API_KEY')
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        
        # Debug da chave da API
        if self.api_key:
            self.log_service.log_debug(f"Brave Search API Key carregada: {self.api_key[:10]}...")
        else:
            self.log_service.log_error("BRAVE_SEARCH_API_KEY não encontrada. Busca externa desabilitada.")
    
    async def search_company_linkedin(self, domain: str, company_name: str = None) -> Optional[str]:
        """Busca o LinkedIn da empresa usando Brave Search"""
        if not self.api_key:
            return None
            
        try:
            # Construir query de busca
            queries = [
                f"site:linkedin.com/company {domain}",
                f"site:linkedin.com/company {company_name}" if company_name else None,
                f"linkedin {domain} empresa",
                f"linkedin {company_name}" if company_name else None
            ]
            
            # Filtrar queries None
            queries = [q for q in queries if q]
            
            for query in queries:
                linkedin_url = await self._search_query(query)
                if linkedin_url:
                    self.log_service.log_info(f"LinkedIn encontrado via busca: {linkedin_url}")
                    return linkedin_url
                    
                # Aguardar entre buscas para evitar rate limiting
                await asyncio.sleep(1)
            
            return None
            
        except Exception as e:
            self.log_service.log_error(f"Erro na busca do LinkedIn: {str(e)}")
            return None
    
    async def search_company_social_media(self, domain: str, company_name: str = None) -> Dict[str, List[str]]:
        """Busca todas as redes sociais da empresa usando Brave Search"""
        if not self.api_key:
            return {}
            
        try:
            social_results = {
                'linkedin': [],
                'facebook': [],
                'instagram': [],
                'youtube': [],
                'twitter': []
            }
            
            # Queries específicas para cada rede social
            social_queries = {
                'linkedin': [
                    f"site:linkedin.com/company {domain}",
                    f"site:linkedin.com/company {company_name}" if company_name else None
                ],
                'facebook': [
                    f"site:facebook.com {domain}",
                    f"site:facebook.com {company_name}" if company_name else None
                ],
                'instagram': [
                    f"site:instagram.com {domain}",
                    f"site:instagram.com {company_name}" if company_name else None
                ],
                'youtube': [
                    f"site:youtube.com {domain}",
                    f"site:youtube.com {company_name}" if company_name else None
                ],
                'twitter': [
                    f"site:twitter.com {domain}",
                    f"site:x.com {domain}",
                    f"site:twitter.com {company_name}" if company_name else None
                ]
            }
            
            for platform, queries in social_queries.items():
                # Filtrar queries None
                queries = [q for q in queries if q]
                
                for query in queries:
                    results = await self._search_multiple_results(query, platform)
                    if results:
                        social_results[platform].extend(results)
                        
                    # Aguardar entre buscas
                    await asyncio.sleep(0.5)
            
            # Remover duplicatas
            for platform in social_results:
                social_results[platform] = list(set(social_results[platform]))
            
            return social_results
            
        except Exception as e:
            self.log_service.log_error(f"Erro na busca de redes sociais: {str(e)}")
            return {}
    
    async def _search_query(self, query: str) -> Optional[str]:
        """Executa uma busca e retorna o primeiro resultado relevante"""
        try:
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.api_key
            }
            
            params = {
                "q": query,
                "count": 5,
                "offset": 0,
                "mkt": "pt-BR",
                "safesearch": "moderate",
                "freshness": "pw",  # Past week
                "text_decorations": False,
                "spellcheck": True
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, headers=headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                if 'web' in data and 'results' in data['web']:
                    for result in data['web']['results']:
                        url = result.get('url', '')
                        if self._is_valid_linkedin_url(url):
                            return url
                
                return None
                
        except Exception as e:
            self.log_service.log_error(f"Erro na busca '{query}': {str(e)}")
            return None
    
    async def _search_multiple_results(self, query: str, platform: str) -> List[str]:
        """Executa uma busca e retorna múltiplos resultados relevantes"""
        try:
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.api_key
            }
            
            params = {
                "q": query,
                "count": 10,
                "offset": 0,
                "mkt": "pt-BR",
                "safesearch": "moderate",
                "text_decorations": False,
                "spellcheck": True
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, headers=headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                results = []
                
                if 'web' in data and 'results' in data['web']:
                    for result in data['web']['results']:
                        url = result.get('url', '')
                        if self._is_valid_social_url(url, platform):
                            results.append(url)
                
                return results
                
        except Exception as e:
            self.log_service.log_error(f"Erro na busca múltipla '{query}': {str(e)}")
            return []
    
    def _is_valid_linkedin_url(self, url: str) -> bool:
        """Verifica se a URL é um LinkedIn válido de empresa"""
        if not url:
            return False
            
        linkedin_patterns = [
            r'linkedin\.com/company/[^/]+/?$',
            r'linkedin\.com/company/[^/]+/about/?$',
            r'linkedin\.com/company/[^/]+/posts/?$'
        ]
        
        for pattern in linkedin_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        return False
    
    def _is_valid_social_url(self, url: str, platform: str) -> bool:
        """Verifica se a URL é válida para a plataforma especificada"""
        if not url:
            return False
            
        platform_patterns = {
            'linkedin': [r'linkedin\.com/company/[^/]+'],
            'facebook': [r'facebook\.com/[^/]+', r'fb\.com/[^/]+'],
            'instagram': [r'instagram\.com/[^/]+'],
            'youtube': [r'youtube\.com/channel/[^/]+', r'youtube\.com/c/[^/]+', r'youtube\.com/@[^/]+'],
            'twitter': [r'twitter\.com/[^/]+', r'x\.com/[^/]+']
        }
        
        if platform not in platform_patterns:
            return False
            
        for pattern in platform_patterns[platform]:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        return False
    
    async def search_company_by_name_location(self, company_name: str, region: str = None, country: str = None) -> Dict[str, Any]:
        """Busca informações da empresa apenas por nome e localização"""
        if not self.api_key:
            return {}
            
        try:
            # Construir queries baseadas em nome e localização
            queries = []
            
            # Query básica com nome da empresa
            base_query = f'"{company_name}" empresa'
            
            # Adicionar localização se fornecida
            if region and country:
                queries.extend([
                    f'"{company_name}" empresa {region} {country}',
                    f'"{company_name}" {region} {country} linkedin',
                    f'"{company_name}" {region} {country} site:linkedin.com/company',
                    f'"{company_name}" {region} {country} contato'
                ])
            elif country:
                queries.extend([
                    f'"{company_name}" empresa {country}',
                    f'"{company_name}" {country} linkedin',
                    f'"{company_name}" {country} site:linkedin.com/company'
                ])
            elif region:
                queries.extend([
                    f'"{company_name}" empresa {region}',
                    f'"{company_name}" {region} linkedin'
                ])
            else:
                queries.append(base_query)
            
            # Adicionar queries específicas para LinkedIn
            queries.extend([
                f'site:linkedin.com/company "{company_name}"',
                f'"{company_name}" linkedin empresa'
            ])
            
            company_info = {
                'company_name': company_name,
                'region': region,
                'country': country,
                'linkedin_url': None,
                'descriptions': [],
                'contact_info': {},
                'addresses': [],
                'social_media': {},
                'website': None,
                'additional_info': []
            }
            
            for query in queries:
                results = await self._search_company_details(query)
                if results:
                    for result in results:
                        # Verificar se é LinkedIn
                        if 'linkedin.com/company' in result.get('url', ''):
                            if not company_info['linkedin_url']:
                                company_info['linkedin_url'] = result['url']
                        
                        # Categorizar resultados
                        if 'linkedin' in query.lower():
                            if 'linkedin_url' not in company_info or not company_info['linkedin_url']:
                                company_info['linkedin_url'] = result.get('url')
                        elif 'contato' in query.lower():
                            if 'results' not in company_info['contact_info']:
                                company_info['contact_info']['results'] = []
                            company_info['contact_info']['results'].append(result)
                        elif 'endereço' in query.lower() or 'localização' in query.lower():
                            company_info['addresses'].append(result)
                        else:
                            company_info['descriptions'].append(result)
                            
                await asyncio.sleep(0.5)
            
            return company_info
            
        except Exception as e:
            self.log_service.log_error(f"Erro na busca da empresa por nome e localização: {str(e)}")
            return {}

    async def search_company_info(self, domain: str, company_name: str = None) -> Dict[str, Any]:
        """Busca informações gerais da empresa"""
        if not self.api_key:
            return {}
            
        try:
            queries = [
                f"{domain} empresa sobre",
                f"{company_name} empresa" if company_name else None,
                f"{domain} contato telefone",
                f"{domain} endereço localização"
            ]
            
            # Filtrar queries None
            queries = [q for q in queries if q]
            
            company_info = {
                'descriptions': [],
                'contact_info': {},
                'addresses': [],
                'additional_info': []
            }
            
            for query in queries:
                results = await self._search_company_details(query)
                if results:
                    if 'sobre' in query or 'empresa' in query:
                        company_info['descriptions'].extend(results)
                    elif 'contato' in query or 'telefone' in query:
                        if 'results' not in company_info['contact_info']:
                            company_info['contact_info']['results'] = []
                        company_info['contact_info']['results'].extend(results)
                    elif 'endereço' in query or 'localização' in query:
                        company_info['addresses'].extend(results)
                    else:
                        company_info['additional_info'].extend(results)
                        
                await asyncio.sleep(0.5)
            
            return company_info
            
        except Exception as e:
            self.log_service.log_error(f"Erro na busca de informações da empresa: {str(e)}")
            return {}
    
    async def _search_company_details(self, query: str) -> List[str]:
        """Busca detalhes específicos da empresa"""
        try:
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.api_key
            }
            
            params = {
                "q": query,
                "count": 5,
                "offset": 0,
                "mkt": "pt-BR",
                "safesearch": "moderate",
                "text_decorations": False,
                "spellcheck": True
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, headers=headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                results = []
                
                if 'web' in data and 'results' in data['web']:
                    for result in data['web']['results']:
                        title = result.get('title', '')
                        description = result.get('description', '')
                        url = result.get('url', '')
                        
                        if title and description:
                            results.append({
                                'title': title,
                                'description': description,
                                'url': url
                            })
                
                return results
                
        except Exception as e:
            self.log_service.log_error(f"Erro na busca de detalhes '{query}': {str(e)}")
            return []